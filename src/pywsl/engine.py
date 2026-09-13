"""Runs every rule over a source file."""

from pywsl.analysis import build_blocks
from pywsl.config import Config
from pywsl.diagnostics import Diagnostic, dedupe
from pywsl.rules import Context, after, cuddle, special, whitespace
from pywsl.source import SourceFile

_STATEMENT_RULES = (cuddle.check, after.check, special.check)


def check_source(source: SourceFile, config: Config) -> list[Diagnostic]:
    found: list[Diagnostic] = []
    for block in build_blocks(source):
        found.extend(whitespace.check_block(source, config, block))

        for index, statement in enumerate(block.body):
            context = Context(source, config, block, index)
            for rule in _STATEMENT_RULES:
                found.extend(rule(context))

            if statement.kind == "match":
                found.extend(whitespace.check_match(source, config, statement.blocks))

    return dedupe(found)
