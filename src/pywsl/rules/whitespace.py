"""Rules about blank lines that must not be there."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import pairwise

from pywsl import diagnostics
from pywsl.analysis import TRY_NODES, Block
from pywsl.config import Config
from pywsl.diagnostics import Diagnostic, FixKind
from pywsl.source import SourceFile

_TRY_CLAUSES = frozenset({"except", "else", "finally"})


def check_block(
    source: SourceFile, config: Config, block: Block
) -> Iterator[Diagnostic]:
    if block.is_module or not block.body:
        return

    yield from _leading(source, config, block)
    yield from _continuation(source, config, block)


def check_match(
    source: SourceFile, config: Config, blocks: list[Block]
) -> Iterator[Diagnostic]:
    if not config.is_enabled("case-max-lines") or config.case_max_lines <= 0:
        return

    cases = [block for block in blocks if block.clause == "case"]
    for previous, current in pairwise(cases):
        if previous.line_span <= config.case_max_lines:
            continue

        if source.is_blank(current.header - 1):
            continue

        yield diagnostics.make(
            "case-max-lines",
            current.header,
            source.indent_of(current.header) + 1,
            FixKind.INSERT_BLANK_ABOVE,
            case_max_lines=config.case_max_lines,
        )


def _leading(source: SourceFile, config: Config, block: Block) -> Iterator[Diagnostic]:
    if not config.is_enabled("leading-whitespace"):
        return

    first = block.body[0].top
    if not block.header or first <= block.header:
        return

    if not source.is_blank(first - 1):
        return

    yield diagnostics.make(
        "leading-whitespace",
        first,
        source.indent_of(first) + 1,
        FixKind.REMOVE_BLANK_ABOVE,
    )


def _continuation(
    source: SourceFile, config: Config, block: Block
) -> Iterator[Diagnostic]:
    if not block.continuation or not block.header:
        return

    if not source.is_blank(block.header - 1):
        return

    is_try = block.clause in _TRY_CLAUSES and isinstance(block.owner, TRY_NODES)
    name = "except-immediate" if is_try else "trailing-whitespace"
    if not config.is_enabled(name):
        return

    yield diagnostics.make(
        name,
        block.header,
        source.indent_of(block.header) + 1,
        FixKind.REMOVE_BLANK_ABOVE,
    )
