from uuid import uuid4

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from witty_agent_server.api.routers.agent_router import create_agent_router
from witty_agent_server.api.routers.session_router import (
    build_default_session_service,
    create_session_router,
)
from witty_agent_server.api.routers.session_ws_router import create_session_ws_router
from witty_agent_server.application.models.errors import ErrorResponse
from witty_agent_server.application.services.agent import AgentService
from witty_agent_server.application.services.session import SessionService
from witty_agent_server.application.services.session_state_sync_service import (
    SessionStateSyncService,
)
from witty_agent_server.application.services.session_ws_orchestrator import (
    SessionWSOrchestrator,
)
from witty_agent_server.application.services.task_pool import TaskPool
from witty_agent_server.infra.ws.openclaw_gateway_client import (
    OpenClawGatewayClient,
)
from witty_agent_server.application.services.agent.openclaw_lifecycle_service import (
    OpenClawLifecycleService,
)
from witty_agent_server.application.services.skill.openclaw_skill_service import (
    OpenClawSkillService,
)
from witty_agent_server.logger.logging_config import configure_logging


base_router = APIRouter()


@base_router.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@base_router.get("/server/capabilities")
def capabilities() -> dict[str, list[str]]:
    return {"supported_runtimes": ["openclaw"]}


def create_app(
    session_service: SessionService | None = None,
    *,
    agent_service: AgentService | None = None,
) -> FastAPI:
    configure_logging()
    shared_gateway_client = OpenClawGatewayClient()
    shared_lifecycle_service = OpenClawLifecycleService()
    resolved_agent_service = agent_service or AgentService(
        lifecycle_service=shared_lifecycle_service,
        gateway_agent_client=shared_gateway_client,
    )
    resolved_session_service = session_service or build_default_session_service(
        gateway_client=shared_gateway_client,
    )
    session_state_sync_service = SessionStateSyncService()
    session_ws_orchestrator = SessionWSOrchestrator(
        session_service=resolved_session_service,
        agent_service=resolved_agent_service,
        state_sync_service=session_state_sync_service,
    )

    task_pool = TaskPool(orchestrator=session_ws_orchestrator)

    app = FastAPI(title="Witty Agent Server")

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        body = ErrorResponse(
            code="REQUEST_VALIDATION_ERROR",
            message="request validation failed",
            request_id=_get_request_id(request),
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=body.model_dump(exclude_none=True))

    app.include_router(base_router)
    app.include_router(
        create_agent_router(
            resolved_agent_service,
            openclaw_skill_service=OpenClawSkillService(
                openclaw_client=shared_gateway_client
            ),
        )
    )
    app.include_router(
        create_session_router(
            resolved_session_service,
            state_sync_service=session_state_sync_service,
            agent_service=resolved_agent_service,
        )
    )
    app.include_router(
        create_session_ws_router(
            task_pool=task_pool,
            state_sync_service=session_state_sync_service,
        )
    )
    return app


def _get_request_id(request: Request) -> str:
    header_value = request.headers.get("x-request-id")
    if isinstance(header_value, str) and header_value:
        return header_value
    return str(uuid4())
