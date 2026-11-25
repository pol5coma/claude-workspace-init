from __future__ import annotations

import fnmatch
import hashlib
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

from spado.sdd.models import KINDS, PHASES, Checks, Feature, Report, Run
from spado.sdd.store import digest, event, files, git, read, safe, snapshot, transaction, write


def active(state):
    if not state.active:
        raise ValueError("No active feature; invoke feature-spec or sdd start first")
    return state.active


def folder(run):
    return f"docs/features/{run.slug}"


def checks(root, run):
    return Checks.model_validate_json(safe(root, f"{folder(run)}/CHECKS.json").read_text())


def protected(root, run):
    cfg = checks(root, run)
    result = {"@checks": digest(cfg.model_dump())}
    for pattern in cfg.protected:
        if pattern.startswith("/") or ".." in Path(pattern).parts:
            raise ValueError("Protected patterns must stay inside the repository")
        for path in root.glob(pattern):
            if path.is_file():
                name = path.relative_to(root).as_posix()
                safe(root, name)
                result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def integrity(root, run):
    if run.frozen and protected(root, run) != run.frozen:
        raise ValueError("Protected tests/configuration changed; reopen red explicitly")


def approved_inputs(root, run):
    for key, approval in run.approvals.items():
        for path, expected in approval.get("artifacts", {}).items():
            target = safe(root, path)
            actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
            if actual != expected:
                raise ValueError(f"Approved input changed: {path}; reopen {key}")


def artifact_paths(root, run):
    base = folder(run)
    if run.phase == "spec":
        return [f"{base}/FEATURE.md"]
    if run.phase == "roadmap":
        return [f"{base}/ROADMAP.md"]
    if run.phase == "red":
        return [f"{base}/CHECKS.json"]
    return []


def start(root: Path, slug: str, mode="manual", feature_id=None):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Invalid feature slug")
    if mode not in {"manual", "supervised"}:
        raise ValueError("Mode must be manual or supervised")
    with transaction(root) as state:
        if state.active and state.active.status != "complete":
            raise ValueError("A feature is already active")
        if git(root, "status", "--porcelain"):
            raise ValueError("Commit or move pending changes before starting a feature")
        sources = []
        if feature_id:
            product_valid(root, state)
            entries = {f["id"]: f for f in state.product["features"]}
            if feature_id not in entries or entries[feature_id]["slug"] != slug:
                raise ValueError("Feature id/slug does not match the approved product roadmap")
            item = entries[feature_id]
            sources = item["sources"]
            if item["status"] != "pending":
                raise ValueError("Feature is not pending")
            if any(entries[d]["status"] != "complete" for d in item["depends_on"]):
                raise ValueError("Feature dependencies are not complete")
        if state.active:
            state.history.append(state.active)
        state.active = Run(
            id=uuid4().hex,
            slug=slug,
            feature_id=feature_id,
            mode=mode,
            base=git(root, "rev-parse", "HEAD"),
            lessons=[
                lesson for lesson in state.lessons if set(lesson.get("sources", [])) & set(sources)
            ][-5:],
        )
        event(state, "start", slug=slug, mode=mode)
        return state.active.model_dump()


def begin(root, phase, milestone=None):
    with transaction(root) as state:
        run = active(state)
        if run.phase != phase or (milestone is not None and milestone != run.milestone):
            raise ValueError("Phase/milestone is not the next permitted work item")
        if run.status not in {"pending", "paused", "blocked", "changes_requested"}:
            raise ValueError("Work is already running or awaiting approval")
        approved_inputs(root, run)
        integrity(root, run)
        if phase == "red" and not run.evidence.get("baseline"):
            raise ValueError("Configure CHECKS.json and run sdd check --baseline first")
        if phase == "red":
            evidence = run.evidence["baseline"]
            if evidence["snapshot"] != snapshot(root) or not evidence["passed"]:
                raise ValueError("Baseline is stale or failed; run it again before adding tests")
        if run.status == "pending" or not run.phase_snapshot:
            run.phase_snapshot = files(root)
        run.report = None
        run.submitted_snapshot = None
        run.status = "in_progress"
        event(state, "begin", phase=phase, milestone=run.milestone)


