"""Domain primitives for witty service."""

from witty_service.domain.enums import AgentStatus, can_transition
from witty_service.domain.errors import DomainError
from witty_service.domain.models import ErrorPayload

__all__ = [
    "AgentStatus",
    "DomainError",
    "ErrorPayload",
    "can_transition",
]
