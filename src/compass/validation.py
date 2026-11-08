from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


REQUIRED_FIELDS = {
    "career": {"type", "employer", "employment_type", "period_start", "visibility"},
    "project": {"type", "scope", "visibility"},
    "achievement": {"type", "project", "visibility"},
    "company": {"type", "labels"},
    "job": {"type", "company", "position", "status", "source_urls", "retrieved_at"},
    "scout": {"type", "company", "medium", "status"},
    "application": {"type", "company", "job", "medium", "position", "status"},
    "interview": {"type", "company", "application", "stage", "status"},
}
VALID_VISIBILITIES = {"internal", "review", "external-safe"}
VALID_STATUSES = {
    "job": {"active", "inactive"},
    "scout": {"new", "considering", "declined", "promoted"},
    "application": {"pre-application", "applied", "in-progress", "offer", "rejected", "withdrawn"},
    "interview": {"planned", "completed"},
}
WIKILINK_PATTERN = re.compile(r"!?(?:\[\[)([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(vault: Path) -> ValidationResult:
    managed_root = vault / "compass"
    if not managed_root.is_dir():
        return ValidationResult(
            errors=(f"Managed Vault directory does not exist: {managed_root}",), warnings=()
        )

    notes = tuple(managed_root.rglob("*.md"))
    known_targets = _known_targets(notes, managed_root)
    errors: list[str] = []
    warnings: list[str] = []

    for note in notes:
        relative = note.relative_to(managed_root)
        if relative.parts and relative.parts[0] == "templates":
            continue
        content = note.read_text(encoding="utf-8")
        data, parse_error = _frontmatter(content)
        if parse_error:
            errors.append(f"{relative}: {parse_error}")
            continue
        if data is not None:
            _validate_data(relative, data, errors)
        _validate_links(relative, content, known_targets, warnings)

    return ValidationResult(tuple(errors), tuple(warnings))


def _frontmatter(content: str) -> tuple[dict[str, object] | None, str | None]:
    if not content.startswith("---\n"):
        return None, None
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return None, "Frontmatter closing delimiter is missing"
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as error:
        return None, f"Invalid YAML Frontmatter: {error.problem}"
    if data is None:
        return {}, None
    if not isinstance(data, dict):
        return None, "Frontmatter must be a YAML mapping"
    return data, None


def _validate_data(relative: Path, data: dict[str, object], errors: list[str]) -> None:
    note_type = data.get("type")
    if note_type not in REQUIRED_FIELDS:
        return
    missing = sorted(field for field in REQUIRED_FIELDS[note_type] if not _has_value(data.get(field)))
    if missing:
        errors.append(f"{relative}: missing required properties: {', '.join(missing)}")
    visibility = data.get("visibility")
    if visibility is not None and visibility not in VALID_VISIBILITIES:
        errors.append(f"{relative}: invalid visibility: {visibility!r}")
    valid_statuses = VALID_STATUSES.get(note_type)
    if valid_statuses and data.get("status") not in valid_statuses:
        errors.append(f"{relative}: invalid {note_type} status: {data.get('status')!r}")
    for property_name in ("industry", "labels", "research_sources", "skills", "source_refs", "source_urls"):
        value = data.get(property_name)
        if value is not None and not isinstance(value, list):
            errors.append(f"{relative}: {property_name} must be a list")


def _has_value(value: object) -> bool:
    return value is not None and value != "" and value != []


def _known_targets(notes: tuple[Path, ...], root: Path) -> set[str]:
    targets: set[str] = set()
    for note in notes:
        relative = note.relative_to(root).with_suffix("")
        targets.add(relative.as_posix())
        targets.add(note.stem)
    return targets


def _validate_links(
    relative: Path, content: str, known_targets: set[str], warnings: list[str]
) -> None:
    for target in WIKILINK_PATTERN.findall(content):
        normalized = target.strip().removesuffix(".md")
        if normalized and normalized not in known_targets:
            warnings.append(f"{relative}: unresolved link: [[{target}]]")
