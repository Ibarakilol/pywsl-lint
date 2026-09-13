# pywsl

Whitespace linter and formatter for Python — a port of
[bombsimon/wsl](https://github.com/bombsimon/wsl) with rules adapted to Python
syntax.

It enforces one idea: **if the line above a block statement is not related to it
through a shared variable, there must be a blank line between them.**

Run it next to `ruff` — it only reports blank-line placement, which `ruff` does
not check.