def validate_check_config(run, cfg):
    expected = {m.id for m in run.milestones}
    known = set(run.criteria)
    if not any(c.kind == "baseline" for c in cfg.checks):
        raise ValueError("A baseline check is required")
    for c in cfg.checks:
        if c.kind == "baseline":
            continue
        if not c.milestones or set(c.milestones) - expected:
            raise ValueError(f"Check {c.id}: invalid milestone assignment")
        if not c.criteria or set(c.criteria) - known:
            raise ValueError(f"Check {c.id}: invalid acceptance criteria mapping")
        if not c.junit or not c.red_failures or set(c.red_reasons) != set(c.red_failures):
            raise ValueError(f"Check {c.id}: JUnit and exact Red failures/reasons are required")
    for m in run.milestones:
        selected = [c for c in cfg.checks if m.id in c.milestones]
        if KINDS - {c.kind for c in selected}:
            raise ValueError(
                f"Milestone {m.id} requires unit, integration, acceptance and e2e checks"
            )
        for kind in ("acceptance", "e2e"):
            covered = {a for c in selected if c.kind == kind for a in c.criteria}
            if set(m.criteria) - covered:
                raise ValueError(
                    f"Milestone {m.id}: {kind} does not cover every acceptance criterion"
                )


def execute_check(root, run, check, red=False):
    result_dir = safe(root, ".workflow/results")
    result_dir.mkdir(exist_ok=True)
    report = None
    if check.junit:
        if not check.junit.startswith(".workflow/results/"):
            raise ValueError("JUnit reports must be inside .workflow/results/")
        report = safe(root, check.junit)
        report.parent.mkdir(parents=True, exist_ok=True)
        if report.exists():
            report.unlink()
    target = root if check.cwd == "." else safe(root, check.cwd)
    record = {"id": check.id, "kind": check.kind, "argv": check.argv, "passed": False}
    try:
        process = subprocess.run(
            check.argv, cwd=target, capture_output=True, text=True, timeout=check.timeout
        )
        record["exit_code"] = process.returncode
        record["passed"] = process.returncode == 0
        output = process.stdout + "\n" + process.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        output = str(exc)
        record["error"] = "infrastructure or timeout"
    log = f".workflow/results/{run.id}-{uuid4().hex}-{check.id}.log"
    safe(root, log).write_text(output)
    record["log"] = log
    if report:
        try:
            tree = ET.parse(report)
            cases = list(tree.iter("testcase"))
            failure_nodes = {
                f"{c.get('classname', '')}.{c.get('name', '')}": c.find("failure")
                for c in cases
                if c.find("failure") is not None
            }
            failures = set(failure_nodes)
            errors = any(c.find("error") is not None for c in cases)
            skipped = any(c.find("skipped") is not None for c in cases)
            record.update(
                cases=len(cases), failures=sorted(failures), errors=errors, skipped=skipped
            )
            if red:
                record["passed"] = (
                    record.get("exit_code") == 1
                    and bool(check.red_failures)
                    and failures == set(check.red_failures)
                    and all(
                        reason.strip()
                        and reason
                        in (
                            failure_nodes[name].get("message", "")
                            + " "
                            + (failure_nodes[name].text or "")
                        )
                        for name, reason in check.red_reasons.items()
                    )
                    and not errors
                    and not skipped
                )
            else:
                record["passed"] = (
                    record["passed"] and bool(cases) and not failures and not errors and not skipped
                )
        except (OSError, ET.ParseError):
            record["passed"] = False
            record["error"] = "Missing or invalid JUnit evidence"
    elif red or check.kind in {"acceptance", "e2e"}:
        record["passed"] = False
        record["error"] = "Red, acceptance and E2E checks require JUnit evidence"
    return record


def check(root, baseline=False):
    with transaction(root) as state:
        run = active(state)
        if baseline:
            if run.phase != "red" or run.status not in {"pending", "blocked", "paused"}:
                raise ValueError("Baseline must run before Red edits")
        elif run.phase not in {"red", "build", "close"}:
            raise ValueError("This phase has no executable checks")
        approved_inputs(root, run)
        integrity(root, run)
        cfg = checks(root, run)
        validate_check_config(run, cfg)
        before = snapshot(root)
        selected = (
            [c for c in cfg.checks if c.kind == "baseline"]
            if baseline
            else [
                c
                for c in cfg.checks
                if c.kind == "baseline"
                or run.phase in {"red", "close"}
                or any(m <= run.milestone for m in c.milestones)
            ]
        )
        results = [
            execute_check(
                root, run, c, red=run.phase == "red" and not baseline and c.kind != "baseline"
            )
            for c in selected
        ]
        after = snapshot(root)
        key = "baseline" if baseline else f"{run.phase}:{run.milestone}"
        evidence = {
            "snapshot": after,
            "checks_hash": digest(cfg.model_dump()),
            "results": results,
            "passed": before == after and all(r["passed"] for r in results),
        }
        if run.frozen and protected(root, run) != run.frozen:
            evidence["passed"] = False
        run.evidence[key] = evidence
        event(state, "check", key=key, passed=evidence["passed"])
        return evidence


