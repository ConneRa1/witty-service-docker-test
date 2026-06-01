from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SessionEventCreate(BaseModel):
    type: str
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SessionEvent(BaseModel):
    id: str
    session_id: str
    type: str
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime

    @classmethod
    def create(
        cls,
        *,
        session_id: str,
        type: str,
        source: str,
        payload: dict[str, Any] | None = None,
    ) -> "SessionEvent":
        return cls(
            id=str(uuid4()),
            session_id=session_id,
            type=type,
            source=source,
            payload=payload or {},
            timestamp=datetime.now(UTC),
        )


class EventPagination(BaseModel):
    offset: int
    limit: int
    total: int


class SessionEventPage(BaseModel):
    items: list[SessionEvent]
    pagination: EventPagination
