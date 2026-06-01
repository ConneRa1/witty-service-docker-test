"""Compatibility shim for OpenClaw IO helpers."""

from __future__ import annotations

from witty_agent_server.application.materialization.core import io_utils as _base


def __getattr__(name: str):
    return getattr(_base, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_base)))
