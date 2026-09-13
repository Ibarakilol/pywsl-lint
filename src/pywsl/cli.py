"""Command line interface."""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pywsl import __version__, checks, discovery, fixer, reporting
from pywsl import config as config_module
from pywsl import source as source_module
from pywsl.config import Config, ConfigError
from pywsl.diagnostics import Diagnostic
from pywsl.engine import check_source
from pywsl.source import ParseError, SourceFile

EXIT_OK = 0
EXIT_VIOLATIONS = 1
EXIT_ERROR = 2


@dataclass
class FileReport:
    source: SourceFile
    diagnostics: list[Diagnostic] = field(default_factory=list)
    fixed_count: int = 0
    changed: bool = False
    diff: str = ""


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_ERROR

    try:
        if args.command == "rules":
            return _run_rules(args)

        return _run_lint(args)
    except ConfigError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
    except BrokenPipeError:
        return EXIT_OK


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pywsl",
        description="Whitespace linter for Python, in the spirit of wsl.",
    )
    parser.add_argument("--version", action="version", version=f"pywsl {__version__}")
    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser("check", help="report blank-line violations")
    _add_common(check)
    check.add_argument("--fix", action="store_true", help="apply fixes in place")
    check.add_argument(
        "--output-format",
        choices=reporting.FORMATS,
        default="full",
        help="diagnostic output format (default: full)",
    )
    check.add_argument(
        "--statistics", action="store_true", help="count violations per check"
    )
    check.add_argument(
        "--exit-zero", action="store_true", help="always exit with status 0"
    )

    formatter = sub.add_parser("format", help="rewrite files with correct blank lines")
    _add_common(formatter)
    formatter.add_argument(
        "--check",
        action="store_true",
        help="do not write, exit 1 if changes are needed",
    )

    rules = sub.add_parser("rules", help="list the available checks")
    rules.add_argument("--output-format", choices=("text", "json"), default="text")

    return parser


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("paths", nargs="*", default=["."], help="files or directories")
    parser.add_argument(
        "--diff", action="store_true", help="print the changes instead of applying them"
    )
    parser.add_argument("--config", type=Path, help="path to a pyproject.toml")
    parser.add_argument(
        "--isolated", action="store_true", help="ignore any configuration file"
    )
    parser.add_argument("--select", action="append", help="checks to enable")
    parser.add_argument("--extend-select", action="append", help="checks to add")
    parser.add_argument("--ignore", action="append", help="checks to disable")
    parser.add_argument("--extend-exclude", action="append", help="paths to skip")
    parser.add_argument(
        "--stdin-filename", help="name to report for source read from stdin"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="only print problems"
    )


def _run_rules(args: argparse.Namespace) -> int:
    if args.output_format == "json":
        payload = [
            {
                "code": check.code,
                "name": check.name,
                "summary": check.summary,
                "default": check.default,
            }
            for check in checks.ALL_CHECKS
        ]
        print(json.dumps(payload, indent=2))
        return EXIT_OK

    width = max(len(check.name) for check in checks.ALL_CHECKS)
    for check in checks.ALL_CHECKS:
        mark = " " if check.default else "-"
        print(f"{check.code} {mark} {check.name:<{width}}  {check.summary}")

    return EXIT_OK


def _run_lint(args: argparse.Namespace) -> int:
    config = _resolve_config(args)
    is_format = args.command == "format"
    wants_fix = is_format or getattr(args, "fix", False) or args.diff
    write = wants_fix and not args.diff and not getattr(args, "check", False)

    reports: list[FileReport] = []
    failures = 0
    for source, error, from_stdin in _read(args.paths or ["."], config, args):
        if source is None:
            print(_format_parse_error(error), file=sys.stderr)
            failures += 1
            continue

        reports.append(
            _process(source, config, wants_fix=wants_fix, write=write, stdin=from_stdin)
        )

    return _emit(reports, args, failures)


