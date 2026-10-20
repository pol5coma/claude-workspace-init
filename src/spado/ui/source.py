"""Read-only data sources for `spado ui`: the project's PostgreSQL state, or a demo run."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from spado.ui import transcripts
from spado.workflows.engine import authorize
from spado.workflows.models import Run


class DataSource(Protocol):
    label: str

    def runs(self) -> list[dict]: ...

    def run(self, run_id: str) -> Run: ...

    def events(self, run_id: str) -> list[dict]: ...

    def actors(self, run_id: str) -> list[dict]: ...

    def embeddings(self, run_id: str) -> list[dict]: ...

    def pulse(self, run_id: str) -> dict: ...

    def transcripts(self, run_id: str, actors: list[dict]) -> dict: ...


class PostgresSource:
    """The configured project's database, read with the local Human credential.

    The credential stays in this process; every query runs in a READ ONLY transaction.
    """

    def __init__(self, root: Path, transcript_dir: Path | None = None, use_transcripts=True):
        from spado.runtime import config
        from spado.runtime.store import Store

        root = root.resolve()
        cfg = config.load(root)
        self.label = str(root)
        self.store = Store(config.dsn(root, cfg), cfg.project)
        self._token = config.actor_token(root, human=True)
        self.transcript_dir = (
            (transcript_dir or transcripts.project_dir(root)) if use_transcripts else None
        )

    def runs(self) -> list[dict]:
        return self.store.list_runs(self._token)

    def run(self, run_id: str) -> Run:
        run, actor = self.store.load(self._token, run_id)
        authorize(run, actor, coordinator=True)
        return run

    def events(self, run_id: str) -> list[dict]:
        return self.store.events(self._token, run_id)

    def actors(self, run_id: str) -> list[dict]:
        return self.store.actors(self._token, run_id)

    def embeddings(self, run_id: str) -> list[dict]:
        return self.store.embedding_stats(self._token, run_id)

    def pulse(self, run_id: str) -> dict:
        return self.store.pulse(self._token, run_id) | {
            "transcripts": transcripts.signature(self.transcript_dir)
        }

    def transcripts(self, run_id: str, actors: list[dict]) -> dict:
        if self.transcript_dir is None:
            return {"available": False, "folder": None, "entries": [], "threads": []}
        return transcripts.read(self.transcript_dir, run_id, actors)
