"""Atomic project-scoped persistence. All agent mutations pass through domain policies."""

from __future__ import annotations

import hashlib
import json
import secrets
from contextlib import contextmanager
from importlib.resources import files

import psycopg
from psycopg.types.json import Jsonb

from spado.workflows.engine import apply, authorize
from spado.workflows.models import Actor, Event, Run, now


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Store:
    def __init__(self, dsn: str, project: str):
        self.dsn, self.project = dsn, project

    @contextmanager
    def connection(self, *, readonly=False):
        with psycopg.connect(self.dsn, connect_timeout=5) as conn:
            if readonly:
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            yield conn

    def migrate(self):
        with self.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(773021)")
            exists = conn.execute("SELECT to_regclass('spado_schema')").fetchone()[0]
            if exists and conn.execute("SELECT max(version) FROM spado_schema").fetchone()[0] != 1:
                raise ValueError("Unsupported database schema; upgrade SPADO")
            conn.execute(files("spado.runtime").joinpath("schema.sql").read_text())

    def bootstrap(self) -> tuple[Actor, str]:
        with self.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (self.project,))
            if conn.execute(
                "SELECT 1 FROM spado_actors WHERE project=%s AND data->>'level'='human'",
                (self.project,),
            ).fetchone():
                raise ValueError("Human identity already exists; use the existing local credential")
            actor = Actor(project=self.project, definition="Human", level="human")
            token = secrets.token_urlsafe(32)
            self._insert_actor(conn, actor, token)
            return actor, token

    def _insert_actor(self, conn, actor, token):
        conn.execute(
            "INSERT INTO spado_actors VALUES (%s,%s,%s,%s)",
            (actor.id, self.project, token_hash(token), Jsonb(actor.model_dump())),
        )

    def _actor(self, conn, token: str) -> Actor:
        row = conn.execute(
            "SELECT data FROM spado_actors WHERE project=%s AND token_hash=%s",
            (self.project, token_hash(token)),
        ).fetchone()
        if not row:
            raise PermissionError("Missing or invalid SPADO actor credential")
        return Actor.model_validate(row[0])

    def _run(self, conn, run_id: str, *, lock=False) -> Run:
        suffix = " FOR UPDATE" if lock else ""
        row = conn.execute(
            "SELECT data FROM spado_runs WHERE project=%s AND id=%s" + suffix,
            (self.project, run_id),
        ).fetchone()
        if not row:
            raise ValueError("Execution not found in this project")
        return Run.model_validate(row[0])

    def load(self, token: str, run_id: str) -> tuple[Run, Actor]:
        with self.connection(readonly=True) as conn:
            actor = self._actor(conn, token)
            run = self._run(conn, run_id)
            if actor.run_id and actor.run_id != run.id:
                raise PermissionError("Actor is delegated to another execution")
            return run, actor

    def list_runs(self, token: str) -> list[dict]:
        with self.connection(readonly=True) as conn:
            actor = self._actor(conn, token)
            rows = conn.execute(
                "SELECT data FROM spado_runs WHERE project=%s ORDER BY data->>'created_at'",
                (self.project,),
            ).fetchall()
            return [
                {
                    "id": r[0]["id"],
                    "workflow": r[0]["workflow"]["id"],
                    "scope": r[0]["scope"],
                    "updated_at": r[0]["updated_at"],
                }
                for r in rows
                if not actor.run_id or actor.run_id == r[0]["id"]
            ]

    def create_run(self, token: str, run: Run):
        with self.connection() as conn:
            actor = self._actor(conn, token)
            authorize(run, actor, coordinator=True)
            conn.execute(
                "INSERT INTO spado_runs VALUES (%s,%s,%s,%s)",
                (run.id, self.project, run.version, Jsonb(run.model_dump(mode="json"))),
            )
            event = Event(
                kind="run_created",
                actor=actor.id,
                run_id=run.id,
                rationale=run.objective,
                payload={"scope": run.scope.model_dump(), "workflow_version": run.workflow.version},
            )
            conn.execute(
                "INSERT INTO spado_events(id,project,run_id,actor_id,kind,request,result) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (
                    event.id,
                    self.project,
                    run.id,
                    actor.id,
                    event.kind,
                    Jsonb(event.model_dump()),
                    Jsonb({"run": run.id}),
                ),
            )
        return run.id

    def delegate(self, token: str, run_id: str, definition: str) -> tuple[Actor, str]:
        with self.connection() as conn:
            parent = self._actor(conn, token)
            run = self._run(conn, run_id, lock=True)
            if parent.run_id and parent.run_id != run_id:
                raise PermissionError("Delegation outside assigned run")
            template = run.organization.agents[definition]
            if parent.level == "specialist":
                raise PermissionError(
                    "Specialists request supporting assignments through their lead"
                )
            if template.level == "orchestrator" and parent.level != "human":
                raise PermissionError("Only the Human delegates to CAOAO")
            if parent.level == "officer" and (
                template.level != "specialist"
                or not set(template.subphases).issubset(parent.subphases)
            ):
                raise PermissionError("Officer delegation exceeds its domain")
            actor = Actor(
                project=self.project,
                definition=definition,
                level=template.level,
                run_id=run_id,
                subphases=template.subphases,
                parent_id=parent.id,
            )
            token = secrets.token_urlsafe(32)
            self._insert_actor(conn, actor, token)
            event = Event(
                kind="delegation",
                actor=parent.id,
                run_id=run_id,
                rationale=template.mandate,
                payload=actor.model_dump(),
            )
            conn.execute(
                "INSERT INTO spado_events(id,project,run_id,actor_id,kind,request,result) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (
                    event.id,
                    self.project,
                    run_id,
                    parent.id,
                    event.kind,
                    Jsonb(event.model_dump()),
                    Jsonb({"actor": actor.id}),
                ),
            )
            return actor, token

    def record(
        self,
        token: str,
        run_id: str,
        kind: str,
        payload: dict,
        rationale: str,
        event_id: str,
        expected_version: int | None = None,
    ) -> dict:
        if not rationale.strip():
            raise ValueError("Every event requires an evidence-based rationale")
        with self.connection() as conn:
            actor = self._actor(conn, token)
            run = self._run(conn, run_id, lock=True)
            if actor.run_id and actor.run_id != run_id:
                raise PermissionError("Actor is delegated to another run")
            request = {"kind": kind, "payload": payload, "rationale": rationale}
            previous = conn.execute(
                "SELECT actor_id,run_id,request,result FROM spado_events WHERE project=%s AND id=%s",
                (self.project, event_id),
            ).fetchone()
            if previous:
                if previous[:3] != (actor.id, run_id, request):
                    raise ValueError("Event ID reused with different content or identity")
                return previous[3]
            if expected_version is not None and run.version != expected_version:
                raise ValueError("Execution changed; refresh context before retrying")
            if kind == "prepare":
                owner_row = conn.execute(
                    "SELECT data FROM spado_actors WHERE project=%s AND id=%s",
                    (self.project, payload["owner"]),
                ).fetchone()
                if not owner_row:
                    raise ValueError("Activity owner must be a registered actor")
                owner = Actor.model_validate(owner_row[0])
                if owner.level != "specialist":
                    raise PermissionError("Activity owner must be a delegated specialist")
                if owner.run_id != run.id or payload["subphase"] not in owner.subphases:
                    raise PermissionError("Owner is not assigned to that subphase/run")
            result = apply(run, actor, kind, payload)
            run.version += 1
            run.updated_at = now()
            result["run_version"] = run.version
            conn.execute(
                "UPDATE spado_runs SET version=%s,data=%s WHERE project=%s AND id=%s",
                (run.version, Jsonb(run.model_dump(mode="json")), self.project, run.id),
            )
            conn.execute(
                "INSERT INTO spado_events(id,project,run_id,actor_id,kind,request,result) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (event_id, self.project, run_id, actor.id, kind, Jsonb(request), Jsonb(result)),
            )
            return json.loads(json.dumps(result))

    def events(self, token: str, run_id: str) -> list[dict]:
        with self.connection(readonly=True) as conn:
            actor = self._actor(conn, token)
            run = self._run(conn, run_id)
            authorize(run, actor, coordinator=True)
            return [
                r[0]
                for r in conn.execute(
                    "SELECT jsonb_build_object('id',id,'actor',actor_id,'timestamp',created_at,'request',request,'result',result) FROM spado_events WHERE project=%s AND run_id=%s ORDER BY created_at,id",
                    (self.project, run_id),
                ).fetchall()
            ]