def _process(
    source: SourceFile,
    config: Config,
    *,
    wants_fix: bool,
    write: bool,
    stdin: bool,
) -> FileReport:
    if not wants_fix:
        return FileReport(source, check_source(source, config))

    result = fixer.fix(source, config)
    report = FileReport(
        source,
        result.remaining,
        fixed_count=result.fixed_count,
        changed=result.changed,
        diff=_diff(source, result.text) if result.changed else "",
    )
    if not write:
        return report

    if stdin:
        sys.stdout.write(result.text)
    elif result.changed:
        Path(source.path).write_text(result.text, encoding=source.encoding)

    return report


def _emit(reports: list[FileReport], args: argparse.Namespace, failures: int) -> int:
    changed = sum(1 for report in reports if report.changed)
    if args.diff:
        for report in reports:
            if report.diff:
                print(report.diff)

        if not args.quiet:
            sys.stdout.flush()
            print(
                _changed_summary(changed, len(reports), checked=True), file=sys.stderr
            )

        return EXIT_VIOLATIONS if changed or failures else EXIT_OK

    if args.command == "format":
        if not args.quiet:
            print(_changed_summary(changed, len(reports), checked=args.check))

        if failures or (args.check and changed):
            return EXIT_VIOLATIONS

        return EXIT_OK

    found = [d for report in reports for d in report.diagnostics]
    entries = [(r.source, r.diagnostics) for r in reports if r.diagnostics]
    if args.statistics:
        text = reporting.statistics(found)
        if text:
            print(text)
    elif entries:
        print(reporting.render(entries, args.output_format))

    if not args.quiet and args.output_format in {"full", "concise"}:
        print(
            reporting.summary(
                len(found),
                fixed=sum(report.fixed_count for report in reports),
                fixable=0 if args.fix else len(found),
            )
        )

    if args.exit_zero:
        return EXIT_OK

    return EXIT_VIOLATIONS if found or failures else EXIT_OK


def _changed_summary(changed: int, total: int, *, checked: bool = False) -> str:
    verb = "would be reformatted" if checked else "reformatted"
    unchanged = total - changed
    parts = []
    if changed:
        parts.append(f"{changed} file{'s' if changed != 1 else ''} {verb}")

    if unchanged:
        parts.append(f"{unchanged} file{'s' if unchanged != 1 else ''} left unchanged")

    return ", ".join(parts) or "0 files reformatted"


def _read(
    paths: Sequence[str], config: Config, args: argparse.Namespace
) -> list[tuple[SourceFile | None, ParseError | None, bool]]:
    if list(paths) == ["-"]:
        name = args.stdin_filename or "-"
        try:
            return [(source_module.from_text(sys.stdin.read(), name), None, True)]
        except ParseError as error:
            return [(None, error, True)]

    results: list[tuple[SourceFile | None, ParseError | None, bool]] = []
    for path in discovery.collect(paths, config):
        try:
            results.append((source_module.from_path(path), None, False))
        except ParseError as error:
            results.append((None, error, False))
        except OSError as error:
            results.append((None, ParseError(str(path), 1, 1, str(error)), False))

    return results


def _resolve_config(args: argparse.Namespace) -> Config:
    if args.isolated:
        config = Config()
    elif args.config is not None:
        config = config_module.load(args.config)
    else:
        config = config_module.load(config_module.find_pyproject(Path.cwd()))

    return config_module.apply_selectors(
        config,
        select=_split(args.select),
        extend_select=_split(args.extend_select),
        ignore=_split(args.ignore),
        extend_exclude=_split(args.extend_exclude),
        origin="command line",
    )


def _split(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None

    return [item for value in values for item in value.split(",") if item]


def _diff(source: SourceFile, fixed: str) -> str:
    before = source.text.splitlines(keepends=True)
    after = fixed.splitlines(keepends=True)
    patch = difflib.unified_diff(
        before, after, fromfile=source.path, tofile=source.path, lineterm="\n"
    )
    return "".join(patch).rstrip("\n")


def _format_parse_error(error: ParseError | None) -> str:
    if error is None:
        return "error: unknown failure"

    return f"{error.path}:{error.line}:{error.column}: error: {error.message}"


if __name__ == "__main__":
    raise SystemExit(main())
