from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


class ConfigError(ValueError):
    """Raised when local configuration is missing or malformed."""


@dataclass(frozen=True)
class Settings:
    vault: Path
    archive: Path | None = None


def load_settings(
    config_path: Path,
    *,
    vault_override: Path | None = None,
    archive_override: Path | None = None,
    require_archive: bool = False,
) -> Settings:
    values: dict[str, object] = {}
    if config_path.exists():
        with config_path.open("rb") as handle:
            document = tomllib.load(handle)
        paths = document.get("paths", {})
        if not isinstance(paths, dict):
            raise ConfigError("[paths] must be a table")
        values = paths

    vault_value = vault_override or _path_value(values.get("vault"), config_path)
    archive_value = archive_override or _path_value(values.get("archive"), config_path)
    if vault_value is None:
        raise ConfigError(
            "Vault path is required. Set [paths].vault in config/local.toml or pass --vault."
        )
    if require_archive and archive_value is None:
        raise ConfigError(
            "Archive path is required. Set [paths].archive in config/local.toml or pass --archive."
        )
    return Settings(vault=vault_value, archive=archive_value)


def _path_value(value: object, config_path: Path) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("Configured paths must be non-empty strings")
    path = Path(value).expanduser()
    return path if path.is_absolute() else (config_path.parent / path).resolve()
