from collections.abc import Callable, Sequence
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


class OpenClawLifecycleService:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner: CommandRunner = runner or self._default_runner

    def probe_running(self) -> bool:
        result = self._invoke_gateway_command("status")
        if result.returncode == 0:
            return True
        return self._result_indicates_running(result)

    def stop(self) -> None:
        self._run_or_raise(action="stop")

    def start(self) -> None:
        self._run_or_raise(action="start")

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
        try:
            return self._runner(command)
        except Exception as exc:  # pragma: no cover - defensive guard
            raise self._command_error(
                action=action,
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
