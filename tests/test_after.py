import pytest


@pytest.mark.parametrize(
    ("header", "name"),
    [
        ("if ready:", "after-if"),
        ("for item in items:", "after-for"),
        ("while ready:", "after-while"),
        ("with lock:", "after-with"),
    ],
)
def test_a_block_must_be_followed_by_a_blank_line(lint, header, name):
    code = f"""
    {header}
        run()
    raise Stop()
    """
    assert lint(code, select=[name]) == [f"{name}:3"]


def test_try_must_be_followed_by_a_blank_line(lint):
    code = """
    try:
        run()
    except OSError:
        pass
    raise Stop()
    """
    assert lint(code, select=["after-try"]) == ["after-try:5"]


def test_match_must_be_followed_by_a_blank_line(lint):
    code = """
    match command:
        case "quit":
            stop()
    raise Stop()
    """
    assert lint(code, select=["after-match"]) == ["after-match:4"]


def test_a_function_must_be_followed_by_a_blank_line(lint):
    code = """
    def f():
        pass
    raise Stop()
    """
    assert lint(code, select=["after-block"]) == ["after-block:3"]


def test_consecutive_blocks_of_the_same_kind_may_cuddle(lint):
    code = """
    if a:
        run()
    if b:
        run()

    raise Stop()
    """
    assert lint(code, select=["after-if"]) == []


def test_only_the_last_of_a_run_needs_the_blank_line(lint):
    code = """
    if a:
        run()
    if b:
        run()
    raise Stop()
    """
    assert lint(code, select=["after-if"]) == ["after-if:5"]


def test_declaration_must_be_followed_by_a_blank_line(lint):
    assert lint("count: int\nraise Stop()\n", select=["after-decl"]) == ["after-decl:2"]


def test_consecutive_declarations_may_cuddle(lint):
    code = """
    count: int
    name: str

    raise Stop()
    """
    assert lint(code, select=["after-decl"]) == []


def test_expression_must_be_followed_by_a_blank_line(lint):
    assert lint("run()\nraise Stop()\n", select=["after-expr"]) == ["after-expr:2"]


def test_consecutive_expressions_may_cuddle(lint):
    code = """
    run()
    stop()

    raise Stop()
    """
    assert lint(code, select=["after-expr"]) == []


def test_thread_start_must_be_followed_by_a_blank_line(lint):
    code = """
    worker = Thread(target=run)
    worker.start()
    raise Stop()
    """
    assert lint(code, select=["after-thread-start"]) == ["after-thread-start:3"]
