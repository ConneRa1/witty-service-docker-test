from __future__ import annotations

import logging
from typing import Any


from witty_agent_server.application.models.agent import Agent, AgentStatus
from witty_agent_server.application.services.agent.base import (
    AgentServiceBase,
    GatewayAgentClientPort,
    OpenClawLifecyclePort,
)
from witty_agent_server.application.services.agent.errors import (
    AgentDefaultNotConfiguredError,
    AgentIdNotConfiguredError,
    AgentServiceError,
    OpenClawAgentNotFoundError,
)
from witty_agent_server.application.services.agent.openclaw_lifecycle_service import (
    OpenClawLifecycleError,
    OpenClawLifecycleService,
)

from witty_agent_server.infra.ws.openclaw_gateway_client import OpenClawGatewayClient
from witty_agent_server.runtimes.runtime_base import RuntimeType


logger = logging.getLogger(__name__)


class OpenClawAgentService(AgentServiceBase):
    """当前项目使用的 openclaw 版本 agent service。"""

    PROVIDER_TO_AUTH_CHOICE: dict[str, str] = {
        "openai": "openai-api-key",
        "anthropic": "anthropic-api-key",
        "google": "google-api-key",
        "xai": "xai-api-key",
        "deepseek": "deepseek-api-key",
        "alibaba": "qwen-api-key",
        "zhipuai": "zai-api-key",
        "minimax": "minimax-api-key",
        "moonshotai": "kimi-code-api-key",
        "custom": "custom-api-key",
    }

    def __init__(
        self,
        agent: Agent | None = None,
        lifecycle_service: OpenClawLifecyclePort | None = None,
        gateway_agent_client: GatewayAgentClientPort | None = None,
        runtime: RuntimeType = "openclaw",
    ) -> None:
        super().__init__(agent=agent, runtime=runtime)
        self._lifecycle_service = lifecycle_service or OpenClawLifecycleService()
        self._gateway_agent_client = gateway_agent_client or OpenClawGatewayClient()

    def start(
        self,
        *,
        agent_id: str | None = None,
        config: dict[str, Any] | None = None,
        reload: bool = True,
    ) -> Agent:
        """启动 openclaw runtime，并绑定到 gateway 中已加载的 agent。
        
        使用 onboard 命令启动，支持根据模型提供商选择不同的认证方式。
        """
        with self._lock:

            is_running = self._probe_openclaw_running()
            logger.info(
                "agent start requested: agent_id=%s runtime=%s reload=%s running=%s",
                agent_id,
                self._runtime,
                reload,
                is_running,
            )

            if is_running and not reload:
                resolved_agent_id, configured_agent = self._resolve_target_agent(
                    requested_agent_id=agent_id
                )
                self._ensure_gateway_agent_loaded(agent_id=resolved_agent_id)
                self._agent.id = resolved_agent_id
                self._agent.status = AgentStatus.RUNNING
                self._last_start_already_running = True
                logger.info(
                    "agent start reused existing runtime: agent_id=%s runtime=%s",
                    resolved_agent_id,
                    self._runtime,
                )
                return self.agent

            if is_running:
                self._stop_openclaw()

            model_provider = config.get("model", {}).get("provider", "") if config else ""
            api_key = config.get("model", {}).get("api_key", "") if config else ""

            self._onboard_openclaw(model_provider=model_provider, api_key=api_key)

            resolved_agent_id, configured_agent = self._resolve_target_agent(
                requested_agent_id=agent_id
            )
            self._ensure_gateway_agent_loaded(agent_id=resolved_agent_id)

            self._agent.id = resolved_agent_id
            self._agent.status = AgentStatus.RUNNING
            logger.info(
                "agent start completed: agent_id=%s runtime=%s configured_agent=%s",
                resolved_agent_id,
                self._runtime,
                configured_agent.get("id"),
            )
            return self.agent

    def _setup_mcp(self, mcp_server_name: str | None, mcp_server_config: dict[str, Any] | None) -> None:
        """设置 MCP 配置（如果在 config 中指定了）。"""
        
        if mcp_server_name and mcp_server_config:
            logger.info("Setting up MCP: name=%s", mcp_server_name)
            try:
                self._lifecycle_service.mcp_set(mcp_server_name, mcp_server_config)
            except OpenClawLifecycleError as exc:
                logger.warning("MCP setup failed, continuing: %s", exc)

    def _unset_mcp(self, mcp_server_name: str | None) -> None:
        """卸载 MCP 配置。"""
        
        if mcp_server_name:
            logger.info("Unsetting MCP: name=%s", mcp_server_name)
            try:
                self._lifecycle_service.mcp_unset(mcp_server_name)
            except OpenClawLifecycleError as exc:
                logger.warning("MCP unset failed, continuing: %s", exc)

    def setup_mcp(
        self,
        *,
        agent_id: str | None = None,
        mcp_server_name: str | None = None,
        mcp_server_config: dict[str, Any] | None = None,
    ) -> None:
        """设置 MCP 配置。"""
        with self._lock:
            self._ensure_agent_context(agent_id=agent_id)
            self._setup_mcp(mcp_server_name, mcp_server_config)

    def unset_mcp(
        self,
        *,
        agent_id: str | None = None,
        mcp_server_name: str | None = None,
    ) -> None:
        """卸载 MCP 配置。"""
        with self._lock:
            self._ensure_agent_context(agent_id=agent_id)
            self._unset_mcp(mcp_server_name)

    def _onboard_openclaw(self, *, model_provider: str, api_key: str) -> None:
        """使用 onboard 命令启动 openclaw runtime。"""
        auth_choice = self.PROVIDER_TO_AUTH_CHOICE.get(model_provider, "deepseek-api-key")
        
        logger.info(
            "Onboarding openclaw: provider=%s auth_choice=%s",
            model_provider,
            auth_choice,
        )
        
        try:
            self._lifecycle_service.onboard(
                auth_choice=auth_choice,
                api_key=api_key,
                install_daemon=True,
                skip_channels=True,
                skip_search=True,
                skip_hooks=True,
            )
        except OpenClawLifecycleError as exc:
            raise AgentServiceError(
                code="OPENCLAW_ONBOARD_FAILED",
                message="openclaw onboard failed",
                status_code=500,
                details=self._lifecycle_error_details(exc),
            ) from exc

    def status(self, *, agent_id: str | None = None) -> Agent:
        with self._lock:
            self._ensure_agent_context(agent_id=agent_id)
            return self.agent

    def stop(self, *, agent_id: str | None = None) -> Agent:
        with self._lock:
            self._ensure_agent_context(agent_id=agent_id)
            self._transition(
                allowed_current=(AgentStatus.RUNNING, AgentStatus.PAUSED),
                target=AgentStatus.STOPPED,
            )
            return self.agent

    def list_agents(self) -> dict[str, Any]:
        """返回 gateway 可见 agent 列表。"""
        return self._gateway_agent_client.list_agents()

    def resolve_default_agent(self) -> str:
        """解析默认 agent id。"""
        resolved_agent_id, _ = self._resolve_target_agent(requested_agent_id=None)
        return resolved_agent_id

    def _probe_openclaw_running(self) -> bool:
        """探测 openclaw gateway/runtime 当前是否已就绪。"""
        try:
            return self._lifecycle_service.probe_running()
        except OpenClawLifecycleError as exc:
            raise AgentServiceError(
                code="OPENCLAW_START_FAILED",
                message="openclaw start failed",
                status_code=500,
                details=self._lifecycle_error_details(exc),
            ) from exc

    def _stop_openclaw(self) -> None:
        """重载前先停止旧 runtime，避免进程和端口残留。"""
        try:
            self._lifecycle_service.stop()
        except OpenClawLifecycleError as exc:
            raise AgentServiceError(
                code="OPENCLAW_STOP_FAILED",
                message="openclaw stop failed",
                status_code=500,
                details=self._lifecycle_error_details(exc),
            ) from exc

    def _resolve_target_agent(
        self,
        *,
        requested_agent_id: str | None,
    ) -> tuple[str, dict[str, Any]]:
        """从 Gateway agents.list 中解析目标 agent。"""
        payload = self._gateway_agent_client.list_agents()
        configured_agents = payload.get("agents")
        if not isinstance(configured_agents, list):
            configured_agents = []
        configured_ids = [
            str(item.get("id"))
            for item in configured_agents
            if isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and item.get("id")
        ]

        resolved_agent_id = requested_agent_id
        if resolved_agent_id is None:
            default_id = payload.get("defaultId")
            if not isinstance(default_id, str) or not default_id:
                for item in configured_agents:
                    if isinstance(item, dict) and item.get("default") is True:
                        raw_id = item.get("id")
                        if isinstance(raw_id, str) and raw_id:
                            default_id = raw_id
                            break
            if not isinstance(default_id, str) or not default_id:
                raise AgentDefaultNotConfiguredError()
            resolved_agent_id = default_id

        for item in configured_agents:
            if isinstance(item, dict) and item.get("id") == resolved_agent_id:
                return resolved_agent_id, item
        

        raise AgentIdNotConfiguredError(
            agent_id=resolved_agent_id,
            configured_ids=configured_ids,
        )

    def _ensure_gateway_agent_loaded(self, *, agent_id: str) -> None:
        """校验 Gateway 已经加载目标 agent。"""
        try:
            gateway_agent = self._gateway_agent_client.get_agent(agent_id=agent_id)
        except Exception as exc:
            logger.exception(
                "gateway agent lookup failed: agent_id=%s runtime=%s",
                agent_id,
                self._runtime,
            )
            raise AgentServiceError(
                code="OPENCLAW_AGENT_INIT_FAILED",
                message="openclaw agent init failed",
                status_code=500,
                details={"agent_id": agent_id, "runtime_type": self._runtime},
            ) from exc
        if gateway_agent is None:
            raise OpenClawAgentNotFoundError(agent_id=agent_id)
        if not self._is_gateway_agent_loaded(gateway_agent):
            logger.warning(
                "gateway agent present but not loaded: agent_id=%s runtime=%s payload_keys=%s",
                agent_id,
                self._runtime,
                sorted(gateway_agent.keys()),
            )
            raise OpenClawAgentNotFoundError(agent_id=agent_id)
        logger.info("gateway agent loaded: agent_id=%s runtime=%s", agent_id, self._runtime)

    def _is_gateway_agent_loaded(self, gateway_agent: dict[str, Any]) -> bool:
        """优先读取 gateway 的加载态字段；缺失时回退为存在即视为已加载。"""
        for key in ("loaded", "ready", "active", "started"):
            value = gateway_agent.get(key)
            if isinstance(value, bool):
                return value
        status = gateway_agent.get("status")
        if isinstance(status, str):
            normalized = status.strip().lower()
            if normalized in {"loaded", "ready", "active", "running", "started"}:
                return True
            if normalized in {"unloaded", "inactive", "stopped", "failed", "error"}:
                return False
        return True

    def _lifecycle_error_details(
        self,
        exc: OpenClawLifecycleError,
    ) -> dict[str, Any]:
        """将 lifecycle 错误标准化为响应 details。"""
        return {
            "action": exc.action,
            "command": list(exc.command),
            "returncode": exc.returncode,
            "stdout": exc.stdout,
            "stderr": exc.stderr,
        }
