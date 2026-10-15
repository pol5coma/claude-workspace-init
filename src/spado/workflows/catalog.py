"""Load canonical fiches; render the master document without parsing prose at runtime."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from spado.workflows.models import Organization, Workflow


def safe_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Missing or unsafe catalog file: {relative}")
    return path


def load_workflow(root: Path, workflow_id: str = "spdlc") -> tuple[Workflow, Organization]:
    base = root / "workflows" / workflow_id
    workflow = Workflow.model_validate_json(
        safe_file(root, f"workflows/{workflow_id}/workflow.json").read_text()
    )
    organization = Organization.model_validate_json(
        safe_file(root, f"organizations/{workflow.organization}/organization.json").read_text()
    )
    if workflow.id != workflow_id or organization.id != workflow.organization:
        raise ValueError("Workflow/organization identity mismatch")
    ids = [s for p in workflow.phases for s in p.subphases]
    if len(set(ids)) != len(ids) or set(ids) != set(workflow.subphases):
        raise ValueError("Every subphase must belong to exactly one phase")
    phase_slugs = [phase.slug for phase in workflow.phases]
    if any(
        slug is None or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", slug)
        for slug in phase_slugs
    ):
        raise ValueError("Every phase needs a lowercase hyphenated slug")
    if len(set(phase_slugs)) != len(phase_slugs):
        raise ValueError("Phase slugs must be unique within a workflow")
    slugs = [subphase.slug for subphase in workflow.subphases.values()]
    if any(
        slug is None or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", slug) for slug in slugs
    ):
        raise ValueError("Every subphase needs a lowercase hyphenated slug")
    if len(set(slugs)) != len(slugs):
        raise ValueError("Subphase slugs must be unique within a workflow")
    for phase in workflow.phases:
        for sid in phase.subphases:
            subphase = workflow.subphases[sid]
            if subphase.phase != phase.id or subphase.id != sid:
                raise ValueError(f"Incorrect subphase identity: {sid}")
            subphase.brief_content = safe_file(base, subphase.brief).read_text()
            for dep in subphase.dependencies:
                if dep not in workflow.subphases or dep == sid:
                    raise ValueError(f"Invalid dependency {sid} -> {dep}")
            for aid in [*subphase.owners, *subphase.specialists]:
                if aid not in organization.agents:
                    raise ValueError(f"Unknown agent {aid} in {sid}")
    for aid, agent in organization.agents.items():
        if aid != agent.id:
            raise ValueError("Agent identity mismatch")
        for skill in agent.skills:
            safe_file(root, f"organization-skills/{skill}/SKILL.md")
    workflow.rules_content = safe_file(base, workflow.rules).read_text()
    # Only input dependencies form this graph; collaboration and lifecycle returns stay in briefs.
    visiting, visited = set(), set()

    def visit(sid):
        if sid in visiting:
            raise ValueError(f"Input dependency cycle at {sid}")
        if sid in visited:
            return
        visiting.add(sid)
        for dep in workflow.subphases[sid].dependencies:
            visit(dep)
        visiting.remove(sid)
        visited.add(sid)

    for sid in ids:
        visit(sid)
    workflow.content_digest = hashlib.sha256(
        json.dumps(workflow.model_dump(), sort_keys=True).encode()
    ).hexdigest()
    return workflow, organization


def render_workflow(root: Path, workflow_id: str = "spdlc") -> str:
    workflow, _ = load_workflow(root, workflow_id)
    base = root / "workflows" / workflow_id
    sections = [safe_file(base, workflow.rules).read_text().rstrip(), "# Workflow:"]
    for phase in workflow.phases:
        sections.append(f"## {phase.id}. {phase.title}\n\n{phase.introduction}".rstrip())
        sections.extend(
            safe_file(base, workflow.subphases[s].brief).read_text().rstrip()
            for s in phase.subphases
        )
    return "\n\n".join(sections) + "\n"


def snapshot(root: Path, workflow_id: str = "spdlc") -> dict:
    workflow, organization = load_workflow(root, workflow_id)
    return json.loads(
        json.dumps({"workflow": workflow.model_dump(), "organization": organization.model_dump()})
    )
