from __future__ import annotations

import io
import tarfile
from types import SimpleNamespace

import pytest

from witty_service import workspace_init


def _tar_bytes() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        data = b"hello"
        info = tarfile.TarInfo("agent-config/example.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def test_init_workspace_returns_existing_path(tmp_path) -> None:
    result = workspace_init.init_workspace(str(tmp_path))

    assert result == tmp_path


def test_init_workspace_extracts_packaged_agent_config(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(workspace_init, "get_data", lambda *_args: _tar_bytes())

    result = workspace_init.init_workspace(str(workspace))

    assert result == workspace
    assert (workspace / "agent-config" / "example.txt").read_text() == "hello"
    assert not (workspace / "agent-config.tar.gz").exists()


def test_init_workspace_uses_settings_when_root_is_not_provided(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "settings-workspace"
    monkeypatch.setattr(
        workspace_init,
        "get_settings",
        lambda: SimpleNamespace(workspace=SimpleNamespace(root=str(workspace))),
    )
    monkeypatch.setattr(workspace_init, "get_data", lambda *_args: _tar_bytes())

    result = workspace_init.init_workspace()

    assert result == workspace
    assert (workspace / "agent-config" / "example.txt").exists()


def test_init_workspace_raises_when_package_data_missing(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(workspace_init, "get_data", lambda *_args: None)

    with pytest.raises(FileNotFoundError):
        workspace_init.init_workspace(str(workspace))

    assert not (workspace / "agent-config.tar.gz").exists()
