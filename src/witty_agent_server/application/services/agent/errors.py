from __future__ import annotations

from typing import Any


class AgentServiceError(Exception):
    """Agent 服务层统一错误基类。"""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class InvalidAgentTransitionError(AgentServiceError):
    """非法的 agent 状态迁移。"""

    def __init__(self, *, current: str, target: str) -> None:
        super().__init__(
            code="INVALID_AGENT_TRANSITION",
            message="invalid agent state transition",
            status_code=400,
            details={"current": current, "target": target},
        )


class AgentConfigUpdateForbiddenError(AgentServiceError):
    """运行态禁止修改 agent config。"""

    def __init__(self) -> None:
        super().__init__(
            code="AGENT_CONFIG_UPDATE_FORBIDDEN",
            message="cannot update agent config while running",
            status_code=409,
        )


class InvalidAgentConfigError(AgentServiceError):
    """agent config 不合法。"""

    def __init__(self) -> None:
        super().__init__(
            code="INVALID_AGENT_CONFIG",
            message="invalid agent config",
            status_code=400,
        )


class AgentIdNotConfiguredError(AgentServiceError):
    """Gateway agents.list 中未配置目标 agent。"""

    def __init__(self, *, agent_id: str, configured_ids: list[str]) -> None:
        super().__init__(
            code="AGENT_ID_NOT_CONFIGURED",
            message="agent id is not configured in openclaw agents.list",
            status_code=400,
            details={"agent_id": agent_id, "configured_ids": configured_ids},
        )


class AgentDefaultNotConfiguredError(AgentServiceError):
    """Gateway agents.list 未配置默认 agent。"""

    def __init__(self) -> None:
        super().__init__(
            code="AGENT_DEFAULT_NOT_CONFIGURED",
            message="default agent is not configured in openclaw agents.list",
            status_code=500,
        )


class AgentContextMismatchError(AgentServiceError):
    """请求的 agent id 与当前实例绑定的 agent 不一致。"""

    def __init__(self, *, requested_agent_id: str, current_agent_id: str | None) -> None:
        super().__init__(
            code="AGENT_CONTEXT_MISMATCH",
            message="requested agent id does not match current agent context",
            status_code=409,
            details={
                "requested_agent_id": requested_agent_id,
                "current_agent_id": current_agent_id,
            },
        )


class OpenClawAgentNotFoundError(AgentServiceError):
    """Gateway 未加载已配置的 agent。"""

    def __init__(self, *, agent_id: str) -> None:
        super().__init__(
            code="OPENCLAW_AGENT_NOT_FOUND",
            message="openclaw gateway did not load configured agent",
            status_code=500,
            details={"agent_id": agent_id},
        )
