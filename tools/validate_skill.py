#!/usr/bin/env python3
"""Dependency-free release checks for this repository's Skill and local links."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from _common import VERSION


def validate(root=ROOT):
    root = Path(root).resolve()
    errors = []
    required = ["SKILL.md", "README.md", "LICENSE", "CHANGELOG.md", "install.py",
                "scripts/run_review.py", "scripts/_common.py", "tests/test_review.py",
                "references/cli.md", "agents/openai.yaml"]
    for relative in required:
        if not (root / relative).is_file():
            errors.append(f"Missing required release file: {relative}")
    skill = root / "SKILL.md"
    if not skill.is_file():
        return errors
    text = skill.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        errors.append("SKILL.md must begin with YAML frontmatter")
    else:
        frontmatter = match.group(1)
        if not re.search(r"(?m)^name: code-cleaner$", frontmatter):
            errors.append("Skill name must be code-cleaner")
        description = re.search(r"(?m)^description: (.+)$", frontmatter)
        if not description or not 1 <= len(description.group(1)) <= 1024:
            errors.append("Description must contain 1..1024 characters on one line")
        if f'version: "{VERSION}"' not in frontmatter:
            errors.append("SKILL.md version differs from scripts/_common.py")
        allowed = {"name", "description", "license", "metadata", "allowed-tools"}
        for key in re.findall(r"(?m)^([\w-]+):", frontmatter):
            if key not in allowed:
                errors.append(f"Unsupported frontmatter field: {key}")
    changelog = root / "CHANGELOG.md"
    if changelog.is_file() and f"## {VERSION}" not in changelog.read_text(encoding="utf-8"):
        errors.append("CHANGELOG.md is missing the current version")
    # Check maintained entrypoint/docs links, leaving external URLs and examples alone.
    for document in (skill, root / "README.md"):
        if not document.is_file():
            continue
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            path = (document.parent / target.split("#")[0]).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                errors.append(f"Broken or out-of-project link in {document.name}: {target}")
    return errors


def main():
    errors = validate()
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print(f"Skill release checks passed: code-cleaner {VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
