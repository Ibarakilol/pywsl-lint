from pywsl import source as source_module
from pywsl.config import Config
from pywsl.engine import check_source
from pywsl.fixer import fix

from conftest import normalise


def test_blank_lines_are_inserted_where_needed(reformat):
    code = """
    setup()
    if ready:
        run()
    """
    assert reformat(code) == "setup()\n\nif ready:\n    run()\n"


def test_blank_lines_are_removed_where_forbidden(reformat):
    code = """
    def f():

        return 1
    """
    assert reformat(code) == "def f():\n    return 1\n"


def test_fixing_is_idempotent(reformat):
    code = """
    import os
    def load(path):
        data = read(path)
        count: int
        if os.path.exists(path):
            print(path)
        return data
    """
    once = reformat(code)
    assert reformat(once) == once


def test_fixing_leaves_no_diagnostics(reformat):
    code = """
    import os
    def load(path):
        data = read(path)
        count: int
        if os.path.exists(path):
            print(path)
        return data
    """
    fixed = source_module.from_text(reformat(code), "t.py")
    assert check_source(fixed, Config()) == []


def test_line_endings_are_preserved():
    source = source_module.from_text("setup()\r\nif a:\r\n    run()\r\n", "t.py")
    assert fix(source, Config()).text == "setup()\r\n\r\nif a:\r\n    run()\r\n"


def test_a_missing_final_newline_is_not_added():
    source = source_module.from_text("setup()\nif a:\n    run()", "t.py")
    assert fix(source, Config()).text == "setup()\n\nif a:\n    run()"


def test_clean_source_is_left_untouched():
    text = normalise(
        """
        import os


        def load(path):
            data = read(path)

            if os.path.exists(path):
                print(path)

            return data
        """
    )
    result = fix(source_module.from_text(text, "t.py"), Config())
    assert result.changed is False
    assert result.text == text
