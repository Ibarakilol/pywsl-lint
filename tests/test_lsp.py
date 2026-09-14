from pywsl_lint import lsp
from pywsl_lint import source as source_module
from pywsl_lint.config import Config
from pywsl_lint.diagnostics import FixKind
from pywsl_lint.engine import check_source

from conftest import normalise

DIRTY = "import os\nx = compute()\nsetup()\nif ready:\n    run()\n"


def build(code: str):
    source = source_module.from_text(normalise(code), "t.py")

    return source, check_source(source, Config())


def test_the_highlight_covers_the_statement_not_its_indentation():
    source, found = build("""
    def f():
        value = 1
        if other:
            run()
    """)
    span = lsp.highlight(source, found[0])

    assert (span.start_line, span.start_char) == (2, 4)
    assert span.end_char == len("    if other:")


def test_an_insert_becomes_an_empty_edit_at_the_line_start():
    source, found = build(DIRTY)
    diagnostic = next(d for d in found if d.line == 4)
    edit = lsp.edit_for(source, diagnostic)

    assert edit.span == lsp.Span(3, 0, 3, 0)
    assert edit.new_text == "\n"


def test_a_removal_deletes_the_blank_run_above():
    source, found = build("""
    def f():

        return 1
    """)
    diagnostic = found[0]

    assert diagnostic.fix is FixKind.REMOVE_BLANK_ABOVE
    assert lsp.edit_for(source, diagnostic) == lsp.Edit(lsp.Span(1, 0, 2, 0), "")


def test_formatting_replaces_the_whole_document():
    source, _ = build(DIRTY)
    edit = lsp.format_edit(source, Config())

    assert edit.span == lsp.Span(0, 0, 5, 0)
    assert edit.new_text.startswith("import os\n\nx = compute()")


def test_formatting_a_clean_document_offers_no_edit():
    source, _ = build("import os\n\nx = 1\n")

    assert lsp.format_edit(source, Config()) is None


def test_a_document_without_a_final_newline_ends_on_the_last_character():
    source = source_module.from_text("setup()\nif a:\n    run()", "t.py")

    assert lsp.whole(source) == lsp.Span(0, 0, 2, len("    run()"))


def test_applying_every_single_edit_matches_the_formatter():
    source, found = build(DIRTY)
    lines = list(source.lines)

    for diagnostic in sorted(found, key=lambda d: d.line, reverse=True):
        edit = lsp.edit_for(source, diagnostic)
        lines.insert(edit.span.start_line, "")

    assert "\n".join(lines) + "\n" == lsp.format_edit(source, Config()).new_text
