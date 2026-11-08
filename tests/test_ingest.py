from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from compass.ingest import ingest
from compass.vault import initialise


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class IngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.vault = self.root / "vault"
        self.archive = self.root / "archive"
        initialise(self.vault, self.archive, PROJECT_ROOT / "templates")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_archives_text_and_creates_source_note(self) -> None:
        source = self.root / "resume.txt"
        source.write_text("職務経歴\nGoでAPIを開発", encoding="utf-8")

        result = ingest(source, self.vault, self.archive)

        self.assertEqual(len(result.created), 1)
        note = result.created[0]
        content = note.read_text(encoding="utf-8")
        self.assertIn("type: source", content)
        self.assertIn("GoでAPIを開発", content)
        self.assertEqual(len(tuple((self.archive / "originals").iterdir())), 1)

        duplicate = ingest(source, self.vault, self.archive)
        self.assertEqual(duplicate.created, ())
        self.assertEqual(duplicate.skipped, (source,))

    def test_extracts_visible_html_text_without_scripts(self) -> None:
        source = self.root / "project.html"
        source.write_text(
            "<html><body><h1>決済基盤</h1><p>Goで実装</p><script>secret()</script></body></html>",
            encoding="utf-8",
        )

        result = ingest(source, self.vault, self.archive)

        content = result.created[0].read_text(encoding="utf-8")
        self.assertIn("決済基盤", content)
        self.assertIn("Goで実装", content)
        self.assertNotIn("secret()", content)
