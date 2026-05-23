"""Sync and async HTTP clients for the Docs Feedback Protocol v0."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Optional, Union

import httpx

from fixyourdocs._http import (
    REPORTS_PATH,
    _build_headers,
    is_retryable_status,
    parse_response,
)
from fixyourdocs._results import SendResult
from fixyourdocs.models import Report


def _serialize(report: Report) -> dict[str, Any]:
    """Pydantic-dump a report into the wire-format JSON object."""
    return report.model_dump(mode="json", exclude_none=True, by_alias=True)


def _reports_url(api_url: str) -> str:
    return f"{api_url.rstrip('/')}{REPORTS_PATH}"


class Client:
    """Synchronous client for ``POST /v1/reports``."""

    def __init__(
        self,
        api_url: str,
        *,
        token: Optional[str] = None,
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._api_url = api_url
        self._token = token
        self._timeout = timeout
        self._http = httpx.Client(timeout=timeout, transport=transport)

    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def send(
        self,
        report: Report,
        *,
        idempotency_key: Optional[str] = None,
    ) -> SendResult:
        """Submit ``report``. Returns :class:`SendResult` on 200/201; raises on errors."""
        url = _reports_url(self._api_url)
        body = _serialize(report)
        headers = _build_headers(self._token, idempotency_key)

        response = self._http.post(url, json=body, headers=headers)
        if is_retryable_status(response.status_code):
            response = self._http.post(url, json=body, headers=headers)
        return parse_response(response)


class AsyncClient:
    """Asynchronous client for ``POST /v1/reports``."""

    def __init__(
        self,
        api_url: str,
        *,
        token: Optional[str] = None,
        timeout: float = 10.0,
        transport: Optional[Union[httpx.AsyncBaseTransport, httpx.BaseTransport]] = None,
    ) -> None:
        self._api_url = api_url
        self._token = token
        self._timeout = timeout
        # ``httpx.MockTransport`` satisfies both sync and async transport
        # protocols, which makes it convenient for tests; we just accept
        # either here and pass it through.
        self._http = httpx.AsyncClient(
            timeout=timeout,
            transport=transport,  # type: ignore[arg-type]
        )

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def send(
        self,
        report: Report,
        *,
        idempotency_key: Optional[str] = None,
    ) -> SendResult:
        """Submit ``report``. Returns :class:`SendResult` on 200/201; raises on errors."""
        url = _reports_url(self._api_url)
        body = _serialize(report)
        headers = _build_headers(self._token, idempotency_key)

        response = await self._http.post(url, json=body, headers=headers)
        if is_retryable_status(response.status_code):
            response = await self._http.post(url, json=body, headers=headers)
        return parse_response(response)
