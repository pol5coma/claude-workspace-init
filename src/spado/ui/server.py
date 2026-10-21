"""Local read-only HTTP server for `spado ui`: a JSON API plus the compiled React app."""

from __future__ import annotations

import json
import logging
import mimetypes
import re
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from spado.ui.communication import messages
from spado.ui.organization import organization
from spado.ui.source import DataSource
from spado.workflows.engine import main_phase, review, status
from spado.workflows.models import Run

log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"
_RUN = re.compile(r"^/api/runs/([^/]+)(/.*)?$")


def _when(value) -> datetime:
    if not value:
        return datetime.max.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.max.replace(tzinfo=UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _workflow(run: Run) -> dict:
    return {
        "id": run.workflow.id,
        "version": run.workflow.version,
        "title": run.workflow.title,
        "phases": [
            {
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "lifecycle": p.lifecycle,
                "subphases": p.subphases,
            }
            for p in run.workflow.phases
        ],
        "subphases": {
            sid: {
                "id": sid,
                "title": s.title,
                "slug": s.slug,
                "phase": s.phase,
                "owners": s.owners,
                "specialists": s.specialists,
                "dependencies": s.dependencies,
                "deliverable": s.deliverable,
                "exit_criteria": s.exit_criteria,
                "applicability": s.applicability,
            }
            for sid, s in run.workflow.subphases.items()
        },
    }


class Api:
    """Route GET requests to read-only views of a DataSource."""

    def __init__(self, source: DataSource):
        self.source = source

    def get(self, path: str):
        if path == "/api/source":
            return {"label": self.source.label}
        if path == "/api/runs":
            return self.source.runs()
        match = _RUN.match(path)
        if not match:
            raise LookupError(path)
        run_id, rest = match.group(1), match.group(2) or ""
        if rest == "/pulse":
            return self.source.pulse(run_id)
        run = self.source.run(run_id)
        if rest == "":
            return {
                "id": run.id,
                "objective": run.objective,
                "scope": run.scope.model_dump(),
                "mode": run.mode,
                "version": run.version,
                "created_at": run.created_at,
                "updated_at": run.updated_at,
                "main_phase": main_phase(run),
                "scope_subphases": run.workflow.select(run.scope),
                "workflow": _workflow(run),
                "status": status(run),
                "review": review(run, run.scope),
                "phase_plans": {k: v.model_dump(mode="json") for k, v in run.phase_plans.items()},
                "phase_reviews": run.phase_reviews,
            }
        if rest == "/organization":
            return organization(run, self.source.actors(run_id), self.source.events(run_id))
        if rest == "/messages":
            actors = self.source.actors(run_id)
            transcript = self.source.transcripts(run_id, actors)
            merged = messages(run, actors, self.source.events(run_id)) + transcript["entries"]
            merged.sort(key=lambda m: _when(m.get("timestamp")))
            return {
                "messages": merged,
                "actors": actors,
                "transcripts": {
                    "available": transcript["available"],
                    "folder": transcript.get("folder"),
                    "sessions": transcript.get("sessions", []),
                },
                "threads": transcript.get("threads", []),
            }
        if rest == "/documents":
            official = set(run.official.values())
            return [
                {k: v for k, v in r.model_dump(mode="json").items() if k != "content"}
                | {"official": r.id in official, "size": len(r.content)}
                for r in sorted(run.revisions.values(), key=lambda r: r.sequence)
            ]
        if rest.startswith("/documents/"):
            revision = run.revisions.get(rest.removeprefix("/documents/"))
            if not revision:
                raise LookupError(rest)
            return revision.model_dump(mode="json") | {
                "official": run.official.get(revision.path) == revision.id
            }
        if rest == "/db":
            return {
                "spado_runs": 1,
                "spado_events": len(self.source.events(run_id)),
                "spado_actors": len(self.source.actors(run_id)),
                "spado_embeddings": sum(e["chunks"] for e in self.source.embeddings(run_id)),
            }
        if rest == "/db/runs":
            return [run.model_dump(mode="json")]
        if rest == "/db/events":
            return self.source.events(run_id)
        if rest == "/db/actors":
            return self.source.actors(run_id)
        if rest == "/db/embeddings":
            return self.source.embeddings(run_id)
        raise LookupError(path)


def make_server(source: DataSource, port: int = 8765, static_dir: Path = STATIC_DIR):
    api = Api(source)

    class Handler(BaseHTTPRequestHandler):
        server_version = "spado-ui"

        def log_message(self, format, *args):  # noqa: A002 - BaseHTTPRequestHandler signature
            log.debug("%s %s", self.address_string(), format % args)

        def _allowed_host(self) -> bool:
            port_now = self.server.server_address[1]
            return self.headers.get("Host", "") in {
                f"127.0.0.1:{port_now}",
                f"localhost:{port_now}",
            }

        def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: HTTPStatus, value) -> None:
            body = json.dumps(value, ensure_ascii=False, default=str).encode()
            self._send(status, body, "application/json; charset=utf-8")

        def do_GET(self):  # noqa: N802 - http.server naming
            if not self._allowed_host():
                return self._json(HTTPStatus.FORBIDDEN, {"error": "Unexpected Host header"})
            path = unquote(urlparse(self.path).path)
            if path.startswith("/api/"):
                try:
                    return self._json(HTTPStatus.OK, api.get(path))
                except LookupError:
                    return self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                except PermissionError as exc:
                    return self._json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
                except ValueError as exc:
                    return self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
                except Exception:  # never leak connection strings or credentials
                    log.exception("spado ui request failed: %s", path)
                    return self._json(
                        HTTPStatus.SERVICE_UNAVAILABLE,
                        {"error": "Could not read SPADO state; check `spado db up`"},
                    )
            return self._static(path)

        def _static(self, path: str) -> None:
            root = static_dir.resolve()
            index = root / "index.html"
            if not index.is_file():
                return self._send(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    b"spado ui: the web app is not built. Run: npm --prefix ui ci && npm --prefix ui run build",
                    "text/plain; charset=utf-8",
                )
            target = (root / path.lstrip("/")).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                target = index
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            return self._send(HTTPStatus.OK, target.read_bytes(), content_type)

        def _refuse(self):
            self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "spado ui is read-only"})

        do_POST = do_PUT = do_PATCH = do_DELETE = _refuse  # noqa: N815

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
