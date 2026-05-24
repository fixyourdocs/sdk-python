"""Result type returned by ``Client.send`` / ``AsyncClient.send``."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SendResult(BaseModel):
    """Server acknowledgement parsed from a ``200``/``201`` response.

    ``is_duplicate`` is derived from the HTTP status code: ``201`` means
    the server accepted a new submission, ``200`` means the idempotency
    key matched an existing one.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    received_at: datetime
    protocol_version: str
    server_capabilities: list[str] = Field(default_factory=list)
    is_duplicate: bool = False
    status_code: Optional[int] = None
