from collections.abc import Iterator
from abc import ABC, abstractmethod
from typing import Any, Literal, NotRequired, TypedDict


RuntimeType = Literal["openclaw", "opencode"]


class RuntimeResult(TypedDict):
    text: str


class RuntimeChunk(TypedDict):
    type: str
    delta: NotRequired[str]


class RuntimeTurnEvent(TypedDict):
    type: str
    payload: dict[str, Any]


class RuntimeBase(ABC):
    runtime_type: RuntimeType

    @abstractmethod
    def list_sessions(self, *, agent_id: str) -> list[dict[str, Any]]:
        """列出指定 agent 在 runtime 侧可见的会话。"""

    @abstractmethod
    def send_message(self, session_id: str, message: str) -> RuntimeResult:
        """发送一轮消息并返回最终文本结果。"""

    @abstractmethod
    def stream_message(
        self, session_id: str, message: str
    ) -> Iterator[RuntimeChunk]:
        """流式发送消息并输出统一的分片事件。"""


    @abstractmethod
    def run_turn(
        self,
        *,
        session_key: str,
        message: str,
    ) -> Iterator[RuntimeTurnEvent]:
        """执行单轮对话并输出统一的运行时事件流。"""

    @abstractmethod
    def create_session(self, *, session_key: str) -> None:
        """创建 runtime 侧会话。"""

    @abstractmethod
    def delete_session(self, *, session_key: str) -> None:
        """删除 runtime 侧会话。"""

    @abstractmethod
    def abort_session(self, *, session_key: str) -> None:
        """终止 runtime 侧会话执行。"""


def supports_runtime_turn(runtime: object) -> bool:
    """判断 runtime 是否支持 run_turn 会话事件流能力。"""
    return callable(getattr(runtime, "run_turn", None))


def supports_runtime_lifecycle(runtime: object) -> bool:
    """判断 runtime 是否支持会话生命周期能力（create/delete/abort）。"""
    return (
        callable(getattr(runtime, "create_session", None))
        and callable(getattr(runtime, "delete_session", None))
        and callable(getattr(runtime, "abort_session", None))
    )


def supports_runtime_session_listing(runtime: object) -> bool:
    """判断 runtime 是否支持按 agent 列出会话。"""
    return callable(getattr(runtime, "list_sessions", None))
