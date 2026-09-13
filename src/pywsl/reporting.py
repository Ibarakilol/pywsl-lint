"""Rendering diagnostics in the supported output formats."""

import json
from collections import Counter
from collections.abc import Iterable, Sequence

from pywsl.diagnostics import Diagnostic
from pywsl.source import SourceFile

FORMATS = ("full", "concise", "json", "github")


def render(
    entries: Sequence[tuple[SourceFile, list[Diagnostic]]], output_format: str
) -> str:
    if output_format == "json":
        return _json(entries)

    lines: list[str] = []
    for source, found in entries:
        for diagnostic in found:
            if output_format == "github":
                lines.append(_github(source, diagnostic))
            elif output_format == "concise":
                lines.append(_concise(source, diagnostic))
            else:
                lines.extend(_full(source, diagnostic))

    return "\n".join(lines)


def summary(total: int, *, fixed: int = 0, fixable: int = 0) -> str:
    lines: list[str] = []

    if fixed:
        noun = "error" if fixed == 1 else "errors"
        lines.append(f"Fixed {fixed} {noun}.")

    if total:
        noun = "error" if total == 1 else "errors"
        lines.append(f"Found {total} {noun}.")
    elif not fixed:
        lines.append("All checks passed!")

    if fixable:
        lines.append(f"[*] {fixable} fixable with the `--fix` option.")

    return "\n".join(lines)


def statistics(found: Iterable[Diagnostic]) -> str:
    counts = Counter((d.code, d.name) for d in found)
    if not counts:
        return ""

    width = max(len(str(count)) for count in counts.values())

    return "\n".join(
        f"{count:>{width}}\t{code}\t[*] {name}"
        for (code, name), count in counts.most_common()
    )


def _concise(source: SourceFile, diagnostic: Diagnostic) -> str:
    location = f"{source.path}:{diagnostic.line}:{diagnostic.column}"
    return f"{location}: {diagnostic.code} {diagnostic.message}"


def _full(source: SourceFile, diagnostic: Diagnostic) -> list[str]:
    gutter = " " * len(str(diagnostic.line))
    text = source.line(diagnostic.line) if diagnostic.line <= source.line_count else ""

    return [
        f"{_concise(source, diagnostic)}",
        f"{gutter} |",
        f"{diagnostic.line} | {text}",
        f"{gutter} | {' ' * (diagnostic.column - 1)}^ {diagnostic.fix_title}",
        f"{gutter} |",
    ]


def _github(source: SourceFile, diagnostic: Diagnostic) -> str:
    return (
        f"::error title=pywsl ({diagnostic.code}),file={source.path},"
        f"line={diagnostic.line},col={diagnostic.column},"
        f"endLine={diagnostic.line},endColumn={diagnostic.column}::"
        f"{source.path}:{diagnostic.line}:{diagnostic.column}: "
        f"{diagnostic.code} {diagnostic.message}"
    )


def _json(entries: Sequence[tuple[SourceFile, list[Diagnostic]]]) -> str:
    payload = [
        {
            "filename": source.path,
            "code": diagnostic.code,
            "name": diagnostic.name,
            "message": diagnostic.message,
            "location": {"row": diagnostic.line, "column": diagnostic.column},
            "fix": {"applicability": "safe", "action": diagnostic.fix.value},
        }
        for source, found in entries
        for diagnostic in found
    ]

    return json.dumps(payload, indent=2)
