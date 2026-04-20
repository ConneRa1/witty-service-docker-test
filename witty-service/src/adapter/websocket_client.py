from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import websockets

from src.adapter.exceptions import (
    AdaptorConnectionError,
    AdaptorConnectionTimeout,
    AdaptorSendFailed,
    AdaptorReceiveError,
)
from src.adapter.websocket_protocol import InboundEvent, OutboundMessage

logger = logging.getLogger(__name__)


class WebSocketClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._connected: bool = False
        self._session_id: str | None = None
        self._url: str | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _build_url(self, session_id: str) -> str:
        return f"{self._base_url}/sessions/{session_id}/ws"

    async def connect(self, session_id: str) -> None:
        url = self._build_url(session_id)
        try:
            # Keep behavior aligned with witty-agent-server/test.py default:
            # disable client ping to avoid spurious disconnects on long-running turns.
            self._ws = await websockets.connect(url, ping_interval=None)
            self._connected = True
            self._session_id = session_id
            self._url = url
            logger.info(
                "WebSocket connected: client_id=%s session_id=%s url=%s",
                id(self),
                session_id,
                url,
            )
        except Exception as exc:
            raise AdaptorConnectionError(
                message="WebSocket connection failed",
                details={"url": url, "error": str(exc)},
            ) from exc

    async def disconnect(self) -> None:
        if self._ws:
            logger.info(
                "WebSocket disconnect requested: client_id=%s session_id=%s url=%s",
                id(self),
                self._session_id,
                self._url,
            )
            await self._ws.close()
            self._ws = None
            self._connected = False

    async def send(self, message: OutboundMessage) -> None:
        if not self._ws or not self._connected:
            raise AdaptorSendFailed(
                message="Cannot send - not connected",
                details={},
            )
        try:
            await self._ws.send(json.dumps(message))
        except Exception as exc:
            raise AdaptorSendFailed(
                message="Failed to send WebSocket message",
                details={"error": str(exc)},
            ) from exc

    async def recv(self) -> AsyncIterator[InboundEvent]:
        if not self._ws or not self._connected:
            raise AdaptorReceiveError(
                message="Cannot recv - not connected",
                details={},
            )
        try:
            async for raw in self._ws:
                try:
                    data = json.loads(raw)
                    event_type = data.get("type", "")

                    # client.error events may not have standard envelope fields
                    if event_type == "client.error":
                        yield InboundEvent(
                            type=event_type,
                            session_id=data.get("session_id", ""),
                            runtime_type=data.get("runtime_type", "unknown"),
                            event_id=data.get("event_id", ""),
                            ts_ms=data.get("ts_ms", 0),
                            payload=data.get("payload", {}),
                        )
                    else:
                        yield InboundEvent(
                            type=data["type"],
                            session_id=data["session_id"],
                            runtime_type=data["runtime_type"],
                            event_id=data["event_id"],
                            ts_ms=data["ts_ms"],
                            payload=data.get("payload", {}),
                        )
                except (json.JSONDecodeError, KeyError) as exc:
                    raise AdaptorReceiveError(
                        message="Failed to parse WebSocket message",
                        details={"error": str(exc), "raw": raw[:200]},
                    ) from exc
        except websockets.ConnectionClosed as exc:
            self._connected = False
            logger.warning(
                "WebSocket connection closed: client_id=%s session_id=%s url=%s code=%s reason=%s",
                id(self),
                self._session_id,
                self._url,
                getattr(exc, "code", None),
                getattr(exc, "reason", None),
            )
            raise AdaptorReceiveError(
                message="WebSocket connection closed before stream completed",
                details={
                    "code": getattr(exc, "code", None),
                    "reason": getattr(exc, "reason", None),
                    "session_id": self._session_id,
                    "url": self._url,
                },
            ) from exc
        except AdaptorReceiveError:
            raise
        except Exception as exc:
            logger.exception(
                "WebSocket recv exception: client_id=%s session_id=%s url=%s",
                id(self),
                self._session_id,
                self._url,
            )
            raise AdaptorReceiveError(
                message="WebSocket receive failed",
                details={"error": str(exc)},
            ) from exc

    async def close(self) -> None:
        await self.disconnect()
