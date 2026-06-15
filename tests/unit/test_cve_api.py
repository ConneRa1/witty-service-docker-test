from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from witty_service.api import cve as cve_api
from witty_service.api.cve_schemas import UpdateCveConfigRequest


def _service() -> MagicMock:
    service = MagicMock()
    service.get_config.return_value = {
        "gitcode_token": "token",
        "signer_name": "Witty",
        "signer_email": "witty@example.com",
        "clone_dir": "/tmp/repos",
        "branches": "main,stable",
        "fork_repo_url": "https://example.com/fork",
        "repo_url": "https://example.com/repo",
        "issue_url": "https://example.com/issues",
    }
    service.get_workbench.return_value = {
        "cve_id": "CVE-1",
        "cache_key": "key-1",
        "branches": [
            {
                "name": "main",
                "status": "ready",
                "artifacts": [
                    {
                        "kind": "patch",
                        "label": "Patch",
                        "status": "ready",
                        "path": "/tmp/patch.diff",
                        "file_name": "patch.diff",
                        "viewable": True,
                    }
                ],
            }
        ],
    }
    service.get_pr_readiness.return_value = {"ready": True}
    service.read_artifact.return_value = {
        "path": "/tmp/report.md",
        "file_name": "report.md",
        "content": "hello",
    }
    issue = {
        "id": 1,
        "number": 2,
        "title": "CVE issue",
        "body": "details",
        "state": "open",
        "html_url": "https://example.com/issues/2",
        "created_at": "2026-01-01",
        "updated_at": "2026-01-02",
        "labels": [{"name": "security", "color": "red"}],
        "user": {"login": "user", "avatar_url": "https://example.com/avatar.png"},
    }
    service.get_issues.return_value = [issue]
    service.search_issues.return_value = [issue]
    return service


def test_cve_config_and_token_updates() -> None:
    service = _service()

    config = cve_api.get_config(cve_service=service)
    updated = cve_api.update_config(
        payload=UpdateCveConfigRequest(signer_name="New"),
        cve_service=service,
    )
    token_updated = cve_api.update_token(
        x_gitcode_token=" new-token ",
        cve_service=service,
    )

    assert config.has_gitcode_token is True
    assert config.signer_name == "Witty"
    assert updated.ok is True
    assert token_updated.ok is True
    service.update_config.assert_called_once()
    service.update_token.assert_called_once_with("new-token")


def test_cve_update_token_requires_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        cve_api.update_token(x_gitcode_token="  ", cve_service=_service())

    assert exc_info.value.status_code == 400


def test_cve_workbench_readiness_artifact_and_issues() -> None:
    service = _service()

    workbench = cve_api.get_workbench(
        cve_id="CVE-1",
        branches="main",
        clone_dir="/tmp/repos",
        cve_service=service,
    )
    readiness = cve_api.get_pr_readiness(
        cve_id="CVE-1",
        branches="main",
        clone_dir="/tmp/repos",
        issue_number="2",
        cve_service=service,
    )
    artifact = cve_api.get_artifact(path="/tmp/report.md", cve_service=service)
    issues = cve_api.get_issues(
        issue_url="https://example.com/issues",
        limit=10,
        cve_service=service,
    )
    searched = cve_api.search_issues(
        issue_url="https://example.com/issues",
        query="CVE-1",
        limit=5,
        cve_service=service,
    )

    assert workbench.cve_id == "CVE-1"
    assert workbench.branches[0].artifacts[0].viewable is True
    assert readiness == {"ready": True}
    assert artifact.file_name == "report.md"
    assert issues.items[0].labels[0].name == "security"
    assert searched.items[0].user.login == "user"
    service.get_issues.assert_called_once_with(
        issue_url="https://example.com/issues",
        limit=10,
        token="token",
    )
    service.search_issues.assert_called_once_with(
        issue_url="https://example.com/issues",
        query="CVE-1",
        limit=5,
        token="token",
    )
