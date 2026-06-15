from __future__ import annotations

import pytest

from witty_service.storage.workspace_store import LocalWorkspaceStore, WorkspaceStore


def test_workspace_store_requires_a_base_path() -> None:
    with pytest.raises(TypeError, match="requires base_dir or base_path"):
        WorkspaceStore()


def test_workspace_store_rejects_conflicting_base_paths(tmp_path) -> None:
    with pytest.raises(ValueError, match="must refer to the same path"):
        WorkspaceStore(base_dir=tmp_path / "a", base_path=tmp_path / "b")


def test_workspace_store_initializes_and_cleans_agent_workspace(tmp_path) -> None:
    store = WorkspaceStore(base_dir=tmp_path)

    workspace = store.init_workspace("agent-1")

    assert workspace == tmp_path / "agent-workspaces" / "agent-1" / "workspace"
    assert (workspace / ".agent").is_dir()
    assert (workspace / "code").is_dir()
    assert (workspace / "input").is_dir()
    assert (workspace / "output").is_dir()

    store.cleanup_workspace("agent-1")

    assert not workspace.exists()


@pytest.mark.parametrize("agent_id", ["", ".", "..", "../evil", "a/b", "a\\b"])
def test_workspace_store_rejects_invalid_agent_ids(tmp_path, agent_id) -> None:
    store = WorkspaceStore(base_dir=tmp_path)

    with pytest.raises(ValueError):
        store.init_workspace(agent_id)


def test_local_workspace_store_uses_default_base_path(tmp_path) -> None:
    store = LocalWorkspaceStore(base_path=tmp_path)

    assert store.base_dir == tmp_path.resolve()
