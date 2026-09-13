# pywsl-lint

Whitespace linter and formatter for Python — a port of
[bombsimon/wsl](https://github.com/bombsimon/wsl) with rules adapted to Python
syntax.

It enforces one idea: **if the line above a block statement is not related to it
through a shared variable, there must be a blank line between them.** Every
diagnostic it reports reduces to inserting or removing one blank line, so every
diagnostic is fixable.

```python
# before
data = read(path)
count: int
if os.path.exists(path):
    print(path)
return data

# after `pywsl-lint format`
data = read(path)

count: int

if os.path.exists(path):
    print(path)

return data
```

## Install

```sh
uv tool install pywsl-lint          # as a standalone tool
uv add --dev pywsl-lint             # into a project
```

Requires Python 3.11 or newer.

## Use

```sh
pywsl-lint check .                  # report
pywsl-lint check --fix .            # report and fix
pywsl-lint check --diff .           # show what --fix would do
pywsl-lint format .                 # fix quietly, like a formatter
pywsl-lint format --check .         # exit 1 if anything would change
pywsl-lint rules                    # list every check
```

Exit codes match `ruff`: `0` clean, `1` violations remain, `2` bad invocation or
configuration.

`--output-format` accepts `full` (default), `concise`, `json` and `github`.
Reading from `-` lints stdin; pair it with `--stdin-filename` for editor
integration.

### Next to ruff

`pywsl-lint` only ever moves blank lines, which `ruff` and `black` do not touch
inside a block. Run them in either order:

```sh
ruff check --fix . && ruff format . && pywsl-lint format .
```

## Rules

`-` marks a check that is off unless you select it.

| Code | Name | What it requires |
| --- | --- | --- |
| WSL001 | `assign` | An assignment may only cuddle another assignment. |
| WSL002 | `aug-assign` | `x += 1` follows the same rule as `assign`. |
| WSL003 | `branch` | `break` / `continue` may only cuddle inside a block of at most `branch-max-lines` lines. |
| WSL004 | `decl` | A bare annotation (`x: int`) never cuddles code — but annotated names cuddle each other, with or without a value. |
| WSL005 | `for` | A `for` may only cuddle an assignment used in its target or iterable. |
| WSL006 | `while` | A `while` may only cuddle an assignment used in its condition. |
| WSL007 | `if` | An `if` may only cuddle an assignment used in its condition. |
| WSL008 | `expr` | A bare call may only cuddle an assignment it uses. Docstrings are not calls and are exempt. |
| WSL009 | `return` | A `return` needs a blank line above it in a block longer than `branch-max-lines` lines. |
| WSL010 | `with` | A `with` may only cuddle an assignment used in its context expression. |
| WSL011 | `try` | A `try` may only cuddle an assignment used by the code it guards. |
| WSL012 | `match` | A `match` may only cuddle an assignment used in its subject. |
| WSL013 | `case-isinstance` | As `match`, reported separately when the cases are class patterns. |
| WSL014 | `thread-start` | `t.start()`, `asyncio.create_task(...)` and friends may only cuddle an assignment used in the call. |
| WSL015 | `queue-put` | `q.put(x)` may only cuddle an assignment used in the send. |
| WSL020 | `after-block` | A `def` or `class` is followed by a blank line. |
| WSL021 | `after-if` | An `if` is followed by a blank line. |
| WSL022 | `after-for` | A `for` is followed by a blank line. |
| WSL023 | `after-while` | A `while` is followed by a blank line. |
| WSL024 | `after-try` | A `try` is followed by a blank line. |
| WSL025 | `after-with` | A `with` is followed by a blank line. |
| WSL026 | `after-match` | A `match` is followed by a blank line. |
| WSL027 | `after-decl` | A bare annotation is followed by a blank line. |
| WSL028 | `after-expr` | A bare call is followed by a blank line. |
| WSL029 | `after-thread-start` | A thread or task start is followed by a blank line. |
| WSL030 | `append` | `items.append(x)` and `items = items + [x]` may only cuddle a line that binds the list or the value. |
| WSL031 - | `assign-expr` | An assignment never cuddles a bare call, even one that uses it. |
| WSL032 | `cuddle-group` | At most `cuddle-max-statements` statements may be cuddled above a block. |
| WSL033 | `except-immediate` | `except` / `else` / `finally` follow the body with no blank line, and `if x is None:` stays glued to the call that produced `x`. |
| WSL034 | `leading-whitespace` | A block body does not start with a blank line. |
| WSL035 | `trailing-whitespace` | A block body does not end with a blank line before `elif` or `else`. |
| WSL036 | `case-max-lines` | A `case` longer than `case-max-lines` lines is followed by a blank line. Off until you set the option. |

The `after-*` rules exempt a run of the same construct, so consecutive `if`
statements may cuddle and only the last one needs the blank line below it.

## Configuration

`[tool.pywsl-lint]` in the nearest `pyproject.toml`. Keys accept dashes or
underscores.

```toml
[tool.pywsl-lint]
allow-first-in-block = true     # cuddle if the variable is used by the block's first statement
allow-whole-block = false       # cuddle if the variable is used anywhere in the block
branch-max-lines = 2            # block size above which return/break/continue need a blank line
case-max-lines = 0              # 0 disables the case-max-lines check
cuddle-max-statements = 1       # statements allowed to cuddle above a block
select = ["ALL"]                # replaces the default set
extend-select = ["assign-expr"] # adds to it
ignore = ["after-expr"]         # removes from it
exclude = [".venv", "build"]    # replaces the default exclusions
extend-exclude = ["generated"]  # adds to them
```

`--select`, `--extend-select`, `--ignore` and `--extend-exclude` take the same
values on the command line, comma-separated or repeated. A selector may be a
name (`if`), a code (`WSL007`), a code prefix (`WSL00`) or `ALL`.

## How the Go rules were adapted

| wsl (Go) | pywsl-lint |
| --- | --- |
| `var` / `const` / `type` | a bare annotation, `x: int` |
| `inc-dec` | `aug-assign` |
| `switch` | `match` |
| `type-switch` | `case-isinstance` |
| `go` | `thread-start` — `Thread(...).start()`, `create_task`, `ensure_future`, `submit` |
| `send` | `queue-put` — `q.put(x)`, `await q.put(x)` |
| `defer` | split into `with` and `try` |
| `err` | `except-immediate` |
| `for` without `range` | `while` |
| `label`, `select`, `goto`, `fallthrough` | dropped — no Python equivalent |
| `assign-exclusive` | dropped — Python has no `:=` / `=` distinction for statements |

Three places needed a decision that wsl did not face, because Python has no
closing brace and carries meaning in constructs Go spells differently:

- **`trailing-whitespace`.** A dedent does not close a block the way `}` does,
  so a blank line after the last statement of a block is the same blank line
  the `after-*` rules require below it. Forbidding and requiring it at once
  would leave the fixer nothing to converge on, so the check only fires before
  a continuation clause (`elif`, `else`), where the blank is unambiguously
  inside the block.
- **Annotated names.** `x: int` and `x: int = 0` both declare a field, so
  `decl`, `assign` and `after-decl` treat them as one kind and let them cuddle
  each other. Otherwise a dataclass with defaults would need a blank line in
  the middle of its field list.
- **Docstrings.** A string statement opening a module, class or function is not
  a call, so `expr` and `after-expr` skip it. A block statement below one still
  needs its blank line.

A blank line before the next `case` of a `match` is deliberately left free:
neither required nor forbidden, unless `case-max-lines` is set and the case
above it is longer than that.

## Development

```sh
uv sync
uv run pytest
uv run ruff check src tests && uv run ruff format --check src tests
uv run pywsl-lint check src tests
```

The test suite lints pywsl-lint's own source with its own rules, so the codebase
cannot drift from what it enforces.
