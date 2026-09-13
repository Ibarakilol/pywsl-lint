"""Rules requiring a blank line after a construct."""

from collections.abc import Iterator

from pywsl import diagnostics
from pywsl.diagnostics import Diagnostic, FixKind
from pywsl.rules import Context

_BLOCK_CHECKS = {
    "if": "after-if",
    "for": "after-for",
    "while": "after-while",
    "try": "after-try",
    "with": "after-with",
    "match": "after-match",
    "def": "after-block",
    "class": "after-block",
}

_STATEMENT_CHECKS = {
    "decl": "after-decl",
    "expr": "after-expr",
    "thread-start": "after-thread-start",
}

_GROUPED = frozenset(
    {"if", "for", "while", "try", "with", "match", "decl", "expr", "thread-start"}
)


def check(ctx: Context) -> Iterator[Diagnostic]:
    previous = ctx.prev
    if previous is None or not ctx.cuddled:
        return

    name = _BLOCK_CHECKS.get(previous.kind) or _STATEMENT_CHECKS.get(previous.kind)
    if name is None or not ctx.config.is_enabled(name):
        return

    if previous.kind in _GROUPED and ctx.stmt.kind == previous.kind:
        return

    yield diagnostics.make(name, ctx.stmt.top, ctx.column, FixKind.INSERT_BLANK_ABOVE)
