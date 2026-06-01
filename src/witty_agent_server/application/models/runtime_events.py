from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from witty_agent_server.runtimes.runtime_base import RuntimeType


class RuntimeEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    runtime_type: RuntimeType
    payload: dict[str, Any] = Field(default_factory=dict)
    ts_ms: int = Field(
        default_factory=lambda: int(datetime.now(UTC).timestamp() * 1000)
    )


class OutboundSessionEvent(BaseModel):
    type: str
    agent_id: str
    session_id: str
    runtime_type: RuntimeType
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    ts_ms: int = Field(
        default_factory=lambda: int(datetime.now(UTC).timestamp() * 1000)
    )
    payload: dict[str, Any] = Field(default_factory=dict)


def build_outbound_event(
    *,
    agent_id: str,
    session_id: str,
    runtime_type: RuntimeType,
    type: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = OutboundSessionEvent(
        type=type,
        agent_id=agent_id,
        session_id=session_id,
        runtime_type=runtime_type,
        payload=payload or {},
    )
    return event.model_dump(mode="json")
