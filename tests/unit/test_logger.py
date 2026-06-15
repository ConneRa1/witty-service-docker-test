from __future__ import annotations

import logging
from types import SimpleNamespace

from witty_service import logger as logger_module


def _settings(log_file=None):
    return SimpleNamespace(
        logging=SimpleNamespace(
            level="DEBUG",
            file=log_file,
            max_bytes=1024,
            backup_count=2,
        )
    )


def test_configure_logging_replaces_handlers_and_configures_console(monkeypatch) -> None:
    root = logging.getLogger()
    old_handler = logging.NullHandler()
    root.addHandler(old_handler)
    monkeypatch.setattr(logger_module, "get_settings", lambda: _settings())

    logger_module.configure_logging()

    assert old_handler not in root.handlers
    assert len(root.handlers) == 1
    assert root.level == logging.DEBUG
    assert logging.getLogger("uvicorn").level == logging.WARNING
    assert logging.getLogger("httpx").level == logging.WARNING


def test_configure_logging_adds_rotating_file_handler(tmp_path, monkeypatch) -> None:
    log_file = tmp_path / "logs" / "witty.log"
    monkeypatch.setattr(logger_module, "get_settings", lambda: _settings(log_file))

    logger_module.configure_logging()

    root = logging.getLogger()
    assert log_file.parent.exists()
    assert len(root.handlers) == 2


def test_get_logger_returns_plain_logger_without_context() -> None:
    result = logger_module.get_logger("plain")

    assert isinstance(result, logging.Logger)


def test_logger_adapter_prepends_context() -> None:
    adapter = logger_module.get_logger(
        "context",
        agent_id="agent-1",
        session_id="session-1",
        request_id="request-1",
    )

    message, kwargs = adapter.process("hello", {})

    assert message == (
        "[agent_id=agent-1, session_id=session-1, request_id=request-1] hello"
    )
    assert kwargs == {}
