import textwrap

import pytest

from pywsl_lint import source as source_module
from pywsl_lint.config import Config, apply_selectors
from pywsl_lint.engine import check_source
from pywsl_lint.fixer import fix


def normalise(code: str) -> str:
    return textwrap.dedent(code).lstrip("\n")


def build_config(
    select: list[str] | None = None,
    ignore: list[str] | None = None,
    **options: object,
) -> Config:
    config = Config(**options)
    if select is None and ignore is None:
        return config

    return apply_selectors(config, select=select, ignore=ignore)


@pytest.fixture
def lint():
    def run(
        code: str,
        select: list[str] | None = None,
        ignore: list[str] | None = None,
        **options: object,
    ) -> list[str]:
        source = source_module.from_text(normalise(code), "t.py")
        config = build_config(select, ignore, **options)

        return [f"{d.name}:{d.line}" for d in check_source(source, config)]

    return run


@pytest.fixture
def reformat():
    def run(
        code: str,
        select: list[str] | None = None,
        ignore: list[str] | None = None,
        **options: object,
    ) -> str:
        source = source_module.from_text(normalise(code), "t.py")
        return fix(source, build_config(select, ignore, **options)).text

    return run
