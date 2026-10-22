"""共享服务配置的有界路径测试；仅探测空文件，不读取配置内容。"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'backend/common/services_config.py'


class ServicesConfigPathsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name).resolve() / 'workspace'
        self.demo = self.workspace / 'demo'
        self.backend = self.demo / 'hasn-cloud-backend-demo'
        self.worktree = self.backend / '.worktrees/layout'
        self.environment = dict(os.environ)
        self.environment.pop('HUANXING_SERVICES_CONFIG', None)
        for checkout in (self.backend, self.worktree):
            common = checkout / 'backend/common'
            common.mkdir(parents=True)
            shutil.copyfile(SOURCE, common / 'services_config.py')

    def locate(self, checkout: Path) -> str:
        result = subprocess.run(
            [sys.executable, '-I', '-c',
             'import runpy, sys; module = runpy.run_path(sys.argv[1]); '
             'print(module["_find_config_file"]())',
             str(checkout / 'backend/common/services_config.py')],
            env=self.environment, check=True, capture_output=True, text=True,
        )
        return result.stdout.strip()

    def test_default_is_demo_config_even_when_legacy_config_remains(self) -> None:
        expected = self.demo / 'services.toml'
        expected.touch()
        legacy = self.workspace / 'hasn-apps'
        legacy.mkdir()
        (legacy / 'services.toml').touch()
        # 即使未清理旧 checkout 附近的同名文件，也只能消费 Demo 的共享配置。
        (self.backend / 'services.toml').touch()
        for checkout in (self.backend, self.worktree):
            with self.subTest(checkout=checkout):
                self.assertEqual(self.locate(checkout), str(expected))

    def test_missing_demo_config_does_not_escape_to_legacy_or_parent_config(self) -> None:
        (self.workspace / 'hasn-apps').mkdir()
        (self.workspace / 'hasn-apps/services.toml').touch()
        (self.workspace / 'services.toml').touch()
        self.assertEqual(self.locate(self.worktree), 'None')

    def test_explicit_path_remains_authoritative_and_missing_path_does_not_fall_back(self) -> None:
        (self.demo / 'services.toml').touch()
        explicit = self.workspace / 'selected.toml'
        explicit.touch()
        self.environment['HUANXING_SERVICES_CONFIG'] = str(explicit)
        self.assertEqual(self.locate(self.worktree), str(explicit))
        self.environment['HUANXING_SERVICES_CONFIG'] = str(self.workspace / 'missing.toml')
        self.assertEqual(self.locate(self.worktree), 'None')


if __name__ == '__main__':
    unittest.main()
