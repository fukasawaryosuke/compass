from pathlib import Path
import importlib.util
import tempfile
import unittest

from compass.job_preview import JobPreviewError, preview_local_job


class JobPreviewTests(unittest.TestCase):
    def test_rejects_remote_urls(self) -> None:
        with self.assertRaises(JobPreviewError):
            preview_local_job(Path("https://offers.jp/jobs/123"))

    @unittest.skipUnless(importlib.util.find_spec("playwright"), "optional Playwright dependency is not installed")
    def test_extracts_only_selected_fields_without_running_page_script(self) -> None:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            if not Path(playwright.chromium.executable_path).exists():
                self.skipTest("Playwright Chromium is not installed")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.html"
            source.write_text('''<script type="application/ld+json">{"@type":"JobPosting","title":"Backend", "hiringOrganization":{"name":"Example"},"description":"private text"}</script>
<script>document.querySelector('[type="application/ld+json"]').textContent = '{}';</script>''', encoding="utf-8")
            self.assertEqual(preview_local_job(source), {"title": "Backend", "company": "Example"})


if __name__ == "__main__":
    unittest.main()
