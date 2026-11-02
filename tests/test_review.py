"""Behavioral regressions for scanners and command-line contracts."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import _common
import analyze_structure
import detect_dead_code
import find_duplicates
import run_review


class ProjectCase(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix=".code-cleaner-test-", dir=ROOT.parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path


class DeadCodeTests(ProjectCase):
    def test_js_imports_do_not_crash_and_used_bindings_are_kept(self):
        self.write("app.tsx", 'import React, {useState as state, type FC} from "react";\nimport * as util from "./util";\nstate(); util.run(); React.createElement("div");\nconst view: FC = () => null;\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_unused_js_import_has_original_line(self):
        self.write("app.js", '// header\nimport unused from "pkg";\nconsole.log("unused");\n')
        result = detect_dead_code.analyze(self.root)
        self.assertEqual([(item["rule_id"], item["line"]) for item in result], [("dead.import", 2)])

    def test_called_js_function_is_kept(self):
        self.write("app.js", 'function render() {}\nrender();\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_js_exports_are_kept(self):
        self.write("api.ts", 'export function publicApi() {}\nconst helper = () => 1;\nexport {helper};\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_java_used_import_and_class_are_kept(self):
        self.write("App.java", 'import java.util.List;\nclass App { List<String> data; }\nclass Main { App app = new App(); Main self; }\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_python_method_is_not_dead_definition(self):
        self.write("app.py", 'class Service:\n    def run(self):\n        return 1\n\nService().run()\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_python_imports_are_file_local(self):
        self.write("a.py", 'import os\n')
        self.write("b.py", 'import os\nprint(os.getcwd())\n')
        result = detect_dead_code.analyze(self.root)
        self.assertEqual([(item["path"], item["line"]) for item in result], [("a.py", 1)])

    def test_python_imports_are_scope_local(self):
        self.write("app.py", 'import os\ndef run():\n    import os\n    print(os.getcwd())\nrun()\n')
        result = detect_dead_code.analyze(self.root)
        self.assertEqual([(item["rule_id"], item["line"]) for item in result], [("dead.import", 1)])

    def test_python_global_import_used_in_nested_function(self):
        self.write("app.py", 'import os\ndef run():\n    return os.getcwd()\nrun()\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_python_closure_resolves_import(self):
        self.write("app.py", 'def outer():\n    import os\n    def inner():\n        return os.getcwd()\n    return inner()\nouter()\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_python_exports_and_package_imports_are_kept(self):
        self.write("api.py", 'from pkg import Service\n__all__ = ["Service"]\n')
        self.write("__init__.py", 'from pkg import Plugin\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_python_unused_function_has_line_and_low_confidence(self):
        self.write("app.py", '# comment\ndef unused():\n    return 1\n')
        result = detect_dead_code.analyze(self.root)
        self.assertEqual((result[0]["line"], result[0]["confidence"]), (2, "low"))

    def test_python_bom_and_encoding_cookie(self):
        (self.root / "bom.py").write_bytes(b'\xef\xbb\xbfprint("ok")\n')
        (self.root / "latin.py").write_bytes(b'# coding: latin-1\nprint("caf\xe9")\n')
        diagnostics = []
        self.assertEqual(detect_dead_code.analyze(self.root, diagnostics=diagnostics), [])
        self.assertEqual(diagnostics, [])

    def test_python_forward_annotations_keep_imports(self):
        self.write("api.py", 'from __future__ import annotations\nfrom pkg import Service, Other\ndef run(value: "Service") -> Other:\n    pass\nrun(None)\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_test_discovery_entries_are_kept(self):
        self.write("test_app.py", 'import unittest\nclass TestApp(unittest.TestCase):\n    def test_run(self):\n        pass\ndef test_function():\n    pass\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_template_expression_keeps_import(self):
        self.write("app.js", 'import name from "pkg";\nconsole.log(`Hello ${name}!`);\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_string_containing_import_syntax_is_not_an_import(self):
        self.write("app.js", 'const example = "import pretend from \'pkg\'";\nconsole.log(example);\n')
        self.assertEqual(detect_dead_code.analyze(self.root), [])

    def test_syntax_failure_is_visible(self):
        self.write("broken.py", 'def broken(:\n')
        diagnostics = []
        detect_dead_code.analyze(self.root, diagnostics=diagnostics)
        self.assertTrue(diagnostics)


class StructureTests(ProjectCase):
    def test_java_and_react_capitalized_names_are_allowed(self):
        self.write("UserService.java", 'public class UserService {}\n')
        self.write("UserCard.tsx", 'export function UserCard() { return null; }\n')
        self.assertEqual(analyze_structure.analyze(self.root), [])

    def test_empty_package_file_is_not_removal_candidate(self):
        self.write("__init__.py", '')
        self.assertEqual(analyze_structure.analyze(self.root), [])

    def test_strings_with_comment_markers_are_code(self):
        self.write("url.js", '"https://example.com/#fragment";\n')
        self.assertEqual(analyze_structure.analyze(self.root), [])

    def test_async_definitions_and_thresholds(self):
        self.write("large.py", '\n'.join(f'async def f{i}():\n    pass' for i in range(16)))
        rules = {item["rule_id"] for item in analyze_structure.analyze(self.root, max_lines=10)}
        self.assertIn("structure.lines", rules)
        self.assertIn("structure.definitions", rules)


class DuplicateTests(ProjectCase):
    def operations(self):
        return [f'operation_{i}()' for i in range(6)]

    def test_partial_duplicate_is_found_with_original_lines(self):
        lines = self.operations()
        self.write("a.py", '\n'.join(lines))
        self.write("b.py", '\n'.join(['setup()', '', '# note'] + lines + ['cleanup()']))
        result = find_duplicates.analyze(self.root, threshold=1)
        self.assertTrue(any(item["path"] == "a.py" and item["line"] == 1 and item["path_b"] == "b.py" and item["line_b"] == 4 for item in result))

    def test_order_is_significant(self):
        lines = self.operations()
        self.write("a.py", '\n'.join(lines))
        self.write("b.py", '\n'.join(reversed(lines)))
        self.assertEqual(find_duplicates.analyze(self.root), [])

    def test_fuzzy_window_can_match_one_changed_line(self):
        lines = self.operations() + ['operation_6()', 'operation_7()']
        other = list(lines)
        other[3] = 'different()'
        self.write("a.py", '\n'.join(lines))
        self.write("b.py", '\n'.join(other))
        self.assertTrue(find_duplicates.analyze(self.root, min_lines=8, threshold=0.85))

    def test_overlapping_self_windows_are_not_duplicates(self):
        self.write("a.py", '\n'.join(self.operations() + ['operation_6()']))
        self.assertEqual(find_duplicates.analyze(self.root), [])

    def test_limits_are_reported_as_incomplete(self):
        self.write("a.py", '\n'.join(self.operations()))
        self.write("b.py", '\n'.join(self.operations()))
        diagnostics = []
        find_duplicates.analyze(self.root, diagnostics=diagnostics, max_findings=1)
        self.assertTrue(diagnostics)

    def test_quoted_urls_and_hashes_are_normalized_as_strings(self):
        first = _common.normalized_lines('url = "https://a.test/#one"\n', '.py')
        second = _common.normalized_lines('url = "different"\n', '.py')
        self.assertEqual(first, second)


class TraversalAndCliTests(ProjectCase):
    def test_ignores_dependencies_protected_data_and_user_globs(self):
        self.write("ok.py", 'print(1)\n')
        for directory in ("node_modules", "vendor", ".venv", ".workbuddy", "generated"):
            self.write(directory + "/skip.py", 'print(1)\n')
        self.write(".codecleanerignore", '# comment\ngenerated/\n')
        self.assertEqual([path.name for path in _common.walk_files(self.root)], ["ok.py"])
        self.assertEqual(list(_common.walk_files(self.root, ["*.py"])), [])

    def test_external_symlinks_are_skipped(self):
        target = self.write("real.py", 'print(1)\n')
        try:
            os.symlink(target, self.root / "link.py")
        except OSError:
            self.skipTest("Symlink permission unavailable")
        self.assertEqual([path.name for path in _common.walk_files(self.root)], ["real.py"])

    def test_protected_scan_root_is_refused(self):
        protected = self.root / '.workbuddy'
        self.write('.workbuddy/private.py', 'print(1)\n')
        diagnostics = []
        self.assertEqual(list(_common.walk_files(protected, diagnostics=diagnostics)), [])
        self.assertTrue(diagnostics)

    def test_scan_does_not_change_project_files(self):
        path = self.write("app.py", 'import os\n')
        before = path.read_bytes()
        run_review.scan(self.root, dict(run_review.DEFAULTS))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual([item.name for item in self.root.iterdir()], ["app.py"])

    def cli(self, *args):
        return subprocess.run([sys.executable, '-X', 'utf8', '-B', str(ROOT / 'scripts/run_review.py'), str(self.root), *args], capture_output=True, encoding='utf-8')

    def test_json_and_ci_threshold(self):
        self.write("app.py", 'def unused():\n    pass\n')
        result = self.cli('--fail-on', 'warning')
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["complete"])
        self.assertEqual(report["findings"][0]["line"], 1)
        self.assertEqual(self.cli('--fail-on', 'error').returncode, 0)

    def test_invalid_config_and_syntax_error_return_two(self):
        self.write(".codecleaner.json", '{"unknown": true}')
        self.assertEqual(self.cli().returncode, 2)
        self.write(".codecleaner.json", '{"checks": ["dead"]}')
        self.write("broken.py", 'def broken(:\n')
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["complete"])

    def test_config_and_cli_override_and_markdown_file(self):
        self.write(".codecleaner.json", '{"checks": ["structure"], "max_lines": 1}')
        self.write("app.py", 'print(1)\nprint(2)\n')
        output = self.root / 'report.md'
        result = self.cli('--max-lines', '10', '--format', 'markdown', '--output', str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Code Cleaner', output.read_text(encoding='utf-8'))
        self.assertNotIn('structure.lines', output.read_text(encoding='utf-8'))

    def test_bad_threshold_and_missing_root(self):
        self.assertEqual(self.cli('--threshold', '2').returncode, 2)
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit) as error:
            run_review.main([str(self.root / 'missing')])
        self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
