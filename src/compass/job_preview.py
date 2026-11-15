from __future__ import annotations

import json
from pathlib import Path


class JobPreviewError(ValueError):
    pass


def preview_local_job(source: Path) -> dict[str, str]:
    """Extract limited fields from a user-supplied local HTML file, without networking."""
    if source.suffix.lower() not in {".html", ".htm"} or not source.is_file():
        raise JobPreviewError("A local HTML file is required.")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise JobPreviewError("Install the optional browser dependency: pip install -e '.[browser]'") from error
    html = source.read_text(encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(java_script_enabled=False, service_workers="block")
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(html, wait_until="domcontentloaded")
            for raw in page.locator('script[type="application/ld+json"]').all_text_contents():
                try:
                    data = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        org = item.get("hiringOrganization")
                        return {
                            "title": str(item.get("title") or ""),
                            "company": str(org.get("name") or "") if isinstance(org, dict) else "",
                        }
            title = page.locator("h1").first
            return {"title": title.inner_text() if title.count() else "", "company": ""}
        finally:
            browser.close()
