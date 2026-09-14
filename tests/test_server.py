"""Drives the language server over stdio, the way an editor does."""

import json
import subprocess
import sys

import pytest

pytest.importorskip("pygls")

DIRTY = "import os\nx = compute()\nsetup()\nif ready:\n    run()\n"
URI = "file:///tmp/demo.py"


class Client:
    def __init__(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "pywsl_lint", "server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def send(self, payload: dict) -> None:
        body = json.dumps(payload).encode()

        self.process.stdin.write(b"Content-Length: %d\r\n\r\n%s" % (len(body), body))

        self.process.stdin.flush()

    def receive(self) -> dict:
        header = b""
        while not header.endswith(b"\r\n\r\n"):
            chunk = self.process.stdout.read(1)
            if not chunk:
                raise AssertionError("the server closed the connection")

            header += chunk

        for field in header.decode().split("\r\n"):
            if field.lower().startswith("content-length"):
                return json.loads(self.process.stdout.read(int(field.split(":")[1])))

        raise AssertionError("no Content-Length in the reply")

    def request(self, identifier: int, method: str, params: dict) -> dict:
        self.send(
            {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}
        )

        return self.receive()

    def close(self) -> None:
        self.process.stdin.close()

        self.process.wait(timeout=15)


@pytest.fixture
def client():
    session = Client()
    session.request(
        1, "initialize", {"processId": None, "rootUri": None, "capabilities": {}}
    )

    session.send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
    yield session

    session.close()


def open_document(client: Client, text: str = DIRTY) -> dict:
    client.send(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": URI,
                    "languageId": "python",
                    "version": 1,
                    "text": text,
                }
            },
        }
    )

    return client.receive()


def test_the_server_announces_what_it_can_do():
    session = Client()
    capabilities = session.request(
        1, "initialize", {"processId": None, "rootUri": None, "capabilities": {}}
    )["result"]["capabilities"]

    session.close()

    assert capabilities["documentFormattingProvider"] is True
    assert capabilities["codeActionProvider"]["codeActionKinds"] == ["quickfix"]


def test_opening_a_document_publishes_diagnostics(client):
    published = open_document(client)

    assert published["method"] == "textDocument/publishDiagnostics"

    found = published["params"]["diagnostics"]
    assert [d["code"] for d in found] == ["WSL001", "WSL008", "WSL007"]
    assert all(d["source"] == "pywsl-lint" for d in found)
    assert all(d["severity"] == 2 for d in found)


def test_a_clean_document_publishes_nothing(client):
    published = open_document(client, "import os\n\nx = 1\n")

    assert published["params"]["diagnostics"] == []


def test_a_syntax_error_is_not_reported_as_a_violation(client):
    published = open_document(client, "def f(:\n")

    assert published["params"]["diagnostics"] == []


def test_the_cursor_line_offers_a_quick_fix(client):
    open_document(client)

    actions = client.request(
        2,
        "textDocument/codeAction",
        {
            "textDocument": {"uri": URI},
            "range": {
                "start": {"line": 3, "character": 0},
                "end": {"line": 3, "character": 0},
            },
            "context": {"diagnostics": []},
        },
    )["result"]

    titles = [a["title"] for a in actions]
    assert titles == ["Insert blank line", "Fix all pywsl-lint violations"]

    edit = actions[0]["edit"]["changes"][URI][0]
    assert edit["newText"] == "\n"
    assert edit["range"]["start"] == {"line": 3, "character": 0}


def test_formatting_returns_the_fixed_document(client):
    open_document(client)

    edits = client.request(
        3,
        "textDocument/formatting",
        {"textDocument": {"uri": URI}, "options": {"tabSize": 4, "insertSpaces": True}},
    )["result"]

    assert len(edits) == 1
    assert edits[0]["newText"] == (
        "import os\n\nx = compute()\n\nsetup()\n\nif ready:\n    run()\n"
    )


def test_formatting_a_clean_document_returns_no_edits(client):
    open_document(client, "import os\n\nx = 1\n")

    edits = client.request(
        4,
        "textDocument/formatting",
        {"textDocument": {"uri": URI}, "options": {"tabSize": 4, "insertSpaces": True}},
    )["result"]

    assert edits == []
