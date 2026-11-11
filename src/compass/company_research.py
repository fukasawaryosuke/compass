from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
import http.client
import ipaddress
from pathlib import Path
import re
import socket
import ssl
from urllib.parse import urljoin, urlparse

import yaml


class CompanyResearchError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        results: tuple["CompanyResearchResult", ...] = (),
        targets: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.results = results
        self.targets = targets


@dataclass(frozen=True)
class CompanyResearchResult:
    note: Path
    url: str
    previous_content: bytes | None


_RESEARCH_START = "<!-- compass:company-research:start -->"
_RESEARCH_END = "<!-- compass:company-research:end -->"
_PREFIX_PATTERN = re.compile(r"^\d+_")


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, server_hostname: str, address: str, port: int) -> None:
        super().__init__(address, port=port, timeout=20, context=ssl.create_default_context())
        self._server_hostname = server_hostname

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self._server_hostname)


class _PageSummary(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self._inside_title = False
        self._ignored_depth = 0
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if tag == "title":
            self._inside_title = True
        if tag == "meta" and attributes.get("name") == "description":
            self.description = attributes.get("content") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1
        if tag == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._inside_title:
            self.title += text
        self._text.append(text)

    def summary(self) -> str:
        source = self.description or " ".join(self._text)
        return re.sub(r"\s+", " ", source).strip()[:600]


def research_company(vault: Path, name: str, url: str) -> CompanyResearchResult:
    summary = _fetch_summary(url)
    companies = vault / "compass" / "job-search" / "companies"
    companies.mkdir(parents=True, exist_ok=True)
    note = _find_company_note(companies, name) or companies / f"{_safe_name(name)}.md"
    previous_content = note.read_bytes() if note.exists() else None
    timestamp = datetime.now(UTC).date().isoformat()
    data, body = _read_note(note)
    sources = list(data.get("research_sources", []))
    if url not in sources:
        sources.append(url)
    data.update(
        {
            "type": "company",
            "labels": data.get("labels") or ["researching"],
            "industry": data.get("industry") or [],
            "research_sources": sources,
            "retrieved_at": timestamp,
        }
    )
    if not body:
        body = f"# {name}\n\n## 事業・主要プロダクト\n\n## 開発組織\n\n## 成長性・収益性の調査メモ\n"
    body = _replace_managed_research(body, timestamp, url, summary)
    note.write_text(
        "---\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False).strip() + "\n---\n\n" + body.lstrip(),
        encoding="utf-8",
    )
    return CompanyResearchResult(note=note, url=url, previous_content=previous_content)


def refresh_companies(vault: Path) -> tuple[CompanyResearchResult, ...]:
    results: list[CompanyResearchResult] = []
    targets: list[str] = []
    try:
        for note in (vault / "compass" / "job-search" / "companies").glob("*.md"):
            data, body = _read_note(note)
            for url in data.get("research_sources", []):
                if isinstance(url, str) and url.startswith("https://"):
                    targets.append(url)
                    results.append(research_company(vault, _title(body) or note.stem, url))
    except Exception as error:
        rollback_results(results)
        raise CompanyResearchError(
            str(error), results=tuple(results), targets=tuple(targets)
        ) from error
    return tuple(results)


def rollback_results(results: tuple[CompanyResearchResult, ...] | list[CompanyResearchResult]) -> None:
    """Restore only notes touched by the current company-research operation."""
    originals: dict[Path, bytes | None] = {}
    for result in results:
        originals.setdefault(result.note, result.previous_content)
    for note, original in originals.items():
        if original is None:
            note.unlink(missing_ok=True)
        else:
            note.write_bytes(original)


def _fetch_summary(url: str) -> str:
    try:
        document, charset = _fetch_public_document(url)
    except (OSError, http.client.HTTPException) as error:
        raise CompanyResearchError(f"Could not fetch {url}: {error}") from error
    parser = _PageSummary()
    parser.feed(document.decode(charset, errors="replace"))
    return parser.summary() or "公開ページから要約可能な本文を取得できませんでした。"


def _fetch_public_document(url: str) -> tuple[bytes, str]:
    current_url = url
    for _ in range(4):
        parsed, address = _resolve_public_https_url(current_url)
        port = parsed.port or 443
        target = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
        connection = _PinnedHTTPSConnection(parsed.hostname or "", address, port)
        try:
            connection.request("GET", target, headers={"Host": parsed.netloc, "User-Agent": "compass-career/0.1 (+local research)"})
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise CompanyResearchError(f"Redirect response from {current_url} has no Location header.")
                current_url = urljoin(current_url, location)
                continue
            if response.status >= 400:
                raise CompanyResearchError(f"Could not fetch {current_url}: HTTP {response.status}")
            return response.read(1_000_000), response.headers.get_content_charset() or "utf-8"
        finally:
            connection.close()
    raise CompanyResearchError("Company research stopped after too many redirects.")


def _resolve_public_https_url(url: str) -> tuple[object, str]:
    parsed = urlparse(url)
    host = parsed.hostname
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise CompanyResearchError("Company research requires a public HTTPS URL.")
    if host.casefold() in {"localhost", "localhost.localdomain"}:
        raise CompanyResearchError("Company research does not allow localhost URLs.")
    try:
        resolved = {str(ipaddress.ip_address(host))}
    except ValueError:
        try:
            addresses = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
        except OSError as error:
            raise CompanyResearchError(f"Could not resolve {host}: {error}") from error
        resolved = {item[4][0] for item in addresses}
    if not resolved or any(not ipaddress.ip_address(address).is_global for address in resolved):
        raise CompanyResearchError("Company research does not allow non-public IP addresses.")
    return parsed, sorted(resolved)[0]


def _read_note(note: Path) -> tuple[dict[str, object], str]:
    if not note.exists():
        return {}, ""
    content = note.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return {}, content
    _, raw, body = content.split("---\n", 2)
    return yaml.safe_load(raw) or {}, body.lstrip("\n")


def _replace_managed_research(body: str, timestamp: str, url: str, summary: str) -> str:
    entries = _managed_research_entries(body)
    entries[url] = (timestamp, summary)
    sections = "\n\n".join(
        f"### 調査元: {source_url}\n取得日: {retrieved_at}\n\n- {source_summary}"
        for source_url, (retrieved_at, source_summary) in entries.items()
    )
    section = f"{_RESEARCH_START}\n## 調査メモ\n\n{sections}\n{_RESEARCH_END}\n"
    start = body.find(_RESEARCH_START)
    end = body.find(_RESEARCH_END, start + len(_RESEARCH_START)) if start >= 0 else -1
    if start >= 0 and end >= 0:
        return body[:start].rstrip() + "\n\n" + section + body[end + len(_RESEARCH_END):].lstrip("\n")
    return body.rstrip() + "\n\n" + section


def _managed_research_entries(body: str) -> dict[str, tuple[str, str]]:
    start = body.find(_RESEARCH_START)
    end = body.find(_RESEARCH_END, start + len(_RESEARCH_START)) if start >= 0 else -1
    if start < 0 or end < 0:
        return {}
    managed = body[start + len(_RESEARCH_START):end]
    matches = re.finditer(
        r"^### 調査元: (?P<url>\S+)\n取得日: (?P<date>[^\n]+)\n\n- (?P<summary>.*?)(?=\n### 調査元:|\Z)",
        managed,
        re.MULTILINE | re.DOTALL,
    )
    return {
        match.group("url"): (match.group("date"), match.group("summary").strip())
        for match in matches
    }


def _find_company_note(companies: Path, name: str) -> Path | None:
    normalized_name = _normalize_company_name(name)
    for note in companies.glob("*.md"):
        _, body = _read_note(note)
        if _normalize_company_name(_title(body)) == normalized_name:
            return note
        if _normalize_company_name(note.stem) == normalized_name:
            return note
    return None


def _normalize_company_name(value: str) -> str:
    return _PREFIX_PATTERN.sub("", value).strip()


def _title(body: str) -> str:
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _safe_name(value: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", value).strip() or "company"
