from __future__ import annotations

import hashlib
import json
import subprocess
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from spado.install.filesystem import FileSystem
from spado.runtime.config import dump
from spado.sdd.models import State


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Git operation failed")
    return result.stdout.strip()


def safe(root: Path, relative: str) -> Path:
    return FileSystem(root).path(relative)


def files(root: Path) -> dict[str, str]:
    names = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    result = {}
    for name in sorted(set(names.split("\0")) - {""}):
        if name.startswith(".workflow/"):
            continue
        path = safe(root, name)
        if path.is_file():
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def snapshot(root: Path) -> str:
    return digest(files(root))


def read(root: Path) -> State:
    return State.model_validate_json(safe(root, ".workflow/state.json").read_text())


def write(root: Path, state: State):
    FileSystem(root).atomic_write_bytes(".workflow/state.json", dump(state.model_dump()).encode())


def event(state: State, kind: str, **details):
    state.events.append({"at": datetime.now(UTC).isoformat(), "kind": kind, **details})


@contextmanager
def lock(root: Path, name="state"):
    # flock releases after a crashed process; separate runner lock survives individual transitions.
    import fcntl

    path = safe(root, f".workflow/{name}.lock")
    with path.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError(f"SDD {name} is busy; retry after the current operation") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def transaction(root: Path):
    with lock(root):
        state = read(root)
        yield state
        state.revision += 1
        write(root, state)
