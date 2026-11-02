#!/usr/bin/env python3
"""Install code-cleaner using staged copy/symlink and recoverable replacement."""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

PLATFORMS = {
    "workbuddy": "~/.workbuddy/skills",
    "claude": "~/.claude/skills",
    "codex": "~/.agents/skills",
}
SKILL_NAME = "code-cleaner"


def get_skill_source():
    return Path(__file__).resolve().parent


def install_to(target_dir, source, use_symlink=True, force=False, dry_run=False):
    source = Path(source).expanduser().resolve()
    target_dir = Path(target_dir).expanduser().resolve()
    dest = target_dir / SKILL_NAME
    if not (source / "SKILL.md").is_file():
        print(f"Invalid skill source: {source}")
        return False
    try:
        resolved_dest = dest.resolve()
        if dest.is_relative_to(source) or source.is_relative_to(dest):
            print(f"Refusing overlapping source/destination: {source} -> {dest}")
            return False
        same_link = dest.is_symlink() and resolved_dest == source
        if same_link and use_symlink:
            print(f"Already linked: {dest}")
            return True
        if not same_link and (resolved_dest.is_relative_to(source) or source.is_relative_to(resolved_dest)):
            print(f"Refusing overlapping source/destination: {source} -> {dest}")
            return False
        exists = dest.exists() or dest.is_symlink()
        if exists and not force:
            print(f"Target exists: {dest}. Use --force to replace it with a backup.")
            return False
        if dry_run:
            print(f"Would install: {source} -> {dest}" + (" (backup existing target)" if exists else ""))
            return True
        target_dir.mkdir(parents=True, exist_ok=True)
        backup = None
        # Stage completely before moving the old version. Only the temporary stage
        # is cleaned automatically; the old installation is kept as a sibling backup.
        with TemporaryDirectory(prefix=".code-cleaner-stage-", dir=target_dir) as temporary:
            stage = Path(temporary) / SKILL_NAME
            linked = False
            if use_symlink:
                try:
                    os.symlink(source, stage, target_is_directory=True)
                    linked = True
                except OSError:
                    if stage.is_symlink():
                        stage.unlink()
            if not linked:
                shutil.copytree(source, stage, ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", ".git", "*.zip", "*.egg-info", ".workbuddy",
                ))
            if exists:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                backup = target_dir / f".code-cleaner.backup-{stamp}-{uuid4().hex[:8]}"
                dest.rename(backup)
            try:
                stage.rename(dest)
            except OSError:
                if backup is not None:
                    backup.rename(dest)
                raise
        print(f"Installed ({'symlink' if linked else 'copy'}): {dest}")
        if backup is not None:
            print(f"Backup: {backup}")
        return True
    except (OSError, RuntimeError) as error:
        print(f"Installation failed: {error}")
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platforms", nargs="*", choices=None, help="workbuddy, claude and/or codex")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Install for all platforms")
    group.add_argument("--target", type=Path, help="Custom skills parent directory")
    parser.add_argument("--no-symlink", action="store_true", help="Always copy")
    parser.add_argument("--force", action="store_true", help="Replace existing target, keeping a backup")
    parser.add_argument("--dry-run", action="store_true", help="Validate and display without writing")
    args = parser.parse_args(argv)
    if args.platforms and (args.all or args.target):
        parser.error("Use platform names, --all or --target separately")
    unknown = set(args.platforms) - set(PLATFORMS)
    if unknown:
        parser.error(f"Unknown platforms: {', '.join(sorted(unknown))}")
    targets = [args.target] if args.target else [Path(PLATFORMS[name]) for name in (PLATFORMS if args.all else dict.fromkeys(args.platforms))]
    if not targets:
        if not sys.stdin.isatty():
            parser.error("Specify a platform, --all or --target")
        try:
            choice = input("Platforms (workbuddy,claude,codex or all): ").strip()
        except (EOFError, KeyboardInterrupt):
            return 1
        names = list(PLATFORMS) if choice == "all" else [name.strip() for name in choice.split(",")]
        if any(name not in PLATFORMS for name in names):
            parser.error("Unknown platform selection")
        targets = [Path(PLATFORMS[name]) for name in dict.fromkeys(names)]
    success = [install_to(target, get_skill_source(), not args.no_symlink, args.force, args.dry_run) for target in targets]
    return 0 if all(success) else 1


if __name__ == "__main__":
    sys.exit(main())
