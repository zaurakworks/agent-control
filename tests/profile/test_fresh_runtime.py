from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from agent_system.profile import cli as profile


class FreshRuntimeTests(TestCase):
    def test_runtime_parent_is_under_home(self) -> None:
        with TemporaryDirectory() as temporary:
            home = Path(temporary)
            with patch.object(profile.Path, "home", return_value=home):
                parent = profile._fresh_runtime_parent()
            self.assertEqual(parent, home / ".agent-system-state" / "tmp")
            self.assertTrue(parent.is_dir())

    def test_omp_config_dir_is_home_relative(self) -> None:
        home = Path("C:/Users/tester")
        runtime = home / ".agent-system-state" / "tmp" / "run-1"
        self.assertEqual(
            profile._omp_config_dir_name(runtime, home),
            ".agent-system-state/tmp/run-1",
        )

    def test_omp_config_dir_rejects_root_outside_home(self) -> None:
        with self.assertRaisesRegex(profile.ProfileError, "under the launch HOME"):
            profile._omp_config_dir_name(
                Path("C:/Temp/run-1"), Path("C:/Users/tester")
            )
