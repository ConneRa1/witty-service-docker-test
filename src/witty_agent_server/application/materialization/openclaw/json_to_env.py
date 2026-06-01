"""Compatibility shim for OpenClaw JSON materialization entrypoints."""

from __future__ import annotations

from witty_agent_server.application.materialization import json_to_env as _base


def __getattr__(name: str):
    return getattr(_base, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_base)))
