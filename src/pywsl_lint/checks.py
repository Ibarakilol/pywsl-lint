"""Registry of every check pywsl-lint can report."""

from dataclasses import dataclass

PRIORITY_WHITESPACE = 0
PRIORITY_SPECIAL = 5
PRIORITY_CUDDLE = 10
PRIORITY_GROUP = 20
PRIORITY_AFTER = 30


@dataclass(frozen=True)
class Check:
    code: str
    name: str
    summary: str
    priority: int

    default: bool = True


_CHECKS: tuple[Check, ...] = (
    Check(
        "WSL001",
        "assign",
        "assignments should only be cuddled with other assignments",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL002",
        "aug-assign",
        "augmented assignments should only be cuddled with assignments",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL003",
        "branch",
        "branch statements should not be cuddled if block has more than "
        "{branch_max_lines} lines",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL004",
        "decl",
        "declarations should never be cuddled",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL005",
        "for",
        "for statements should only be cuddled with assignments used in the loop",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL006",
        "while",
        "while statements should only be cuddled with assignments used in the "
        "condition",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL007",
        "if",
        "if statements should only be cuddled with assignments used in the condition",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL008",
        "expr",
        "only cuddled expressions if assigning variable or using from line above",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL009",
        "return",
        "return statements should not be cuddled if block has more than "
        "{branch_max_lines} lines",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL010",
        "with",
        "with statements should only be cuddled with assignments used in the "
        "context expression",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL011",
        "try",
        "try statements should only be cuddled with assignments used in the try body",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL012",
        "match",
        "match statements should only be cuddled with assignments used in the subject",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL013",
        "case-isinstance",
        "type matches should only be cuddled with assignments used in the subject",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL014",
        "thread-start",
        "thread and task starts should only be cuddled with assignments used in "
        "the call",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL015",
        "queue-put",
        "queue sends should only be cuddled with assignments used in the send",
        PRIORITY_CUDDLE,
    ),
    Check(
        "WSL020",
        "after-block",
        "block should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL021",
        "after-if",
        "if statement should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL022",
        "after-for",
        "for statement should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL023",
        "after-while",
        "while statement should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL024",
        "after-try",
        "try statement should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL025",
        "after-with",
        "with statement should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL026",
        "after-match",
        "match statement should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL027",
        "after-decl",
        "declaration should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL028",
        "after-expr",
        "expression statement should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL029",
        "after-thread-start",
        "thread or task start should be followed by a blank line",
        PRIORITY_AFTER,
    ),
    Check(
        "WSL030",
        "append",
        "append only allowed to cuddle with appended value",
        PRIORITY_SPECIAL,
    ),
    Check(
        "WSL031",
        "assign-expr",
        "assignments should never be cuddled with expression statements",
        PRIORITY_GROUP,
        default=False,
    ),
    Check(
        "WSL032",
        "cuddle-group",
        "at most {cuddle_max_statements} statement(s) may be cuddled above a block",
        PRIORITY_GROUP,
    ),
    Check(
        "WSL033",
        "except-immediate",
        "except and error handling must follow the code it guards without a blank line",
        PRIORITY_SPECIAL,
    ),
    Check(
        "WSL034",
        "leading-whitespace",
        "block should not start with a blank line",
        PRIORITY_WHITESPACE,
    ),
    Check(
        "WSL035",
        "trailing-whitespace",
        "block should not end with a blank line",
        PRIORITY_WHITESPACE,
    ),
    Check(
        "WSL036",
        "case-max-lines",
        "case blocks longer than {case_max_lines} lines should be followed by a "
        "blank line",
        PRIORITY_SPECIAL,
    ),
)

BY_NAME: dict[str, Check] = {check.name: check for check in _CHECKS}
BY_CODE: dict[str, Check] = {check.code: check for check in _CHECKS}
ALL_CHECKS: tuple[Check, ...] = _CHECKS
DEFAULT_CHECKS: frozenset[str] = frozenset(c.name for c in _CHECKS if c.default)


def resolve(selector: str) -> set[str]:
    """Expand a name, a code, a code prefix or ``ALL`` into check names."""

    selector = selector.strip()

    if not selector:
        return set()

    upper = selector.upper()
    if upper in {"ALL", "WSL"}:
        return {check.name for check in _CHECKS}

    if selector in BY_NAME:
        return {selector}

    if upper in BY_CODE:
        return {BY_CODE[upper].name}

    prefixed = {check.name for check in _CHECKS if check.code.startswith(upper)}
    if prefixed:
        return prefixed

    raise KeyError(selector)
