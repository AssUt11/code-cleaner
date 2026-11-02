"""Shared traversal, diagnostics and output. Python 3.10+, standard library only."""

import fnmatch
import io
import json
import os
from pathlib import Path
import re
import tokenize

VERSION = "1.1.0"
SOURCE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".mjs", ".cjs"}
SKIP_DIRS = {
    "node_modules", "vendor", "bower_components", ".venv", "venv", "env",
    "__pycache__", ".git", ".svn", ".hg", ".idea", ".vscode", "dist",
    "build", "out", "target", "coverage", ".workbuddy",
}
SEVERITIES = {"error": 0, "warning": 1, "info": 2}
JS_LITERALS = re.compile(
    r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|'
    r"'(?:\\[\s\S]|[^'\\])*'|`(?:\\[\s\S]|[^`\\])*`"
)


def diagnostic(items, path, message):
    if items is not None:
        items.append({"path": str(path), "message": str(message)})


def read_source(path, diagnostics=None):
    try:
        if Path(path).suffix.lower() == ".py":
            with tokenize.open(path) as handle:
                return handle.read()
        return Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError, SyntaxError, LookupError) as error:
        diagnostic(diagnostics, path, f"Cannot read source: {error}")
        return None


def excluded(relative, patterns):
    parts = relative.replace("\\", "/").split("/")
    prefixes = ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
    for pattern in patterns:
        pattern = pattern.replace("\\", "/").strip().rstrip("/")
        if pattern and any(fnmatch.fnmatchcase(item, pattern) for item in prefixes):
            return True
    return False


def ignore_patterns(root, extra=(), diagnostics=None):
    patterns = list(extra)
    ignore = Path(root) / ".codecleanerignore"
    if ignore.is_file():
        try:
            patterns.extend(
                line.strip() for line in ignore.read_text(encoding="utf-8-sig").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
        except (OSError, UnicodeError) as error:
            diagnostic(diagnostics, ignore, error)
    return patterns


def walk_files(root, exclude=(), diagnostics=None):
    """Never follow symlinks/junctions or scan dependency/project-data directories."""
    root = Path(root).resolve()
    if root.name in SKIP_DIRS or ".workbuddy" in root.parts:
        diagnostic(diagnostics, root, "Refusing to scan a protected/dependency directory as the root")
        return
    patterns = ignore_patterns(root, exclude, diagnostics)
    for directory, names, files in os.walk(
        root, followlinks=False,
        onerror=lambda error: diagnostic(diagnostics, error.filename, error),
    ):
        parent = Path(directory)
        kept = []
        for name in sorted(names):
            path = parent / name
            if name in SKIP_DIRS or name.startswith("."):
                continue
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                continue
            if not path.resolve().is_relative_to(root):
                continue
            if not excluded(path.relative_to(root).as_posix(), patterns):
                kept.append(name)
        names[:] = kept
        for name in sorted(files):
            path = parent / name
            if path.suffix.lower() not in SOURCE_EXTS or path.is_symlink():
                continue
            if path.resolve().is_relative_to(root) and not excluded(path.relative_to(root).as_posix(), patterns):
                yield path


def mask_js(source, strings=True):
    """Preserve offsets/newlines; quoted URLs must not become line comments."""
    def replace(match):
        value = match.group()
        if not strings and not value.startswith(("//", "/*")):
            return value
        return "".join("\n" if char == "\n" else " " for char in value)
    return JS_LITERALS.sub(replace, source)


def normalized_lines(source, extension):
    """Return (original line number, normalized code) without comments/blank lines."""
    if extension == ".py":
        lines = {}
        skip = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                tokenize.DEDENT, tokenize.ENDMARKER, tokenize.ENCODING}
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type in skip:
                continue
            value = "STR" if token.type == tokenize.STRING else "NUM" if token.type == tokenize.NUMBER else token.string
            lines.setdefault(token.start[0], []).append(value)
        return [(line, " ".join(tokens)) for line, tokens in sorted(lines.items()) if tokens]

    def replace(match):
        value = match.group()
        if value.startswith(("//", "/*")):
            return "".join("\n" if char == "\n" else " " for char in value)
        return " STR " + "\n" * value.count("\n")

    cleaned = JS_LITERALS.sub(replace, source)
    result = []
    for number, line in enumerate(cleaned.splitlines(), 1):
        tokens = re.findall(r"[A-Za-z_$][\w$]*|\d+(?:\.\d+)?|[^\s]", line)
        normalized = " ".join("NUM" if token[0].isdigit() else token for token in tokens)
        if normalized and any(char.isalnum() for char in normalized):
            result.append((number, normalized))
    return result


def finding(rule, kind, path, line, detail, suggestion, severity="warning", confidence="medium", **extra):
    return dict(rule_id=rule, type=kind, path=str(path), line=line, severity=severity,
                confidence=confidence, detail=detail, suggestion=suggestion, **extra)


def report(root, findings, diagnostics=None):
    findings.sort(key=lambda item: (SEVERITIES[item["severity"]], item["path"], item.get("line") or 0, item["rule_id"]))
    diagnostics = diagnostics or []
    return {
        "schema_version": 1, "version": VERSION, "root": str(Path(root).resolve()),
        "complete": not diagnostics, "total_findings": len(findings),
        "counts": {level: sum(item["severity"] == level for item in findings) for level in SEVERITIES},
        "diagnostics": diagnostics, "findings": findings,
    }


def add_common_arguments(parser):
    parser.add_argument("root", type=Path, help="Project root")
    parser.add_argument("--exclude", action="append", default=[], help="Additional relative glob (repeatable)")


def require_root(parser, root):
    if not root.is_dir():
        parser.error(f"Project directory does not exist: {root}")


def print_report(root, findings, diagnostics):
    print(json.dumps(report(root, findings, diagnostics), ensure_ascii=False, indent=2))
