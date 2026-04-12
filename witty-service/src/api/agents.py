from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from src.api.auth import require_bearer_auth
from src.api.schemas import (
    AgentResponse,
    CreateAgentRequest,
    MessageEventsResponse,
    SendMessageRequest,
    SessionResponse,
)
from src.api.services import ServiceContainer
from src.application.agent_manager import AGENT_NOT_FOUND, AgentCreateRequest
from src.domain.errors import DomainError
from src.persistence.repositories import AgentRecord

router = APIRouter(prefix="/api/v1/agents", tags=["agents"], dependencies=[Depends(require_bearer_auth)])


def get_services(request: Request) -> ServiceContainer:
    return request.app.state.services


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: CreateAgentRequest,
    services: ServiceContainer = Depends(get_services),
) -> AgentResponse:
    manager = services.get_agent_manager_for_sandbox(payload.sandbox_type)
    result = manager.create_agent(
        AgentCreateRequest(
            name=payload.name,
            sandbox_type=payload.sandbox_type,
            adapter_type=payload.adapter_type,
            idle_timeout_seconds=payload.idle_timeout_seconds,
            sandbox_id=payload.sandbox_id,
            has_scheduled_tasks=payload.has_scheduled_tasks,
        )
    )
    return _to_agent_response(result.agent, default_session_id=result.default_session.id)


@router.get("", response_model=list[AgentResponse])
def list_agents(services: ServiceContainer = Depends(get_services)) -> list[AgentResponse]:
    agents = services.repository.list_agents()
    return [
        _to_agent_response(
            agent,
            default_session_id=(
                sessions[0].id if (sessions := services.session_manager.list_sessions(agent.id)) else None
            ),
        )
        for agent in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, services: ServiceContainer = Depends(get_services)) -> AgentResponse:
    agent = services.repository.get_agent(agent_id)
    if agent is None:
        raise DomainError(
            code=AGENT_NOT_FOUND,
            message="Agent was not found.",
            details={"agent_id": agent_id},
        )
    sessions = services.session_manager.list_sessions(agent_id)
    default_session_id = sessions[0].id if sessions else None
    return _to_agent_response(agent, default_session_id=default_session_id)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, services: ServiceContainer = Depends(get_services)) -> Response:
    manager = services.get_agent_manager_for_agent(agent_id)
    manager.delete_agent(agent_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{agent_id}/pause", response_model=AgentResponse)
def pause_agent(agent_id: str, services: ServiceContainer = Depends(get_services)) -> AgentResponse:
    manager = services.get_agent_manager_for_agent(agent_id)
    agent = manager.pause_agent(agent_id)
    sessions = services.session_manager.list_sessions(agent_id)
    default_session_id = sessions[0].id if sessions else None
    return _to_agent_response(agent, default_session_id=default_session_id)


@router.post("/{agent_id}/resume", response_model=AgentResponse)
def resume_agent(agent_id: str, services: ServiceContainer = Depends(get_services)) -> AgentResponse:
    manager = services.get_agent_manager_for_agent(agent_id)
    agent = manager.resume_agent(agent_id)
    sessions = services.session_manager.list_sessions(agent_id)
    default_session_id = sessions[0].id if sessions else None
    return _to_agent_response(agent, default_session_id=default_session_id)


@router.get("/{agent_id}/sessions", response_model=list[SessionResponse])
def list_sessions(agent_id: str, services: ServiceContainer = Depends(get_services)) -> list[SessionResponse]:
    sessions = services.session_manager.list_sessions(agent_id)
    return [SessionResponse.model_validate(session) for session in sessions]


@router.post(
    "/{agent_id}/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(agent_id: str, services: ServiceContainer = Depends(get_services)) -> SessionResponse:
    session = services.session_manager.create_session(agent_id)
    return SessionResponse.model_validate(session)


@router.get("/{agent_id}/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    agent_id: str,
    session_id: str,
    services: ServiceContainer = Depends(get_services),
) -> SessionResponse:
    session = services.session_manager.get_session(agent_id, session_id)
    return SessionResponse.model_validate(session)


@router.delete("/{agent_id}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    agent_id: str,
    session_id: str,
    services: ServiceContainer = Depends(get_services),
) -> Response:
    services.session_manager.delete_session(agent_id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{agent_id}/sessions/{session_id}/messages",
    response_model=MessageEventsResponse,
)
def send_message(
    agent_id: str,
    session_id: str,
    payload: SendMessageRequest,
    services: ServiceContainer = Depends(get_services),
) -> MessageEventsResponse:
    manager = services.get_agent_manager_for_agent(agent_id)
    events = manager.send_message(agent_id=agent_id, session_id=session_id, content=payload.content)
    return MessageEventsResponse(events=events)


def _to_agent_response(agent: AgentRecord, default_session_id: str | None) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        sandbox_type=agent.sandbox_type,
        adapter_type=agent.adapter_type,
        status=agent.status.value,
        sandbox_id=agent.sandbox_id,
        workspace_path=agent.workspace_path,
        idle_timeout_seconds=agent.idle_timeout_seconds,
        has_scheduled_tasks=agent.has_scheduled_tasks,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        default_session_id=default_session_id,
    )
