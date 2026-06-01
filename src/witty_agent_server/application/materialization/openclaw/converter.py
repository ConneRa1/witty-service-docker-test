"""Compatibility shim for OpenClaw converter module.

Use the shared implementation in `application.materialization.converter` as the
single source of truth while keeping historical import paths stable.
"""

from __future__ import annotations

from witty_agent_server.application.materialization import converter as _base


def __getattr__(name: str):
    return getattr(_base, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_base)))
