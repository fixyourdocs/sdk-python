"""Round-trip the canonical fixtures through the Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError as PydanticValidationError

from fixyourdocs import (
    AgentInfo,
    Evidence,
    EvidenceKind,
    Report,
    ReportBody,
    ReportKind,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict[str, Any]:
    """Load a fixture and drop the SPDX ``$comment`` (tooling-only field)."""
    data = json.loads((FIXTURES / name).read_text())
    data.pop("$comment", None)
    return data


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True)


@pytest.mark.parametrize(
    "fixture",
    ["minimum-required.json", "golden-path.json", "full.json"],
)
def test_fixture_round_trip(fixture: str) -> None:
    expected = _load_fixture(fixture)
    report = Report.model_validate(expected)
    actual = report.model_dump(mode="json", exclude_none=True, by_alias=True)
    assert _canonical(actual) == _canonical(expected)


def test_invalid_fixture_rejected() -> None:
    data = _load_fixture("invalid.json")
    with pytest.raises(PydanticValidationError):
        Report.model_validate(data)


def test_create_minimum_required() -> None:
    fixture = _load_fixture("minimum-required.json")
    report = Report.create(
        doc_url=fixture["doc_url"],
        summary=fixture["report"]["summary"],
        kind=fixture["report"]["kind"],
        agent_name=fixture["agent"]["name"],
    )
    actual = report.model_dump(mode="json", exclude_none=True, by_alias=True)
    assert _canonical(actual) == _canonical(fixture)


def test_create_golden_path() -> None:
    fixture = _load_fixture("golden-path.json")
    report = Report.create(
        doc_url=fixture["doc_url"],
        summary=fixture["report"]["summary"],
        kind=fixture["report"]["kind"],
        agent_name=fixture["agent"]["name"],
        agent_version=fixture["agent"]["version"],
        agent_vendor=fixture["agent"]["vendor"],
        details=fixture["report"]["details"],
        evidence=fixture["report"]["evidence"],
        suggested_fix=fixture["report"]["suggested_fix"],
        task_summary=fixture["task_context"]["task_summary"],
        submitted_at=Report.model_validate(fixture).submitted_at,
    )
    actual = report.model_dump(mode="json", exclude_none=True, by_alias=True)
    assert _canonical(actual) == _canonical(fixture)


def test_create_full() -> None:
    fixture = _load_fixture("full.json")
    parsed = Report.model_validate(fixture)
    report = Report.create(
        doc_url=fixture["doc_url"],
        summary=fixture["report"]["summary"],
        kind=fixture["report"]["kind"],
        agent_name=fixture["agent"]["name"],
        agent_version=fixture["agent"]["version"],
        agent_vendor=fixture["agent"]["vendor"],
        details=fixture["report"]["details"],
        evidence=fixture["report"]["evidence"],
        suggested_fix=fixture["report"]["suggested_fix"],
        task_summary=fixture["task_context"]["task_summary"],
        transcript_excerpt=fixture["task_context"]["transcript_excerpt"],
        idempotency_key=fixture["idempotency_key"],
        submitted_at=parsed.submitted_at,
        locale=fixture["locale"],
        client_capabilities=fixture["client_capabilities"],
    )
    actual = report.model_dump(mode="json", exclude_none=True, by_alias=True)
    assert _canonical(actual) == _canonical(fixture)


def test_nested_constructor_form() -> None:
    """The typed nested constructor builds an equivalent object."""
    flat = Report.create(
        doc_url="https://docs.example.org/page",
        summary="Summary",
        kind=ReportKind.INCORRECT,
        agent_name="claude-code",
    )
    nested = Report(
        doc_url="https://docs.example.org/page",
        agent=AgentInfo(name="claude-code"),
        report=ReportBody(kind=ReportKind.INCORRECT, summary="Summary"),
    )
    assert flat.model_dump(mode="json", exclude_none=True) == nested.model_dump(
        mode="json", exclude_none=True
    )


def test_evidence_kind_enum_values() -> None:
    ev = Evidence(kind=EvidenceKind.ERROR_MESSAGE, text="boom")
    dumped = ev.model_dump(mode="json")
    assert dumped == {"kind": "error_message", "text": "boom"}


def test_agent_name_pattern_enforced() -> None:
    with pytest.raises(PydanticValidationError):
        AgentInfo(name="Bad_Name")


def test_summary_length_enforced() -> None:
    with pytest.raises(PydanticValidationError):
        ReportBody(kind=ReportKind.OTHER, summary="x" * 501)


def test_extra_fields_forbidden() -> None:
    with pytest.raises(PydanticValidationError):
        Report.model_validate(
            {
                "protocol_version": "0",
                "doc_url": "https://docs.example.org/page",
                "agent": {"name": "claude-code"},
                "report": {"kind": "incorrect", "summary": "S"},
                "priority": "high",
            }
        )
