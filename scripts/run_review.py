#!/usr/bin/env python3
"""Unified read-only scanner with JSON/Markdown output and CI exit codes."""

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from _common import SEVERITIES, VERSION, add_common_arguments, report, require_root
import analyze_structure
import detect_dead_code
import find_duplicates

DEFAULTS = {
    "checks": ["structure", "dead", "duplicates"], "exclude": [],
    "max_lines": 500, "max_depth": 6, "min_lines": 6, "threshold": 0.85,
    "max_comparisons": 50000, "max_findings": 200,
}


def load_config(path):
    options = dict(DEFAULTS)
    if path is not None:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError("Configuration must be a JSON object")
        unknown = set(value) - set(DEFAULTS)
        if unknown:
            raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
        options.update(value)
    return options


def validate_options(options):
    for key in ("max_lines", "min_lines", "max_comparisons", "max_findings", "max_depth"):
        minimum = 0 if key == "max_depth" else 2 if key == "min_lines" else 1
        if type(options[key]) is not int or options[key] < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")
    if type(options["threshold"]) not in (int, float) or not 0.5 <= options["threshold"] <= 1:
        raise ValueError("threshold must be a number in [0.5, 1]")
    if not isinstance(options["exclude"], list) or not all(isinstance(item, str) for item in options["exclude"]):
        raise ValueError("exclude must be a list of glob strings")
    checks = options["checks"]
    if not isinstance(checks, list) or not checks or any(item not in DEFAULTS["checks"] for item in checks):
        raise ValueError("checks must contain structure, dead and/or duplicates")


def scan(root, options):
    validate_options(options)
    findings, diagnostics = [], []
    if "structure" in options["checks"]:
        findings.extend(analyze_structure.analyze(root, options["max_lines"], options["max_depth"], options["exclude"], diagnostics))
    if "dead" in options["checks"]:
        findings.extend(detect_dead_code.analyze(root, options["exclude"], diagnostics))
    if "duplicates" in options["checks"]:
        findings.extend(find_duplicates.analyze(root, options["min_lines"], options["threshold"], options["exclude"], diagnostics,
                                               options["max_comparisons"], options["max_findings"]))
    return report(root, findings, diagnostics)


def markdown(result):
    def escape(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    rows = ["# Code Cleaner 扫描报告", "", f"版本：{result['version']} · 模式：只读筛查",
            f"项目：`{result['root']}`", "",
            f"完成状态：{'完整' if result['complete'] else '不完整，请检查诊断信息'}", "",
            "| 严重 | 警告 | 建议 | 合计 |", "|---:|---:|---:|---:|",
            f"| {result['counts']['error']} | {result['counts']['warning']} | {result['counts']['info']} | {result['total_findings']} |", "",
            "## 问题明细", "", "| 级别 | 位置 | 规则 / 置信度 | 问题 | 建议 |", "|---|---|---|---|---|"]
    for item in result["findings"]:
        location = f"{item['path']}:{item['line']}"
        if "path_b" in item:
            location += f" ↔ {item['path_b']}:{item['line_b']}"
        rows.append("| " + " | ".join(escape(value) for value in (
            item["severity"], location, f"{item['rule_id']} / {item['confidence']}", item["detail"], item["suggestion"])) + " |")
    if not result["findings"]:
        rows.extend(["", "当前启用的静态规则未发现候选问题；这不代表完整的安全审计。"])
    if result["diagnostics"]:
        rows.extend(["", "## 诊断信息", ""])
        rows.extend(f"- {escape(item['path'])}: {escape(item['message'])}" for item in result["diagnostics"])
    rows.extend(["", "## 建议处理顺序", "", "1. 先检查扫描是否完整，再复核严重问题。",
                 "2. 结合调用、导出、框架入口和副作用确认候选结果。", "3. 在授权范围内备份并小批量修改，随后运行相关测试。", ""])
    return "\n".join(rows)


def exit_code(result, fail_on):
    if not result["complete"]:
        return 2
    if fail_on != "none" and any(SEVERITIES[item["severity"]] <= SEVERITIES[fail_on] for item in result["findings"]):
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_arguments(parser)
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--config", type=Path, help="JSON config; defaults to ROOT/.codecleaner.json if present")
    parser.add_argument("--checks", help="Comma-separated: structure,dead,duplicates")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="Write report to this path (default stdout)")
    parser.add_argument("--fail-on", choices=("none", "info", "warning", "error"), default="none")
    for key in ("max_lines", "max_depth", "min_lines", "max_comparisons", "max_findings"):
        parser.add_argument("--" + key.replace("_", "-"), type=int)
    parser.add_argument("--threshold", type=float)
    args = parser.parse_args(argv)
    require_root(parser, args.root)
    try:
        config = args.config
        if config is None and (args.root / ".codecleaner.json").is_file():
            config = args.root / ".codecleaner.json"
        options = load_config(config)
        for key in DEFAULTS:
            value = getattr(args, key, None)
            if key == "exclude":
                if not isinstance(options[key], list):
                    raise ValueError("exclude must be a list")
                options[key] = options[key] + value
            elif value is not None:
                options[key] = value.split(",") if key == "checks" else value
        result = scan(args.root, options)
        output = markdown(result) if args.format == "markdown" else json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        else:
            print(output, end="")
        return exit_code(result, args.fail_on)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"code-cleaner: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
