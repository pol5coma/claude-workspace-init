"""Bounded controller: fresh CLI process per assignment, never resume a host chat."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path
from uuid import uuid4

from spado.runtime.config import dump
from spado.sdd import engine
from spado.sdd.models import Report, Review, Settings
from spado.sdd.store import event, git, lock, read, safe, snapshot, transaction

SKILLS = {
    "spec": "feature-spec",
    "roadmap": "feature-roadmap",
    "red": "feature-tdd-start",
    "build": "feature-tdd-build",
    "close": "feature-close",
}


def worker_command(host, root, prompt, schema, output, readonly):
    if host == "codex":
        return [
            "codex",
            "exec",
            "--cd",
            str(root),
            "--sandbox",
            "read-only" if readonly else "workspace-write",
            "--output-schema",
            str(schema),
            "--output-last-message",
            str(output),
            prompt,
        ]
    if host == "claude":
        command = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--json-schema",
            schema.read_text(),
            "--tools",
            "Read,Glob,Grep" if readonly else "Read,Glob,Grep,Edit,Write,Bash",
            "--permission-mode",
            "default" if readonly else "acceptEdits",
        ]
        if not readonly:
            command += ["--agent", "sdd-worker"]
        return command
    raise ValueError("Host must be claude or codex")


def strict_schema(schema):
    if isinstance(schema, dict):
        schema.pop("default", None)
        if "properties" in schema:
            schema["required"] = list(schema["properties"])
        for v in schema.values():
            strict_schema(v)
    elif isinstance(schema, list):
        for v in schema:
            strict_schema(v)
    return schema


def launch(root, host, role, instruction, settings, deadline, readonly=False):
    run = engine.active(read(root))
    worker_id = uuid4().hex
    schema_type = Review if readonly else Report
    base = safe(root, ".workflow/results")
    base.mkdir(exist_ok=True)
    schema_path, output = base / f"{worker_id}.schema.json", base / f"{worker_id}.json"
    schema_path.write_text(dump(strict_schema(schema_type.model_json_schema())))
    skill_root = ".claude/skills" if host == "claude" else ".agents/skills"
    before = snapshot(root)
    diff_path = base / f"{worker_id}.diff"
    if readonly:
        diff_path.write_text(
            git(root, "diff", "--no-ext-diff", run.base, "--")
            + "\nUntracked paths (read separately):\n"
            + git(root, "ls-files", "--others", "--exclude-standard")
        )
    prompt = (
        f"SDD assignment {worker_id}, role {role}. Read .workflow/PROTOCOL.md, AGENTS.md if present, "
        f"and {skill_root}/{SKILLS[run.phase]}/SKILL.md. You are a worker, not the coordinator. "
        "Do not run spado sdd transitions, approve, commit, push, or delegate. "
        "Return only the schema-conforming report. Do not edit state, checks to evade failures, or host configuration. "
        f"Feature context: {dump(run.model_dump())}\nCurrent snapshot: {before}\n"
        f"Relevant verified lessons: {dump(run.lessons[-5:])}\n{instruction}"
    )
    if readonly:
        prompt += f"\nThe controller prepared the complete Git diff at {diff_path.relative_to(root)}. Read it."
    command = worker_command(host, root, prompt, schema_path, output, readonly)
    log = base / f"{worker_id}.log"
    with log.open("w") as stream:
        process = subprocess.Popen(
            command, cwd=root, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True
        )
        try:
            remaining = min(settings.worker_timeout, deadline - time.monotonic())
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, 0)
            code = process.wait(timeout=remaining)
        except BaseException:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
    if code:
        raise ValueError(f"Worker failed ({code}); inspect {log.relative_to(root)}")
    if host == "claude":
        # Claude stdout may contain diagnostics; the result envelope is a JSON line.
        envelopes = []
        for line in log.read_text().splitlines():
            try:
                envelopes.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        envelopes = [e for e in envelopes if isinstance(e, dict) and "structured_output" in e]
        if not envelopes or envelopes[-1].get("is_error"):
            raise ValueError("Claude did not return a structured result")
        value = envelopes[-1]["structured_output"]
    else:
        value = json.loads(output.read_text())
    if readonly:
        if snapshot(root) != before:
            raise ValueError("Reviewer changed repository files")
        value.update(worker=worker_id, role=role, snapshot=before)
    else:
        value["author"] = worker_id
        value["reviews"] = []  # Only separately launched reviewers provide authoritative reports.
    result = schema_type.model_validate(value)
    output.write_text(dump(result.model_dump()))
    with transaction(root) as state:
        event(
            state,
            "worker",
            worker=worker_id,
            role=role,
            host=host,
            log=str(log.relative_to(root)),
            fresh_process=True,
        )
    return result


def run_feature(root: Path, host: str):
    settings = Settings.model_validate_json(safe(root, ".workflow/config.json").read_text())
    if host not in settings.hosts:
        raise ValueError("Host is not installed for this SDD project")
    if engine.active(read(root)).mode != "supervised":
        raise ValueError("Start the feature explicitly in supervised mode")
    deadline = time.monotonic() + settings.run_timeout
    calls = 0

    def call(role, instruction, readonly=False):
        nonlocal calls
        calls += 1
        if calls > settings.max_worker_calls or time.monotonic() >= deadline:
            raise ValueError("Supervised execution budget exhausted")
        return launch(root, host, role, instruction, settings, deadline, readonly)

    with lock(root, "runner"):
        try:
            while True:
                run = engine.active(read(root))
                if run.status == "complete" or (
                    run.phase == "close" and run.status == "awaiting_review"
                ):
                    return {
                        "status": run.status,
                        "feature": run.slug,
                        "worker_calls": calls,
                        "next": "Review the feature, then sdd approve --response YOUR_RESPONSE",
                    }
                if run.pending_commit:
                    raise ValueError("An interrupted commit requires sdd recover before resuming")
                if run.status == "awaiting_review":
                    engine.approve(
                        root, "Independent reviews and executable gates passed", delegated=True
                    )
                    continue
                if run.phase == "red" and run.status in {"pending", "paused", "blocked"}:
                    call(
                        "test-plan",
                        "Only prepare CHECKS.json from the approved spec and milestones. "
                        "Do not write tests or implementation yet. Include baseline commands for existing tests, "
                        "unit/integration/acceptance/e2e commands for every milestone, explicit protected globs, "
                        "criterion mappings and JUnit outputs in .workflow/results/. Return a Report.",
                    )
                    baseline = engine.check(root, baseline=True)
                    if not baseline["passed"]:
                        raise ValueError("Baseline failed; no tests or code were authorized")
                if run.status != "in_progress":
                    engine.begin(root, run.phase, run.milestone if run.phase == "build" else None)
                feedback = ""
                for attempt in range(settings.max_attempts):
                    run = engine.active(read(root))
                    report = call(
                        "author",
                        f"Execute only {run.phase}, milestone {run.milestone}. "
                        "For spec produce FEATURE.md and FEATURE-MAP.md and criterion IDs. "
                        "For roadmap produce ROADMAP.md and structured milestones. "
                        "For Red write all tests; do not implement production code. "
                        "For Build implement the selected milestone without changing tests. "
                        "For Close clean up and update AGENTS.md and FEATURE-MAP.md; preserve specs. "
                        f"Return blocked=true if a requirement, permission, or frozen test needs changing.\n{feedback}",
                    )
                    if report.blocked:
                        engine.submit(root, report)
                        return {
                            "status": "blocked",
                            "reason": report.summary,
                            "worker_calls": calls,
                        }
                    if run.phase in {"red", "build", "close"}:
                        evidence = engine.check(root)
                        if not evidence["passed"]:
                            feedback = (
                                "Correct these actual failures without weakening contracts:\n"
                                + dump(evidence)
                            )
                            with transaction(root) as state:
                                event(
                                    state,
                                    "attempt_failed",
                                    phase=run.phase,
                                    attempt=attempt + 1,
                                    evidence=evidence,
                                )
                            continue
                    reviews = []
                    for role in sorted(engine.expected_reviews(run)):
                        reviews.append(
                            call(
                                role,
                                f"Read-only independent {role} review. Inspect the source "
                                "artifacts and contracts yourself. For code/security review all changes "
                                f"since {run.base}, including working tree changes. Report concrete "
                                "findings and evidence. decision=approve only if there are no blockers. "
                                "Do not claim tests pass from an author's statement.",
                                readonly=True,
                            )
                        )
                    report.reviews = reviews
                    if any(r.decision != "approve" for r in reviews):
                        feedback = "Resolve these independent findings:\n" + dump(
                            [r.model_dump() for r in reviews]
                        )
                        continue
                    engine.submit(root, report)
                    if feedback:
                        with transaction(root) as state:
                            item = next(
                                (
                                    f
                                    for f in state.product.get("features", [])
                                    if f["id"] == run.feature_id
                                ),
                                None,
                            )
                            lesson = {
                                "phase": run.phase,
                                "milestone": run.milestone,
                                "failure_evidence": feedback,
                                "resolution": report.summary,
                                "verified_snapshot": snapshot(root),
                                "scope": run.slug,
                                "sources": item["sources"] if item else [],
                            }
                            state.active.lessons.append(lesson)
                            state.lessons.append(lesson)
                    break
                else:
                    raise ValueError("Attempt limit reached; inspect failures before resuming")
        except (ValueError, OSError, subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            with transaction(root) as state:
                state.active.status = "blocked"
                event(state, "runner_blocked", reason=str(exc), worker_calls=calls)
            return {"status": "blocked", "reason": str(exc), "worker_calls": calls}
