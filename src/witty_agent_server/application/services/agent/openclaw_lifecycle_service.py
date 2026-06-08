from collections.abc import Callable, Sequence
import json
from subprocess import CompletedProcess, run


CommandRunner = Callable[[list[str]], CompletedProcess[str]]


class OpenClawLifecycleError(Exception):
    def __init__(
        self,
        *,
        action: str,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.action = action
        self.command = tuple(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class OpenClawGatewayStatusError(OpenClawLifecycleError):
    def __init__(
        self,
        *,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(
            action="status",
            command=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            message="openclaw gateway status failed",
        )


class OpenClawGatewayStopError(OpenClawLifecycleError):
    def __init__(
        self,
        *,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(
            action="stop",
            command=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            message="openclaw gateway stop failed",
        )


class OpenClawGatewayStartError(OpenClawLifecycleError):
    def __init__(
        self,
        *,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(
            action="start",
            command=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            message="openclaw gateway start failed",
        )


class OpenClawMcpSetError(OpenClawLifecycleError):
    def __init__(
        self,
        *,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(
            action="mcp set",
            command=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            message="openclaw mcp set failed",
        )


class OpenClawMcpUnsetError(OpenClawLifecycleError):
    def __init__(
        self,
        *,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(
            action="mcp unset",
            command=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            message="openclaw mcp unset failed",
        )


class OpenClawOnboardError(OpenClawLifecycleError):
    def __init__(
        self,
        *,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(
            action="onboard",
            command=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            message="openclaw onboard failed",
        )


class OpenClawLifecycleService:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner: CommandRunner = runner or self._default_runner

    def probe_running(self) -> bool:
        result = self._invoke_gateway_command("status")
        if result.returncode != 0:
            return False
        return self._result_indicates_running(result)

    def stop(self) -> None:
        self._run_or_raise(action="stop")

    def start(self) -> None:
        """已废弃：使用 onboard() 方法替代。"""
        raise NotImplementedError(
            "start() method is deprecated. Use onboard() instead."
        )

    def mcp_set(self, name: str, config: dict[str, object]) -> None:
        """设置 MCP 配置。"""
        config_str = json.dumps(config, ensure_ascii=False)
        command = ["openclaw", "mcp", "set", name, config_str]
        result = self._run_command(command)
        if result.returncode != 0:
            raise OpenClawMcpSetError(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )

    def mcp_unset(self, name: str) -> None:
        """卸载 MCP 配置。"""
        command = ["openclaw", "mcp", "unset", name]
        result = self._run_command(command)
        if result.returncode != 0:
            raise OpenClawMcpUnsetError(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )

    def onboard(
        self,
        *,
        auth_choice: str,
        api_key: str,
        install_daemon: bool = False,
        skip_channels: bool = True,
        skip_search: bool = True,
        skip_hooks: bool = True,
    ) -> None:
        """执行 openclaw onboard 命令来配置和启动 gateway。
        
        根据 temp/model 方案，不同模型提供商对应不同的 --auth-choice 参数：
        
        | 模型提供商 | --auth-choice 参数 |
        | :--- | :--- |
        | openai | openai-api-key |
        | anthropic | anthropic-api-key |
        | google | google-api-key |
        | xai | xai-api-key |
        | deepseek | deepseek-api-key |
        | alibaba | qwen-api-key |
        | zhipuai | zai-api-key |
        | minimax | minimax-api-key |
        | moonshotai | kimi-code-api-key |
        | custom | custom-api-key |
        """
        command = [
            "openclaw",
            "onboard",
            "--non-interactive",
            "--accept-risk",
            "--auth-choice",
            auth_choice,
            f"--{auth_choice}",
            api_key,
        ]
        if install_daemon:
            command.append("--install-daemon")
        if skip_channels:
            command.append("--skip-channels")
        if skip_search:
            command.append("--skip-search")
        if skip_hooks:
            command.append("--skip-hooks")
        
        result = self._run_command(command)
        if result.returncode != 0:
            raise OpenClawOnboardError(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )

    def _run_or_raise(
        self,
        *,
        action: str,
    ) -> None:
        result = self._invoke_gateway_command(action)
        if result.returncode == 0:
            return
        raise self._command_error(
            action=action,
            command=(
                tuple(result.args)
                if isinstance(result.args, Sequence)
                and not isinstance(result.args, str)
                else (str(result.args),)
            ),
            returncode=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    def _invoke_gateway_command(
        self,
        action: str,
    ) -> CompletedProcess[str]:
        command = ["openclaw", "gateway", action]
        return self._run_command(command)

    def _run_command(self, command: list[str]) -> CompletedProcess[str]:
        try:
            return self._runner(command)
        except Exception as exc:  # pragma: no cover - defensive guard
            raise self._command_error(
                action=" ".join(command[:2]),
                command=command,
                returncode=-1,
                stdout="",
                stderr=str(exc),
            ) from exc

    def _command_error(
        self,
        *,
        action: str,
        command: Sequence[str],
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> OpenClawLifecycleError:
        if action == "status":
            return OpenClawGatewayStatusError(
                command=command,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )
        if action == "stop":
            return OpenClawGatewayStopError(
                command=command,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )
        if action == "mcp set":
            return OpenClawMcpSetError(
                command=command,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )
        if action == "mcp unset":
            return OpenClawMcpUnsetError(
                command=command,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )
        if action == "onboard":
            return OpenClawOnboardError(
                command=command,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )
        return OpenClawGatewayStartError(
            command=command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    def _result_indicates_running(self, result: CompletedProcess[str]) -> bool:
        output = self._combined_output(result).lower()
        if "not running" in output or "stopped" in output or "inactive" in output:
            return False
        if "running" in output or "active" in output or "started" in output:
            return True
        return False

    def _combined_output(self, result: CompletedProcess[str]) -> str:
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        return f"{stdout}\n{stderr}".strip()

    @staticmethod
    def _default_runner(command: list[str]) -> CompletedProcess[str]:
        return run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
