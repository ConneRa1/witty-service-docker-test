from collections.abc import Iterator

from witty_agent_server.runtimes.runtime_base import (
    RuntimeBase,
    RuntimeChunk,
    RuntimeResult,
    RuntimeTurnEvent,
    RuntimeType,
)


class OpenCodeRuntime(RuntimeBase):
    runtime_type: RuntimeType = "opencode"

    def create_session(self, *, session_key: str) -> None:
        del session_key
        raise NotImplementedError("opencode runtime is not implemented yet")

    def delete_session(self, *, session_key: str) -> None:
        del session_key
        raise NotImplementedError("opencode runtime is not implemented yet")

    def abort_session(self, *, session_key: str) -> None:
        del session_key
        raise NotImplementedError("opencode runtime is not implemented yet")

    def run_turn(
        self,
        *,
        session_key: str,
        message: str,
    ) -> Iterator[RuntimeTurnEvent]:
        del session_key, message
        raise NotImplementedError("opencode runtime is not implemented yet")

    def send_message(self, session_id: str, message: str) -> RuntimeResult:
        raise NotImplementedError("opencode runtime is not implemented yet")

    def stream_message(self, session_id: str, message: str) -> Iterator[RuntimeChunk]:
        raise NotImplementedError("opencode runtime is not implemented yet")
