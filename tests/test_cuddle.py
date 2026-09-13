import pytest


def test_assignments_may_cuddle_each_other(lint):
    assert lint("x = 1\ny = 2\n") == []


def test_assignment_may_not_cuddle_a_call(lint):
    assert lint("setup()\ny = 2\n", select=["assign"]) == ["assign:2"]


def test_aug_assign_follows_the_assign_rule(lint):
    assert lint("x = 1\nx += 1\n") == []
    assert lint("setup()\nx += 1\n", select=["aug-assign"]) == ["aug-assign:2"]


def test_branch_may_cuddle_inside_a_short_block(lint):
    code = """
    for item in items:
        seen = 1
        break
    """
    assert lint(code, select=["branch"]) == []


def test_branch_may_not_cuddle_inside_a_long_block(lint):
    code = """
    for item in items:
        first = 1
        second = 2
        third = 3
        break
    """
    assert lint(code, select=["branch"]) == ["branch:5"]


def test_branch_max_lines_is_configurable(lint):
    code = """
    for item in items:
        first = 1
        second = 2
        third = 3
        continue
    """
    assert lint(code, select=["branch"], branch_max_lines=4) == []


def test_bare_annotation_never_cuddles_code(lint):
    assert lint("x = 1\ncount: int\n", select=["decl"]) == ["decl:2"]


def test_consecutive_bare_annotations_may_cuddle(lint):
    assert lint("count: int\nname: str\n", select=["decl"]) == []


def test_for_may_cuddle_the_iterated_variable(lint):
    code = """
    items = collect()
    for item in items:
        use(item)
    """
    assert lint(code, select=["for"]) == []


def test_for_may_not_cuddle_an_unrelated_assignment(lint):
    code = """
    other = collect()
    for item in items:
        use(item)
    """
    assert lint(code, select=["for"]) == ["for:2"]


def test_while_may_cuddle_a_variable_from_its_condition(lint):
    code = """
    remaining = 10
    while remaining > 0:
        remaining -= 1
    """
    assert lint(code, select=["while"]) == []


def test_while_may_not_cuddle_an_unrelated_assignment(lint):
    code = """
    other = 10
    while remaining > 0:
        remaining -= 1
    """
    assert lint(code, select=["while"]) == ["while:2"]


def test_if_may_cuddle_a_variable_from_its_condition(lint):
    code = """
    ready = check()
    if ready:
        run()
    """
    assert lint(code, select=["if"]) == []


def test_if_may_not_cuddle_an_unrelated_assignment(lint):
    code = """
    other = check()
    if ready:
        run()
    """
    assert lint(code, select=["if"]) == ["if:2"]


def test_expression_may_cuddle_a_variable_it_uses(lint):
    assert lint("value = build()\nsend(value)\n", select=["expr"]) == []


def test_expression_may_not_cuddle_an_unrelated_assignment(lint):
    assert lint("value = build()\nsend(other)\n", select=["expr"]) == ["expr:2"]


def test_return_may_cuddle_inside_a_short_block(lint):
    code = """
    def f():
        value = 1
        return value
    """
    assert lint(code, select=["return"]) == []


def test_return_may_not_cuddle_inside_a_long_block(lint):
    code = """
    def f():
        first = 1
        second = 2
        return second
    """
    assert lint(code, select=["return"]) == ["return:4"]


def test_with_may_cuddle_a_variable_from_the_context_expression(lint):
    code = """
    path = resolve()
    with open(path) as handle:
        read(handle)
    """
    assert lint(code, select=["with"]) == []


def test_with_may_not_cuddle_an_unrelated_assignment(lint):
    code = """
    other = resolve()
    with open(path) as handle:
        read(handle)
    """
    assert lint(code, select=["with"]) == ["with:2"]


def test_try_may_cuddle_the_variable_it_guards(lint):
    code = """
    path = resolve()
    try:
        read(path)
    except OSError:
        pass
    """
    assert lint(code, select=["try"]) == []