def expected_reviews(run):
    return {
        "spec": {"architecture"},
        "roadmap": {"plan"},
        "red": {"asserts"} if run.mode == "supervised" else set(),
        "build": set(),
        "close": {"code", "security"},
    }[run.phase]


def submit(root, report: Report):
    with transaction(root) as state:
        run = active(state)
        if run.status != "in_progress":
            raise ValueError("Begin work before submitting")
        if report.blocked:
            run.status = "blocked"
            run.report = report
            event(state, "blocked", summary=report.summary)
            return
        approved_inputs(root, run)
        integrity(root, run)
        current = snapshot(root)
        current_files = files(root)
        changed = {
            p
            for p in set(current_files) | set(run.phase_snapshot)
            if current_files.get(p) != run.phase_snapshot.get(p)
        }
        if run.phase in {"spec", "roadmap"} and any(not p.endswith(".md") for p in changed):
            raise ValueError("Design phases cannot change implementation files")
        if run.phase == "red":
            cfg = checks(root, run)

            def allowed(p):
                return (
                    p.endswith(".md")
                    or p == f"{folder(run)}/CHECKS.json"
                    or any(
                        fnmatch.fnmatch(p, pattern) or Path(p).match(pattern)
                        for pattern in cfg.protected
                    )
                )

            if any(not allowed(p) for p in changed):
                raise ValueError("Red cannot change production implementation")
        required = expected_reviews(run)
        valid = {
            r.role
            for r in report.reviews
            if r.decision == "approve" and r.snapshot == current and r.worker != report.author
        }
        if required - valid:
            raise ValueError(f"Missing current independent reviews: {sorted(required - valid)}")
        workers = [r.worker for r in report.reviews if r.role in required]
        if len(workers) != len(set(workers)):
            raise ValueError("Reviewers must be independent workers")
        for name in artifact_paths(root, run):
            if not safe(root, name).is_file() or not safe(root, name).read_text().strip():
                raise ValueError(f"Missing deliverable: {name}")
        if run.phase == "spec":
            if not report.criteria or len(report.criteria) != len(set(report.criteria)):
                raise ValueError("Spec needs unique acceptance criterion ids")
            if not safe(root, "FEATURE-MAP.md").is_file():
                raise ValueError("FEATURE-MAP.md is required")
            run.criteria = report.criteria
        if run.phase == "roadmap":
            milestones = report.milestones
            if [m.id for m in milestones] != list(range(1, len(milestones) + 1)) or not milestones:
                raise ValueError("Milestones must be numbered consecutively from 1")
            if {c for m in milestones for c in m.criteria} != set(run.criteria):
                raise ValueError("Milestones must cover exactly the spec criteria")
            run.milestones = milestones
        if run.phase in {"red", "build", "close"}:
            ev = run.evidence.get(f"{run.phase}:{run.milestone}", {})
            if not ev.get("passed") or ev.get("snapshot") != current:
                raise ValueError(
                    "Run checks successfully against the current files before submitting"
                )
        if run.phase == "close":
            for name in ("FEATURE-MAP.md", "AGENTS.md"):
                if not safe(root, name).is_file():
                    raise ValueError(f"Close requires {name}")
        run.report = report
        run.submitted_snapshot = current
        run.status = "awaiting_review"
        event(state, "submit", phase=run.phase, milestone=run.milestone)


def commit(root, state, run):
    current = files(root)
    names = [
        n
        for n in set(current) | set(run.phase_snapshot)
        if current.get(n) != run.phase_snapshot.get(n)
    ]
    # First build includes the approved spec, plan and tests produced before implementation.
    if run.phase == "build" and run.milestone == 1:
        raw = git(root, "status", "--porcelain", "-z")
        if raw:
            names = sorted(set(current) | set(run.phase_snapshot))
            names = [n for n in names if git(root, "status", "--porcelain", "--", n)]
    key = f"{run.phase}:{run.milestone}"
    if (
        key in run.commits
        and git(root, "rev-parse", "HEAD") == run.commits[key]
        and not git(root, "status", "--porcelain")
    ):
        return
    if not names:
        raise ValueError("No changes to commit for this milestone")
    staged = git(root, "diff", "--cached", "--name-only", "-z").split("\0")
    if set(staged) - {""} - set(names):
        raise ValueError("Unrelated staged files; unstage them before approving")
    previous = git(root, "rev-parse", "HEAD")
    message = f"feat({run.slug}): {key}\n\nSDD-Run: {run.id}\nSDD-Step: {key}"
    run.pending_commit = {
        "parent": previous,
        "key": key,
        "message": message,
        "snapshot": snapshot(root),
        "paths": sorted(names),
    }
    write(root, state)  # Recovery journal before the Git side effect.
    git(root, "add", "-A", "--", *sorted(names))
    git(root, "commit", "-m", message)
    run.commits[key] = git(root, "rev-parse", "HEAD")
    run.pending_commit = None


