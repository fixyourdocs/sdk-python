"""Pydantic v2 models mirroring ``schema/v0/report.schema.json``.

The models are deliberately a 1:1 translation of the JSON Schema so
serialised output round-trips byte-for-byte against the canonical
example fixtures. ``Report.create(...)`` is the ergonomic, flat
constructor most callers should reach for; the nested
``Report(agent=..., report=...)`` form is exposed for advanced use.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class EvidenceKind(str, Enum):
    """Enumerated kinds of evidence; see §4.4 of the spec."""

    ERROR_MESSAGE = "error_message"
    ATTEMPTED_ACTION = "attempted_action"
    EXPECTED = "expected"
    OBSERVED = "observed"
    CODE_SNIPPET = "code_snippet"
    QUOTE = "quote"


class ReportKind(str, Enum):
    """Enumerated kinds of report; see §4.4 of the spec."""

    BROKEN = "broken"
    INCORRECT = "incorrect"
    OUTDATED = "outdated"
    MISSING = "missing"
    UNCLEAR = "unclear"
    OTHER = "other"


class Evidence(BaseModel):
    """One evidence item attached to a report body."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    kind: EvidenceKind
    text: str = Field(..., min_length=1, max_length=4000)


class AgentInfo(BaseModel):
    """Identification of the agent that produced the report."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
    )
    version: Optional[str] = Field(default=None, max_length=64)
    vendor: Optional[str] = Field(default=None, max_length=128)


class ReportBody(BaseModel):
    """The substance of the feedback."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    kind: ReportKind
    summary: str = Field(..., min_length=1, max_length=500)
    details: Optional[str] = Field(default=None, max_length=8000)
    evidence: Optional[list[Evidence]] = Field(default=None, max_length=20)
    suggested_fix: Optional[str] = Field(default=None, max_length=4000)


class TaskContext(BaseModel):
    """Optional context about the agent task that surfaced the issue."""

    model_config = ConfigDict(extra="forbid")

    task_summary: Optional[str] = Field(default=None, max_length=500)
    transcript_excerpt: Optional[str] = Field(default=None, max_length=4000)


class Report(BaseModel):
    """A single Docs Feedback Protocol v0 report.

    Use :meth:`Report.create` for the ergonomic flat constructor. The
    nested form (passing :class:`AgentInfo` / :class:`ReportBody`
    explicitly) is also supported.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    protocol_version: Literal["0"] = "0"
    doc_url: str = Field(..., max_length=2048)
    agent: AgentInfo
    report: ReportBody
    task_context: Optional[TaskContext] = None
    idempotency_key: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[\x21-\x7e]+$",
    )
    submitted_at: Optional[datetime] = None
    locale: Optional[str] = Field(
        default=None,
        max_length=35,
        pattern=r"^[A-Za-z]{1,8}(-[A-Za-z0-9]{1,8})*$",
    )
    client_capabilities: Optional[list[str]] = Field(default=None, max_length=32)

    @classmethod
    def create(
        cls,
        *,
        doc_url: str,
        summary: str,
        kind: ReportKind | str,
        agent_name: str,
        agent_version: Optional[str] = None,
        agent_vendor: Optional[str] = None,
        details: Optional[str] = None,
        evidence: Optional[list[Evidence | dict[str, Any]]] = None,
        suggested_fix: Optional[str] = None,
        task_summary: Optional[str] = None,
        transcript_excerpt: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        submitted_at: Optional[datetime] = None,
        locale: Optional[str] = None,
        client_capabilities: Optional[list[str]] = None,
    ) -> Report:
        """Build a :class:`Report` from a flat keyword-argument set.

        This is the convenience constructor for the common case of
        producing a one-shot report without manually instantiating the
        nested ``AgentInfo``, ``ReportBody``, and ``TaskContext``
        objects.
        """
        agent = AgentInfo(name=agent_name, version=agent_version, vendor=agent_vendor)

        ev_models: Optional[list[Evidence]]
        if evidence is None:
            ev_models = None
        else:
            ev_models = [
                item if isinstance(item, Evidence) else Evidence(**item) for item in evidence
            ]

        body = ReportBody(
            kind=ReportKind(kind) if not isinstance(kind, ReportKind) else kind,
            summary=summary,
            details=details,
            evidence=ev_models,
            suggested_fix=suggested_fix,
        )

        task_context: Optional[TaskContext]
        if task_summary is None and transcript_excerpt is None:
            task_context = None
        else:
            task_context = TaskContext(
                task_summary=task_summary,
                transcript_excerpt=transcript_excerpt,
            )

        return cls(
            doc_url=doc_url,
            agent=agent,
            report=body,
            task_context=task_context,
            idempotency_key=idempotency_key,
            submitted_at=submitted_at,
            locale=locale,
            client_capabilities=client_capabilities,
        )
