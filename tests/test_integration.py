import ast
from pathlib import Path

import pytest

from pywsl import source as source_module
from pywsl.config import Config
from pywsl.engine import check_source
from pywsl.fixer import fix

SOURCES = sorted((Path(__file__).parent.parent / "src" / "pywsl").rglob("*.py"))


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_our_own_source_obeys_the_rules(path):
    source = source_module.from_path(path)
    result = fix(source, Config())

    assert check_source(source, Config()) == []
    assert ast.dump(ast.parse(result.text)) == ast.dump(ast.parse(source.text))
    assert result.changed is False


def test_a_one_line_block_body_is_not_leading_whitespace(lint):
    code = """
    def f(m):
        "doc"

        if not m: return ''
    """
    assert lint(code, select=["leading-whitespace"]) == []


def test_a_sentinel_check_outweighs_the_cuddle_group_limit(lint):
    code = """
    width = half(size)
    cached = lookup(width)
    if cached is None:
        store(width)
    """
    assert lint(code, select=["cuddle-group", "except-immediate"]) == []


def test_async_constructs_are_understood(lint):
    code = """
    async def f(items):
        other = 1
        async for item in items:
            await handle(item)
    """
    assert lint(code, select=["for"]) == ["for:3"]


def test_async_with_is_understood(lint):
    code = """
    async def f(path):
        other = 1
        async with open(path) as handle:
            await read(handle)
    """
    assert lint(code, select=["with"]) == ["with:3"]


def test_decorators_belong_to_the_function_below(lint):
    code = """
    value = 1
    @cache
    def f():
        pass
    """
    assert lint(code, select=["after-block", "assign"]) == []


def test_elif_chains_are_not_treated_as_nested_blocks(lint):
    code = """
    if a:
        run()
    elif b:
        stop()
    else:
        wait()
    """
    assert lint(code) == []


def test_walrus_targets_count_as_assignments(lint):
    code = """
    if (match := pattern.search(text)) is not None:
        use(match)
    """
    assert lint(code) == []
