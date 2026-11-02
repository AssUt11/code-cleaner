#!/usr/bin/env python3
"""Conservative unused-import and definition candidates, never automatic deletions."""

import argparse
import ast
from collections import Counter
from pathlib import Path
import re
import sys
import symtable

sys.dont_write_bytecode = True

from _common import (add_common_arguments, diagnostic, finding, mask_js,
                     print_report, read_source, require_root, walk_files)

IDENTIFIER = r"[A-Za-z_$][\w$]*"


def _python_references(table):
    """Resolve symbol-table references to their binding scope, including closures."""
    referenced = set()

    def visit(current, parents, key):
        for symbol in current.get_symbols():
            if not symbol.is_referenced():
                continue
            owner = key
            if symbol.is_global() and parents:
                owner = ()
            elif symbol.is_free():
                for parent, parent_key in reversed(parents):
                    try:
                        binding = parent.lookup(symbol.get_name())
                    except KeyError:
                        continue
                    if binding.is_local() and str(parent.get_type()) not in ("class", "SymbolTableType.CLASS"):
                        owner = parent_key
                        break
            referenced.add((owner, symbol.get_name()))
        for child in current.get_children():
            visit(child, parents + [(current, key)], key + ((child.get_name(), child.get_lineno()),))

    visit(table, [], ())
    return referenced


def analyze_python(file_path, source=None):
    source = read_source(file_path) if source is None else source
    if source is None:
        return None
    tree = ast.parse(source, filename=str(file_path))
    tables = symtable.symtable(source, str(file_path), "exec")
    referenced = _python_references(tables)
    exported = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
                try:
                    value = ast.literal_eval(node.value)
                    if isinstance(value, (list, tuple, set)):
                        exported.update(item for item in value if isinstance(item, str))
                except (ValueError, TypeError):
                    pass

    imports = []
    class ImportVisitor(ast.NodeVisitor):
        scope = ()

        def visit_FunctionDef(self, node):
            previous = self.scope
            self.scope += ((node.name, node.lineno),)
            for child in node.body:
                self.visit(child)
            self.scope = previous

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef

        def visit_Import(self, node):
            for alias in node.names:
                imports.append((alias.asname or alias.name.split(".")[0], alias.name, node.lineno, self.scope, False))

        def visit_ImportFrom(self, node):
            if node.module == "__future__":
                return
            for alias in node.names:
                if alias.name != "*":
                    imports.append((alias.asname or alias.name, alias.name, node.lineno, self.scope, alias.asname == alias.name))

    ImportVisitor().visit(tree)
    # Quoted/future annotations are meaningful references even when the compiler
    # does not evaluate them. Prefer suppressing a candidate over deleting a type.
    annotation_names = set()
    for node in ast.walk(tree):
        annotations = []
        if isinstance(node, ast.arg) and node.annotation is not None:
            annotations.append(node.annotation)
        elif isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
            annotations.append(node.returns)
        for annotation in annotations:
            for part in ast.walk(annotation):
                if isinstance(part, ast.Name):
                    annotation_names.add(part.id)
                elif isinstance(part, ast.Constant) and isinstance(part.value, str):
                    annotation_names.update(re.findall(IDENTIFIER, part.value))
    unused = [
        (name, original, line) for name, original, line, scope, explicit_export in imports
        if (scope, name) not in referenced and not explicit_export
        and name not in annotation_names
        and not (not scope and (name in exported or Path(file_path).name == "__init__.py"))
    ]
    # Methods, nested and decorated functions may be registered or called dynamically.
    defined = {
        node.name: node.lineno for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name not in exported and not node.decorator_list
        and not (node.name.startswith("__") and node.name.endswith("__"))
        and not (
            (Path(file_path).name.startswith("test_") or Path(file_path).name.endswith("_test.py") or Path(file_path).name == "conftest.py")
            and (isinstance(node, ast.ClassDef) or node.name.startswith("test_"))
        )
    }
    references = {name for scope, name in referenced if not scope}
    references.update(node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute))
    references.update(original.split(".")[-1] for _, original, _, _, _ in imports)
    return {"defined": defined, "imports": unused, "references": references}


