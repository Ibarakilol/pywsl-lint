"""Finding the Python files to check."""

import os
from collections.abc import Iterable
from fnmatch import fnmatch
from pathlib import Path

from pywsl_lint.config import Config

SUFFIXES = frozenset({".py", ".pyi"})


def collect(
    paths: Iterable[str | Path], config: Config, *, force_exclude: bool = False
) -> list[Path]:
    patterns = (*config.exclude, *config.extend_exclude)
    found: list[Path] = []
    seen: set[Path] = set()

    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found.extend(_walk(path, patterns))
        elif not force_exclude or not _excluded(path, Path(), patterns):
            found.append(path)

    return [p for p in found if not (p in seen or seen.add(p))]


def _walk(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    found: list[Path] = []

    for directory, subdirs, files in os.walk(root):
        base = Path(directory)
        subdirs[:] = sorted(
            d for d in subdirs if not _excluded(base / d, root, patterns)
        )

        for name in sorted(files):
            path = base / name
            if path.suffix in SUFFIXES and not _excluded(path, root, patterns):
                found.append(path)

    return found


def _excluded(path: Path, root: Path, patterns: tuple[str, ...]) -> bool:
    relative = path.relative_to(root) if path.is_relative_to(root) else path
    parts = relative.parts

    return any(
        fnmatch(relative.as_posix(), pattern)
        or any(fnmatch(part, pattern) for part in parts)
        for pattern in patterns
    )
