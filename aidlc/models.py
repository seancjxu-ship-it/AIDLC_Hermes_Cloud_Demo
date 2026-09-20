from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class RunRequest(BaseModel):
    repository: str = Field(default="https://github.com/seancjxu-ship-it/AIDLC_Simple_Order_Demo")
    base_branch: str = Field(default="main", pattern=r"^[A-Za-z0-9._/-]+$")
    requirement_file: str = Field(default="demo/GITHUB_ISSUE.md")
    execution_mode: Literal["plan", "live"] = "live"
    skill_profile: str = "openspec-core+aidlc-demo"
    model: str = "glm-5.2"


class AgentTask(BaseModel):
    task_id: str
    run_id: str
    role: Literal["dev", "qa", "review", "deploy"]
    stage: str
    skill_names: list[str]
    payload: dict[str, Any]


class TaskResult(BaseModel):
    task_id: str
    run_id: str
    role: str
    passed: bool
    summary: str
    outputs: dict[str, Any] = Field(default_factory=dict)
    completed_at: str = Field(default_factory=utc_now)

