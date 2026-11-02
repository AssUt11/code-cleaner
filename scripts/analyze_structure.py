#!/usr/bin/env python3
"""Read-only structure checks; candidates require contextual review."""

import argparse
import ast
from pathlib import Path
import re
import sys
import tokenize

sys.dont_write_bytecode = True

from _common import (add_common_arguments, diagnostic, finding, mask_js,
                     normalized_lines, print_report, read_source, require_root, walk_files)

DEFAULT_MAX_LINES = 500
DEFAULT_MAX_DEPTH = 6
DEFAULT_MAX_DEFS = 15


def analyze(root, max_lines=DEFAULT_MAX_LINES, max_depth=DEFAULT_MAX_DEPTH, exclude=(), diagnostics=None):
    root = Path(root).resolve()
    findings = []
    deep_directories = set()
    for path in walk_files(root, exclude, diagnostics):
        relative = path.relative_to(root).as_posix()
        source = read_source(path, diagnostics)
        if source is None:
            continue
        depth = len(path.relative_to(root).parts) - 1
        if depth > max_depth and path.parent not in deep_directories:
            deep_directories.add(path.parent)
            findings.append(finding("structure.depth", "目录过深", Path(relative).parent.as_posix(), 1,
                                    f"目录深度 {depth}，超过阈值 {max_depth}", "考虑按职责简化目录层级。"))
        count = len(source.splitlines())
        if count > max_lines:
            findings.append(finding("structure.lines", "文件过大", relative, 1,
                                    f"{count} 行，超过阈值 {max_lines}", "结合职责判断是否拆分文件。"))
        try:
            if path.suffix.lower() == ".py":
                tree = ast.parse(source)
                definitions = sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) for node in tree.body)
                empty = not tree.body or all(
                    isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str) for node in tree.body
                )
            else:
                cleaned = mask_js(source)
                definitions = len(re.findall(r"\b(?:function|class|interface|enum|record)\s+[\w$]+", cleaned))
                empty = not normalized_lines(source, path.suffix.lower())
        except (SyntaxError, tokenize.TokenError, IndentationError) as error:
            diagnostic(diagnostics, relative, f"Structure analysis skipped: {error}")
            continue
        if definitions > DEFAULT_MAX_DEFS:
            findings.append(finding("structure.definitions", "定义过多", relative, 1,
                                    f"约 {definitions} 个定义，超过阈值 {DEFAULT_MAX_DEFS}", "检查文件是否承担多种职责。"))
        if empty and path.name != "__init__.py":
            findings.append(finding("structure.empty", "空文件或仅含文档/注释", relative, 1,
                                    "未发现可执行语句", "先确认占位、包结构和工具约定，再考虑删除。", "info"))
        if re.search(r"\s", path.stem):
            findings.append(finding("structure.naming", "命名建议", relative, 1,
                                    "源码文件名含空格", "遵循当前语言和项目已有的命名约定。", "info"))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_arguments(parser)
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
    args = parser.parse_args()
    require_root(parser, args.root)
    if args.max_lines < 1 or args.max_depth < 0:
        parser.error("max-lines must be positive and max-depth nonnegative")
    diagnostics = []
    print_report(args.root, analyze(args.root, args.max_lines, args.max_depth, args.exclude, diagnostics), diagnostics)


if __name__ == "__main__":
    main()
