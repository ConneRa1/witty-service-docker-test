from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

import httpx

from src.api.services import ServiceContainer
from src.domain.errors import DomainError


def _default_config() -> dict[str, str]:
    return {
        "gitcode_token": "",
        "signer_name": "",
        "signer_email": "",
        "clone_dir": "/home/dev/Image",
        "branches": "OLK-6.6,OLK-5.10",
        "fork_repo_url": "",
        "issue_url": "https://gitcode.com/src-openeuler/kernel/issues",
        "repo_url": "https://gitcode.com/openeuler/kernel",
    }


class CveService:
    def __init__(self, services: ServiceContainer) -> None:
        self._services = services
        self._config_path = services.workspace_store.base_dir / "config" / "cve.json"
        self._browser_headers: dict[str, str] = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        }

    def get_config(self) -> dict[str, str]:
        if not self._config_path.exists():
            return _default_config()

        try:
            loaded = json.loads(self._config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DomainError(
                code="CVE_CONFIG_LOAD_FAILED",
                message="CVE config is invalid.",
                details={"path": str(self._config_path), "error": str(exc)},
            ) from exc

        config = _default_config()
        for key in config:
            value = loaded.get(key, "")
            config[key] = value if isinstance(value, str) else ""
        return config

    def update_config(self, payload: dict[str, str]) -> None:
        config = self.get_config()
        for key in config:
            if key == "gitcode_token":
                continue
            value = payload.get(key, "")
            config[key] = value.strip() if isinstance(value, str) else ""

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update_token(self, token: str) -> None:
        config = self.get_config()
        config["gitcode_token"] = token.strip()
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_issues(self, issue_url: str, limit: int = 20, *, token: str = "") -> list[dict[str, Any]]:
        org_name, repo_name = self._parse_issue_url(issue_url)
        safe_limit = max(1, min(limit or 20, 100))
        items = self._fetch_issues_from_api(
            org_name=org_name,
            repo_name=repo_name,
            limit=safe_limit,
            token=token,
        )

        filtered: list[dict[str, Any]] = []
        for item in items:
            if "CVE-" not in str(item.get("title") or "").upper():
                continue
            filtered.append(item)
            if len(filtered) >= safe_limit:
                break
        return filtered

    def search_issues(
        self,
        issue_url: str,
        query: str,
        limit: int = 20,
        *,
        token: str = "",
    ) -> list[dict[str, Any]]:
        org_name, repo_name = self._parse_issue_url(issue_url)
        safe_limit = max(1, min(limit or 20, 100))
        needle = query.strip().lower()
        if not needle:
            return self.get_issues(issue_url, safe_limit, token=token)

        items = self._fetch_issues_from_api(
            org_name=org_name,
            repo_name=repo_name,
            limit=max(safe_limit, 50),
            token=token,
            query=query.strip(),
        )

        filtered: list[dict[str, Any]] = []
        for issue in items:
            haystacks = [
                str(issue.get("number", "")),
                str(issue.get("title", "")),
                str(issue.get("body", "")),
                str(issue.get("html_url", "")),
            ]
            haystacks.extend(str(label.get("name", "")) for label in issue.get("labels", []))
            if any(needle in value.lower() for value in haystacks if value):
                filtered.append(issue)
            if len(filtered) >= safe_limit:
                break
        return filtered

    def _parse_issue_url(self, issue_url: str) -> tuple[str, str]:
        parsed = urlparse(issue_url.strip())
        path = parsed.path.strip("/")
        if path.endswith("/issues"):
            path = path[: -len("/issues")]
        if path.endswith(".git"):
            path = path[:-4]

        parts = [part for part in path.split("/") if part]
        if len(parts) < 2:
            raise DomainError(
                code="INVALID_CVE_ISSUE_URL",
                message="Invalid CVE issue URL.",
                details={"issue_url": issue_url},
            )
        return parts[0], parts[1]

    def _fetch_issues_from_api(
        self,
        *,
        org_name: str,
        repo_name: str,
        limit: int,
        token: str,
        query: str = "",
    ) -> list[dict[str, Any]]:
        endpoints = [
            "https://api.atomgit.com/api/v5",
            "https://gitcode.com/api/v5",
        ]
        errors: list[dict[str, Any]] = []

        for base in endpoints:
            url = self._build_issue_api_url(
                base=base,
                org_name=org_name,
                repo_name=repo_name,
                limit=limit,
                query=query,
            )
            headers = dict(self._browser_headers)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            try:
                with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                    response = client.get(url, headers=headers)
            except httpx.HTTPError as exc:
                errors.append({"base": base, "error": str(exc)})
                continue

            if response.status_code >= 400:
                errors.append(
                    {
                        "base": base,
                        "status_code": response.status_code,
                        "response_text": response.text[:500],
                    }
                )
                continue

            try:
                payload = response.json()
            except ValueError as exc:
                errors.append({"base": base, "error": str(exc)})
                continue

            if not isinstance(payload, list):
                errors.append({"base": base, "error": "payload is not a list"})
                continue

            return [self._normalize_issue(issue, org_name, repo_name) for issue in payload]

        if errors and all(self._is_invalid_gitcode_token_error(error) for error in errors):
            raise DomainError(
                code="CVE_GITCODE_TOKEN_INVALID",
                message="GitCode token is invalid.",
                details={"org_name": org_name, "repo_name": repo_name, "errors": errors},
            )

        raise DomainError(
            code="CVE_ISSUES_FETCH_FAILED",
            message="Failed to fetch CVE issues.",
            details={"org_name": org_name, "repo_name": repo_name, "errors": errors},
        )

    def _build_issue_api_url(
        self,
        *,
        base: str,
        org_name: str,
        repo_name: str,
        limit: int,
        query: str = "",
    ) -> str:
        url = (
            f"{base}/repos/{org_name}/{repo_name}/issues"
            f"?state=all&sort=updated&direction=desc&page=1&per_page={limit}"
        )
        if query:
            url += f"&search={query}"
        return url

    def _normalize_issue(self, issue: dict[str, Any], org_name: str, repo_name: str) -> dict[str, Any]:
        number = int(issue.get("number") or issue.get("iid") or 0)
        html_url = issue.get("html_url") or f"https://gitcode.com/{org_name}/{repo_name}/issues/{number}"

        labels: list[dict[str, str]] = []
        raw_labels = issue.get("labels") or []
        if isinstance(raw_labels, list):
            for label in raw_labels:
                if isinstance(label, dict):
                    labels.append(
                        {
                            "name": str(label.get("name") or ""),
                            "color": str(label.get("color") or ""),
                        }
                    )
                else:
                    labels.append({"name": str(label), "color": ""})

        raw_user = issue.get("user") or {}
        if not isinstance(raw_user, dict):
            raw_user = {}

        return {
            "id": int(issue.get("id") or number),
            "number": number,
            "title": str(issue.get("title") or ""),
            "body": str(issue.get("body") or ""),
            "state": str(issue.get("state") or ""),
            "html_url": str(html_url),
            "created_at": str(issue.get("created_at") or ""),
            "updated_at": str(issue.get("updated_at") or ""),
            "labels": labels,
            "user": {
                "login": str(raw_user.get("login") or ""),
                "avatar_url": str(raw_user.get("avatar_url") or ""),
            },
        }

    @staticmethod
    def _is_invalid_gitcode_token_error(error: dict[str, Any]) -> bool:
        response_text = str(error.get("response_text") or "").lower()
        return error.get("status_code") == 404 and "token not found" in response_text
