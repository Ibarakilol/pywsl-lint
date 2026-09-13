"""Statement and block model built on top of the AST."""

from __future__ import annotations

import ast
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from pywsl.source import SourceFile

THREAD_FACTORIES = frozenset({"Thread", "Process", "Timer"})
TASK_FUNCTIONS = frozenset(
    {"create_task", "ensure_future", "submit", "run_coroutine_threadsafe", "spawn"}
)
PUT_METHODS = frozenset({"put", "put_nowait", "send", "send_nowait"})
APPEND_METHODS = frozenset({"append", "extend", "add", "insert"})

BLOCK_KINDS = frozenset({"if", "for", "while", "with", "try", "match", "def", "class"})

TRY_NODES: tuple[type[ast.stmt], ...] = (ast.Try,)
if hasattr(ast, "TryStar"):
    TRY_NODES = (ast.Try, ast.TryStar)


@dataclass
class Stmt:
    node: ast.stmt
    kind: str
    start: int
    end: int
    top: int
    bound: frozenset[str]
    used: frozenset[str]
    blocks: list[Block] = field(default_factory=list)

    @property
    def is_block(self) -> bool:
        return self.kind in BLOCK_KINDS

    @property
    def primary_body(self) -> list[Stmt]:
        return self.blocks[0].body if self.blocks else []

    @property
    def other_bodies(self) -> list[list[Stmt]]:
        return [block.body for block in self.blocks[1:]]


@dataclass
class Block:
    owner: ast.AST
    clause: str
    body: list[Stmt]
    header: int = 0
    is_module: bool = False
    continuation: bool = False

    @property
    def line_span(self) -> int:
        if not self.body:
            return 0

        return self.body[-1].end - self.body[0].top + 1


def build_blocks(source: SourceFile) -> list[Block]:
    blocks: list[Block] = []
    _collect(source, source.tree, "module", source.tree.body, blocks, is_module=True)
    return blocks


@dataclass(frozen=True)
class Suite:
    clause: str
    body: list[ast.stmt]
    header: int
    continuation: bool = False


def _collect(
    source: SourceFile,
    owner: ast.AST,
    clause: str,
    body: Sequence[ast.stmt],
    blocks: list[Block],
    *,
    header: int = 0,
    is_module: bool = False,
    continuation: bool = False,
) -> None:
    if not body:
        return

    statements = _statements(source, body)
    blocks.append(
        Block(
            owner=owner,
            clause=clause,
            body=statements,
            header=header,
            is_module=is_module,
            continuation=continuation,
        )
    )
    for statement in statements:
        for suite in _suites(source, statement.node):
            before = len(blocks)
            _collect(
                source,
                statement.node,
                suite.clause,
                suite.body,
                blocks,
                header=suite.header,
                continuation=suite.continuation,
            )
            if len(blocks) > before:
                statement.blocks.append(blocks[before])


def _suites(source: SourceFile, node: ast.stmt) -> Iterator[Suite]:
    def else_suite(body: list[ast.stmt], keyword: str = "else") -> Suite:
        return Suite(keyword, body, _clause_line(source, node, keyword, body), True)

    if isinstance(node, ast.If):
        yield Suite("body", node.body, node.lineno)
        if node.orelse and _is_elif(node):
            yield Suite("elif", node.orelse, node.orelse[0].lineno)
        elif node.orelse:
            yield else_suite(node.orelse)
    elif isinstance(node, TRY_NODES):
        yield Suite("body", node.body, node.lineno)
        for handler in node.handlers:
            yield Suite("except", handler.body, handler.lineno, True)

        if node.orelse:
            yield else_suite(node.orelse)

        if node.finalbody:
            yield else_suite(node.finalbody, "finally")
    elif isinstance(node, ast.For | ast.AsyncFor | ast.While):
        yield Suite("body", node.body, node.lineno)
        if node.orelse:
            yield else_suite(node.orelse)
    elif isinstance(node, ast.Match):
        for case in node.cases:
            yield Suite("case", case.body, case.pattern.lineno)
    elif isinstance(
        node,
        ast.FunctionDef
        | ast.AsyncFunctionDef
        | ast.ClassDef
        | ast.With
        | ast.AsyncWith,
    ):
        yield Suite("body", node.body, node.lineno)


def _clause_line(
    source: SourceFile, owner: ast.stmt, keyword: str, body: Sequence[ast.stmt]
) -> int:
    indent = owner.col_offset
    for line in range(body[0].lineno - 1, owner.lineno, -1):
        if line not in source.code_lines:
            continue

        text = source.line(line)
        if len(text) - len(text.lstrip()) == indent and text.strip().startswith(
            keyword
        ):
            return line

        return 0

    return 0


def _is_elif(node: ast.If) -> bool:
    return (
        len(node.orelse) == 1
        and isinstance(node.orelse[0], ast.If)
        and node.orelse[0].col_offset == node.col_offset
    )


def _statements(source: SourceFile, body: Sequence[ast.stmt]) -> list[Stmt]:
    thread_names = _thread_names(body)
    statements: list[Stmt] = []
    previous_end = 0
    for node in body:
        start = _start_line(node)
        top = _extend_upwards(source, start, previous_end)
        statements.append(
            Stmt(
                node=node,
                kind=classify(node, thread_names),
                start=start,
                end=node.end_lineno or start,
                top=top,
                bound=frozenset(bound_names(node)),
                used=frozenset(used_names(node)),
            )
        )
        previous_end = node.end_lineno or start

    return statements


