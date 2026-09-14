"""Language server exposing the checks as diagnostics and quick fixes."""

from pathlib import Path

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

from pywsl_lint import __version__
from pywsl_lint import config as config_module
from pywsl_lint import lsp as convert
from pywsl_lint import source as source_module
from pywsl_lint.config import Config
from pywsl_lint.diagnostics import Diagnostic
from pywsl_lint.engine import check_source
from pywsl_lint.source import ParseError, SourceFile

SOURCE_NAME = "pywsl-lint"


def create() -> LanguageServer:
    server = LanguageServer(SOURCE_NAME, __version__)

    @server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
    @server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
    @server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
    def _publish(ls: LanguageServer, params) -> None:
        uri = params.text_document.uri
        parsed = _parse(ls, uri)
        if parsed is None:
            ls.text_document_publish_diagnostics(
                lsp.PublishDiagnosticsParams(uri=uri, diagnostics=[])
            )

            return

        source, config = parsed
        found = check_source(source, config)
        ls.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(
                uri=uri,
                diagnostics=[_as_diagnostic(source, d) for d in found],
            )
        )

    @server.feature(
        lsp.TEXT_DOCUMENT_CODE_ACTION,
        lsp.CodeActionOptions(
            code_action_kinds=[lsp.CodeActionKind.QuickFix],
            resolve_provider=False,
        ),
    )
    def _code_action(ls: LanguageServer, params: lsp.CodeActionParams):
        uri = params.text_document.uri
        parsed = _parse(ls, uri)
        if parsed is None:
            return []

        source, config = parsed
        found = check_source(source, config)
        selected = [d for d in found if _touches(params.range, d.line)]
        actions = []

        for diagnostic in selected:
            edit = convert.edit_for(source, diagnostic)
            if edit is None:
                continue

            actions.append(
                _action(
                    uri,
                    diagnostic.fix_title,
                    [edit],
                    [_as_diagnostic(source, diagnostic)],
                )
            )

        whole = convert.format_edit(source, config)
        if whole is not None and found:
            actions.append(_action(uri, "Fix all pywsl-lint violations", [whole], []))

        return actions

    @server.feature(lsp.TEXT_DOCUMENT_FORMATTING)
    def _format(ls: LanguageServer, params: lsp.DocumentFormattingParams):
        parsed = _parse(ls, params.text_document.uri)
        if parsed is None:
            return []

        source, config = parsed
        edit = convert.format_edit(source, config)

        return [] if edit is None else [_text_edit(edit)]

    return server


def _parse(ls: LanguageServer, uri: str) -> tuple[SourceFile, Config] | None:
    document = ls.workspace.get_text_document(uri)
    try:
        source = source_module.from_text(document.source, document.path)
    except ParseError:
        return None

    return source, _config_for(document.path)


def _config_for(path: str) -> Config:
    try:
        return config_module.load(config_module.find_pyproject(Path(path)))
    except config_module.ConfigError:
        return Config()


def _as_diagnostic(source: SourceFile, diagnostic: Diagnostic) -> lsp.Diagnostic:
    span = convert.highlight(source, diagnostic)

    return lsp.Diagnostic(
        range=_range(span),
        message=f"{diagnostic.message} ({diagnostic.name})",
        severity=lsp.DiagnosticSeverity.Warning,
        code=diagnostic.code,
        source=SOURCE_NAME,
    )


def _action(
    uri: str,
    title: str,
    edits: list[convert.Edit],
    diagnostics: list[lsp.Diagnostic],
) -> lsp.CodeAction:
    return lsp.CodeAction(
        title=title,
        kind=lsp.CodeActionKind.QuickFix,
        diagnostics=diagnostics,
        edit=lsp.WorkspaceEdit(changes={uri: [_text_edit(e) for e in edits]}),
    )


def _text_edit(edit: convert.Edit) -> lsp.TextEdit:
    return lsp.TextEdit(range=_range(edit.span), new_text=edit.new_text)


def _range(span: convert.Span) -> lsp.Range:
    return lsp.Range(
        start=lsp.Position(line=span.start_line, character=span.start_char),
        end=lsp.Position(line=span.end_line, character=span.end_char),
    )


def _touches(selection: lsp.Range, line: int) -> bool:
    return selection.start.line <= line - 1 <= selection.end.line


def main() -> int:
    create().start_io()

    return 0