def approve(root, response: str, delegated=False):
    if not response.strip():
        raise ValueError("Approval requires the explicit Human response or delegated rationale")
    with transaction(root) as state:
        run = active(state)
        if run.status != "awaiting_review":
            raise ValueError("No concrete result awaits approval")
        if delegated and (run.mode != "supervised" or run.phase == "close"):
            raise ValueError("This result requires Human approval")
        if run.pending_commit:
            raise ValueError("Recover the interrupted commit before approving")
        approved_inputs(root, run)
        integrity(root, run)
        if run.submitted_snapshot != snapshot(root):
            raise ValueError("Submitted files changed; request changes and resubmit")
        if run.phase in {"red", "build", "close"}:
            ev = run.evidence.get(f"{run.phase}:{run.milestone}", {})
            if not ev.get("passed") or ev.get("snapshot") != run.submitted_snapshot:
                raise ValueError(
                    "The latest verification failed or is stale; rerun checks and submit"
                )
        key = f"build:{run.milestone}" if run.phase == "build" else run.phase
        approval = {
            "by": "delegated" if delegated else "human",
            "response": response,
            "snapshot": run.submitted_snapshot,
            "artifacts": {
                p: hashlib.sha256(safe(root, p).read_bytes()).hexdigest()
                for p in artifact_paths(root, run)
            },
        }
        if run.phase == "build":
            commit(root, state, run)
        if run.phase == "red":
            run.frozen = protected(root, run)
        run.approvals[key] = approval
        event(state, "approve", phase=run.phase, milestone=run.milestone, by=approval["by"])
        if run.phase == "close":
            if run.feature_id:
                product_valid(root, state)
                for f in state.product.get("features", []):
                    if f["id"] == run.feature_id:
                        f["status"] = "complete"
                render_product(root, state)
            if git(root, "status", "--porcelain"):
                commit(root, state, run)
            run.status = "complete"
            return
        if run.phase == "build" and run.milestone < len(run.milestones):
            run.milestone += 1
        else:
            run.phase = PHASES[PHASES.index(run.phase) + 1]
        run.status = "pending"
        run.report = None
        run.submitted_snapshot = None


def recover(root):
    with transaction(root) as state:
        run = active(state)
        pending = run.pending_commit
        if not pending:
            return {"recovered": False}
        head = git(root, "rev-parse", "HEAD")
        if snapshot(root) != pending["snapshot"]:
            raise ValueError("Files changed after interrupted commit; inspect before recovering")
        if head != pending["parent"]:
            if (
                git(root, "rev-parse", "HEAD^") != pending["parent"]
                or git(root, "log", "-1", "--format=%B") != pending["message"]
            ):
                raise ValueError("HEAD is not the journaled SDD commit")
            run.commits[pending["key"]] = head
        run.pending_commit = None
        event(state, "recover", commit=head)
        return {"recovered": True, "committed": head != pending["parent"]}


def pause(root, reason):
    with transaction(root) as state:
        run = active(state)
        run.status = "paused"
        event(state, "pause", reason=reason)


def reopen(root, phase, reason):
    if phase not in PHASES or not reason.strip():
        raise ValueError("A valid phase and explicit reason are required")
    with transaction(root) as state:
        run = active(state)
        if PHASES.index(phase) > PHASES.index(run.phase):
            raise ValueError("Cannot skip forward by reopening")
        for key in list(run.approvals):
            if PHASES.index(key.split(":")[0]) >= PHASES.index(phase):
                del run.approvals[key]
        if PHASES.index(phase) <= PHASES.index("red"):
            run.frozen = {}
        run.phase = phase
        run.status = "pending"
        run.evidence = {}
        run.report = None
        if phase in {"spec", "roadmap", "red"}:
            run.milestone = 1
        event(state, "reopen", phase=phase, reason=reason)


