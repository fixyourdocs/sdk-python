"""Shared HTTP helpers used by both ``Client`` and ``AsyncClient``."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from fixyourdocs._results import SendResult
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

PROTOCOL_VERSION = "0"
PROTOCOL_VERSION_HEADER = "X-Docs-Feedback-Protocol-Version"
REPORTS_PATH = "/v1/reports"
RETRYABLE_STATUS_CODES = frozenset({502, 503, 504})


def _sdk_user_agent() -> str:
    # Import here to avoid an import cycle (``__init__`` re-exports from
    # ``client.py``, which imports this module).
    from fixyourdocs import __version__

    return f"fixyourdocs-python/{__version__}"


def _build_headers(
    token: Optional[str],
    idempotency_key: Optional[str],
) -> dict[str, str]:
    """Assemble the request headers for ``POST /v1/reports``."""
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        PROTOCOL_VERSION_HEADER: PROTOCOL_VERSION,
        "User-Agent": _sdk_user_agent(),
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    """Decode a response body as JSON, returning ``{}`` on failure."""
    try:
        data = response.json()
    except Exception:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _retry_after_seconds(response: httpx.Response) -> Optional[int]:
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def is_retryable_status(status_code: int) -> bool:
    """Return ``True`` if the SDK should retry once on this status."""
    return status_code in RETRYABLE_STATUS_CODES


def _raise_for_status(response: httpx.Response) -> None:
    """Translate a non-2xx response into the matching typed error."""
    status = response.status_code
    body = _safe_json(response)
    error_message = str(body.get("error") or response.reason_phrase or f"HTTP {status}")

    if status == 400:
        raise ValidationError(
            error_message,
            status_code=status,
            body=body,
            details=list(body.get("details") or []),
        )
    if status == 401:
        raise AuthError(error_message, status_code=status, body=body)
    if status == 404:
        raise NotFoundError(error_message, status_code=status, body=body)
    if status == 410:
        raise OptedOutError(
            error_message,
            status_code=status,
            body=body,
            since=body.get("since"),
        )
    if status == 413:
        raw_max = body.get("max_bytes")
        max_bytes: Optional[int]
        try:
            max_bytes = int(raw_max) if raw_max is not None else None
        except (TypeError, ValueError):
            max_bytes = None
        raise PayloadTooLargeError(
            error_message,
            status_code=status,
            body=body,
            max_bytes=max_bytes,
        )
    if status == 415:
        raise UnsupportedMediaTypeError(error_message, status_code=status, body=body)
    if status == 422:
        raise PolicyRejectedError(
            error_message,
            status_code=status,
            body=body,
            reason=body.get("reason"),
        )
    if status == 429:
        raise RateLimitedError(
            error_message,
            status_code=status,
            body=body,
            retry_after=_retry_after_seconds(response),
        )
    if 500 <= status < 600:
        raise ServerError(error_message, status_code=status, body=body)

    # Any other 4xx the spec doesn't enumerate.
    raise FixYourDocsError(error_message, status_code=status, body=body)


def parse_response(response: httpx.Response) -> SendResult:
    """Map a 2xx response to :class:`SendResult`; raise on non-2xx."""
    if response.status_code in (200, 201):
        body = _safe_json(response)
        return SendResult(
            id=str(body.get("id", "")),
            received_at=body.get("received_at"),  # type: ignore[arg-type]
            protocol_version=str(body.get("protocol_version", PROTOCOL_VERSION)),
            server_capabilities=list(body.get("server_capabilities") or []),
            is_duplicate=(response.status_code == 200),
            status_code=response.status_code,
        )
    _raise_for_status(response)
    # Unreachable, but keeps mypy happy.
    raise FixYourDocsError(  # pragma: no cover
        f"Unexpected status {response.status_code}", status_code=response.status_code
    )
