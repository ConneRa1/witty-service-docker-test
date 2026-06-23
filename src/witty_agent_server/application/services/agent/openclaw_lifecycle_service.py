from collections.abc import Callable, Sequence
import json
import logging
import socket
import subprocess
import time
from subprocess import CompletedProcess, Popen, run


logger = logging.getLogger(__name__)


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
    def __init__(
        self,
        runner: CommandRunner | None = None,
        *,
        profile: str | None = None,
        gateway_port: int | None = None,
    ) -> None:
        self._runner: CommandRunner = runner or self._default_runner
        self._profile = profile
        self._gateway_port = gateway_port
        self._gateway_process: Popen[str] | None = None

    def update_config(
        self,
        *,
        profile: str | None,
        gateway_port: int | None,
    ) -> None:
        self._profile = profile
        self._gateway_port = gateway_port

    def _build_base_command(self) -> list[str]:
        cmd = ["openclaw"]
        if self._profile:
            cmd.extend(["--profile", self._profile])
        return cmd

    def probe_running(self) -> bool:
        if not self._profile:
            return False
        result = self._invoke_gateway_command("status")
        if result.returncode != 0:
            return False
        return self._result_indicates_running(result)

    def stop(self) -> None:
        """停止 openclaw gateway 并执行完整卸载"""
        if not self._profile:
            return
        
        # 构建卸载命令
        command = self._build_base_command() + [
            "uninstall",
            "--yes",
            "--non-interactive",
            "--all"
        ]
        
        result = self._run_command(command)
        if result.returncode != 0:
            raise OpenClawLifecycleError(
                action="uninstall",
                command=command,
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                message="openclaw uninstall failed",
            )
        
        self._stop_gateway_process()

    def start(self) -> None:
        raise NotImplementedError(
            "start() method is deprecated. Use onboard() instead."
        )

    def start_gateway(self) -> None:
        if not self._profile or not self._gateway_port:
            raise OpenClawLifecycleError(
                action="gateway run",
                command=[],
                returncode=-1,
                stdout="",
                stderr="profile and gateway_port are required",
                message="profile and gateway_port are required for gateway run",
            )

        self._stop_gateway_process()

        command = self._build_base_command() + [
            "gateway",
            "run",
            "--port",
            str(self._gateway_port),
            "--bind",
            "loopback",
        ]
        logger.info("Starting gateway in background: %s", command)
        self._gateway_process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.time() + 30
        while time.time() < deadline:
            if self._gateway_process.poll() is not None:
                _, stderr = self._gateway_process.communicate()
                raise OpenClawLifecycleError(
                    action="gateway run",
                    command=command,
                    returncode=self._gateway_process.returncode or -1,
                    stdout="",
                    stderr=stderr or "",
                    message="gateway process exited prematurely",
                )
            if self._port_is_listening(self._gateway_port):
                logger.info("Gateway started successfully on port %s", self._gateway_port)
                return
            time.sleep(1)

        raise OpenClawLifecycleError(
            action="gateway run",
            command=command,
            returncode=-1,
            stdout="",
            stderr="",
            message="gateway start timed out after 30 seconds",
        )

    def _stop_gateway_process(self) -> None:
        if self._gateway_process is None:
            return
        try:
            self._gateway_process.terminate()
            self._gateway_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            logger.exception("Failed to terminate gateway process")

        if self._gateway_process.poll() is None:
            try:
                self._gateway_process.kill()
                self._gateway_process.wait()
            except Exception:
                logger.exception("Failed to kill gateway process, giving up")

        self._gateway_process = None

    @staticmethod
    def _port_is_listening(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except (OSError, ConnectionRefusedError):
            return False

    def mcp_set(self, name: str, config: dict[str, object]) -> None:
        if not self._profile:
            raise OpenClawLifecycleError(
                action="mcp set",
                command=[],
                returncode=-1,
                stdout="",
                stderr="profile is required",
                message="profile is required for mcp set",
            )

        config_str = json.dumps(config, ensure_ascii=False)
        command = self._build_base_command() + ["mcp", "set", name, config_str]
        result = self._run_command(command)
        if result.returncode != 0:
            raise OpenClawMcpSetError(
                command=command,
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )

    def mcp_unset(self, name: str) -> None:
        if not self._profile:
            raise OpenClawLifecycleError(
                action="mcp unset",
                command=[],
                returncode=-1,
                stdout="",
                stderr="profile is required",
                message="profile is required for mcp unset",
            )

        command = self._build_base_command() + ["mcp", "unset", name]
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
        skip_health: bool = False,
    ) -> None:
        if not self._profile:
            raise OpenClawLifecycleError(
                action="onboard",
                command=[],
                returncode=-1,
                stdout="",
                stderr="profile is required",
                message="profile is required for onboard",
            )

        command = self._build_base_command() + [
            "onboard",
            "--non-interactive",
            "--accept-risk",
            "--auth-choice",
            auth_choice,
            f"--{auth_choice}",
            api_key,
        ]
        if self._gateway_port:
            command.extend(["--gateway-port", str(self._gateway_port)])
        if install_daemon:
            command.append("--install-daemon")
        if skip_channels:
            command.append("--skip-channels")
        if skip_search:
            command.append("--skip-search")
        if skip_hooks:
            command.append("--skip-hooks")
        if skip_health:
            command.append("--skip-health")

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
        command = self._build_base_command() + ["gateway", action]
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
