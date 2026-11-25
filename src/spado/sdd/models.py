from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Phase = Literal["spec", "roadmap", "red", "build", "close"]
Mode = Literal["manual", "supervised"]
PHASES = ("spec", "roadmap", "red", "build", "close")
KINDS = {"unit", "integration", "acceptance", "e2e"}


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Check(Model):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    kind: Literal["baseline", "unit", "integration", "acceptance", "e2e"]
    argv: list[str] = Field(min_length=1)
    cwd: str = "."
    milestones: list[int] = Field(default_factory=list)
    criteria: list[str] = Field(default_factory=list)
    timeout: int = Field(default=300, ge=1, le=3600)
    junit: str | None = None
    red_failures: list[str] = Field(default_factory=list)
    red_reasons: dict[str, str] = Field(default_factory=dict)


class Checks(Model):
    protected: list[str] = Field(min_length=1)
    checks: list[Check] = Field(min_length=1)

    @model_validator(mode="after")
    def unique(self):
        if len({c.id for c in self.checks}) != len(self.checks):
            raise ValueError("Duplicate check ids")
        return self


class Milestone(Model):
    id: int = Field(ge=1)
    title: str = Field(min_length=1)
    criteria: list[str] = Field(min_length=1)


class Feature(Model):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1)
    sources: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)
    status: Literal["pending", "active", "complete"] = "pending"


class Review(Model):
    role: Literal["architecture", "plan", "asserts", "code", "security"]
    worker: str = Field(min_length=1)
    snapshot: str
    decision: Literal["approve", "changes"]
    findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(min_length=1)


class Report(Model):
    author: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    criteria: list[str] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)
    reviews: list[Review] = Field(default_factory=list)
    blocked: bool = False


class Run(Model):
    id: str
    slug: str
    feature_id: str | None = None
    mode: Mode = "manual"
    base: str
    phase: Phase = "spec"
    milestone: int = 1
    status: str = "pending"
    criteria: list[str] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)
    approvals: dict = Field(default_factory=dict)
    evidence: dict = Field(default_factory=dict)
    frozen: dict[str, str] = Field(default_factory=dict)
    report: Report | None = None
    submitted_snapshot: str | None = None
    phase_snapshot: dict[str, str] = Field(default_factory=dict)
    commits: dict[str, str] = Field(default_factory=dict)
    pending_commit: dict | None = None
    lessons: list[dict] = Field(default_factory=list)


class State(Model):
    schema_version: Literal[1] = 1
    revision: int = 0
    product: dict = Field(default_factory=dict)
    active: Run | None = None
    history: list[Run] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    lessons: list[dict] = Field(default_factory=list)


class Settings(Model):
    schema_version: Literal[1] = 1
    hosts: list[Literal["claude", "codex"]] = Field(min_length=1)
    max_attempts: int = Field(default=3, ge=1, le=10)
    worker_timeout: int = Field(default=900, ge=1, le=7200)
    run_timeout: int = Field(default=7200, ge=1, le=86400)
    max_worker_calls: int = Field(default=30, ge=1, le=100)
