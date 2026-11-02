#!/usr/bin/env python3
"""Validate and package source, tests and GitHub configuration as a release ZIP."""

import argparse
import hashlib
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

from validate_skill import ROOT, validate

SKIP = {".git", ".workbuddy", "__pycache__", ".venv", "venv", "node_modules",
        ".pytest_cache", ".ruff_cache", "dist", "build", "vendor"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    errors = validate()
    if errors:
        parser.error("; ".join(errors))
    output = args.output.expanduser().absolute()
    if output.suffix.lower() != ".zip":
        parser.error("Output must end in .zip")
    if output.is_symlink():
        parser.error("Refusing a symlink output")
    output.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    # Prune protected directories before traversal; do not even enumerate their contents.
    import os
    for directory, names, files in os.walk(ROOT, followlinks=False):
        parent = Path(directory)
        names[:] = sorted(name for name in names if name not in SKIP
                          and not name.startswith((".code-cleaner-stage-", ".code-cleaner.backup-"))
                          and not (parent / name).is_symlink()
                          and not getattr(parent / name, "is_junction", lambda: False)()
                          and (parent / name).resolve().is_relative_to(ROOT))
        for name in sorted(files):
            path = parent / name
            if path.is_symlink() or path.suffix.lower() in {".zip", ".pyc", ".pyo"}:
                continue
            if name == ".env" or name.startswith(".env."):
                continue
            entries.append(path)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in entries:
            archive.write(path, "code-cleaner/" + path.relative_to(ROOT).as_posix())
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"Created: {output}\nFiles: {len(entries)}\nSHA256: {checksum}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
