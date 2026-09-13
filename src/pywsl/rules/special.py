"""Rules that do not fit the plain cuddle or after-block shapes."""

from __future__ import annotations

import ast
from collections.abc import Iterator

from pywsl import diagnostics
from pywsl.analysis import BLOCK_KINDS, used_names
from pywsl.diagnostics import Diagnostic, FixKind
from pywsl.rules import Context, is_assignment

_EXPR_KINDS = frozenset({"expr", "append", "thread-start", "queue-put"})


def check(ctx: Context) -> Iterator[Diagnostic]:
    yield from _sentinel_if(ctx)
    if not ctx.cuddled:
        return

    yield from _append(ctx)
    yield from _assign_expr(ctx)
    yield from _cuddle_group(ctx)


def _append(ctx: Context) -> Iterator[Diagnostic]:
    if ctx.stmt.kind != "append" or not ctx.config.is_enabled("append"):
        return

    if ctx.prev.bound & used_names(ctx.stmt.node):
        return

    yield diagnostics.make(
        "append", ctx.stmt.top, ctx.column, FixKind.INSERT_BLANK_ABOVE
    )


def _assign_expr(ctx: Context) -> Iterator[Diagnostic]:
    if not ctx.config.is_enabled("assign-expr"):
        return

    pair = {ctx.stmt.kind, ctx.prev.kind}
    assigning = is_assignment(ctx.stmt) or is_assignment(ctx.prev)
    if not assigning or not pair & _EXPR_KINDS:
        return

    yield diagnostics.make(
        "assign-expr", ctx.stmt.top, ctx.column, FixKind.INSERT_BLANK_ABOVE
    )


def _cuddle_group(ctx: Context) -> Iterator[Diagnostic]:
    if ctx.stmt.kind not in BLOCK_KINDS or not ctx.config.is_enabled("cuddle-group"):
        return

    if _is_sentinel_pair(ctx):
        return

    group = 0
    index = ctx.index
    while index > 0 and ctx.block.body[index].top == ctx.block.body[index - 1].end + 1:
        group += 1
        index -= 1

    if group <= ctx.config.cuddle_max_statements:
        return

    yield diagnostics.make(
        "cuddle-group",
        ctx.stmt.top,
        ctx.column,
        FixKind.INSERT_BLANK_ABOVE,
        cuddle_max_statements=ctx.config.cuddle_max_statements,
    )


def _sentinel_if(ctx: Context) -> Iterator[Diagnostic]:
    if ctx.cuddled or not _is_sentinel_pair(ctx):
        return

    if not ctx.source.is_blank(ctx.stmt.top - 1):
        return

    yield diagnostics.make(
        "except-immediate", ctx.stmt.top, ctx.column, FixKind.REMOVE_BLANK_ABOVE
    )


def _is_sentinel_pair(ctx: Context) -> bool:
    previous = ctx.prev
    if previous is None or ctx.stmt.kind != "if":
        return False

    if not ctx.config.is_enabled("except-immediate"):
        return False

    node = ctx.stmt.node
    assert isinstance(node, ast.If)
    checked = _sentinel_name(node.test)
    return checked is not None and checked in previous.bound


def _sentinel_name(test: ast.expr) -> str | None:
    if not isinstance(test, ast.Compare) or len(test.ops) != 1:
        return None

    if not isinstance(test.ops[0], ast.Is | ast.IsNot):
        return None

    comparator = test.comparators[0]
    if not isinstance(comparator, ast.Constant) or comparator.value is not None:
        return None

    return test.left.id if isinstance(test.left, ast.Name) else None
