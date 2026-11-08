from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import re
import shutil

import yaml


SUPPORTED_EXTENSIONS = {
    ".docx",
    ".html",
    ".htm",
    ".markdown",
    ".md",
    ".pdf",
    ".pptx",
    ".txt",
    ".xlsx",
}


class IngestionError(ValueError):
    """Raised when a source cannot be processed by the selected extractor."""


@dataclass(frozen=True)
class IngestionResult:
    created: tuple[Path, ...]
    skipped: tuple[Path, ...]


def ingest(source: Path, vault: Path, archive: Path) -> IngestionResult:
    """Archive supported local files and create source notes under `compass/inbox`."""
    managed_root = vault / "compass"
    inbox = managed_root / "inbox"
    originals = archive / "originals"
    if not inbox.is_dir():
        raise IngestionError("Compass Vault is not initialised. Run `compass init` first.")
    if not source.exists():
        raise IngestionError(f"Source does not exist: {source}")

    candidates = _source_files(source)
    existing_hashes = _existing_hashes(inbox)
    created: list[Path] = []
    skipped: list[Path] = []
    originals.mkdir(parents=True, exist_ok=True)

    for candidate in candidates:
        content = candidate.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        archive_path = originals / f"{digest[:16]}--{candidate.name}"
        if not archive_path.exists():
            shutil.copy2(candidate, archive_path)

        if digest in existing_hashes:
            skipped.append(candidate)
            continue

        extracted_text, source_format = _extract(candidate, content)
        note = inbox / f"{digest[:16]}--{_slug(candidate.stem)}.md"
        note.write_text(
            _source_note(
                original_name=candidate.name,
                archive_path=archive_path,
                content_hash=digest,
                source_format=source_format,
                extracted_text=extracted_text,
            ),
            encoding="utf-8",
        )
        created.append(note)
        existing_hashes.add(digest)

    return IngestionResult(tuple(created), tuple(skipped))


def _source_files(source: Path) -> tuple[Path, ...]:
    if source.is_file():
        _ensure_supported(source)
        return (source,)
    candidates = tuple(
        path for path in sorted(source.rglob("*")) if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not candidates:
        raise IngestionError(f"No supported files found in: {source}")
    return candidates


def _ensure_supported(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        extensions = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise IngestionError(f"Unsupported file type: {path.suffix or '(none)'}. Supported: {extensions}")


def _extract(path: Path, content: bytes) -> tuple[str, str]:
    extension = path.suffix.lower()
    if extension == ".pdf":
        return _extract_pdf(path), "pdf"
    if extension == ".docx":
        return _extract_docx(path), "docx"
    if extension == ".pptx":
        return _extract_pptx(path), "pptx"
    if extension == ".xlsx":
        return _extract_xlsx(path), "xlsx"
    text = _decode(content, path)
    if extension in {".html", ".htm"}:
        parser = _HTMLTextExtractor()
        parser.feed(text)
        return _normalise_text("".join(parser.parts)), "html"
    return _normalise_text(text), "text"


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(path)
        return _normalise_text("\n\n".join(page.extract_text() or "" for page in reader.pages))
    except Exception as error:  # pypdf exposes several format-specific exception types.
        raise IngestionError(f"Cannot extract PDF text from {path}: {error}") from error


def _extract_docx(path: Path) -> str:
    from docx import Document

    document = Document(path)
    sections = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            values = [cell.text.strip() for cell in row.cells]
            if any(values):
                sections.append(" | ".join(values))
    return _normalise_text("\n".join(sections))


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation

    presentation = Presentation(path)
    sections: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        values: list[str] = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                text = shape.text.strip()
                if text:
                    values.append(text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    row_values = [cell.text.strip() for cell in row.cells]
                    if any(row_values):
                        values.append(" | ".join(row_values))
        if values:
            sections.append(f"# Slide {index}\n" + "\n".join(values))
    return _normalise_text("\n\n".join(sections))


def _extract_xlsx(path: Path) -> str:
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    sections: list[str] = []
    for sheet in workbook.worksheets:
        rows: list[str] = []
        for row in sheet.iter_rows(values_only=True):
            values = ["" if value is None else str(value) for value in row]
            if any(values):
                rows.append(" | ".join(values))
        if rows:
            sections.append(f"# Sheet: {sheet.title}\n" + "\n".join(rows))
    return _normalise_text("\n\n".join(sections))


def _decode(content: bytes, path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise IngestionError(f"Cannot decode text file: {path}")


def _existing_hashes(inbox: Path) -> set[str]:
    hashes: set[str] = set()
    for note in inbox.glob("*.md"):
        match = re.search(r"^content_sha256:\s*['\"]?([0-9a-f]{64})['\"]?\s*$", note.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            hashes.add(match.group(1))
    return hashes


def _source_note(
    *,
    original_name: str,
    archive_path: Path,
    content_hash: str,
    source_format: str,
    extracted_text: str,
) -> str:
    metadata = {
        "type": "source",
        "original_name": original_name,
        "archive_file": str(archive_path),
        "content_sha256": content_hash,
        "source_format": source_format,
        "extracted_at": datetime.now(UTC).isoformat(),
    }
    frontmatter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{frontmatter}\n---\n\n# {original_name}\n\n## 抽出テキスト\n\n{extracted_text}\n"


def _normalise_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug or "source"


class _HTMLTextExtractor(HTMLParser):
    BLOCK_TAGS = {"article", "br", "div", "h1", "h2", "h3", "h4", "li", "p", "section", "table", "tr"}
    IGNORED_TAGS = {"script", "style"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.IGNORED_TAGS:
            self._ignored_depth += 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)
