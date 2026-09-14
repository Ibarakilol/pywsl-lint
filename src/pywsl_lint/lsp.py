"""Turning diagnostics into the ranges and edits an editor needs.

Kept free of any language-server dependency so the core package needs none.
"""

from dataclasses import dataclass

from pywsl_lint.config import Config
from pywsl_lint.diagnostics import Diagnostic, FixKind
from pywsl_lint.fixer import fix
from pywsl_lint.source import SourceFile


@dataclass(frozen=True)
class Span:
    """A half-open range in zero-based line/character coordinates."""

    start_line: int
    start_char: int
    end_line: int
    end_char: int


@dataclass(frozen=True)
class Edit:
    span: Span
    new_text: str


def highlight(source: SourceFile, diagnostic: Diagnostic) -> Span:
    line = diagnostic.line
    if line > source.line_count:
        return Span(max(line - 1, 0), 0, max(line - 1, 0), 0)

    text = source.line(line)
    start = len(text) - len(text.lstrip())

    return Span(line - 1, start, line - 1, max(len(text), start + 1))


def edit_for(source: SourceFile, diagnostic: Diagnostic) -> Edit | None:
    if diagnostic.fix is FixKind.INSERT_BLANK_ABOVE:
        at = diagnostic.line - 1

        return Edit(Span(at, 0, at, 0), source.newline)

    run = source.blank_run_above(diagnostic.line)
    if run is None:
        return None

    first, last = run

    return Edit(Span(first - 1, 0, last, 0), "")


def format_edit(source: SourceFile, config: Config) -> Edit | None:
    result = fix(source, config)
    if not result.changed:
        return None

    return Edit(whole(source), result.text)


def whole(source: SourceFile) -> Span:
    if source.final_newline or not source.lines:
        return Span(0, 0, source.line_count, 0)

    return Span(0, 0, source.line_count - 1, len(source.lines[-1]))
