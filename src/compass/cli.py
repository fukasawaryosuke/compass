from __future__ import annotations

import argparse
from pathlib import Path
import sys

from compass.config import ConfigError, load_settings
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
            result = initialise(settings.vault, _required_archive(settings.archive), template_root)
            _print_paths("Created", result.created)
            _print_paths("Kept", result.skipped)
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
    except (ConfigError, FileNotFoundError, PermissionError) as error:
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
