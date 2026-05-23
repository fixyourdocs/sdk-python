"""Asynchronous ``AsyncClient`` behaviour against a mocked HTTP transport."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from fixyourdocs import (
    AsyncClient,
    AuthError,
    OptedOutError,
    PolicyRejectedError,
    RateLimitedError,
    Report,
    ServerError,
    ValidationError,
)

API_URL = "https://hub.example.test"
REPORTS_URL = f"{API_URL}/v1/reports"
FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict[str, Any]:
    data = json.loads((FIXTURES / name).read_text())
    data.pop("$comment", None)
    return data


@pytest.fixture
def golden_report() -> Report:
    return Report.model_validate(_load("golden-path.json"))


def _ack_body() -> dict[str, Any]:
    return {
        "id": "rep_01HZA4F8PD9YQF1XGM3KQ8E5VR",
        "received_at": "2026-06-06T12:34:56Z",
        "protocol_version": "0",
        "server_capabilities": [],
    }


@respx.mock
async def test_send_201_returns_new(golden_report: Report) -> None:
    respx.post(REPORTS_URL).mock(return_value=httpx.Response(201, json=_ack_body()))
    async with AsyncClient(API_URL) as client:
        result = await client.send(golden_report)
    assert result.is_duplicate is False
    assert result.id == "rep_01HZA4F8PD9YQF1XGM3KQ8E5VR"


@respx.mock
async def test_send_200_returns_duplicate(golden_report: Report) -> None:
    respx.post(REPORTS_URL).mock(return_value=httpx.Response(200, json=_ack_body()))
    async with AsyncClient(API_URL) as client:
        result = await client.send(golden_report)
    assert result.is_duplicate is True


@respx.mock
async def test_request_body_matches_fixture(golden_report: Report) -> None:
    route = respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(201, json=_ack_body())
    )
    async with AsyncClient(API_URL) as client:
        await client.send(golden_report)

    sent = json.loads(route.calls.last.request.content)
    assert sent == _load("golden-path.json")


@respx.mock
async def test_headers_with_token_and_idempotency(golden_report: Report) -> None:
    route = respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(201, json=_ack_body())
    )
    async with AsyncClient(API_URL, token="opaque-token") as client:
        await client.send(golden_report, idempotency_key="key-123")
    headers = route.calls.last.request.headers
    assert headers["Authorization"] == "Bearer opaque-token"
    assert headers["Idempotency-Key"] == "key-123"
    assert headers["X-Docs-Feedback-Protocol-Version"] == "0"
    assert headers["User-Agent"] == "fixyourdocs-python/0.1.0"


@respx.mock
async def test_default_headers_no_token(golden_report: Report) -> None:
    route = respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(201, json=_ack_body())
    )
    async with AsyncClient(API_URL) as client:
        await client.send(golden_report)
    headers = route.calls.last.request.headers
    assert "Authorization" not in headers
    assert "Idempotency-Key" not in headers


@respx.mock
async def test_400_raises_validation_error(golden_report: Report) -> None:
    respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "error": "validation_error",
                "details": [{"path": "report.kind", "message": "unknown"}],
            },
        )
    )
    async with AsyncClient(API_URL) as client:
        with pytest.raises(ValidationError) as exc_info:
            await client.send(golden_report)
    assert exc_info.value.details == [{"path": "report.kind", "message": "unknown"}]


@respx.mock
async def test_401_raises_auth_error(golden_report: Report) -> None:
    respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(401, json={"error": "auth_required"})
    )
    async with AsyncClient(API_URL) as client:
        with pytest.raises(AuthError):
            await client.send(golden_report)


@respx.mock
async def test_410_raises_opted_out(golden_report: Report) -> None:
    respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(
            410, json={"error": "opted_out", "since": "2026-06-01T00:00:00Z"}
        )
    )
    async with AsyncClient(API_URL) as client:
        with pytest.raises(OptedOutError) as exc_info:
            await client.send(golden_report)
    assert exc_info.value.since == "2026-06-01T00:00:00Z"


@respx.mock
async def test_422_raises_policy_rejected(golden_report: Report) -> None:
    respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(
            422, json={"error": "policy_rejected", "reason": "unknown_agent"}
        )
    )
    async with AsyncClient(API_URL) as client:
        with pytest.raises(PolicyRejectedError) as exc_info:
            await client.send(golden_report)
    assert exc_info.value.reason == "unknown_agent"


@respx.mock
async def test_429_raises_rate_limited(golden_report: Report) -> None:
    respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(
            429,
            json={"error": "rate_limited"},
            headers={"Retry-After": "42"},
        )
    )
    async with AsyncClient(API_URL) as client:
        with pytest.raises(RateLimitedError) as exc_info:
            await client.send(golden_report)
    assert exc_info.value.retry_after == 42


@respx.mock
async def test_503_retried_once_then_raises(golden_report: Report) -> None:
    route = respx.post(REPORTS_URL).mock(
        return_value=httpx.Response(503, json={"error": "unavailable"})
    )
    async with AsyncClient(API_URL) as client:
        with pytest.raises(ServerError):
            await client.send(golden_report)
    assert route.call_count == 2
