from __future__ import annotations

import json

import pytest

from pywsl.cli import EXIT_ERROR, EXIT_OK, EXIT_VIOLATIONS, main

DIRTY = "setup()\nif ready:\n    run()\n"
CLEAN = "setup()\n\nif ready:\n    run()\n"


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[tool.pywsl]\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    return tmp_path


def write(project, name: str, text: str):
    path = project / name
    path.write_text(text, encoding="utf-8")

    return path


def test_clean_source_exits_zero(project, capsys):
    write(project, "clean.py", CLEAN)

    assert main(["check", "clean.py"]) == EXIT_OK
    assert "All checks passed!" in capsys.readouterr().out


def test_violations_exit_one(project, capsys):
    write(project, "dirty.py", DIRTY)

    assert main(["check", "dirty.py"]) == EXIT_VIOLATIONS
    assert "WSL007" in capsys.readouterr().out


def test_exit_zero_suppresses_the_failure(project):
    write(project, "dirty.py", DIRTY)

    assert main(["check", "--exit-zero", "dirty.py"]) == EXIT_OK


def test_fix_rewrites_the_file(project):
    path = write(project, "dirty.py", DIRTY)
    assert main(["check", "--fix", "dirty.py"]) == EXIT_OK
    assert path.read_text(encoding="utf-8") == CLEAN


def test_diff_leaves_the_file_alone(project, capsys):
    path = write(project, "dirty.py", DIRTY)
    assert main(["check", "--diff", "dirty.py"]) == EXIT_VIOLATIONS
    assert path.read_text(encoding="utf-8") == DIRTY
    assert "+++ dirty.py" in capsys.readouterr().out


def test_format_check_reports_without_writing(project, capsys):
    path = write(project, "dirty.py", DIRTY)
    assert main(["format", "--check", "dirty.py"]) == EXIT_VIOLATIONS
    assert path.read_text(encoding="utf-8") == DIRTY
    assert "would be reformatted" in capsys.readouterr().out


def test_format_writes_and_reports(project, capsys):
    path = write(project, "dirty.py", DIRTY)
    assert main(["format", "dirty.py"]) == EXIT_OK
    assert path.read_text(encoding="utf-8") == CLEAN
    assert "1 file reformatted" in capsys.readouterr().out


def test_directories_are_walked(project, capsys):
    package = project / "pkg"
    package.mkdir()

    (package / "dirty.py").write_text(DIRTY, encoding="utf-8")

    assert main(["check", "--output-format", "concise", "."]) == EXIT_VIOLATIONS
    assert "pkg/dirty.py:2:1" in capsys.readouterr().out


def test_excluded_directories_are_skipped(project):
    hidden = project / ".venv"
    hidden.mkdir()

    (hidden / "dirty.py").write_text(DIRTY, encoding="utf-8")

    assert main(["check", "."]) == EXIT_OK


def test_extend_exclude_skips_a_directory(project):
    package = project / "generated"
    package.mkdir()

    (package / "dirty.py").write_text(DIRTY, encoding="utf-8")

    assert main(["check", "--extend-exclude", "generated", "."]) == EXIT_OK


def test_json_output_is_machine_readable(project, capsys):
    write(project, "dirty.py", DIRTY)

    main(["check", "--output-format", "json", "dirty.py"])

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["code"] == "WSL007"
    assert payload[0]["location"] == {"row": 2, "column": 1}


def test_github_output_is_annotated(project, capsys):
    write(project, "dirty.py", DIRTY)

    main(["check", "--output-format", "github", "dirty.py"])

    assert capsys.readouterr().out.startswith("::error title=pywsl (WSL007)")


def test_statistics_count_each_check(project, capsys):
    write(project, "dirty.py", DIRTY * 2)

    main(["check", "--statistics", "dirty.py"])

    assert "WSL007" in capsys.readouterr().out


def test_select_narrows_the_enabled_checks(project):
    write(project, "dirty.py", DIRTY)

    assert main(["check", "--select", "assign", "dirty.py"]) == EXIT_OK


def test_ignore_disables_a_check(project):
    write(project, "dirty.py", DIRTY)

    assert main(["check", "--ignore", "if,after-expr", "dirty.py"]) == EXIT_OK


def test_stdin_is_linted(project, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", _Stdin(DIRTY))

    args = ["check", "--output-format", "concise", "--stdin-filename", "x.py", "-"]
    assert main(args) == EXIT_VIOLATIONS
    assert "x.py:2:1" in capsys.readouterr().out


def test_stdin_fix_writes_to_stdout(project, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", _Stdin(DIRTY))

    assert main(["check", "--fix", "-q", "-"]) == EXIT_OK
    assert capsys.readouterr().out == CLEAN


def test_a_syntax_error_is_reported(project, capsys):
    write(project, "broken.py", "def f(:\n")

    assert main(["check", "broken.py"]) == EXIT_VIOLATIONS
    assert "error:" in capsys.readouterr().err


def test_a_bad_config_exits_two(project, capsys):
    assert main(["check", "--select", "nope", "."]) == EXIT_ERROR
    assert "unknown check" in capsys.readouterr().err


def test_rules_lists_every_check(project, capsys):
    assert main(["rules"]) == EXIT_OK

    output = capsys.readouterr().out
    assert "WSL001" in output
    assert "case-max-lines" in output


def test_rules_as_json(project, capsys):
    assert main(["rules", "--output-format", "json"]) == EXIT_OK

    payload = json.loads(capsys.readouterr().out)
    assert {"code", "name", "summary", "default"} <= set(payload[0])


def test_no_command_prints_help(capsys):
    assert main([]) == EXIT_ERROR
    assert "usage: pywsl" in capsys.readouterr().out


class _Stdin:
    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> str:
        return self._text


def test_an_explicit_path_is_linted_even_when_excluded(project):
    hidden = project / ".venv"
    hidden.mkdir()

    write(project, ".venv/dirty.py", DIRTY)

    assert main(["check", ".venv/dirty.py"]) == EXIT_VIOLATIONS


def test_force_exclude_skips_an_explicit_path(project):
    hidden = project / ".venv"
    hidden.mkdir()

    write(project, ".venv/dirty.py", DIRTY)

    assert main(["check", "--force-exclude", ".venv/dirty.py"]) == EXIT_OK
