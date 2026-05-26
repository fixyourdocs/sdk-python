"""Reference Python SDK for the Docs Feedback Protocol v0.

See <https://github.com/fixyourdocs/protocol> for the wire-format spec.
"""

from __future__ import annotations

__version__ = "0.2.0"

from fixyourdocs._results import SendResult
from fixyourdocs.client import AsyncClient, Client
from fixyourdocs.errors import (
    AuthError,
    FixYourDocsError,
    NotFoundError,
    OptedOutError,
    PayloadTooLargeError,
    PolicyRejectedError,
    RateLimitedError,
    ServerError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from fixyourdocs.models import (
    AgentInfo,
    Evidence,
    EvidenceKind,
    Report,
    ReportBody,
    ReportKind,
    TaskContext,
)

__all__ = [
    "__version__",
    "AgentInfo",
    "AsyncClient",
    "AuthError",
    "Client",
    "Evidence",
    "EvidenceKind",
    "FixYourDocsError",
    "NotFoundError",
    "OptedOutError",
    "PayloadTooLargeError",
    "PolicyRejectedError",
    "RateLimitedError",
    "Report",
    "ReportBody",
    "ReportKind",
    "SendResult",
    "ServerError",
    "TaskContext",
    "UnsupportedMediaTypeError",
    "ValidationError",
]
