from witty_agent_server.runtimes.runtime_base import RuntimeBase


class RuntimeRegistry:
    def __init__(self) -> None:
        self._runtimes: dict[str, RuntimeBase] = {}

    def register(self, runtime: RuntimeBase) -> None:
        self._runtimes[runtime.runtime_type] = runtime

    def get(self, runtime_type: str) -> RuntimeBase | None:
        return self._runtimes.get(runtime_type)
