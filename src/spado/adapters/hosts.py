from __future__ import annotations

import json
from pathlib import Path

from spado.workflows.catalog import load_workflow

CONTROL = """Use SPADO's project context and the current run ID. Translate the invocation:
- --status -> `spado status [--run ID]`.
- --review all|phase N|subphase N.N|activity ID -> `spado review TARGET [ID] --run ID`.
- --chat -> read `spado workflow context --run ID` and the requested phase/subphase briefs; discuss only.
Status, review and chat MUST NOT write project files, create runs, synchronize docs, index content,
persist events, approve plans or change external systems. Report suggestions without applying them.
For semantic review, ask relevant C-Agents to inspect only their authorized evidence in read-only mode;
return findings, sources, impact and uncertainties to CAOAO. Structural review is not a guarantee of
semantic consistency. Do not change the selected execution mode during consultation.
Use --run explicitly when the conversation has no unambiguous run. Never pick the most recent run silently.
Commands accept --root to identify the configured project. Credentials come from the actor's token file;
never print tokens or treat an agent's title as identity. --human represents a real Human action, not an
agent escape hatch. Host tool permissions always apply.
"""

EXECUTION = """Coordinate the installed SPDLC organization through CAOAO.
Read `.spado/catalog/workflows/spdlc/rules.md` and use `spado workflow context` for selected briefs.
The workflow has phases and reusable subphases; an activity is a concrete execution of a subphase.
`--phase N`, `--subphase N.N` or `--activity ID` chooses the target; `--mode` overrides its mode.
Use the conversation's run unless --new-run was explicitly requested. To start a run, use
`spado workflow create --objective TEXT --mode MODE [--phase N|--subphase N.N] --human` only on
the Human's instruction to begin. Register CAOAO via `spado actor create CAOAO --run ID --human`.
Delegate officers and specialists with `spado actor create DEFINITION --run ID` using the parent token.
Pass each returned token-file path only to its assigned agent; instantiate native agents by their
installed definitions and load their declared skills. Delegate the plan to the relevant officers.

Before substantive execution, submit a phase plan (when executing a phase/workflow) and an activity
plan using `spado workflow record --run ID --request FILE`. Each request has kind, payload, rationale
and a stable event_id; see `.spado/protocol.md` for the transition contract. Use the CLI validation
errors to correct the plan; never bypass its gates. `spado workflow prepare` submits a prepare request.
Every plan identifies objective, exact expected deliverable, actions, input revision IDs and hashes,
the canonical exit criterion plus product-specific criteria, assumptions and known missing inputs.
The activity owner must be a delegated specialist. Reference actual evidence, not invented completion.

agentic: CAOAO validates plans and domain agents decide; never request Human approval.
auto: same, but ask only for genuinely missing Human information, authority or action.
semi-auto: obtain Human approval of each plan version before execution; agents review the result.
manual: obtain Human plan approval, record human/assisted/delegated execution, then Human result review.
Approval must refer to a concrete plan ID/version and an actual Human response where required.
Do not execute Human CLI approvals without that response. Plan approval is not result acceptance.

Run phases sequentially by default; internal subphase order follows input dependencies.
Explicit advances need a recorded reason. Show missing dependencies, retain the full workflow map,
and permit bounded provisional work with explicit assumptions. Do not accept it until inputs and
domain reviews are satisfied. After the advance return to the pending main sequence.
Record deliverables via `spado docs sync`, then deliver their revision IDs and criterion evidence.
Domain officers review in their own identity. CAOAO accepts only when all gates pass and promotes
accepted document revisions. Revalidate changed evidence before resuming. Phase 6 repeats by cycle;
phase 7 requires CEAO's recorded lifecycle decision. No automatic product retirement.
"""


def render(catalog: Path, host: str, workflow_id="spdlc") -> dict[str, bytes]:
    workflow, organization = load_workflow(catalog, workflow_id)
    if host not in {"claude", "codex"}:
        raise ValueError(f"Unsupported host: {host}")
    skill_root = ".claude/skills" if host == "claude" else ".agents/skills"
    output = {}
    for name, description, body in [
        (
            "spado",
            "Inspect SPADO execution status, review consistency, or discuss workflow scopes without modifications.",
            CONTROL,
        ),
        (
            workflow_id,
            "Execute the configured SPDLC organization for a workflow, phase or subphase using its selected mode.",
            EXECUTION,
        ),
    ]:
        output[f"{skill_root}/{name}/SKILL.md"] = (
            f"---\nname: {name}\ndescription: {description}\n---\n\n{body}".encode()
        )
    for agent in organization.agents.values():
        skill_paths = []
        for skill in agent.skills:
            for source in (catalog / "organization-skills" / skill).rglob("*"):
                if source.is_file():
                    target = f"{skill_root}/{skill}/{source.relative_to(catalog / 'organization-skills' / skill).as_posix()}"
                    output[target] = source.read_bytes()
            skill_paths.append(f"{skill_root}/{skill}/SKILL.md")
        instructions = (
            agent.mandate
            + "\nRead the assigned skills: "
            + ", ".join(skill_paths)
            + "\nUse the assigned SPADO actor identity and scoped context. Follow the configured mode and versioned plan. "
            "Status, review and conversation are read-only. Never substitute your role for another officer's decision."
        )
        name = agent.id.lower()
        if host == "claude":
            body = f"---\nname: {name}\ndescription: {json.dumps(agent.name)}\nskills:\n"
            body += "".join(f"  - {s}\n" for s in agent.skills)
            body += f"---\n\n{instructions}\n"
            output[f".claude/agents/{name}.md"] = body.encode()
        else:
            body = f"name = {json.dumps(name)}\ndescription = {json.dumps(agent.name)}\ndeveloper_instructions = {json.dumps(instructions)}\n"
            output[f".codex/agents/{name}.toml"] = body.encode()
    return output
