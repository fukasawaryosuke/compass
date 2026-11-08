from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil


MANAGED_DIRECTORY = "compass"
DIRECTORIES = (
    "inbox",
    "drafts",
    "profile",
    "career/employers",
    "projects",
    "achievements",
    "job-search/companies",
    "job-search/jobs",
    "job-search/applications",
    "job-search/interviews",
    "job-search/scouts",
    "job-search/exclusions",
    "sources",
    "templates",
)
TEMPLATE_FILENAMES = (
    "achievement.md",
    "application.md",
    "career.md",
    "company.md",
    "interview.md",
    "job.md",
    "project.md",
    "scout.md",
)


@dataclass(frozen=True)
class InitResult:
    created: tuple[Path, ...]
    skipped: tuple[Path, ...]


def initialise(vault: Path, archive: Path, template_root: Path) -> InitResult:
    """Create the managed Vault and archive layout without overwriting user files."""
    managed_root = vault / MANAGED_DIRECTORY
    created: list[Path] = []
    skipped: list[Path] = []

    for relative_path in DIRECTORIES:
        path = managed_root / relative_path
        if path.exists():
            skipped.append(path)
        else:
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)

    for relative_path in ("originals", "exports"):
        path = archive / relative_path
        if path.exists():
            skipped.append(path)
        else:
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)

    home = managed_root / "Home.md"
    _write_if_missing(home, home_content(), created, skipped)

    for filename in TEMPLATE_FILENAMES:
        source = template_root / filename
        if not source.is_file():
            raise FileNotFoundError(f"Template is missing from repository: {source}")
        destination = managed_root / "templates" / filename
        if destination.exists():
            skipped.append(destination)
        else:
            shutil.copyfile(source, destination)
            created.append(destination)

    return InitResult(tuple(created), tuple(skipped))


def home_content() -> str:
    return """# compass Home

## 有効求人

```dataview
TABLE annual_income_min AS \"年収下限\", skills AS \"技術\", score AS \"評価\"
FROM \"compass/job-search/jobs\"
WHERE status = \"active\"
SORT score DESC
```

## 気になる企業

```dataview
TABLE labels AS \"ラベル\", industry AS \"業界\"
FROM \"compass/job-search/companies\"
WHERE contains(labels, \"watchlist\") OR contains(labels, \"researching\") OR contains(labels, \"target\")
SORT file.name ASC
```

## 選考中の応募

```dataview
TABLE company AS \"企業\", position AS \"ポジション\", status AS \"状態\"
FROM \"compass/job-search/applications\"
WHERE status = \"in-progress\"
SORT file.name ASC
```
"""


def _write_if_missing(
    path: Path, content: str, created: list[Path], skipped: list[Path]
) -> None:
    if path.exists():
        skipped.append(path)
        return
    path.write_text(content, encoding="utf-8")
    created.append(path)
