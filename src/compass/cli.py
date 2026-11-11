from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
import sys

from compass.config import ConfigError, load_settings
from compass.company_research import (
    CompanyResearchError,
    refresh_companies,
    research_company,
    rollback_results,
)
from compass.ingest import IngestionError, ingest
from compass.runtime import Run, VaultLockedError
from compass.validation import validate
from compass.vault import initialise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local tooling for the compass Obsidian workspace")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/local.toml"),
        help="Path to local TOML configuration (default: config/local.toml)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    initialise_parser = commands.add_parser("init", help="Create the managed Vault and archive layout")
    initialise_parser.add_argument("--vault", type=Path, help="Obsidian Vault root")
    initialise_parser.add_argument("--archive", type=Path, help="Local compass archive root")

    validation_parser = commands.add_parser("validate", help="Validate compass Markdown notes")
    validation_parser.add_argument("--vault", type=Path, help="Obsidian Vault root")

    ingestion_parser = commands.add_parser("ingest", help="Archive supported files and create source notes")
    ingestion_parser.add_argument(
        "source",
        type=Path,
        nargs="?",
        help="File or directory to ingest (default: archive/incoming)",
    )
    ingestion_parser.add_argument("--vault", type=Path, help="Obsidian Vault root")
    ingestion_parser.add_argument("--archive", type=Path, help="Local compass archive root")
    company_parser = commands.add_parser("research-company", help="Research a public company URL into a company note")
    company_parser.add_argument("name")
    company_parser.add_argument("url")
    company_parser.add_argument("--vault", type=Path, help="Obsidian Vault root")
    refresh_parser = commands.add_parser("refresh-companies", help="Refresh company notes from their public source URLs")
    refresh_parser.add_argument("--vault", type=Path, help="Obsidian Vault root")
    schedule_parser = commands.add_parser("schedule-company-refresh", help="Write a macOS launchd plist for company refresh")
    schedule_parser.add_argument("--output", type=Path, required=True, help="Destination plist path")
    schedule_parser.add_argument("--hour", type=int, default=8, choices=range(24), help="Local execution hour (default: 8)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            settings = load_settings(
                args.config,
                vault_override=args.vault,
                archive_override=args.archive,
                require_archive=True,
            )
            template_root = Path(__file__).resolve().parents[2] / "templates"
            with Run("init") as run:
                result = initialise(settings.vault, _required_archive(settings.archive), template_root)
                run.add_summary(created=len(result.created), kept=len(result.skipped))
            _print_paths("Created", result.created)
            _print_paths("Kept", result.skipped)
            return 0

        if args.command == "ingest":
            settings = load_settings(
                args.config,
                vault_override=args.vault,
                archive_override=args.archive,
                require_archive=True,
            )
            with Run("ingest") as run:
                archive = _required_archive(settings.archive)
                result = ingest(args.source or archive / "incoming", settings.vault, archive)
                validation = validate(settings.vault)
                if validation.errors:
                    for note in result.created:
                        note.unlink(missing_ok=True)
                    raise IngestionError(
                        "Post-ingestion validation failed; created source notes were rolled back: "
                        + "; ".join(validation.errors)
                    )
                run.add_summary(created=len(result.created), skipped=len(result.skipped))
            _print_paths("Created", result.created)
            _print_paths("Skipped", result.skipped)
            return 0

        if args.command in {"research-company", "refresh-companies"}:
            settings = load_settings(args.config, vault_override=args.vault)
            with Run(args.command) as run:
                results = ()
                try:
                    if args.command == "research-company":
                        result = research_company(settings.vault, args.name, args.url)
                        results = (result,)
                    else:
                        results = refresh_companies(settings.vault)
                    validation = validate(settings.vault)
                    if validation.errors:
                        raise CompanyResearchError("Post-research validation failed: " + "; ".join(validation.errors))
                    run.add_summary(updated=len(results))
                    run.add_details(
                        targets=[result.url for result in results],
                        changed_notes=[str(result.note) for result in results],
                        validation="passed",
                    )
                except CompanyResearchError as error:
                    rollback_candidates = error.results or results
                    rollback_results(rollback_candidates)
                    targets = error.targets or ([args.url] if args.command == "research-company" else [result.url for result in results])
                    run.add_details(
                        targets=targets,
                        changed_notes=[str(result.note) for result in rollback_candidates],
                        validation="failed; changes rolled back",
                    )
                    raise
                except Exception:
                    rollback_results(results)
                    run.add_details(
                        targets=[args.url] if args.command == "research-company" else [result.url for result in results],
                        changed_notes=[str(result.note) for result in results],
                        validation="failed; changes rolled back",
                    )
                    raise
            _print_paths("Updated", tuple(result.note for result in results))
            return 0

        if args.command == "schedule-company-refresh":
            config_path = args.config.resolve()
            executable = Path(sys.executable).resolve()
            runtime_root = Path(__file__).resolve().parents[2] / ".runtime"
            runtime_root.mkdir(parents=True, exist_ok=True)
            payload = {
                "Label": "local.compass.company-refresh",
                "ProgramArguments": [str(executable), "-m", "compass", "--config", str(config_path), "refresh-companies"],
                "StartCalendarInterval": {"Hour": args.hour, "Minute": 0},
                "StandardOutPath": str(runtime_root / "company-refresh.log"),
                "StandardErrorPath": str(runtime_root / "company-refresh.error.log"),
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("wb") as handle:
                plistlib.dump(payload, handle)
            print(f"Created: {args.output}")
            return 0

        settings = load_settings(args.config, vault_override=args.vault)
        result = validate(settings.vault)
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if result.ok:
            print("Validation passed")
            return 0
        return 1
    except (ConfigError, FileNotFoundError, IngestionError, CompanyResearchError, PermissionError, VaultLockedError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


def _required_archive(archive: Path | None) -> Path:
    if archive is None:
        raise AssertionError("archive must be set when require_archive=True")
    return archive


def _print_paths(label: str, paths: tuple[Path, ...]) -> None:
    if not paths:
        return
    print(f"{label}:")
    for path in paths:
        print(f"  - {path}")
