"""Tests for ``fixyourdocs._cli.run_cli``."""

from __future__ import annotations

import io
import json
import os
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
import respx

from fixyourdocs._cli import run_cli
from fixyourdocs.snippet import SNIPPET_HEADING

API_URL = "https://hub.example.test"
REPORTS_URL = f"{API_URL}/v1/reports"


def _io() -> tuple[io.StringIO, io.StringIO]:
    return io.StringIO(), io.StringIO()


@pytest.fixture
def cwd(tmp_path: Path) -> Iterator[Path]:
    original = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(original)


def test_version_prints_package_version() -> None:
    out, err = _io()
    code = run_cli(["--version"], stdout=out, stderr=err)
    # argparse writes --version output to stdout itself; we map its exit
    # to our return code.
    assert code == 0


def test_help_returns_zero() -> None:
    out, err = _io()
    code = run_cli(["--help"], stdout=out, stderr=err)
    assert code == 0


def test_unknown_subcommand_returns_two() -> None:
    out, err = _io()
    code = run_cli(["bogus"], stdout=out, stderr=err)
    assert code == 2


def test_init_creates_agents_md(cwd: Path) -> None:
    out, err = _io()
    code = run_cli(["init"], stdout=out, stderr=err)
    assert code == 0
    target = cwd / "AGENTS.md"
    assert SNIPPET_HEADING in target.read_text()
    assert "Created" in out.getvalue()


def test_init_json_output(cwd: Path) -> None:
    out, err = _io()
    code = run_cli(["init", "--json"], stdout=out, stderr=err)
    assert code == 0
    parsed = json.loads(out.getvalue())
    assert parsed["created"] is True
    assert parsed["changed"] is True
    assert parsed["path"] == str((cwd / "AGENTS.md").resolve())


def test_init_idempotent_second_run_reports_no_change(cwd: Path) -> None:
    run_cli(["init"], stdout=io.StringIO(), stderr=io.StringIO())
    out, err = _io()
    code = run_cli(["init"], stdout=out, stderr=err)
    assert code == 0
    assert "No changes" in out.getvalue()


def test_init_rejects_unknown_flag(cwd: Path) -> None:
    out, err = _io()
    code = run_cli(["init", "--nope"], stdout=out, stderr=err)
    assert code == 2


@respx.mock
def test_report_happy_path() -> None:
    captured: dict[str, object] = {}

    def _ack(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            201,
            json={
                "id": "rep_cli_py_01",
                "received_at": "2026-06-06T12:34:56Z",
                "protocol_version": "0",
                "server_capabilities": [],
            },
        )

    respx.post(REPORTS_URL).mock(side_effect=_ack)
    out, err = _io()
    code = run_cli(
        [
            "report",
            "--api-url",
            API_URL,
            "--doc-url",
            "https://example.com/docs/install",
            "--summary",
            "Install fails on macOS 14",
            "--agent",
            "claude-code",
            "--kind",
            "broken",
        ],
        stdout=out,
        stderr=err,
    )
    assert code == 0
    assert "rep_cli_py_01" in out.getvalue()
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["protocol_version"] == "0"
    assert body["doc_url"] == "https://example.com/docs/install"
    assert body["agent"]["name"] == "claude-code"
    assert body["report"]["kind"] == "broken"


def test_report_missing_required_returns_two() -> None:
    out, err = _io()
    code = run_cli(
        ["report", "--api-url", API_URL],
        stdout=out,
        stderr=err,
    )
    assert code == 2


def test_report_bad_kind_returns_two() -> None:
    out, err = _io()
    code = run_cli(
        [
            "report",
            "--api-url",
            API_URL,
            "--doc-url",
            "https://example.com",
            "--summary",
            "x",
            "--agent",
            "claude-code",
            "--kind",
            "weird",
        ],
        stdout=out,
        stderr=err,
    )
    assert code == 2


@respx.mock
def test_report_server_error_returns_one() -> None:
    respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(
            422,
            json={"error": "policy_rejected", "reason": "unknown agent.name"},
        )
    )
    out, err = _io()
    code = run_cli(
        [
            "report",
            "--api-url",
            API_URL,
            "--doc-url",
            "https://example.com",
            "--summary",
            "x",
            "--agent",
            "claude-code",
        ],
        stdout=out,
        stderr=err,
    )
    assert code == 1
    assert "policy_rejected" in err.getvalue()


@respx.mock
def test_report_json_output() -> None:
    respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "rep_cli_py_json",
                "received_at": "2026-06-06T12:34:56Z",
                "protocol_version": "0",
                "server_capabilities": [],
            },
        )
    )
    out, err = _io()
    code = run_cli(
        [
            "report",
            "--api-url",
            API_URL,
            "--doc-url",
            "https://example.com",
            "--summary",
            "x",
            "--agent",
            "claude-code",
            "--json",
        ],
        stdout=out,
        stderr=err,
    )
    assert code == 0
    parsed = json.loads(out.getvalue())
    assert parsed["id"] == "rep_cli_py_json"
