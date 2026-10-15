from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.parse
import urllib.request

from spado.runtime.config import Embeddings


class Embedder:
    def __init__(self, config: Embeddings):
        self.config = config
        self._local = None

    @property
    def identity(self):
        settings = [
            self.config.backend,
            self.config.model,
            self.config.endpoint if self.config.backend == "external" else "local",
        ]
        return hashlib.sha256(json.dumps(settings).encode()).hexdigest()

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.config.backend == "local":
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ValueError("Install spado[local-embeddings] to use local models") from exc
            if self._local is None:
                self._local = SentenceTransformer(self.config.model, trust_remote_code=False)
            vectors = self._local.encode(texts, normalize_embeddings=True).tolist()
        else:
            endpoint = urllib.parse.urlparse(self.config.endpoint)
            if endpoint.scheme != "https" and not (
                endpoint.scheme == "http" and endpoint.hostname in {"127.0.0.1", "localhost"}
            ):
                raise ValueError("Embedding endpoint must use HTTPS (or local HTTP)")
            key = os.environ.get(self.config.key_env)
            if not key:
                raise ValueError(f"Set {self.config.key_env} for the configured embedding provider")
            request = urllib.request.Request(
                self.config.endpoint,
                data=json.dumps({"model": self.config.model, "input": texts}).encode(),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.load(response)
            entries = sorted(body["data"], key=lambda item: item["index"])
            if [entry["index"] for entry in entries] != list(range(len(texts))):
                raise ValueError("Embedding response indices do not match input")
            vectors = [entry["embedding"] for entry in entries]
        if len(vectors) != len(texts) or not vectors or not vectors[0]:
            raise ValueError("Embedding provider returned an invalid batch")
        dimension = len(vectors[0])
        if any(
            len(v) != dimension or not all(math.isfinite(x) for x in v) or not any(v)
            for v in vectors
        ):
            raise ValueError(
                "Embedding vectors must have matching dimensions and finite nonzero values"
            )
        return vectors


def visible_revisions(run, actor):
    # General context is approved and shared. Drafts remain in assigned activity context,
    # and are deliberately not part of the official semantic index.
    return [run.revisions[rid] for rid in run.official.values() if run.revisions[rid].approved_by]


def index(store, token: str, run_id: str, embedder: Embedder) -> dict:
    run, actor = store.load(token, run_id)
    if actor.level not in {"human", "orchestrator"}:
        raise PermissionError("Only CAOAO consolidates the official semantic index")
    count = 0
    for revision in visible_revisions(run, actor):
        chunks = [revision.content[i : i + 800] for i in range(0, len(revision.content), 700)] or [
            " "
        ]
        vectors = embedder.encode(chunks)
        with store.connection() as conn:
            # Recheck identity and approval after an external model call.
            store._actor(conn, token)
            current = store._run(conn, run_id, lock=True)
            if current.official.get(revision.path) != revision.id:
                continue
            conn.execute(
                "DELETE FROM spado_embeddings WHERE project=%s AND run_id=%s AND revision_id=%s AND model=%s",
                (store.project, run_id, revision.id, embedder.identity),
            )
            for number, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                conn.execute(
                    "INSERT INTO spado_embeddings VALUES (%s,%s,%s,%s,%s,%s,%s::vector)",
                    (
                        store.project,
                        run_id,
                        revision.id,
                        number,
                        embedder.identity,
                        chunk,
                        json.dumps(vector),
                    ),
                )
                count += 1
    return {"indexed_chunks": count, "model": embedder.identity}


def search(store, token: str, run_id: str, embedder: Embedder, query: str, limit=5) -> dict:
    if not 1 <= limit <= 50:
        raise ValueError("Search limit must be between 1 and 50")
    run, actor = store.load(token, run_id)
    allowed = {r.id: r for r in visible_revisions(run, actor)}
    if not allowed:
        return {"results": [], "index_complete": True}
    vector = embedder.encode([query])[0]
    with store.connection(readonly=True) as conn:
        actor = store._actor(conn, token)
        current = store._run(conn, run_id)
        allowed = {r.id: r for r in visible_revisions(current, actor)}
        rows = conn.execute(
            "SELECT revision_id,chunk,content,embedding <=> %s::vector AS distance FROM spado_embeddings WHERE project=%s AND run_id=%s AND model=%s AND revision_id=ANY(%s) AND vector_dims(embedding)=%s ORDER BY distance LIMIT %s",
            (
                json.dumps(vector),
                store.project,
                run_id,
                embedder.identity,
                list(allowed),
                len(vector),
                limit,
            ),
        ).fetchall()
        indexed = conn.execute(
            "SELECT DISTINCT revision_id FROM spado_embeddings WHERE project=%s AND run_id=%s AND model=%s AND vector_dims(embedding)=%s",
            (store.project, run_id, embedder.identity, len(vector)),
        ).fetchall()
    return {
        "results": [
            {
                "revision": rid,
                "path": allowed[rid].path,
                "digest": allowed[rid].digest,
                "chunk": chunk,
                "content": content,
                "distance": distance,
                "approved": True,
            }
            for rid, chunk, content, distance in rows
        ],
        "index_complete": set(allowed).issubset({row[0] for row in indexed}),
    }
