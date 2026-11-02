# Code Cleaner

**English** | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

AI-assisted code review with human judgment: **read-only by default, evidence before changes, and edits within your authorization.**

Code Cleaner is an installable Agent Skill and a set of standalone Python command-line tools. It supports Python, JavaScript / TypeScript (including JSX and TSX), and Java. Runtime requirements: Python 3.10+ and the standard library.

[CLI reference](references/cli.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [MIT license](LICENSE)

## Features

- **Project structure:** file length, directory depth, definition counts, empty files, and filenames containing spaces. Java / React capitalized filenames and empty `__init__.py` files are preserved.
- **Unused-code candidates:** Python AST and symbol tables check import scopes and top-level definitions; JS/TS/Java use heuristic import and reference analysis.
- **Duplicate-code candidates:** ordered, normalized sliding windows find matching fragments inside longer blocks. An index filters candidates, with configurable comparison and result limits.
- **Unified reports:** JSON / Markdown with original line numbers, rule IDs, severity, confidence, and suggested actions.
- **Project configuration:** `.codecleaner.json`, `.codecleanerignore`, and CLI overrides.
- **CI integration:** configurable failure severity and explicit diagnostics for read errors, syntax errors, and truncated results.
- **Recoverable installation:** source/destination overlap checks, dry runs, explicit replacement, staging, backups, and failure recovery.

Scripts assist with structure, unused code, and duplicates. Code smells, security, and performance require an AI or human reviewer to inspect the context. Scanners do not modify source files, execute scanned code, or access the network.

## Quick start

Clone the repository and run the scanner from its root:

```bash
git clone https://github.com/AssUt11/code-cleaner.git
cd code-cleaner
python scripts/run_review.py /path/to/project --format markdown
python scripts/run_review.py /path/to/project --format json --output report.json
```

Quote Windows paths containing spaces:

```powershell
python scripts/run_review.py "D:\My Project" --format markdown
```

Example prompts for your AI assistant:

```text
Use code-cleaner to review this project. Start with a read-only report and prioritize findings by impact.
Find unused code and duplicates, excluding the generated directory.
Fix the confirmed findings, preserve public APIs, and run the relevant tests.
```

## Install as a Skill

```bash
python install.py codex --dry-run
python install.py codex
python install.py claude workbuddy
python install.py --all
```

| Target | Default parent directory |
|---|---|
| Codex | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| WorkBuddy | `~/.workbuddy/skills/` |

The installer creates `code-cleaner/` inside the selected parent directory. Discovery and loading depend on the client. The Skill uses the `name`, `description`, `license`, and `metadata` fields from the [Agent Skills specification](https://agentskills.io/specification).

Installation prefers a symbolic link and falls back to copying if permission is unavailable. A linked installation follows updates to the source directory; a copied installation needs to be installed again. Existing targets require explicit replacement:

```bash
python install.py codex --force
python install.py --target /custom/skills --no-symlink --dry-run
```

`--force` keeps a sibling backup named `.code-cleaner.backup-TIMESTAMP-ID`. To restore it, move the current `code-cleaner` aside and rename the backup to `code-cleaner`. If the backup is a symbolic link, retain its original source directory. Installing into the source directory or an overlapping parent/child path is refused.

## Configuration and ignore rules

Copy `.codecleaner.example.json` to `.codecleaner.json` in the scanned project's root and adjust it as needed. The unified scanner loads this file automatically:

```json
{
  "checks": ["structure", "dead", "duplicates"],
  "exclude": ["generated/*", "*.min.js"],
  "max_lines": 500,
  "max_depth": 6,
  "min_lines": 6,
  "threshold": 0.85,
  "max_comparisons": 50000,
  "max_findings": 200
}
```

Alternatively, put one relative glob per line in `.codecleanerignore`. Lines beginning with `#` are comments. Negation with `!` is unsupported, and `.gitignore` is not read automatically. Scalar CLI options override JSON values; `--exclude` appends to the configured list. Dependencies, hidden directories, `.workbuddy/`, virtual environments, build outputs, and links are skipped by default.

## CI and exit codes

```bash
python scripts/run_review.py /path/to/project --checks structure,dead --fail-on warning
```

| Exit code | Meaning |
|---|---|
| `0` | Scan completed without reaching the failure severity. The default `--fail-on none` allows candidates. |
| `1` | Scan completed and findings reached the configured failure severity. |
| `2` | Invalid arguments/configuration, output errors, or an incomplete scan, including parsing failures and truncated results. |

`--fail-on info` includes every severity; `warning` includes warning / error; `error` includes only error. Current built-in rules mainly produce warning / info findings; serious security issues require human or AI review. Use the unified entrypoint for CI; individual scanners provide candidate JSON.

GitHub Actions covers Ubuntu / Windows with Python 3.10 / 3.14. [View CI runs](https://github.com/AssUt11/code-cleaner/actions).

## Limitations

- Findings are candidates. **There is no automatic fix or deletion command.** Static counts alone cannot establish whether imports have side effects or whether public APIs, reflection, plugin registration, or cross-repository calls use a symbol.
- Python class methods, nested definitions, and decorated entrypoints are excluded from unused-definition candidates. Dynamic exports and references embedded in strings may still cause mistakes.
- JS/TS/Java checks are heuristic rather than full compiler analysis. Module aliases, complete scopes, framework conventions, CommonJS, and dynamic imports have limited coverage.
- Duplicate detection preserves line order while normalizing strings and numbers. Approximate matches require shared adjacent normalized lines; semantically similar code may be missed.
- Indexing does not eliminate the worst case for highly repetitive projects. Reaching a limit returns available findings, `complete: false`, and exit code `2`. Narrow the scope or raise the limits.
- Python encoding declarations and UTF-8 BOM are supported; other languages are read as UTF-8. Read failures appear in diagnostics.

## Development and releases

```bash
python -B -m unittest discover -s tests -v
python -B tools/validate_skill.py
python -B tools/package_release.py --output ../code-cleaner.zip
```

The validator checks metadata, version consistency, and local documentation links. Packaging validates the Skill, then creates a ZIP with a top-level `code-cleaner/` directory. Git metadata, caches, dependencies, existing ZIPs, and `.workbuddy/` are excluded. Source files, tests, and `.github/` configuration are included.

When publishing a fork, place this directory's contents at the repository root, including hidden files such as `.github/` and `.gitignore`. Attach the ZIP to a Release if needed; uploading only a ZIP does not run source CI.

## Repository layout

```text
code-cleaner/
├── README*.md               # English, Simplified Chinese and Japanese documentation
├── SKILL.md                 # AI workflow and scope protection
├── install.py               # Installer for supported client directories
├── scripts/                 # Unified CLI, three scanners and shared utilities
├── references/              # CLI, code smells, language rules, security/performance
├── assets/                  # Report template
├── agents/openai.yaml       # Codex UI metadata
├── tests/                   # Behavioral regression tests
├── tools/                   # Release validation and packaging
└── .github/                 # CI, issue templates and PR template
```

## License

MIT. See [LICENSE](LICENSE).
