def test_a_block_may_not_start_with_a_blank_line(lint):
    code = """
    def f():

        return 1
    """
    assert lint(code, select=["leading-whitespace"]) == ["leading-whitespace:3"]


def test_a_blank_line_before_else_is_trailing_whitespace(lint):
    code = """
    if ready:
        run()

    else:
        stop()
    """
    assert lint(code, select=["trailing-whitespace"]) == ["trailing-whitespace:4"]


def test_a_blank_line_before_a_dedent_out_of_the_statement_is_allowed(lint):
    code = """
    def f():
        if ready:
            run()

        return 1
    """
    assert lint(code, select=["trailing-whitespace", "leading-whitespace"]) == []


def test_except_must_follow_the_try_body_immediately(lint):
    code = """
    try:
        run()

    except OSError:
        pass
    """
    assert lint(code, select=["except-immediate"]) == ["except-immediate:4"]


def test_finally_must_follow_the_body_immediately(lint):
    code = """
    try:
        run()
    except OSError:
        pass

    finally:
        close()
    """
    assert lint(code, select=["except-immediate"]) == ["except-immediate:6"]


def test_a_sentinel_check_must_cuddle_the_call_it_checks(lint):
    code = """
    result = find()

    if result is None:
        stop()
    """
    assert lint(code, select=["except-immediate"]) == ["except-immediate:3"]


def test_a_sentinel_check_of_an_unrelated_name_is_left_alone(lint):
    code = """
    result = find()

    if other is None:
        stop()
    """
    assert lint(code, select=["except-immediate"]) == []


def test_case_max_lines_requires_a_blank_line_after_a_long_case(lint):
    code = """
    match command:
        case "run":
            first = 1
            second = 2
            third = 3
        case "quit":
            stop()
    """
    assert lint(code, select=["case-max-lines"], case_max_lines=2) == [
        "case-max-lines:6"
    ]


def test_case_max_lines_is_off_by_default(lint):
    code = """
    match command:
        case "run":
            first = 1
            second = 2
            third = 3
        case "quit":
            stop()
    """
    assert lint(code, select=["case-max-lines"]) == []
