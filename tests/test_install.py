"""Installer tests use isolated fixtures, never real platform/home directories."""

import contextlib
import importlib.util
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('code_cleaner_install', ROOT / 'install.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix='.code-cleaner-install-test-', dir=ROOT.parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source' / 'code-cleaner'
        self.source.mkdir(parents=True)
        (self.source / 'SKILL.md').write_text('new skill', encoding='utf-8')
        self.target = self.root / 'target'

    def install(self, **options):
        with contextlib.redirect_stdout(io.StringIO()):
            return installer.install_to(self.target, self.source, use_symlink=False, **options)

    def old_install(self):
        dest = self.target / 'code-cleaner'
        dest.mkdir(parents=True)
        (dest / 'SKILL.md').write_text('old skill', encoding='utf-8')
        return dest

    def test_copy_install(self):
        self.assertTrue(self.install())
        self.assertEqual((self.target / 'code-cleaner/SKILL.md').read_text(encoding='utf-8'), 'new skill')

    def test_existing_target_is_preserved_without_force(self):
        dest = self.old_install()
        self.assertFalse(self.install())
        self.assertEqual((dest / 'SKILL.md').read_text(encoding='utf-8'), 'old skill')

    def test_force_keeps_backup(self):
        dest = self.old_install()
        self.assertTrue(self.install(force=True))
        backups = list(self.target.glob('.code-cleaner.backup-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / 'SKILL.md').read_text(encoding='utf-8'), 'old skill')
        self.assertEqual((dest / 'SKILL.md').read_text(encoding='utf-8'), 'new skill')

    def test_failed_copy_preserves_old_install(self):
        dest = self.old_install()
        with patch.object(installer.shutil, 'copytree', side_effect=OSError('disk full')):
            self.assertFalse(self.install(force=True))
        self.assertEqual((dest / 'SKILL.md').read_text(encoding='utf-8'), 'old skill')

    def test_failed_publish_restores_old_install(self):
        dest = self.old_install()
        original = Path.rename

        def fail_stage(path, target):
            if path.parent.name.startswith('.code-cleaner-stage-'):
                raise OSError('publish failed')
            return original(path, target)

        with patch.object(Path, 'rename', fail_stage):
            self.assertFalse(self.install(force=True))
        self.assertEqual((dest / 'SKILL.md').read_text(encoding='utf-8'), 'old skill')

    def test_self_install_and_nested_target_are_rejected(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(installer.install_to(self.source.parent, self.source, force=True))
            self.assertFalse(installer.install_to(self.source / 'nested', self.source, force=True))
        self.assertTrue((self.source / 'SKILL.md').is_file())
        self.assertFalse((self.source / 'nested').exists())

    def test_dry_run_has_no_side_effects(self):
        self.assertTrue(self.install(dry_run=True))
        self.assertFalse(self.target.exists())

    def test_symlink_failure_falls_back_to_copy(self):
        with patch.object(installer.os, 'symlink', side_effect=OSError('not permitted')), contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(installer.install_to(self.target, self.source))
        self.assertFalse((self.target / 'code-cleaner').is_symlink())

    def test_reinstalling_same_symlink_is_a_noop(self):
        self.target.mkdir()
        try:
            installer.os.symlink(self.source, self.target / 'code-cleaner', target_is_directory=True)
        except OSError:
            self.skipTest('Symlink permission unavailable')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(installer.install_to(self.target, self.source))
        self.assertEqual(list(self.target.glob('.code-cleaner.backup-*')), [])

    def test_force_can_convert_a_symlink_to_a_copy(self):
        self.target.mkdir()
        try:
            installer.os.symlink(self.source, self.target / 'code-cleaner', target_is_directory=True)
        except OSError:
            self.skipTest('Symlink permission unavailable')
        self.assertTrue(self.install(force=True))
        self.assertFalse((self.target / 'code-cleaner').is_symlink())
        self.assertTrue((self.source / 'SKILL.md').is_file())

    def test_cli_propagates_failure(self):
        with patch.object(installer, 'get_skill_source', return_value=self.source), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(['--target', str(self.source.parent), '--force']), 1)


if __name__ == '__main__':
    unittest.main()
