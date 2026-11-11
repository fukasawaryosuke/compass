from __future__ import annotations

from contextlib import redirect_stderr
from email.message import Message
import io
import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

from compass.cli import main
from compass.company_research import CompanyResearchError, refresh_companies, research_company
from compass.runtime import Run


class _Response:
    def __init__(self, html: str, url: str = "https://example.com/") -> None:
        self._html = html.encode()
        self._url = url
        self.headers = Message()
        self.headers.add_header("Content-Type", "text/html", charset="utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        return self._html[:size]

    def geturl(self) -> str:
        return self._url


class CompanyResearchTests(unittest.TestCase):
    def test_creates_company_note_with_a_managed_research_section(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault = Path(temporary_directory)
            response = _Response('<meta name="description" content="Example summary">')
            with patch("compass.company_research._fetch_public_document", return_value=(response.read(1_000_000), "utf-8")):
                result = research_company(vault, "Example", "https://example.com/")

            content = result.note.read_text(encoding="utf-8")
            self.assertIn("research_sources:", content)
            self.assertIn("https://example.com/", content)
            self.assertIn("Example summary", content)
            self.assertIn("<!-- compass:company-research:start -->", content)

    def test_updates_prefixed_note_without_removing_user_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            companies = Path(temporary_directory) / "compass" / "job-search" / "companies"
            companies.mkdir(parents=True)
            note = companies / "03_Example.md"
            note.write_text(
                "---\ntype: company\nlabels: [watchlist]\n---\n\n# Example\n\n## 利用者の所感\n\n残す文章\n",
                encoding="utf-8",
            )

            with patch("compass.company_research._fetch_public_document", return_value=(b"<title>Example</title>", "utf-8")):
                result = research_company(Path(temporary_directory), "Example", "https://example.com/")

            self.assertEqual(result.note, note)
            self.assertFalse((companies / "Example.md").exists())
            self.assertIn("残す文章", note.read_text(encoding="utf-8"))

    def test_rejects_non_public_or_non_https_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaises(CompanyResearchError):
                research_company(Path(temporary_directory), "Example", "http://example.com/")
            with self.assertRaises(CompanyResearchError):
                research_company(Path(temporary_directory), "Example", "https://127.0.0.1/")

    def test_rejects_hostname_resolving_to_a_private_address(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch("compass.company_research.socket.getaddrinfo", return_value=[(0, 0, 0, "", ("127.0.0.1", 443))]):
                with self.assertRaises(CompanyResearchError):
                    research_company(Path(temporary_directory), "Example", "https://internal.example/")

    def test_refresh_rolls_back_prior_notes_when_later_fetch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault = Path(temporary_directory)
            companies = vault / "compass" / "job-search" / "companies"
            companies.mkdir(parents=True)
            first = companies / "First.md"
            second = companies / "Second.md"
            for note, url in ((first, "https://first.example/"), (second, "https://second.example/")):
                note.write_text(
                    f"---\ntype: company\nlabels: [watchlist]\nresearch_sources: [{url}]\n---\n\n# {note.stem}\n",
                    encoding="utf-8",
                )
            original = first.read_bytes()

            with patch("compass.company_research._fetch_summary", side_effect=["updated", CompanyResearchError("failed")]):
                with self.assertRaises(CompanyResearchError):
                    refresh_companies(vault)

            self.assertEqual(first.read_bytes(), original)

    def test_refresh_keeps_research_for_every_source_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault = Path(temporary_directory)
            companies = vault / "compass" / "job-search" / "companies"
            companies.mkdir(parents=True)
            note = companies / "Example.md"
            note.write_text(
                "---\ntype: company\nlabels: [watchlist]\nresearch_sources: [https://one.example/, https://two.example/]\n---\n\n# Example\n",
                encoding="utf-8",
            )

            with patch("compass.company_research._fetch_summary", side_effect=["first", "second"]):
                refresh_companies(vault)

            content = note.read_text(encoding="utf-8")
            self.assertIn("https://one.example/", content)
            self.assertIn("first", content)
            self.assertIn("https://two.example/", content)
            self.assertIn("second", content)

    def test_failed_validation_rolls_back_and_records_operation_details(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            vault = root / "vault"
            (vault / "compass").mkdir(parents=True)
            (vault / "compass" / "invalid.md").write_text("---\ntype: job\n---\n# Invalid\n", encoding="utf-8")
            config = root / "local.toml"
            config.write_text(f'[paths]\nvault = "{vault}"\n', encoding="utf-8")
            runtime_root = root / "runtime"

            with patch("compass.company_research._fetch_summary", return_value="summary"), patch(
                "compass.cli.Run", side_effect=lambda operation: Run(operation, runtime_root=runtime_root)
            ), redirect_stderr(io.StringIO()):
                exit_code = main(["--config", str(config), "research-company", "Example", "https://example.com/"])

            record = json.loads(next((runtime_root / "runs").glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 2)
            self.assertFalse((vault / "compass" / "job-search" / "companies" / "Example.md").exists())
            self.assertEqual(record["targets"], ["https://example.com/"])
            self.assertEqual(record["validation"], "failed; changes rolled back")

    def test_schedule_uses_absolute_runtime_paths_and_module_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "job.plist"
            exit_code = main(["schedule-company-refresh", "--output", str(output), "--hour", "9"])
            with output.open("rb") as handle:
                payload = plistlib.load(handle)

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["ProgramArguments"][1:3], ["-m", "compass"])
            self.assertTrue(Path(payload["StandardOutPath"]).is_absolute())
            self.assertTrue(Path(payload["StandardErrorPath"]).is_absolute())
            self.assertTrue(Path(payload["StandardOutPath"]).parent.is_dir())