def test_try_may_not_cuddle_an_unrelated_assignment(lint):
    code = """
    other = resolve()
    try:
        read(path)
    except OSError:
        pass
    """
    assert lint(code, select=["try"]) == ["try:2"]


def test_match_may_cuddle_its_subject(lint):
    code = """
    command = read()
    match command:
        case "quit":
            stop()
    """
    assert lint(code, select=["match"]) == []


def test_match_may_not_cuddle_an_unrelated_assignment(lint):
    code = """
    other = read()
    match command:
        case "quit":
            stop()
    """
    assert lint(code, select=["match"]) == ["match:2"]


def test_class_patterns_report_case_isinstance(lint):
    code = """
    other = read()
    match command:
        case Quit():
            stop()
    """
    assert lint(code, select=["case-isinstance"]) == ["case-isinstance:2"]


def test_thread_start_may_cuddle_the_thread_variable(lint):
    code = """
    worker = Thread(target=run)
    worker.start()
    """
    assert lint(code, select=["thread-start"]) == []


def test_thread_start_may_not_cuddle_an_unrelated_assignment(lint):
    code = """
    worker = Thread(target=run)
    other = 1
    worker.start()
    """
    assert lint(code, select=["thread-start"]) == ["thread-start:3"]


def test_task_creation_is_treated_as_a_thread_start(lint):
    code = """
    other = 1
    asyncio.create_task(work())
    """
    assert lint(code, select=["thread-start"]) == ["thread-start:2"]


def test_queue_put_may_cuddle_the_sent_value(lint):
    assert lint("item = build()\nqueue.put(item)\n", select=["queue-put"]) == []


def test_queue_put_may_not_cuddle_an_unrelated_assignment(lint):
    code = """
    other = build()
    queue.put(item)
    """
    assert lint(code, select=["queue-put"]) == ["queue-put:2"]


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({}, []),
        ({"allow_first_in_block": False}, ["if:2"]),
    ],
)
def test_allow_first_in_block(lint, options, expected):
    code = """
    value = build()
    if ready:
        use(value)
    """
    assert lint(code, select=["if"], **options) == expected


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({}, ["if:2"]),
        ({"allow_whole_block": True}, []),
    ],
)
def test_allow_whole_block(lint, options, expected):
    code = """
    value = build()
    if ready:
        prepare()
        use(value)
    """
    assert lint(code, select=["if"], **options) == expected


def test_a_leading_comment_belongs_to_the_statement_below(lint):
    code = """
    other = 1
    # explain the branch
    if ready:
        run()
    """
    assert lint(code, select=["if"]) == ["if:2"]


def test_a_blank_line_above_a_leading_comment_separates_the_statement(lint):
    code = """
    other = 1

    # explain the branch
    if ready:
        run()
    """
    assert lint(code, select=["if"]) == []


def test_annotated_fields_may_cuddle_whether_or_not_they_have_a_value(lint):
    code = """
    @dataclass
    class Config:
        name: str
        count: int = 0
        flag: bool = False
    """
    assert lint(code) == []


def test_a_bare_annotation_may_cuddle_an_annotated_assignment(lint):
    assert lint("count: int = 0\nname: str\n", select=["decl", "after-decl"]) == []


def test_a_plain_assignment_still_may_not_cuddle_an_annotation(lint):
    assert lint("count: int\nplain = 5\n", select=["assign"]) == ["assign:2"]


def test_a_docstring_is_not_an_expression_statement(lint):
    code = """
    def f():
        \"\"\"Doc.\"\"\"
        return 1
    """
    assert lint(code, select=["expr", "after-expr"]) == []


def test_a_real_call_is_still_an_expression_statement(lint):
    code = """
    def f():
        print("a")
        return 1
    """
    assert lint(code, select=["after-expr"]) == ["after-expr:3"]
