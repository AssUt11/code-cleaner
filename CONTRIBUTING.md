# Contributing

**English** | [简体中文](CONTRIBUTING.zh-CN.md) | [日本語](CONTRIBUTING.ja.md)

Contributions are welcome: bug fixes, reproducible false-positive examples, and checks with clearly defined coverage. Prioritize reviewable results before expanding detection.

## Local checks

Use Python 3.10+. No runtime packages need to be installed:

```bash
python -B -m unittest discover -s tests -v
python -B tools/validate_skill.py
```

Tests create and clean up isolated temporary directories beside the repository; they never install into real client directories. On Windows, real-symlink tests may be skipped when permission is unavailable. Copy fallback remains covered.

## Submission guidelines

- Issues and pull requests may be written in English, Simplified Chinese, or Japanese.
- Include a minimal source example for detection fixes. Assert observable behavior: whether a candidate appears, original line numbers, diagnostics, and exit codes.
- Do not hide reproductions or weaken assertions to make tests pass. Document heuristic limitations in the README translations.
- Keep scanning read-only. Do not execute scanned code, upload source, or introduce automatic deletion.
- Prefer the standard library. Explain the necessity, installation impact, and license of any new dependency.
- Breaking JSON schema changes require updates to schema_version, documentation, and regression coverage.
- When changing the version, update `scripts/_common.py`, `SKILL.md`, and all changelog translations together.
- Describe the problem, resulting behavior, and actual validation in the PR. Exclude caches, generated reports, and real credentials.

## Release process

1. Run tests and Skill validation; check version consistency and changelogs.
2. Run `python tools/package_release.py --output ../code-cleaner.zip`.
3. Check the actual cross-platform GitHub Actions results, then create a tag / Release and attach the ZIP.

Maintainers explicitly perform publishing and pushing. The tools do not create repositories, commit, or upload files automatically.
