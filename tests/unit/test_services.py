from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from witty_service.api import services as services_module
from witty_service.api.services import ServiceContainer
from witty_service.domain.errors import DomainError


class BackendStub:
    pass


def test_service_container_initializes_session_manager() -> None:
    repository = MagicMock()
    container = ServiceContainer(repository=repository, workspace_store=MagicMock())

    assert container.session_manager._repository is repository


def test_get_sandbox_backend_reuses_existing_backend() -> None:
    backend = BackendStub()
    container = ServiceContainer(
        repository=MagicMock(),
        workspace_store=MagicMock(),
        sandbox_backends={"docker": backend},
    )

    assert container.get_sandbox_backend("Docker") is backend


def test_get_sandbox_backend_creates_missing_backend(monkeypatch) -> None:
    backend = BackendStub()
    monkeypatch.setattr(
        services_module,
        "create_sandbox_backend",
        lambda sandbox_type: backend,
    )
    container = ServiceContainer(repository=MagicMock(), workspace_store=MagicMock())

    assert container.get_sandbox_backend("local_process") is backend
    assert container.sandbox_backends["local_process"] is backend


def test_get_agent_manager_for_agent_requires_existing_agent() -> None:
    repository = MagicMock()
    repository.get_agent.return_value = None
    container = ServiceContainer(repository=repository, workspace_store=MagicMock())

    with pytest.raises(DomainError) as exc_info:
        container.get_agent_manager_for_agent("missing")

    assert exc_info.value.code == services_module.AGENT_NOT_FOUND


def test_get_agent_manager_for_agent_uses_agent_sandbox(monkeypatch) -> None:
    backend = BackendStub()
    repository = MagicMock()
    repository.get_agent.return_value = SimpleNamespace(sandbox_type="docker")
    monkeypatch.setattr(
        services_module,
        "create_sandbox_backend",
        lambda sandbox_type: backend,
    )
    container = ServiceContainer(repository=repository, workspace_store=MagicMock())

    manager = container.get_agent_manager_for_agent("agent-1")

    assert manager._repository is repository
    assert manager._sandbox_backend is backend


def test_ensure_dir_exists_creates_sqlite_parent(tmp_path) -> None:
    db_path = tmp_path / "nested" / "witty.db"

    services_module._ensure_dir_exists(f"sqlite:///{db_path}")
    services_module._ensure_dir_exists("postgresql://example")

    assert db_path.parent.exists()
