from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from compass.ingest import ingest
from compass.vault import initialise


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class IngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.vault = self.root / "vault"
        self.archive = self.root / "archive"
        initialise(self.vault, self.archive)

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

    def test_extracts_word_powerpoint_and_excel_content(self) -> None:
        from docx import Document
        from openpyxl import Workbook
        from pptx import Presentation

        word = self.root / "career.docx"
        document = Document()
        document.add_paragraph("GoでAPIを設計")
        document.save(word)

        presentation_path = self.root / "project.pptx"
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[5])
        slide.shapes.add_textbox(0, 0, 1_000_000, 1_000_000).text_frame.text = "決済基盤を刷新"
        presentation.save(presentation_path)

        spreadsheet = self.root / "metrics.xlsx"
        workbook = Workbook()
        workbook.active.title = "Metrics"
        workbook.active.append(["指標", "改善"])
        workbook.active.append(["障害", "50%"])
        workbook.save(spreadsheet)

        result = ingest(self.root, self.vault, self.archive)

        content = "\n".join(note.read_text(encoding="utf-8") for note in result.created)
        self.assertIn("GoでAPIを設計", content)
        self.assertIn("決済基盤を刷新", content)
        self.assertIn("障害 | 50%", content)

    def test_extracts_pdf_text(self) -> None:
        source = self.root / "resume.pdf"
        source.write_bytes(b"placeholder")

        class Page:
            def extract_text(self) -> str:
                return "PDFから抽出した職務経歴"

        class Reader:
            pages = [Page()]

        with patch("pypdf.PdfReader", return_value=Reader()):
            result = ingest(source, self.vault, self.archive)

        self.assertIn("PDFから抽出した職務経歴", result.created[0].read_text(encoding="utf-8"))

    def test_moves_managed_incoming_file_into_originals(self) -> None:
        incoming = self.archive / "incoming"
        incoming.mkdir(exist_ok=True)
        source = incoming / "resume.txt"
        source.write_text("職務経歴", encoding="utf-8")

        result = ingest(incoming, self.vault, self.archive)

        self.assertEqual(len(result.created), 1)
        self.assertFalse(source.exists())
        self.assertEqual(len(tuple((self.archive / "originals").iterdir())), 1)

    def test_keeps_one_archived_copy_for_identical_source_content(self) -> None:
        first = self.root / "resume-one.txt"
        second = self.root / "resume-two.txt"
        first.write_text("同じ内容", encoding="utf-8")
        second.write_text("同じ内容", encoding="utf-8")

        ingest(first, self.vault, self.archive)
        duplicate = ingest(second, self.vault, self.archive)

        self.assertEqual(duplicate.created, ())
        self.assertEqual(duplicate.skipped, (second,))
        self.assertEqual(len(tuple((self.archive / "originals").iterdir())), 1)