def analyze_regex_based(file_path, source=None):
    source = read_source(file_path) if source is None else source
    if source is None:
        return None
    clean = mask_js(source, strings=False)
    masked = mask_js(source)
    imports = []
    import_spans = []
    if Path(file_path).suffix.lower() == ".java":
        pattern = r"\bimport\s+(?:static\s+)?([\w.]+(?:\*)?)\s*;"
        for match in re.finditer(pattern, clean):
            if masked[match.start():match.start() + 6] != "import":
                continue
            original = match.group(1)
            if not original.endswith("*"):
                imports.append((original.split(".")[-1], original, clean.count("\n", 0, match.start()) + 1))
            import_spans.append(match.span())
    else:
        pattern = r"\bimport\s+(?!['\"])([\s\S]*?)\s+from\s*(['\"])[^'\"]+\2"
        for match in re.finditer(pattern, clean):
            if masked[match.start():match.start() + 6] != "import":
                continue
            clause = re.sub(r"^type\s+", "", match.group(1).strip())
            line = clean.count("\n", 0, match.start()) + 1
            names = []
            default = re.match(IDENTIFIER, clause)
            if default:
                names.append(default.group())
            namespace = re.search(r"\*\s+as\s+(" + IDENTIFIER + ")", clause)
            if namespace:
                names.append(namespace.group(1))
            named = re.search(r"\{([^}]*)\}", clause)
            if named:
                for part in named.group(1).split(","):
                    part = re.sub(r"^\s*type\s+", "", part.strip())
                    local = re.split(r"\s+as\s+", part)[-1].strip()
                    if re.fullmatch(IDENTIFIER, local):
                        names.append(local)
            imports.extend((name, name, line) for name in names)
            import_spans.append(match.span())
    characters = list(masked)
    for start, end in import_spans:
        characters[start:end] = ["\n" if char == "\n" else " " for char in characters[start:end]]
    body = "".join(characters)
    counts = Counter(re.findall(IDENTIFIER, body))
    for literal in re.finditer(r"`(?:\\[\s\S]|[^`\\])*`", clean):
        for expression in re.finditer(r"\$\{([\s\S]*?)\}", literal.group()):
            counts.update(re.findall(IDENTIFIER, expression.group(1)))
    defined = {}
    pattern = r"\b(?:function|class|interface|enum|record)\s+(" + IDENTIFIER + r")|\b(?:const|let|var)\s+(" + IDENTIFIER + r")\s*=\s*(?:async\s*)?(?:\([^)]*\)|" + IDENTIFIER + r")\s*=>"
    for match in re.finditer(pattern, body):
        name = match.group(1) or match.group(2)
        counts[name] -= 1
        prefix = body[max(0, match.start() - 40):match.start()]
        if not re.search(r"\bexport\s+(?:default\s+)?(?:async\s+)?$", prefix):
            defined[name] = body.count("\n", 0, match.start()) + 1
    exported = set()
    for match in re.finditer(r"\bexport\s*\{([^}]*)\}", body):
        for part in match.group(1).split(","):
            exported.add(re.split(r"\s+as\s+", part.strip())[0])
    defined = {name: line for name, line in defined.items() if name not in exported}
    unused = [item for item in imports if counts[item[0]] <= 0]
    return {"defined": defined, "imports": unused,
            "references": {name for name, count in counts.items() if count > 0} | exported}


def analyze(root, exclude=(), diagnostics=None):
    root = Path(root).resolve()
    per_file = {}
    references = set()
    for path in walk_files(root, exclude, diagnostics):
        source = read_source(path, diagnostics)
        if source is None:
            continue
        try:
            info = analyze_python(path, source) if path.suffix.lower() == ".py" else analyze_regex_based(path, source)
        except (SyntaxError, ValueError, RecursionError) as error:
            diagnostic(diagnostics, path.relative_to(root), f"Dead-code analysis skipped: {error}")
            continue
        if info is not None:
            per_file[path] = info
            references.update(info["references"])
    findings = []
    for path, info in per_file.items():
        relative = path.relative_to(root).as_posix()
        for name, original, line in info["imports"]:
            findings.append(finding("dead.import", "疑似未使用的 import", relative, line,
                                    f"'{original}' 的绑定 '{name}' 在当前作用域未发现使用",
                                    "确认副作用、注册行为、导出和类型注解后再删除。", "info"))
        for name, line in info["defined"].items():
            if name not in references:
                findings.append(finding("dead.definition", "疑似未使用的定义", relative, line,
                                        f"符号 '{name}' 未发现静态引用",
                                        "确认公开 API、框架入口和动态调用后再删除。", confidence="low"))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_arguments(parser)
    args = parser.parse_args()
    require_root(parser, args.root)
    diagnostics = []
    print_report(args.root, analyze(args.root, args.exclude, diagnostics), diagnostics)


if __name__ == "__main__":
    main()
