"""Cuddling rules: what may sit directly above a statement."""

from __future__ import annotations

import ast
from collections.abc import Iterator

from pywsl import diagnostics
from pywsl.analysis import call_of, used_names
from pywsl.diagnostics import Diagnostic, FixKind
from pywsl.rules import Context, is_assignment, shares_name


def check(ctx: Context) -> Iterator[Diagnostic]:
    if not ctx.cuddled:
        return

    handler = _HANDLERS.get(ctx.stmt.kind)
    if handler is None:
        return

    yield from handler(ctx)


def _report(ctx: Context, name: str, **fields: object) -> Iterator[Diagnostic]:
    if not ctx.config.is_enabled(name):
        return

    yield diagnostics.make(
        name, ctx.stmt.top, ctx.column, FixKind.INSERT_BLANK_ABOVE, **fields
    )


def _assign(ctx: Context) -> Iterator[Diagnostic]:
    if is_assignment(ctx.prev):
        return

    yield from _report(ctx, "assign")


def _aug_assign(ctx: Context) -> Iterator[Diagnostic]:
    if is_assignment(ctx.prev):
        return

    yield from _report(ctx, "aug-assign")


def _decl(ctx: Context) -> Iterator[Diagnostic]:
    if ctx.prev.kind == "decl":
        return

    yield from _report(ctx, "decl")


def _for(ctx: Context) -> Iterator[Diagnostic]:
    node = ctx.stmt.node
    assert isinstance(node, ast.For | ast.AsyncFor)
    if _related(ctx, [node.iter, node.target]):
        return

    yield from _report(ctx, "for")


def _while(ctx: Context) -> Iterator[Diagnostic]:
    node = ctx.stmt.node
    assert isinstance(node, ast.While)
    if _related(ctx, [node.test]):
        return

    yield from _report(ctx, "while")


def _if(ctx: Context) -> Iterator[Diagnostic]:
    node = ctx.stmt.node
    assert isinstance(node, ast.If)
    if _related(ctx, [node.test]):
        return

    yield from _report(ctx, "if")


def _with(ctx: Context) -> Iterator[Diagnostic]:
    node = ctx.stmt.node
    assert isinstance(node, ast.With | ast.AsyncWith)
    contexts = [item.context_expr for item in node.items]
    if _related(ctx, contexts):
        return

    yield from _report(ctx, "with")


def _try(ctx: Context) -> Iterator[Diagnostic]:
    guarded = ctx.stmt.primary_body
    if _related(ctx, [guarded[0].node] if guarded else []):
        return

    yield from _report(ctx, "try")


def _match(ctx: Context) -> Iterator[Diagnostic]:
    node = ctx.stmt.node
    assert isinstance(node, ast.Match)
    if _related(ctx, [node.subject]):
        return

    name = "case-isinstance" if _is_type_match(node) else "match"
    yield from _report(ctx, name)


def _expr(ctx: Context) -> Iterator[Diagnostic]:
    if _uses_bound_names(ctx):
        return

    yield from _report(ctx, "expr")


def _thread_start(ctx: Context) -> Iterator[Diagnostic]:
    if _uses_bound_names(ctx):
        return

    yield from _report(ctx, "thread-start")


def _queue_put(ctx: Context) -> Iterator[Diagnostic]:
    if _uses_bound_names(ctx):
        return

    yield from _report(ctx, "queue-put")


def _return(ctx: Context) -> Iterator[Diagnostic]:
    if ctx.block.line_span <= ctx.config.branch_max_lines:
        return

    yield from _report(ctx, "return", branch_max_lines=ctx.config.branch_max_lines)


def _branch(ctx: Context) -> Iterator[Diagnostic]:
    if ctx.block.line_span <= ctx.config.branch_max_lines:
        return

    yield from _report(ctx, "branch", branch_max_lines=ctx.config.branch_max_lines)


def _related(ctx: Context, exprs: list[ast.AST]) -> bool:
    return shares_name(ctx, exprs, ctx.stmt.primary_body, ctx.stmt.other_bodies)


def _uses_bound_names(ctx: Context) -> bool:
    call = call_of(ctx.stmt.node)
    target = call if call is not None else ctx.stmt.node
    return bool(ctx.prev.bound & used_names(target))


def _is_type_match(node: ast.Match) -> bool:
    return any(isinstance(case.pattern, ast.MatchClass) for case in node.cases)


_HANDLERS = {
    "assign": _assign,
    "aug-assign": _aug_assign,
    "decl": _decl,
    "for": _for,
    "while": _while,
    "if": _if,
    "with": _with,
    "try": _try,
    "match": _match,
    "expr": _expr,
    "thread-start": _thread_start,
    "queue-put": _queue_put,
    "return": _return,
    "branch": _branch,
}
