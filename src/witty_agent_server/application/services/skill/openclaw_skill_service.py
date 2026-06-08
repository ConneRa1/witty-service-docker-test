from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from witty_agent_server.application.services.skill.base import AgentSkillServiceBase
from witty_agent_server.application.services.skill.errors import (
    OpenClawSkillsInstallError,
    OpenClawSkillsQueryError,
    OpenClawSkillsUninstallError,
)
from witty_agent_server.infra.ws.openclaw_gateway_client import (
    OpenClawGatewayClientError,
)


logger = logging.getLogger(__name__)


class OpenClawSkillService(AgentSkillServiceBase):
    runtime_type = "openclaw"
    skills_dir = Path.home() / ".openclaw" / "skills"

    _ALLOWED_DELETE_BASES: list[Path] = [
        skills_dir,
        Path.home() / ".agent" / "skills",
        Path.home() / ".openclaw" / "workspace/skills",
        Path.home() / ".openclaw" / "workspace/.agents/skills",
        Path.home() / ".openclaw" / "plugin-skills",
    ]

    _ALLOWED_SOURCE_BASES: list[Path] = [
        Path(os.getenv("WITTY_WORKSPACE_BASE", "~/.witty")).expanduser() / "skill-repositories",
    ]

    @classmethod
    def _validate_path_under_allowed_bases(cls, target: Path) -> Path:
        resolved = target.expanduser().resolve()
        for base in cls._ALLOWED_DELETE_BASES:
            base_resolved = base.resolve()
            try:
                resolved.relative_to(base_resolved)
                return resolved
            except ValueError:
                continue
        raise ValueError(
            f"Path {resolved} is outside allowed directories: "
            f"{[str(b) for b in cls._ALLOWED_DELETE_BASES]}"
        )

    @classmethod
    def _validate_source_path_under_workspace(cls, target: Path) -> Path:
        resolved = target.expanduser().resolve()
        for base in cls._ALLOWED_SOURCE_BASES:
            base_resolved = base.resolve()
            try:
                resolved.relative_to(base_resolved)
                return resolved
            except ValueError:
                continue
        raise ValueError(
            f"Source path {resolved} is outside allowed directories: "
            f"{[str(b) for b in cls._ALLOWED_SOURCE_BASES]}"
        )

    def list_skills(self, *, agent_id: str | None = None) -> dict[str, Any]:
        """查询并返回当前 agent 可用的技能摘要列表。"""
        logger.info(
            "list_skills requested, runtime_type=%s agent_id=%s",
            self.runtime_type,
            agent_id,
        )
        try:
            skills_payload = self._openclaw_client.get_skills_status(agent_id=agent_id)
        except OpenClawGatewayClientError as exc:
            logger.exception(
                "list_skills openclaw rpc failed, runtime_type=%s agent_id=%s code=%s",
                self.runtime_type,
                agent_id,
                exc.code,
            )
            raise OpenClawSkillsQueryError(
                runtime_type=self.runtime_type,
                code=exc.code,
                message=exc.message,
            ) from exc

        logger.info(
            "list_skills success, runtime_type=%s agent_id=%s skill_count=%s",
            self.runtime_type,
            agent_id,
            self._count_eligible_skills(skills_payload),
        )
        return {
            "runtime_type": self.runtime_type,
            "skills": self._normalize_eligible_skills(skills_payload),
        }

    def _normalize_eligible_skills(
        self, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """筛选可用技能，并裁剪为对外暴露的固定字段。"""
        for key in ("skills", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [
                    self._build_skill_summary(item)
                    for item in value
                    if isinstance(item, dict) and item.get("eligible") is True
                ]
        if payload and all(isinstance(key, str) for key in payload):
            return [
                self._build_skill_summary({"name": key, "description": value})
                for key, value in payload.items()
            ]
        return []

    def _count_eligible_skills(self, payload: dict[str, Any]) -> int:
        """统计当前响应中可用技能数量。"""
        return len(self._normalize_eligible_skills(payload))

    def _build_skill_summary(self, item: dict[str, Any]) -> dict[str, Any]:
        """构造对外返回的技能摘要，仅保留约定字段。"""
        return {
            "name": item.get("name"),
            "description": item.get("description"),
            "filePath": item.get("filePath"),
            "source": item.get("source"),
        }

    def install_skill(
        self,
        *,
        agent_id: str | None = None,
        skill_name: str,
        source_path: str | None = None,
    ) -> dict[str, Any]:
        normalized_name = self._normalize_skill_name(
            skill_name=skill_name,
            error_cls=OpenClawSkillsInstallError,
        )

        if source_path:
            return self._install_local_skill(normalized_name, source_path)
        try:
            install_channel = "clawhub_cmd"
            self._install_skill_via_clawhub(normalized_name)
            self._openclaw_client.enable_skill(
                agent_id=agent_id,
                skill_name=normalized_name,
            )
        except OpenClawSkillsInstallError as cmd_exc:
            logger.warning(
                (
                    "install_skill clawhub command failed, fallback to gateway rpc, "
                    "runtime_type=%s agent_id=%s skill_name=%s code=%s message=%s"
                ),
                self.runtime_type,
                agent_id,
                normalized_name,
                cmd_exc.code,
                cmd_exc.details.get("reason"),
            )
            try:
                install_channel = "gateway_rpc"
                self._openclaw_client.install_skill(
                    agent_id=agent_id,
                    skill_name=normalized_name,
                    version=None,
                    force=True,
                )
            except OpenClawGatewayClientError as rpc_exc:
                raise OpenClawSkillsInstallError(
                    runtime_type=self.runtime_type,
                    skill_name=normalized_name,
                    reason=(
                        "clawhub install failed "
                        f"({cmd_exc.details.get('reason')}); "
                        "gateway rpc fallback failed "
                        f"({rpc_exc.code}: {rpc_exc.message})"
                    ),
                ) from rpc_exc

        logger.info(
            "install_skill success, runtime_type=%s agent_id=%s skill_name=%s channel=%s",
            self.runtime_type,
            agent_id,
            normalized_name,
            install_channel,
        )
        return {
            "runtime_type": self.runtime_type,
            "skill_name": normalized_name,
            "installed": True,
            "install_channel": install_channel,
        }

    def _install_local_skill(self, skill_name: str, source_path: str) -> dict[str, Any]:
        src = Path(source_path).expanduser().resolve()
        try:
            src = self._validate_source_path_under_workspace(src)
        except ValueError as exc:
            raise OpenClawSkillsInstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason=str(exc),
            ) from exc
        if not src.exists():
            raise OpenClawSkillsInstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason=f"source path does not exist: {src}",
            )

        self.skills_dir.mkdir(parents=True, exist_ok=True)
        dst = self.skills_dir / skill_name

        try:
            dst = self._validate_path_under_allowed_bases(dst)
        except ValueError as exc:
            raise OpenClawSkillsInstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason=str(exc),
            ) from exc

        if dst.exists():
            shutil.rmtree(dst)

        if src.is_file():
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / src.name)
        else:
            shutil.copytree(src, dst)

        logger.info(
            "install_local_skill success, runtime_type=%s skill_name=%s src=%s dst=%s",
            self.runtime_type,
            skill_name,
            src,
            dst,
        )
        return {
            "runtime_type": self.runtime_type,
            "skill_name": skill_name,
            "installed": True,
            "install_channel": "local_copy",
        }

    def _install_skill_via_clawhub(self, skill_name: str) -> None:
        command = ["clawhub", "install", skill_name, "--force"]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except FileNotFoundError as exc:
            raise OpenClawSkillsInstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason="clawhub command not found",
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            reason = stderr or stdout or f"clawhub exited with code {exc.returncode}"
            raise OpenClawSkillsInstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason=reason,
            ) from exc
        except Exception as exc:  # pragma: no cover - fs/environment specific
            raise OpenClawSkillsInstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason=str(exc),
            ) from exc

    def uninstall_skill(
        self,
        *,
        agent_id: str | None = None,
        skill_name: str,
        source_type: str | None = None,
        source_path: str | None = None,
    ) -> dict[str, Any]:
        normalized_name = self._normalize_skill_name(
            skill_name=skill_name,
            error_cls=OpenClawSkillsUninstallError,
        )

        if source_type in ("local", "git"):
            return self._uninstall_local_skill(normalized_name)

        if source_type == "builtin" and source_path:
            return self._uninstall_builtin_skill(normalized_name, source_path)

        try:
            uninstall_channel = "clawhub_cmd"
            self._uninstall_skill_via_clawhub(normalized_name)
        except OpenClawSkillsUninstallError as cmd_exc:
            logger.warning(
                (
                    "uninstall_skill clawhub command failed, fallback to gateway rpc, "
                    "runtime_type=%s skill_name=%s reason=%s"
                ),
                self.runtime_type,
                normalized_name,
                cmd_exc.details.get("reason"),
            )
            try:
                uninstall_channel = "gateway_rpc"
                self._openclaw_client.uninstall_skill(
                    agent_id=agent_id,
                    skill_name=normalized_name,
                )
            except OpenClawGatewayClientError as rpc_exc:
                raise OpenClawSkillsUninstallError(
                    runtime_type=self.runtime_type,
                    skill_name=normalized_name,
                    reason=(
                        "clawhub uninstall failed "
                        f"({cmd_exc.details.get('reason')}); "
                        "gateway rpc fallback failed "
                        f"({rpc_exc.code}: {rpc_exc.message})"
                    ),
                ) from rpc_exc

        return {
            "runtime_type": self.runtime_type,
            "skill_name": normalized_name,
            "uninstalled": True,
            "uninstall_channel": uninstall_channel,
        }

    def _uninstall_skill_via_clawhub(self, skill_name: str) -> None:
        command = ["clawhub", "uninstall", skill_name, "--yes"]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logger.info(
                "clawhub uninstall success, skill_name=%s command=%s stdout=%s stderr=%s",
                skill_name, command, result.stdout.strip(), result.stderr.strip(),
            )
        except FileNotFoundError as exc:
            raise OpenClawSkillsUninstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason="clawhub command not found",
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            reason = stderr or stdout or f"clawhub exited with code {exc.returncode}"
            raise OpenClawSkillsUninstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason=reason,
            ) from exc
        except Exception as exc:
            raise OpenClawSkillsUninstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason=str(exc),
            ) from exc

    def _uninstall_local_skill(self, skill_name: str) -> dict[str, Any]:
        dst = self.skills_dir / skill_name
        try:
            dst = self._validate_path_under_allowed_bases(dst)
        except ValueError as exc:
            raise OpenClawSkillsUninstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason=str(exc),
            ) from exc
        if dst.exists():
            shutil.rmtree(dst)

        logger.info(
            "uninstall_local_skill success, runtime_type=%s skill_name=%s dst=%s",
            self.runtime_type,
            skill_name,
            dst,
        )
        return {
            "runtime_type": self.runtime_type,
            "skill_name": skill_name,
            "uninstalled": True,
            "uninstall_channel": "local_remove",
        }

    def _uninstall_builtin_skill(self, skill_name: str, source_path: str) -> dict[str, Any]:
        try:
            dst = self._validate_path_under_allowed_bases(Path(source_path))
        except ValueError as exc:
            raise OpenClawSkillsUninstallError(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason=str(exc),
            ) from exc
        if dst.exists():
            shutil.rmtree(dst)

        logger.info(
            "uninstall_builtin_skill success, runtime_type=%s skill_name=%s dst=%s",
            self.runtime_type,
            skill_name,
            dst,
        )
        return {
            "runtime_type": self.runtime_type,
            "skill_name": skill_name,
            "uninstalled": True,
            "uninstall_channel": "builtin_remove",
        }

    def _normalize_skill_name(
        self,
        *,
        skill_name: str,
        error_cls: type[OpenClawSkillsInstallError] | type[OpenClawSkillsUninstallError],
    ) -> str:
        if not isinstance(skill_name, str) or not skill_name.strip():
            raise error_cls(
                runtime_type=self.runtime_type,
                skill_name=skill_name,
                reason="skill_name is empty",
            )
        normalized_name = skill_name.strip()
        if re.search(r"[\\/]", normalized_name):
            raise error_cls(
                runtime_type=self.runtime_type,
                skill_name=normalized_name,
                reason="skill_name contains path separator",
            )
        return normalized_name
