"""Diagnostics and the edits that fix them."""

from dataclasses import dataclass
from enum import Enum

from pywsl.checks import BY_NAME


class FixKind(Enum):
    INSERT_BLANK_ABOVE = "insert-blank-above"
    REMOVE_BLANK_ABOVE = "remove-blank-above"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    name: str
    line: int
    column: int
    message: str
    fix: FixKind
    priority: int

    @property
    def fix_title(self) -> str:
        if self.fix is FixKind.INSERT_BLANK_ABOVE:
            return "Insert blank line"

        return "Remove blank line"


def make(
    name: str, line: int, column: int, fix: FixKind, **fields: object
) -> Diagnostic:
    check = BY_NAME[name]

    return Diagnostic(
        code=check.code,
        name=check.name,
        line=line,
        column=column,
        message=check.summary.format(**fields) if fields else check.summary,
        fix=fix,
        priority=check.priority,
    )


def dedupe(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    """Keep the most specific diagnostic per line and fix direction."""

    best: dict[tuple[int, FixKind], Diagnostic] = {}

    for diagnostic in diagnostics:
        key = (diagnostic.line, diagnostic.fix)
        current = best.get(key)

        if current is None or (diagnostic.priority, diagnostic.code) < (
            current.priority,
            current.code,
        ):
            best[key] = diagnostic

    return sorted(best.values(), key=lambda d: (d.line, d.column, d.code))
