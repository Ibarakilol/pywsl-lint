from __future__ import annotations


def test_append_may_cuddle_the_list_it_grows(lint):
    assert lint("items = []\nitems.append(value)\n", select=["append"]) == []


def test_append_may_cuddle_the_appended_value(lint):
    assert lint("value = build()\nitems.append(value)\n", select=["append"]) == []


def test_append_may_not_cuddle_an_unrelated_assignment(lint):
    assert lint("other = build()\nitems.append(value)\n", select=["append"]) == [
        "append:2"
    ]


def test_concatenating_reassignment_follows_the_append_rule(lint):
    assert lint("other = build()\nitems = items + [value]\n", select=["append"]) == [
        "append:2"
    ]


def test_assign_expr_is_off_by_default(lint):
    assert lint("value = build()\nsend(value)\n") == []


def test_assign_expr_forbids_mixing_assignments_and_calls(lint):
    assert lint("value = build()\nsend(value)\n", select=["assign-expr"]) == [
        "assign-expr:2"
    ]


def test_one_statement_may_be_cuddled_above_a_block(lint):
    code = """
    ready = check()
    if ready:
        run()
    """
    assert lint(code, select=["cuddle-group"]) == []


def test_two_statements_may_not_be_cuddled_above_a_block(lint):
    code = """
    first = 1
    ready = check()
    if ready:
        run()
    """
    assert lint(code, select=["cuddle-group"]) == ["cuddle-group:3"]


def test_cuddle_max_statements_is_configurable(lint):
    code = """
    first = 1
    ready = check()
    if ready:
        run()
    """
    assert lint(code, select=["cuddle-group"], cuddle_max_statements=2) == []


def test_the_most_specific_diagnostic_wins_on_a_line(lint):
    assert lint("setup()\nif ready:\n    run()\n") == ["if:2"]
