from __future__ import annotations

import pytest

from pywsl import checks
from pywsl.config import Config, ConfigError, from_table, load


def test_defaults_enable_every_check_but_the_opt_in_ones():
    config = Config()
    assert config.is_enabled("if")
    assert not config.is_enabled("assign-expr")


def test_options_accept_dashes_and_underscores():
    assert from_table({"branch-max-lines": 5}).branch_max_lines == 5
    assert from_table({"branch_max_lines": 5}).branch_max_lines == 5


def test_select_replaces_the_default_set():
    config = from_table({"select": ["if", "for"]})
    assert config.enabled == {"if", "for"}


def test_extend_select_adds_to_the_default_set():
    config = from_table({"extend-select": ["assign-expr"]})
    assert config.enabled == checks.DEFAULT_CHECKS | {"assign-expr"}


def test_ignore_removes_from_the_selected_set():
    config = from_table({"ignore": ["after-expr"]})
    assert "after-expr" not in config.enabled


def test_codes_and_prefixes_resolve_to_names():
    assert checks.resolve("WSL007") == {"if"}
    assert checks.resolve("wsl00") == {
        check.name for check in checks.ALL_CHECKS if check.code.startswith("WSL00")
    }
    assert checks.resolve("ALL") == {check.name for check in checks.ALL_CHECKS}


def test_unknown_option_is_rejected():
    with pytest.raises(ConfigError, match="unknown option"):
        from_table({"nope": 1})


def test_unknown_check_is_rejected():
    with pytest.raises(ConfigError, match="unknown check"):
        from_table({"select": ["nope"]})


@pytest.mark.parametrize(
    "table",
    [{"branch-max-lines": "two"}, {"branch-max-lines": -1}, {"allow-whole-block": 1}],
)
def test_wrong_option_types_are_rejected(table):
    with pytest.raises(ConfigError):
        from_table(table)


def test_a_pyproject_without_our_table_uses_defaults(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "x"\n', encoding="utf-8")

    assert load(pyproject) == Config()


def test_a_pyproject_table_is_read(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.pywsl]\nbranch-max-lines = 4\nselect = ['if']\n", encoding="utf-8"
    )

    config = load(pyproject)
    assert config.branch_max_lines == 4
    assert config.enabled == {"if"}
