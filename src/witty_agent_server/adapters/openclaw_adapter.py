from witty_agent_server.infra.ws.openclaw_gateway_client import (
    DEFAULT_GATEWAY_WS_URL,
    OpenClawGatewayClient,
)
from witty_agent_server.runtimes.openclaw_gateway_runtime import OpenClawGatewayRuntime


class OpenClawAdapter:
    def __init__(
        self,
        *,
        client: OpenClawGatewayClient | None = None,
        runtime: OpenClawGatewayRuntime | None = None,
    ) -> None:
        self._client = client or OpenClawGatewayClient()
        self._runtime = runtime or OpenClawGatewayRuntime(client=self._client)

    @property
    def runtime(self) -> OpenClawGatewayRuntime:
        return self._runtime

    def probe(self) -> tuple[bool, str | None]:
        return True, None


def create_openclaw_runtime(
    *,
    ws_url: str = DEFAULT_GATEWAY_WS_URL,
    gateway_token: str | None = None,
) -> OpenClawGatewayRuntime:
    return OpenClawGatewayRuntime(
        client=OpenClawGatewayClient(
            url=ws_url,
            token=gateway_token,
        )
    )


def create_openclaw_adapter(
    *,
    ws_url: str = DEFAULT_GATEWAY_WS_URL,
    gateway_token: str | None = None,
) -> OpenClawAdapter:
    client = OpenClawGatewayClient(
        url=ws_url,
        token=gateway_token,
    )
    return OpenClawAdapter(
        client=client,
        runtime=OpenClawGatewayRuntime(client=client),
    )
