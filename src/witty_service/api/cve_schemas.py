from __future__ import annotations

from pydantic import BaseModel, Field

class CveLabel(BaseModel):
    name: str
    color: str = ""

class CveUser(BaseModel):
    login: str = ""
    avatar_url: str = ""

class CveIssue(BaseModel):
    id: int
    number: int
    title: str
    body: str = ""
    state: str = ""
    html_url: str
    created_at: str = ""
    updated_at: str = ""
    labels: list[CveLabel] = Field(default_factory=list)
    user: CveUser = Field(default_factory=CveUser)

class CveIssueListResponse(BaseModel):
    items: list[CveIssue]

class CveArtifact(BaseModel):
    kind: str
    label: str
    status: str
    path: str = ""
    file_name: str = ""
    viewable: bool = False

class CveWorkbenchBranch(BaseModel):
    name: str
    status: str = ""
    artifacts: list[CveArtifact] = Field(default_factory=list)

class CveWorkbenchResponse(BaseModel):
    cve_id: str
    cache_key: str
    branches: list[CveWorkbenchBranch] = Field(default_factory=list)

class CveArtifactResponse(BaseModel):
    path: str
    file_name: str
    content: str

class CveConfigResponse(BaseModel):
    has_gitcode_token: bool = False
    signer_name: str = ""
    signer_email: str = ""
    clone_dir: str = ""
    branches: str = ""
    fork_repo_url: str = ""
    repo_url: str = ""
    issue_url: str = ""

class UpdateCveConfigRequest(BaseModel):
    signer_name: str = ""
    signer_email: str = ""
    clone_dir: str = ""
    branches: str = ""
    fork_repo_url: str = ""
    repo_url: str = ""
    issue_url: str = ""

class CveConfigUpdateResponse(BaseModel):
    ok: bool
