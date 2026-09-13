"""Rule implementations and the context they are evaluated against."""

from __future__ import annotations

import ast
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pywsl.analysis import Block, Stmt, used_names
from pywsl.config import Config
from pywsl.source import SourceFile


@dataclass(frozen=True)
class Context:
    source: SourceFile
    config: Config
    block: Block
    index: int

    @property
    def stmt(self) -> Stmt:
        return self.block.body[self.index]

    @property
    def prev(self) -> Stmt | None:
        if self.index == 0:
            return None

        return self.block.body[self.index - 1]

    @property
    def cuddled(self) -> bool:
        previous = self.prev
        return previous is not None and self.stmt.top == previous.end + 1

    @property
    def column(self) -> int:
        return self.source.indent_of(self.stmt.top) + 1


def shares_name(
    ctx: Context,
    exprs: Iterable[ast.AST],
    body: Sequence[Stmt] = (),
    nested: Iterable[Sequence[Stmt]] = (),
) -> bool:
    previous = ctx.prev
    if previous is None or not previous.bound:
        return False

    bound = previous.bound
    for expr in exprs:
        if bound & used_names(expr):
            return True

    if ctx.config.allow_whole_block:
        for statements in (body, *nested):
            if any(bound & statement.used for statement in statements):
                return True

    if ctx.config.allow_first_in_block and body and bound & body[0].used:
        return True

    return False


def is_assignment(statement: Stmt) -> bool:
    node = statement.node
    if isinstance(node, ast.AnnAssign):
        return node.value is not None

    return isinstance(node, ast.Assign | ast.AugAssign)
