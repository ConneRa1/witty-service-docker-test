from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from openhands.agent_server.utils import utc_now


class SkillRepoSourceType(str, Enum):
    GIT = 'git'
    LOCAL_IMPORT = 'local_import'


class SkillRepo(BaseModel):
    repo_id: str
    name: str = Field(min_length=1, max_length=255)
    source_type: SkillRepoSourceType
    branch: str | None = None
    url: str | None = None
    local_path: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SkillRepoPage(BaseModel):
    items: list[SkillRepo]


class CreateSkillRepoRequest(BaseModel):
    source_type: SkillRepoSourceType
    branch: str | None = None
    url: str | None = None
    local_path: str | None = None


class UpdateSkillRepoRequest(BaseModel):
    source_type: SkillRepoSourceType | None = None
    branch: str | None = None
    url: str | None = None
    local_path: str | None = None


class SkillRepoDiscoverStatusItem(BaseModel):
    repo_id: str
    repo_name: str
    discover_status: str
    skill_num: int


class SkillRepoDiscoverStatus(BaseModel):
    items: list[SkillRepoDiscoverStatusItem]


class SkillSourceRepo(BaseModel):
    repo_id: str
    name: str
    source_type: SkillRepoSourceType
    branch: str | None = None
    url: str | None = None
    local_path: str | None = None


class SkillDiscoveryItem(BaseModel):
    skill_id: str
    skill_name: str
    relative_path: str | None = None
    metadata: dict | None = None
    source_repo: SkillSourceRepo | None = None
    skill_md_url: str | None = None


class SkillRepoDiscoverPage(BaseModel):
    items: list[SkillDiscoveryItem]
