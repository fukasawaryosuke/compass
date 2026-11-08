from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from compass.validation import validate
from compass.vault import DIRECTORIES, TEMPLATE_FILENAMES, initialise


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class InitialiseTests(unittest.TestCase):
    def test_creates_managed_layout_without_overwriting_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            vault = root / "vault"
            archive = root / "archive"
            templates = PROJECT_ROOT / "templates"

            first = initialise(vault, archive, templates)

            self.assertTrue(first.created)
            for directory in DIRECTORIES:
                self.assertTrue((vault / "compass" / directory).is_dir())
            for filename in TEMPLATE_FILENAMES:
                self.assertTrue((vault / "compass" / "templates" / filename).is_file())
            self.assertTrue((archive / "originals").is_dir())
            self.assertTrue((archive / "exports").is_dir())
            self.assertTrue(validate(vault).ok)

            home = vault / "compass" / "Home.md"
            home.write_text("# User edited home\n", encoding="utf-8")
            second = initialise(vault, archive, templates)

            self.assertIn(home, second.skipped)
            self.assertEqual(home.read_text(encoding="utf-8"), "# User edited home\n")
