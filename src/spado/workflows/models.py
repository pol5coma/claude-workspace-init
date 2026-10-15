from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def uid() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(UTC).isoformat()


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Mode(StrEnum):
    AGENTIC = "agentic"
    AUTO = "auto"
    SEMI_AUTO = "semi-auto"
    MANUAL = "manual"


class Status(StrEnum):
    PENDING = "pending"
    AWAITING_PLAN = "awaiting_plan_approval"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    PROVISIONAL = "provisional"
    REVIEW = "awaiting_review"
    REVALIDATE = "needs_revalidation"
    ACCEPTED = "accepted"
    NA = "not_applicable"


class Scope(Model):
    kind: Literal["workflow", "phase", "subphase"] = "workflow"
    id: str | None = None

    @model_validator(mode="after")
    def valid(self):
        if (self.kind == "workflow") != (self.id is None):
            raise ValueError("Only workflow scope has no id")
        return self


class AgentDefinition(Model):
    id: str
    name: str
    level: Literal["orchestrator", "officer", "specialist"]
    mandate: str
    skills: list[str] = Field(min_length=1)
    subphases: list[str] = Field(default_factory=list)


class Organization(Model):
    id: str
    version: str
    agents: dict[str, AgentDefinition]


class Subphase(Model):
    id: str
    title: str
    phase: str
    brief: str
    brief_content: str = ""
    owners: list[str] = Field(min_length=1)
    specialists: list[str] = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    deliverable: str
    exit_criteria: str
    applicability: str


class Phase(Model):
    id: str
    title: str
    introduction: str = ""
    subphases: list[str]
    lifecycle: Literal["sequential", "recurring", "conditional"] = "sequential"


class Workflow(Model):
    schema_version: Literal[1] = 1
    id: str
    version: str
    content_digest: str = ""
    title: str
    organization: str
    rules: str
    rules_content: str = ""
    phases: list[Phase]
    subphases: dict[str, Subphase]

    def select(self, scope: Scope) -> list[str]:
        if scope.kind == "workflow":
            return [s for p in self.phases for s in p.subphases]
        if scope.kind == "phase":
            for phase in self.phases:
                if phase.id == scope.id:
                    return phase.subphases.copy()
        elif scope.id in self.subphases:
            return [scope.id]
        raise ValueError(f"Unknown {scope.kind}: {scope.id}")


class Actor(Model):
    id: str = Field(default_factory=uid)
    project: str
    definition: str
    level: Literal["human", "orchestrator", "officer", "specialist"]
    run_id: str | None = None
    subphases: list[str] = Field(default_factory=list)
    parent_id: str | None = None


class Plan(Model):
    id: str = Field(default_factory=uid)
    version: int = Field(default=1, ge=1)
    objective: str = Field(min_length=1)
    deliverable: str = Field(min_length=1)
    actions: list[str] = Field(min_length=1)
    criteria: list[str] = Field(min_length=1)
    inputs: dict[str, str] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    missing_dependencies: list[str] = Field(default_factory=list)
    reused_activities: list[str] = Field(default_factory=list)
    approved_by: str | None = None
    approved_at: str | None = None


class Activity(Model):
    id: str = Field(default_factory=uid)
    sequence: int = Field(default=1, ge=1)
    subphase: str
    mode: Mode
    owner: str
    previous_id: str | None = None
    phase_plan_id: str | None = None
    status: Status = Status.AWAITING_PLAN
    plan: Plan
    out_of_order: bool = False
    reason: str = ""
    arrangement: Literal["human", "assisted", "delegated"] | None = None
    outputs: list[str] = Field(default_factory=list)
    domain_reviews: dict[str, str] = Field(default_factory=dict)
    human_review: str | None = None
    criteria_evidence: dict[str, str] = Field(default_factory=dict)


class Revision(Model):
    id: str = Field(default_factory=uid)
    sequence: int = Field(default=1, ge=1)
    path: str
    digest: str
    content: str
    author: str
    subphase: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    approved_by: str | None = None
    supersedes: str | None = None
    created_at: str = Field(default_factory=now)


class Run(Model):
    id: str = Field(default_factory=uid)
    project: str
    workflow: Workflow
    organization: Organization
    scope: Scope
    mode: Mode
    objective: str = Field(min_length=1)
    version: int = 0
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)
    phase_modes: dict[str, Mode] = Field(default_factory=dict)
    subphase_modes: dict[str, Mode] = Field(default_factory=dict)
    phase_plans: dict[str, Plan] = Field(default_factory=dict)
    phase_reviews: dict[str, str] = Field(default_factory=dict)
    activities: dict[str, Activity] = Field(default_factory=dict)
    revisions: dict[str, Revision] = Field(default_factory=dict)
    official: dict[str, str] = Field(default_factory=dict)
    external_inputs: dict[str, str] = Field(default_factory=dict)
    not_applicable: dict[str, str] = Field(default_factory=dict)
    not_applicable_reviews: dict[str, dict[str, str]] = Field(default_factory=dict)
    retirement_authorized: bool = False

    def effective_mode(self, subphase: str, override: Mode | None = None) -> Mode:
        phase = self.workflow.subphases[subphase].phase
        return (
            override
            or self.subphase_modes.get(subphase)
            or self.phase_modes.get(phase)
            or self.mode
        )

    def latest(self, subphase: str) -> Activity | None:
        return max(
            (a for a in self.activities.values() if a.subphase == subphase),
            key=lambda a: a.sequence,
            default=None,
        )

    def latest_revisions(self) -> dict[str, Revision]:
        # JSONB object key order is not insertion order. Persist chronology explicitly.
        return {r.path: r for r in sorted(self.revisions.values(), key=lambda r: r.sequence)}


class Event(Model):
    id: str = Field(default_factory=uid)
    kind: str
    actor: str
    run_id: str
    timestamp: str = Field(default_factory=now)
    rationale: str
    payload: dict = Field(default_factory=dict)
