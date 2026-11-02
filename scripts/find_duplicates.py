#!/usr/bin/env python3
"""Ordered sliding-window duplicate candidates, indexed by shared adjacent lines."""

import argparse
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
import sys
import tokenize

sys.dont_write_bytecode = True

from _common import (add_common_arguments, diagnostic, finding, normalized_lines,
                     print_report, read_source, require_root, walk_files)


def similarity(first, second):
    return SequenceMatcher(None, first, second, autojunk=False).ratio()


def analyze(root, min_lines=6, threshold=0.85, exclude=(), diagnostics=None,
            max_comparisons=50000, max_findings=200):
    root = Path(root).resolve()
    sources = {}
    for path in walk_files(root, exclude, diagnostics):
        source = read_source(path, diagnostics)
        if source is None:
            continue
        try:
            sources[path.relative_to(root).as_posix()] = normalized_lines(source, path.suffix.lower())
        except (tokenize.TokenError, IndentationError, SyntaxError) as error:
            diagnostic(diagnostics, path.relative_to(root), f"Duplicate analysis skipped: {error}")
    # Each window is a short ordered sequence, including across blank/comment lines.
    index = defaultdict(list)
    findings = []
    comparisons = 0
    covered = defaultdict(list)
    for path, lines in sources.items():
        for start in range(max(0, len(lines) - min_lines + 1)):
            tokens = tuple(value for _, value in lines[start:start + min_lines])
            anchors = set(zip(tokens, tokens[1:]))
            candidates = set()
            for anchor in anchors:
                candidates.update(index[anchor])
            for other_path, other_start in sorted(candidates):
                if path == other_path and abs(start - other_start) < min_lines:
                    continue
                key = (other_path, path, other_start - start)
                if any(left <= start < right for left, right in covered[key]):
                    continue
                if comparisons >= max_comparisons:
                    diagnostic(diagnostics, ".", f"Duplicate comparison limit ({max_comparisons}) reached; narrow the scope or raise max_comparisons.")
                    return findings
                comparisons += 1
                other_lines = sources[other_path]
                other_tokens = tuple(value for _, value in other_lines[other_start:other_start + min_lines])
                score = similarity(tokens, other_tokens)
                if score < threshold:
                    continue
                end, other_end = start + min_lines, other_start + min_lines
                while end < len(lines) and other_end < len(other_lines) and lines[end][1] == other_lines[other_end][1]:
                    if path == other_path and other_end >= start:
                        break
                    end += 1
                    other_end += 1
                covered[key].append((start, end))
                findings.append(finding(
                    "duplicates.window", "疑似重复代码", other_path, other_lines[other_start][0],
                    f"至少 {min_lines} 行归一化代码相似度 {score:.1%}",
                    "结合职责判断是否抽取共享逻辑；字面量已归一化。", "info",
                    path_b=path, line_b=lines[start][0], end_line=other_lines[other_end - 1][0],
                    end_line_b=lines[end - 1][0], similarity=round(score, 3),
                ))
                if len(findings) >= max_findings:
                    diagnostic(diagnostics, ".", f"Duplicate finding limit ({max_findings}) reached; results are truncated.")
                    return findings
            for anchor in anchors:
                index[anchor].append((path, start))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_arguments(parser)
    parser.add_argument("--min-lines", type=int, default=6)
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--max-comparisons", type=int, default=50000)
    parser.add_argument("--max-findings", type=int, default=200)
    args = parser.parse_args()
    require_root(parser, args.root)
    if args.min_lines < 2 or not 0.5 <= args.threshold <= 1 or min(args.max_comparisons, args.max_findings) < 1:
        parser.error("min-lines >= 2; threshold in [0.5, 1]; limits must be positive")
    diagnostics = []
    print_report(args.root, analyze(args.root, args.min_lines, args.threshold, args.exclude,
                                   diagnostics, args.max_comparisons, args.max_findings), diagnostics)


if __name__ == "__main__":
    main()
