"""通用事件分发器：支持全量、agent 级、session 级订阅。"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _Subscription:
    agent_id: str | None
    session_id: str | None


class EventEmitter:
    """基于 asyncio.Queue 的事件总线。"""

    def __init__(self) -> None:
        self._client_queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._subscriptions: dict[str, _Subscription] = {}

    async def subscribe(
        self,
        client_id: str,
        *,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> asyncio.Queue[dict[str, Any]]:
        """
        注册订阅。

        语义：
        - `agent_id=None, session_id=None`：订阅全部事件
        - `agent_id='a', session_id=None`：订阅该 agent 全部事件
        - `agent_id='a', session_id='s'`：订阅该 agent 下单 session
        - `agent_id=None, session_id='s'`：非法，避免歧义
        """
        if agent_id is None and session_id is not None:
            raise ValueError("session subscription requires agent_id")

        if client_id not in self._client_queues:
            self._client_queues[client_id] = asyncio.Queue()
        self._subscriptions[client_id] = _Subscription(
            agent_id=agent_id,
            session_id=session_id,
        )
        return self._client_queues[client_id]

    async def emit(self, event: dict[str, Any]) -> None:
        """向匹配订阅范围的客户端推送事件。"""
        event_agent_id = event.get("agent_id")
        event_session_id = event.get("session_id")
        if not isinstance(event_agent_id, str) or not event_agent_id:
            raise ValueError("event missing agent_id")
        if not isinstance(event_session_id, str) or not event_session_id:
            raise ValueError("event missing session_id")

        for client_id, queue in self._client_queues.items():
            subscription = self._subscriptions.get(client_id)
            if subscription is None:
                continue
            if self._matches(
                subscription=subscription,
                agent_id=event_agent_id,
                session_id=event_session_id,
            ):
                await queue.put(event)

    async def unsubscribe(self, client_id: str) -> None:
        self._client_queues.pop(client_id, None)
        self._subscriptions.pop(client_id, None)

    @property
    def subscriber_count(self) -> int:
        return len(self._client_queues)

    def _matches(
        self,
        *,
        subscription: _Subscription,
        agent_id: str,
        session_id: str,
    ) -> bool:
        if subscription.agent_id is None:
            return True
        if subscription.agent_id != agent_id:
            return False
        if subscription.session_id is None:
            return True
        return subscription.session_id == session_id
