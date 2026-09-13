"""Configuration loading for pywsl."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from pywsl import checks

DEFAULT_EXCLUDE: tuple[str, ...] = (
    ".bzr",
    ".direnv",
    ".eggs",
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pypackages__",
    "_build",
    "build",
    "dist",
    "node_modules",
    "venv",
)


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    enabled: frozenset[str] = checks.DEFAULT_CHECKS
    allow_first_in_block: bool = True
    allow_whole_block: bool = False
    branch_max_lines: int = 2
    case_max_lines: int = 0
    cuddle_max_statements: int = 1
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    extend_exclude: tuple[str, ...] = field(default_factory=tuple)

    def is_enabled(self, name: str) -> bool:
        return name in self.enabled


_BOOL_KEYS = {"allow-first-in-block", "allow-whole-block"}
_INT_KEYS = {"branch-max-lines", "case-max-lines", "cuddle-max-statements"}
_LIST_KEYS = {"select", "extend-select", "ignore", "exclude", "extend-exclude"}


def find_pyproject(start: Path) -> Path | None:
    start = start.resolve()
    directory = start if start.is_dir() else start.parent

    for candidate in (directory, *directory.parents):
        pyproject = candidate / "pyproject.toml"
        if pyproject.is_file():
            return pyproject

    return None


def load(path: Path | None) -> Config:
    if path is None:
        return Config()

    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{path}: {error}") from error

    table = raw.get("tool", {}).get("pywsl")
    if table is None:
        return Config()

    if not isinstance(table, dict):
        raise ConfigError(f"{path}: [tool.pywsl] must be a table")

    return from_table(table, origin=str(path))


def from_table(table: dict[str, Any], origin: str = "<config>") -> Config:
    normalised = {key.replace("_", "-"): value for key, value in table.items()}
    unknown = set(normalised) - _BOOL_KEYS - _INT_KEYS - _LIST_KEYS

    if unknown:
        raise ConfigError(f"{origin}: unknown option(s): {', '.join(sorted(unknown))}")

    config = Config()

    for key in _BOOL_KEYS & set(normalised):
        value = normalised[key]
        if not isinstance(value, bool):
            raise ConfigError(f"{origin}: {key} must be a boolean")

        config = replace(config, **{key.replace("-", "_"): value})

    for key in _INT_KEYS & set(normalised):
        value = normalised[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ConfigError(f"{origin}: {key} must be a non-negative integer")

        config = replace(config, **{key.replace("-", "_"): value})

    for key in _LIST_KEYS & set(normalised):
        value = normalised[key]
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise ConfigError(f"{origin}: {key} must be a list of strings")

    return apply_selectors(
        config,
        select=normalised.get("select"),
        extend_select=normalised.get("extend-select"),
        ignore=normalised.get("ignore"),
        exclude=normalised.get("exclude"),
        extend_exclude=normalised.get("extend-exclude"),
        origin=origin,
    )


def apply_selectors(
    config: Config,
    *,
    select: list[str] | None = None,
    extend_select: list[str] | None = None,
    ignore: list[str] | None = None,
    exclude: list[str] | None = None,
    extend_exclude: list[str] | None = None,
    origin: str = "<config>",
) -> Config:
    enabled = set(config.enabled)
    if select is not None:
        enabled = _expand(select, origin)

    if extend_select:
        enabled |= _expand(extend_select, origin)

    if ignore:
        enabled -= _expand(ignore, origin)

    if exclude is not None:
        config = replace(config, exclude=tuple(exclude))

    if extend_exclude:
        config = replace(
            config, extend_exclude=config.extend_exclude + tuple(extend_exclude)
        )

    return replace(config, enabled=frozenset(enabled))


def _expand(selectors: list[str], origin: str) -> set[str]:
    names: set[str] = set()
    for selector in selectors:
        try:
            names |= checks.resolve(selector)
        except KeyError as error:
            raise ConfigError(f"{origin}: unknown check {error.args[0]!r}") from None

    return names
