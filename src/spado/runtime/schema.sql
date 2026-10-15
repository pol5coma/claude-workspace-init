CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS spado_schema (version integer PRIMARY KEY);
INSERT INTO spado_schema VALUES (1) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS spado_actors (
    id text PRIMARY KEY,
    project text NOT NULL,
    token_hash text NOT NULL UNIQUE,
    data jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS spado_runs (
    id text PRIMARY KEY,
    project text NOT NULL,
    version bigint NOT NULL,
    data jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS spado_events (
    id text PRIMARY KEY,
    project text NOT NULL,
    run_id text NOT NULL REFERENCES spado_runs(id),
    actor_id text NOT NULL REFERENCES spado_actors(id),
    kind text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    request jsonb NOT NULL,
    result jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS spado_event_run ON spado_events(project, run_id, created_at);
CREATE TABLE IF NOT EXISTS spado_embeddings (
    project text NOT NULL,
    run_id text NOT NULL REFERENCES spado_runs(id),
    revision_id text NOT NULL,
    chunk integer NOT NULL,
    model text NOT NULL,
    content text NOT NULL,
    embedding vector NOT NULL,
    PRIMARY KEY (project, run_id, revision_id, chunk, model)
);
