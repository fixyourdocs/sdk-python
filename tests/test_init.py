"""Tests for ``fixyourdocs._init.run_init``."""

from __future__ import annotations

from pathlib import Path

from fixyourdocs._init import run_init
from fixyourdocs.snippet import SNIPPET, SNIPPET_HEADING


def test_creates_agents_md_when_nothing_exists(tmp_path: Path) -> None:
    result = run_init(tmp_path)
    assert result.created is True
    assert result.changed is True
    assert result.path == (tmp_path / "AGENTS.md").resolve()
    assert (tmp_path / "AGENTS.md").read_text() == SNIPPET


def test_appends_to_existing_agents_md(tmp_path: Path) -> None:
    target = tmp_path / "AGENTS.md"
    target.write_text("# My repo\n\nDo things.")
    result = run_init(tmp_path)
    assert result.created is False
    assert result.changed is True
    after = target.read_text()
    assert after.startswith("# My repo\n\nDo things.")
    assert SNIPPET_HEADING in after


def test_idempotent_on_second_run(tmp_path: Path) -> None:
    run_init(tmp_path)
    first = (tmp_path / "AGENTS.md").read_text()
    result = run_init(tmp_path)
    assert result.changed is False
    assert (tmp_path / "AGENTS.md").read_text() == first


def test_prefers_claude_md_when_only_claude_exists(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text("# Claude rules\n")
    result = run_init(tmp_path)
    assert result.path == target.resolve()
    assert SNIPPET_HEADING in target.read_text()


def test_prefers_agents_md_when_both_present(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Agents\n")
    (tmp_path / "CLAUDE.md").write_text("# Claude\n")
    result = run_init(tmp_path)
    assert result.path == (tmp_path / "AGENTS.md").resolve()


def test_explicit_file_override(tmp_path: Path) -> None:
    result = run_init(tmp_path, file="INSTRUCTIONS.md")
    target = tmp_path / "INSTRUCTIONS.md"
    assert result.path == target.resolve()
    assert result.created is True
    assert target.read_text() == SNIPPET
