"""Reading a Python file and classifying its physical lines."""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path

_IGNORED_TOKENS = frozenset(
    {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
    }
)


class ParseError(Exception):
    def __init__(self, path: str, line: int, column: int, message: str) -> None:
        super().__init__(message)
        self.path = path
        self.line = line
        self.column = column
        self.message = message


@dataclass(frozen=True)
class SourceFile:
    path: str
    text: str
    lines: tuple[str, ...]
    newline: str
    final_newline: bool
    encoding: str
    tree: ast.Module
    code_lines: frozenset[int]
    comment_lines: frozenset[int]

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def line(self, number: int) -> str:
        return self.lines[number - 1]

    def is_blank(self, number: int) -> bool:
        if number < 1 or number > self.line_count:
            return False

        return not self.lines[number - 1].strip() and number not in self.code_lines

    def is_comment(self, number: int) -> bool:
        return number in self.comment_lines and number not in self.code_lines

    def indent_of(self, number: int) -> int:
        line = self.line(number)
        return len(line) - len(line.lstrip())

    def blank_run_above(self, number: int) -> tuple[int, int] | None:
        """Range of blank lines directly above ``number``, if any."""
        end = number - 1
        start = end
        while self.is_blank(start):
            start -= 1

        if start == end:
            return None

        return start + 1, end


def from_text(text: str, path: str = "<string>", encoding: str = "utf-8") -> SourceFile:
    newline = _detect_newline(text)
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        tree = ast.parse(normalised, filename=path)
    except SyntaxError as error:
        raise ParseError(
            path, error.lineno or 1, error.offset or 1, error.msg
        ) from error

    code_lines, comment_lines = _scan(normalised, path)
    rows = normalised.split("\n")
    final_newline = bool(rows) and rows[-1] == ""
    if final_newline:
        rows.pop()

    return SourceFile(
        path=path,
        text=text,
        lines=tuple(rows),
        newline=newline,
        final_newline=final_newline,
        encoding=encoding,
        tree=tree,
        code_lines=frozenset(code_lines),
        comment_lines=frozenset(comment_lines),
    )


def from_path(path: Path) -> SourceFile:
    with path.open("rb") as handle:
        encoding, _ = tokenize.detect_encoding(handle.readline)

    text = path.read_bytes().decode(encoding)
    return from_text(text, str(path), encoding)


def _scan(text: str, path: str) -> tuple[set[int], set[int]]:
    code: set[int] = set()
    comments: set[int] = set()
    readline = io.StringIO(text).readline
    try:
        for token in tokenize.generate_tokens(readline):
            if token.type == tokenize.COMMENT:
                comments.add(token.start[0])
            elif token.type not in _IGNORED_TOKENS:
                code.update(range(token.start[0], token.end[0] + 1))
    except (tokenize.TokenError, IndentationError) as error:
        raise ParseError(path, 1, 1, str(error)) from error

    return code, comments


def _detect_newline(text: str) -> str:
    index = text.find("\n")
    if index > 0 and text[index - 1] == "\r":
        return "\r\n"

    return "\n"
