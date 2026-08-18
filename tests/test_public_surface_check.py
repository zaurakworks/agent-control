from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.public_surface_check.public_surface_check import scan


class PublicSurfaceCheckTests(unittest.TestCase):
    def test_clean_public_surface_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "authority").mkdir()
            (root / "authority/current.md").write_text(
                "Only self-contained public policy.\n",
                encoding="utf-8",
            )

            self.assertEqual(scan(root), [])

    def test_private_state_lab_fixture_is_rejected(self) -> None:
        fixture = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "public-surface"
            / "private-state-lab.txt"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "leak.txt"
            target.write_bytes(fixture.read_bytes())

            findings = scan(root)

        self.assertEqual(
            [(item.path, item.rule) for item in findings],
            [("leak.txt", "private-state-lab-asset")],
        )

    def test_credential_shaped_value_is_rejected(self) -> None:
        fixture = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "public-surface"
            / "credential.txt"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bad.txt").write_bytes(fixture.read_bytes())

            findings = scan(root)

        self.assertEqual(
            [(item.path, item.rule) for item in findings],
            [("bad.txt", "assigned-secret")],
        )


if __name__ == "__main__":
    unittest.main()
