from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from compass.validation import validate


class ValidationTests(unittest.TestCase):
    def test_accepts_valid_project_note(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "compass"
            root.mkdir()
            (root / "project.md").write_text(
                "---\ntype: project\nscope: professional\nvisibility: review\nskills: [Go]\n---\n# Project\n",
                encoding="utf-8",
            )

            result = validate(root.parent)

            self.assertTrue(result.ok)
            self.assertEqual(result.warnings, ())

    def test_reports_missing_required_property(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "compass"
            root.mkdir()
            (root / "achievement.md").write_text(
                "---\ntype: achievement\nvisibility: review\n---\n# Achievement\n",
                encoding="utf-8",
            )

            result = validate(root.parent)

            self.assertFalse(result.ok)
            self.assertIn("missing required properties: project", result.errors[0])
