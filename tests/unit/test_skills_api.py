from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile

from witty_service.api import skills as skills_api


def _repo_record(**overrides: object) -> SimpleNamespace:
    data = {
        "repo_id": "repo-1",
        "repo_name": "https://github.com/example/skills@main",
        "source_type": "git",
        "branch": "main",
        "url": "https://github.com/example/skills",
        "local_path": "/tmp/skills",
        "skill_discover_status": "done",
        "skill_num": 2,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _skill_record(**overrides: object) -> SimpleNamespace:
    data = {
        "skill_id": "skill-1",
        "repo_id": "repo-1",
        "skill_name": "terminal-helper",
        "relative_path": "skills/terminal-helper/SKILL.md",
        "metadata": {"title": "Terminal Helper"},
        "skill_source": "git",
        "skill_md_url": "https://example.com/SKILL.md",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _services() -> MagicMock:
    services = MagicMock()
    services.repository = MagicMock()
    return services


def test_list_skill_repositories_returns_repository_rows(monkeypatch):
    services = _services()
    service = MagicMock()
    service.list_skill_repositories.return_value = [_repo_record()]
    monkeypatch.setattr(skills_api, "_build_service", lambda _services: service)

    resp = skills_api.list_skill_repositories(services=services)

    assert [item.model_dump() for item in resp] == [
        {
            "repo_id": "repo-1",
            "repo_name": "https://github.com/example/skills@main",
            "source_type": "git",
            "branch": "main",
            "url": "https://github.com/example/skills",
            "local_path": "/tmp/skills",
            "skill_discover_status": "done",
            "skill_num": 2,
        }
    ]


def test_create_skill_repository_from_git_adds_background_discover(monkeypatch):
    services = _services()
    service = MagicMock()
    service.create_skill_repository_from_git.return_value = _repo_record(
        skill_discover_status="init",
        skill_num=0,
    )
    monkeypatch.setattr(skills_api, "_build_service", lambda _services: service)
    background_tasks = BackgroundTasks()

    resp = skills_api.create_skill_repository_from_git(
        payload=SimpleNamespace(
            source_type="git",
            url="https://github.com/example/skills.git",
            branch="main",
            local_path=None,
        ),
        background_tasks=background_tasks,
        services=services,
    )

    assert resp.skill_discover_status == "init"
    assert len(background_tasks.tasks) == 1
    task = background_tasks.tasks[0]
    assert task.func is service.discover_skill_repository_in_background
    assert task.kwargs == {"repository": services.repository, "repo_id": "repo-1"}


def test_create_skill_repository_from_git_raises_400_on_validation_error(monkeypatch):
    services = _services()
    service = MagicMock()
    service.create_skill_repository_from_git.side_effect = ValueError("bad request")
    monkeypatch.setattr(skills_api, "_build_service", lambda _services: service)

    with pytest.raises(HTTPException) as exc_info:
        skills_api.create_skill_repository_from_git(
            payload=SimpleNamespace(source_type="git", url=None, branch=None, local_path=None),
            background_tasks=BackgroundTasks(),
            services=services,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "bad request"


def test_upload_skill_repository_archive_returns_created_repository(monkeypatch):
    services = _services()
    service = MagicMock()
    service.create_skill_repository_from_archive.return_value = _repo_record(
        source_type="local",
        branch=None,
        url=None,
        local_path="/tmp/skills.zip",
        skill_discover_status="init",
        skill_num=0,
    )
    monkeypatch.setattr(skills_api, "_build_service", lambda _services: service)
    background_tasks = BackgroundTasks()
    upload = UploadFile(filename="skills.zip", file=BytesIO(b"fake zip bytes"))

    resp = skills_api.upload_skill_repository_archive(
        background_tasks=background_tasks,
        file=upload,
        services=services,
    )

    assert resp.model_dump() == {
        "repo_id": "repo-1",
        "repo_name": "https://github.com/example/skills@main",
        "source_type": "local",
        "branch": None,
        "url": None,
        "local_path": "/tmp/skills.zip",
        "skill_discover_status": "init",
        "skill_num": 0,
    }
    assert len(background_tasks.tasks) == 1


def test_upload_skill_repository_archive_raises_500_on_unexpected_error(monkeypatch):
    services = _services()
    service = MagicMock()
    service.create_skill_repository_from_archive.side_effect = RuntimeError("boom")
    monkeypatch.setattr(skills_api, "_build_service", lambda _services: service)

    with pytest.raises(HTTPException) as exc_info:
        skills_api.upload_skill_repository_archive(
            background_tasks=BackgroundTasks(),
            file=UploadFile(filename="skills.zip", file=BytesIO(b"fake zip bytes")),
            services=services,
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "boom"


def test_update_skill_repository_raises_404_when_repo_missing(monkeypatch):
    services = _services()
    service = MagicMock()
    service.update_skill_repository.side_effect = KeyError("missing repo")
    monkeypatch.setattr(skills_api, "_build_service", lambda _services: service)

    with pytest.raises(HTTPException) as exc_info:
        skills_api.update_skill_repository(
            repo_id="repo-1",
            payload=SimpleNamespace(source_type="git", url="https://github.com/example/skills.git"),
            services=services,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "'missing repo'"


def test_discover_one_skill_repository_returns_202_when_already_running(monkeypatch):
    services = _services()
    service = MagicMock()
    service.discover_one_skill_repository.side_effect = ValueError(
        "Skill repository discovery is already in progress"
    )
    monkeypatch.setattr(skills_api, "_build_service", lambda _services: service)

    with pytest.raises(HTTPException) as exc_info:
        skills_api.discover_one_skill_repository(repo_id="repo-1", services=services)

    assert exc_info.value.status_code == 202
    assert exc_info.value.detail == "Skill repository discovery is already in progress"


def test_list_skills_returns_discovered_skills(monkeypatch):
    services = _services()
    service = MagicMock()
    service.list_skills.return_value = [_skill_record()]
    monkeypatch.setattr(skills_api, "_build_service", lambda _services: service)

    resp = skills_api.list_skills(services=services)

    assert [item.model_dump() for item in resp] == [
        {
            "skill_id": "skill-1",
            "repo_id": "repo-1",
            "skill_name": "terminal-helper",
            "relative_path": "skills/terminal-helper/SKILL.md",
            "metadata": {"title": "Terminal Helper"},
            "skill_source": "git",
            "skill_md_url": "https://example.com/SKILL.md",
        }
    ]
