# CLI reference

**English** | [简体中文](cli.zh-CN.md) | [日本語](cli.ja.md)

Requires Python 3.10+ with no third-party runtime dependencies. Scanners are read-only and do not execute project code. Run the following commands from the Skill directory.

## Unified scanner

```bash
python scripts/run_review.py PROJECT [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--checks` | `structure,dead,duplicates` | Comma-separated checks |
| `--format` | `json` | `json` / `markdown` |
| `--output PATH` | Standard output | Explicit report destination; the parent directory must exist |
| `--config PATH` | `PROJECT/.codecleaner.json`, if present | JSON configuration; unknown fields and invalid types are errors |
| `--exclude GLOB` | No additional rules | Repeatable; appends to configured exclusions |
| `--max-lines` | `500` | File-length threshold; positive integer |
| `--max-depth` | `6` | Relative directory-depth threshold; nonnegative integer |
| `--min-lines` | `6` | Normalized lines per duplicate window; at least 2 |
| `--threshold` | `0.85` | Ordered-window similarity threshold in `[0.5, 1]` |
| `--max-comparisons` | `50000` | Duplicate comparison limit; positive integer |
| `--max-findings` | `200` | Duplicate result limit; positive integer |
| `--fail-on` | `none` | `none` / `info` / `warning` / `error` |
| `--version` | — | Print the tool version |

JSON keys use underscores, such as `max_lines`. Both `checks` and `exclude` are arrays of strings. Only the unified scanner reads JSON configuration.

## Ignore rules

All scanners read `.codecleanerignore` from the project root: one relative glob per line, using `/` as the path separator. Matching follows Python `fnmatch` semantics: `*` can match path separators, and directory prefixes are checked too. `generated/` skips that directory, `tests/*` skips test files, and `*.min.js` matches at any depth. Lines beginning with `#` are comments. Git negation, escaping, and full `.gitignore` semantics are not implemented.

Built-in exclusions cannot be disabled through configuration: dependency directories, virtual environments, build outputs, hidden directories, `.workbuddy/`, symbolic links, and junctions are skipped. Point the scanner at the actual project, rather than using a dependency directory as its root.

## JSON format (schema_version 1)

Top-level fields: `schema_version`, `version`, `root`, `complete`, `total_findings`, `counts`, `diagnostics`, and `findings`.

Each finding includes `rule_id`, `type`, `path`, `line`, `severity`, `confidence`, `detail`, and `suggestion`. Paths are relative to the project root; line numbers start at 1. Duplicates also include `path_b`, `line_b`, `end_line`, `end_line_b`, and `similarity`. Positions refer to the original source, despite normalization.

- `severity`: `error` / `warning` / `info`. Classification reflects impact; rule output is not proof of a bug.
- `confidence`: `high` / `medium` / `low`. Confidence in a static inference does not replace review.
- `diagnostics`: read, parse, or limit information. Each item contains `path` and `message`. A nonempty list makes `complete` false.
- Exit codes: 0 = complete and below the failure level; 1 = complete with findings at the failure level; 2 = argument, configuration, I/O, or incomplete-scan errors. Handle exit code 2 explicitly.

Rule IDs: `structure.depth`, `structure.lines`, `structure.definitions`, `structure.empty`, `structure.naming`, `dead.import`, `dead.definition`, and `duplicates.window`.

## Individual scanners

```bash
python scripts/analyze_structure.py PROJECT --max-lines 600 --max-depth 6
python scripts/detect_dead_code.py PROJECT --exclude "generated/*"
python scripts/find_duplicates.py PROJECT --min-lines 8 --threshold 0.9
```

They emit the same JSON schema, but do not apply JSON configuration or CI severity thresholds. Check `complete` for diagnostics. Use `run_review.py` for CI.

## Installer

```bash
python install.py codex --dry-run
python install.py claude workbuddy --no-symlink
python install.py --all --force
python install.py --target ./local-skills --no-symlink
```

`--target` specifies a parent directory; the installer creates `code-cleaner/` beneath it. Do not combine it with platform names or `--all`. `--force` explicitly replaces an existing target and keeps the old version. Without replacement authorization, existing targets are refused. Staging failures leave the old installation intact. A failed final rename triggers an attempt to restore it; retained backups can also be restored manually. `--dry-run` creates no directories or installations. Exit code 0 means success, 1 means at least one target failed, and 2 means invalid arguments.
