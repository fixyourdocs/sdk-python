"""Typed exceptions raised by the SDK on non-2xx HTTP responses.

These mirror the error table in §7.3 of the protocol spec. Each
exception captures whatever extra context the wire format carries for
its status code (e.g. ``retry_after`` for 429, ``since`` for 410), so
callers can branch on the type and read the structured fields instead
of re-parsing the response body.
"""

from __future__ import annotations

from typing import Any, Optional


class FixYourDocsError(Exception):
    """Base class for every typed SDK error.

    All concrete subclasses carry the raw decoded JSON body (when one
    was returned) on ``.body`` so callers can inspect server-specific
    extensions that v0 does not standardise.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body or {}


class ValidationError(FixYourDocsError):
    """``400`` — body failed schema validation or version header mismatch."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[dict[str, Any]] = None,
        details: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.details: list[dict[str, Any]] = details or []


class AuthError(FixYourDocsError):
    """``401`` — auth required and missing/invalid."""


class NotFoundError(FixYourDocsError):
    """``404`` — endpoint does not map to a known receiving organisation."""


class OptedOutError(FixYourDocsError):
    """``410`` — the receiving organisation has opted out."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[dict[str, Any]] = None,
        since: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.since = since


class PayloadTooLargeError(FixYourDocsError):
    """``413`` — body exceeds the server's size limit."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[dict[str, Any]] = None,
        max_bytes: Optional[int] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.max_bytes = max_bytes


class UnsupportedMediaTypeError(FixYourDocsError):
    """``415`` — Content-Type was not JSON."""


class PolicyRejectedError(FixYourDocsError):
    """``422`` — body validated but server rejected on policy grounds."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.reason = reason


class RateLimitedError(FixYourDocsError):
    """``429`` — rate-limited; ``retry_after`` from the ``Retry-After`` header."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, body=body)
        self.retry_after = retry_after


class ServerError(FixYourDocsError):
    """``5xx`` — server-side failure (after the one allowed retry)."""
