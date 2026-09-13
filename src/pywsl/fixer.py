"""Applies diagnostics as blank-line edits."""

from __future__ import annotations

from dataclasses import dataclass

from pywsl import source as source_module
from pywsl.config import Config
from pywsl.diagnostics import Diagnostic, FixKind
from pywsl.engine import check_source
from pywsl.source import SourceFile

MAX_PASSES = 8


@dataclass(frozen=True)
class FixResult:
    text: str
    changed: bool
    initial: list[Diagnostic]
    remaining: list[Diagnostic]

    @property
    def fixed_count(self) -> int:
        return max(len(self.initial) - len(self.remaining), 0)


def fix(source: SourceFile, config: Config) -> FixResult:
    initial = check_source(source, config)
    original = _render(source)
    current = source
    text = original

    for _ in range(MAX_PASSES):
        found = check_source(current, config)
        if not found:
            break

        updated = apply(current, found)
        if updated == text:
            break

        text = updated
        current = source_module.from_text(text, current.path)

    return FixResult(
        text=text,
        changed=text != original,
        initial=initial,
        remaining=check_source(current, config),
    )


def apply(source: SourceFile, diagnostics: list[Diagnostic]) -> str:
    inserts = {d.line for d in diagnostics if d.fix is FixKind.INSERT_BLANK_ABOVE}
    deletions: set[int] = set()

    for diagnostic in diagnostics:
        if diagnostic.fix is not FixKind.REMOVE_BLANK_ABOVE:
            continue

        run = source.blank_run_above(diagnostic.line)
        if run is not None:
            deletions.update(range(run[0], run[1] + 1))

    output: list[str] = []

    for number, text in enumerate(source.lines, start=1):
        if number in deletions:
            continue

        if number in inserts:
            output.append("")

        output.append(text)

    return _join(output, source)


def _render(source: SourceFile) -> str:
    return _join(list(source.lines), source)


def _join(lines: list[str], source: SourceFile) -> str:
    text = source.newline.join(lines)
    if source.final_newline and text:
        text += source.newline

    return text