def render_product(root, state):
    product = state.product
    body = "# Feature implementation roadmap\n\n| Order | ID | Feature | Dependencies | Status | Rationale | Sources |\n| --- | --- | --- | --- | --- | --- | --- |\n"
    for i, f in enumerate(product["features"], 1):
        values = [
            str(i),
            f["id"],
            f["title"],
            ", ".join(f["depends_on"]),
            f["status"],
            f["rationale"],
            ", ".join(f["sources"]),
        ]
        body += "| " + " | ".join(v.replace("|", "\\|").replace("\n", " ") for v in values) + " |\n"
    safe(root, "feature-roadmap-implementation.md").write_text(body)
    product["document_hash"] = hashlib.sha256(body.encode()).hexdigest()


def source_hash(path: Path) -> str:
    """README assumptions are feature working notes, not changed product requirements."""
    data = path.read_bytes()
    if path.name.lower() in {"readme.md", "readme.mdown"}:
        text = data.decode("utf-8")
        text = re.sub(r"(?ms)^## Assumptions\s*\n.*?(?=^##? [^\n]+\s*$|\Z)", "", text)
        data = (text.rstrip() + "\n").encode()
    return hashlib.sha256(data).hexdigest()


def product_valid(root, state):
    product = state.product
    if not product.get("approved"):
        raise ValueError("Approve the product roadmap first")
    if (
        hashlib.sha256(safe(root, "feature-roadmap-implementation.md").read_bytes()).hexdigest()
        != product["document_hash"]
    ):
        raise ValueError("Product roadmap changed; submit and approve the new version")
    for name, expected in product["source_hashes"].items():
        if source_hash(safe(root, name)) != expected:
            raise ValueError(f"Product requirements changed: {name}; review the roadmap")


def product_submit(root, features: list[Feature], sources: list[str]):
    if not features:
        raise ValueError("Product roadmap must contain features")
    ids = [f.id for f in features]
    if len(set(ids)) != len(ids) or len({f.slug for f in features}) != len(features):
        raise ValueError("Feature ids and slugs must be unique")
    seen = set()
    for f in features:
        if set(f.depends_on) - seen:
            raise ValueError("Dependencies must precede their consumers (cycles are invalid)")
        seen.add(f.id)
    with transaction(root) as state:
        running = state.active if state.active and state.active.status != "complete" else None
        old = {f["id"]: f for f in state.product.get("features", [])}
        for f in features:
            if f.id in old:
                if f.slug != old[f.id]["slug"]:
                    raise ValueError("Existing feature IDs cannot change slug")
                f.status = old[f.id]["status"]
            elif f.status != "pending":
                raise ValueError("New features must be pending")
        if any(f["status"] == "complete" and f["id"] not in ids for f in old.values()):
            raise ValueError("Cannot discard completed features")
        if running:
            if not running.feature_id or running.feature_id not in ids:
                raise ValueError("Active feature must remain on the product roadmap")
            current = next(f for f in features if f.id == running.feature_id)
            if current.slug != running.slug:
                raise ValueError("Active feature slug cannot change")
            running.phase = "spec"
            running.milestone = 1
            running.status = "pending"
            running.approvals.clear()
            running.evidence.clear()
            running.frozen.clear()
            running.report = None
            running.submitted_snapshot = None
            running.phase_snapshot = {}
            running.commits.clear()
            event(state, "product_reconcile", feature=running.feature_id)
        hashes = {}
        for source in sources:
            path = safe(root, source)
            paths = sorted(path.rglob("*")) if path.is_dir() else [path]
            for p in paths:
                if p.is_file():
                    name = p.relative_to(root).as_posix()
                    safe(root, name)
                    hashes[name] = source_hash(p)
        if not hashes:
            raise ValueError("Provide requirement sources; interviews should produce backlog.md")
        state.product = {
            "features": [f.model_dump() for f in features],
            "source_hashes": hashes,
            "approved": False,
        }
        render_product(root, state)
        event(state, "product_submit")


def product_approve(root, response):
    if not response.strip():
        raise ValueError("Explicit Human approval is required")
    with transaction(root) as state:
        if not state.product:
            raise ValueError("No proposed roadmap")
        state.product["approved"] = True
        product_valid(root, state)
        state.product["approval_response"] = response
        event(state, "product_approve", response=response)


def next_product_feature(root):
    state = read(root)
    product_valid(root, state)
    entries = {f["id"]: f for f in state.product["features"]}
    for item in state.product["features"]:
        if item["status"] == "pending" and all(
            entries[dep]["status"] == "complete" for dep in item["depends_on"]
        ):
            return item
    if any(item["status"] == "pending" for item in state.product["features"]):
        raise ValueError("Pending features have unmet or inconsistent dependencies")
    return None