def _start_line(node: ast.stmt) -> int:
    decorators = getattr(node, "decorator_list", None)
    if decorators:
        return min(node.lineno, *(d.lineno for d in decorators))

    return node.lineno


def _extend_upwards(source: SourceFile, start: int, floor: int) -> int:
    line = start - 1
    while line > floor and source.is_comment(line):
        line -= 1

    return line + 1


def _thread_names(body: Sequence[ast.stmt]) -> frozenset[str]:
    names: set[str] = set()
    for node in body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue

        if _callee_name(node.value) in THREAD_FACTORIES:
            for target in node.targets:
                names |= _target_names(target)

    return frozenset(names)


def classify(node: ast.stmt, thread_names: frozenset[str] = frozenset()) -> str:
    if isinstance(node, ast.AnnAssign):
        return "assign" if node.value is not None else "decl"

    if isinstance(node, ast.Assign):
        return "append" if _is_append_assign(node) else "assign"

    if isinstance(node, ast.AugAssign):
        return "append" if _is_append_aug(node) else "aug-assign"

    if isinstance(node, ast.Expr):
        return _classify_expr(node.value, thread_names)

    if isinstance(node, ast.Return):
        return "return"

    if isinstance(node, ast.Break | ast.Continue):
        return "branch"

    if isinstance(node, ast.For | ast.AsyncFor):
        return "for"

    if isinstance(node, ast.While):
        return "while"

    if isinstance(node, ast.If):
        return "if"

    if isinstance(node, ast.With | ast.AsyncWith):
        return "with"

    if isinstance(node, TRY_NODES):
        return "try"

    if isinstance(node, ast.Match):
        return "match"

    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return "def"

    if isinstance(node, ast.ClassDef):
        return "class"

    if isinstance(node, ast.Import | ast.ImportFrom):
        return "import"

    return "other"


def _classify_expr(value: ast.expr, thread_names: frozenset[str]) -> str:
    call = value.value if isinstance(value, ast.Await) else value
    if not isinstance(call, ast.Call):
        return "expr"

    if is_thread_start(call, thread_names):
        return "thread-start"

    if isinstance(call.func, ast.Attribute):
        if call.func.attr in PUT_METHODS:
            return "queue-put"

        if call.func.attr in APPEND_METHODS:
            return "append"

    return "expr"


def is_thread_start(call: ast.Call, thread_names: frozenset[str]) -> bool:
    name = _callee_name(call)
    if name in TASK_FUNCTIONS:
        return True

    if name != "start" or not isinstance(call.func, ast.Attribute):
        return False

    receiver = call.func.value
    if isinstance(receiver, ast.Call):
        return _callee_name(receiver) in THREAD_FACTORIES

    return _root_name(receiver) in thread_names


def _is_append_assign(node: ast.Assign) -> bool:
    if not isinstance(node.value, ast.BinOp) or not isinstance(node.value.op, ast.Add):
        return False

    targets = set()
    for target in node.targets:
        targets |= _target_names(target)

    return bool(targets & used_names(node.value.left))


def _is_append_aug(node: ast.AugAssign) -> bool:
    return isinstance(node.op, ast.Add) and isinstance(
        node.value, ast.List | ast.Tuple | ast.Set
    )


def _callee_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id

    if isinstance(call.func, ast.Attribute):
        return call.func.attr

    return None


def _root_name(node: ast.expr) -> str | None:
    while isinstance(node, ast.Attribute | ast.Subscript):
        node = node.value

    return node.id if isinstance(node, ast.Name) else None


def _target_names(target: ast.expr) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(target):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute | ast.Subscript):
            root = _root_name(child)
            if root is not None:
                names.add(root)

    return names


def bound_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.Assign):
        for target in node.targets:
            names |= _target_names(target)
    elif isinstance(node, ast.AnnAssign | ast.AugAssign | ast.For | ast.AsyncFor):
        names |= _target_names(node.target)
    elif isinstance(node, ast.With | ast.AsyncWith):
        for item in node.items:
            if item.optional_vars is not None:
                names |= _target_names(item.optional_vars)
    elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        names.add(node.name)
    elif isinstance(node, ast.Import | ast.ImportFrom):
        for alias in node.names:
            names.add((alias.asname or alias.name).split(".")[0])
    elif isinstance(node, ast.Expr):
        names |= _mutated_names(node.value)

    for child in ast.walk(node):
        if isinstance(child, ast.NamedExpr):
            names |= _target_names(child.target)

    return names


def _mutated_names(value: ast.expr) -> set[str]:
    call = value.value if isinstance(value, ast.Await) else value
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
        return set()

    if call.func.attr not in APPEND_METHODS | PUT_METHODS:
        return set()

    root = _root_name(call.func.value)
    return {root} if root is not None else set()


def used_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            root = _root_name(child)
            if root is not None:
                names.add(root)

    return names


def call_of(node: ast.stmt) -> ast.Call | None:
    if not isinstance(node, ast.Expr):
        return None

    value = node.value.value if isinstance(node.value, ast.Await) else node.value
    return value if isinstance(value, ast.Call) else None
