# Changelog

**English** | [简体中文](CHANGELOG.zh-CN.md) | [日本語](CHANGELOG.ja.md)

## Unreleased

- Make English the default documentation language, with Simplified Chinese and Japanese versions of the README, CLI reference, contribution guide, and changelog.
- Use English by default in GitHub issue and pull request templates.

## 1.1.0 — 2026-11-02

### Added

- A unified read-only scanner with JSON / Markdown reports, rule IDs, line numbers, confidence, suggestions, and diagnostics.
- JSON project configuration, a dedicated ignore file, repeatable exclusion options, and CI failure levels.
- Ordered sliding windows, candidate indexing, and comparison/result limits for duplicate detection.
- Installation previews, explicit replacement, old-version backups, and staged installation recovery.
- Behavioral regression tests, GitHub Actions, contribution guidance, issue / PR templates, release validation, and ZIP packaging.

### Fixed

- Source deletion risk when the installation destination overlapped the source directory.
- JS/TS import unpacking crashes and false positives caused by missing non-Python reference data.
- Cross-file Python names hiding unused imports, and methods being treated as unused definitions.
- Missed duplicate fragments within longer blocks and similarity checks ignoring line order.
- Inappropriate cleanup suggestions for Java / React capitalized filenames and empty `__init__.py` files.

### Changed

- Simplified Skill metadata and workflow without assuming every client accepts arbitrary extension fields.
- Documented the coverage limits of heuristic checks, dynamic calls, and security review.
- Unused imports and empty-file candidates are no longer treated as safe automatic deletions.
