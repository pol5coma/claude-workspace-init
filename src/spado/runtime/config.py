from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import Field

from spado.workflows.models import Mode, Model


class Embeddings(Model):
    backend: Literal["local", "external"]
    model: str = Field(min_length=1)
    endpoint: str = "https://api.openai.com/v1/embeddings"
    key_env: str = "SPADO_EMBEDDING_API_KEY"


class ProjectConfig(Model):
    schema_version: Literal[1] = 1
    project: str = Field(default_factory=lambda: str(uuid4()))
    hosts: list[Literal["claude", "codex"]] = Field(min_length=1)
    mode: Mode
    embeddings: Embeddings
    workflow: str = "spdlc"
    capabilities: list[str] = Field(default_factory=list)
    database_port: int = Field(default=55432, ge=1024, le=65535)


def load(root: Path) -> ProjectConfig:
    return ProjectConfig.model_validate_json((root / ".spado/project.json").read_text())


def dsn(root: Path, config: ProjectConfig) -> str:
    if os.environ.get("SPADO_DATABASE_URL"):
        return os.environ["SPADO_DATABASE_URL"]
    password = (root / ".spado/local/database.password").read_text().strip()
    from psycopg.conninfo import make_conninfo

    return make_conninfo(
        host="127.0.0.1", port=config.database_port, dbname="spado", user="spado", password=password
    )


def actor_token(root: Path, *, human=False) -> str:
    if human:
        return (root / ".spado/local/human.token").read_text().strip()
    token = os.environ.get("SPADO_ACTOR_TOKEN")
    token_file = os.environ.get("SPADO_ACTOR_TOKEN_FILE")
    if token_file and not token:
        token = Path(token_file).read_text().strip()
    if not token:
        raise PermissionError(
            "Set SPADO_ACTOR_TOKEN_FILE for the assigned agent, or use --human for a direct Human action"
        )
    return token


def default_catalog() -> Path:
    bundled = Path(__file__).resolve().parents[1] / "bundled_catalog"
    if bundled.is_dir():
        return bundled
    return Path(__file__).resolve().parents[3] / "catalog"


def dump(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"
