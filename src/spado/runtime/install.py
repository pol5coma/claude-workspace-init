from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

from spado.adapters.hosts import render
from spado.install.filesystem import FileSystem
from spado.runtime.config import ProjectConfig, dump
from spado.workflows.catalog import load_workflow


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resources(catalog: Path, config: ProjectConfig) -> dict[str, bytes]:
    workflow, organization = load_workflow(catalog, config.workflow)
    output = {}
    for host in config.hosts:
        output.update(render(catalog, host, config.workflow))
    for folder in [
        catalog / "workflows" / config.workflow,
        catalog / "organizations" / organization.id,
    ]:
        for source in folder.rglob("*"):
            if source.is_file():
                output[f".spado/catalog/{source.relative_to(catalog).as_posix()}"] = (
                    source.read_bytes()
                )
    for agent in organization.agents.values():
        for skill in agent.skills:
            for source in (catalog / "organization-skills" / skill).rglob("*"):
                if source.is_file():
                    output[f".spado/catalog/{source.relative_to(catalog).as_posix()}"] = (
                        source.read_bytes()
                    )
    from importlib.resources import files

    output[".spado/protocol.md"] = files("spado.runtime").joinpath("protocol.md").read_bytes()
    output[".spado/tools/agent-record.py"] = (
        catalog / "workflows/tools/agent-record.py"
    ).read_bytes()
    output[".spado/project.json"] = dump(config.model_dump(mode="json")).encode()
    compose = f"""name: spado-{config.project[:8]}
services:
  database:
    image: pgvector/pgvector:0.8.2-pg17
    environment:
      POSTGRES_USER: spado
      POSTGRES_DB: spado
      POSTGRES_PASSWORD_FILE: /run/secrets/database_password
    ports:
      - "127.0.0.1:{config.database_port}:5432"
    secrets:
      - database_password
    volumes:
      - database:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U spado -d spado"]
      interval: 2s
      timeout: 3s
      retries: 30
secrets:
  database_password:
    file: database.password
volumes:
  database:
"""
    output[".spado/local/compose.yaml"] = compose.encode()
    return output


def install(
    root: Path,
    desired: dict[str, bytes],
    *,
    dry_run=False,
    merge_preconditions: dict[str, str] | None = None,
) -> dict:
    """Preflight all collisions, atomic file replacement, rollback on any failure."""
    fs = FileSystem(root)
    state_path = fs.path(".spado/installation.json")
    owned = json.loads(state_path.read_text()).get("files", {}) if state_path.exists() else {}
    changes, conflicts = {}, []
    for relative, content in desired.items():
        path = fs.path(relative)
        existing = path.read_bytes() if path.exists() else None
        if existing == content:
            continue
        if (
            existing is not None
            and owned.get(relative) != sha(existing)
            and (merge_preconditions or {}).get(relative) != sha(existing)
        ):
            conflicts.append(relative)
        else:
            changes[relative] = content
    if conflicts:
        raise ValueError("User files or edits conflict with installation: " + ", ".join(conflicts))
    preview = {"writes": sorted(changes), "unchanged": len(desired) - len(changes)}
    password = fs.path(".spado/local/database.password")
    if ".spado/local/compose.yaml" in desired and not password.exists():
        changes[".spado/local/database.password"] = secrets.token_urlsafe(32).encode()
    ignore = fs.path(".spado/.gitignore")
    if not ignore.exists():
        changes[".spado/.gitignore"] = b"local/\nbackups/\n"
    new_owned = dict(owned)
    new_owned.update({name: sha(content) for name, content in desired.items()})
    state = dump({"schema_version": 1, "files": new_owned}).encode()
    if not state_path.exists() or state_path.read_bytes() != state:
        changes[".spado/installation.json"] = state
    preview["writes"] = sorted(changes)
    if dry_run:
        return preview
    backups, created_dirs = {}, []
    try:
        for relative, content in changes.items():
            path = fs.path(relative)
            if (
                merge_preconditions
                and relative in merge_preconditions
                and (not path.exists() or sha(path.read_bytes()) != merge_preconditions[relative])
            ):
                raise ValueError(f"Configuration changed after planning: {relative}")
            backups[relative] = path.read_bytes() if path.exists() else None
            parents = []
            parent = path.parent
            while not parent.exists():
                parents.append(parent)
                parent = parent.parent
            for directory in reversed(parents):
                directory.mkdir(mode=0o700 if "local" in directory.parts else 0o755)
                created_dirs.append(directory)
            fs.atomic_write_bytes(relative, content)
            if "/local/" in relative:
                os.chmod(path, 0o600)
    except Exception:
        for relative, previous in reversed(list(backups.items())):
            path = fs.path(relative)
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                fs.atomic_write_bytes(relative, previous)
        for directory in reversed(created_dirs):
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
        raise
    return preview
