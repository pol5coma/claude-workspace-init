"""All state access goes through StateRepository (schema checks, future migrations)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from cwi import paths
from cwi.domain.errors import StateError
from cwi.domain.models import SUPPORTED_STATE_SCHEMA, CWIState


class StateRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    @property
    def path(self) -> Path:
        return self.root / paths.rel(paths.STATE_FILE)

    @property
    def legacy_path(self) -> Path:
        return self.root / paths.rel(paths.LEGACY_STATE_FILE)

    def exists(self) -> bool:
        return self.path.is_file() or self.legacy_path.is_file()

    def load(self) -> CWIState | None:
        path = (
            self.path
            if self.path.is_file()
            else self.legacy_path
            if self.legacy_path.is_file()
            else None
        )
        if path is None:
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f"Cannot read CWI state {path}: {exc}") from exc
        version = data.get("schema_version") if isinstance(data, dict) else None
        if version != SUPPORTED_STATE_SCHEMA:
            raise StateError(
                f"Unsupported CWI state schema version: {version} ({path}).\n"
                f"This CWI version supports state schema {SUPPORTED_STATE_SCHEMA}. Upgrade CWI before continuing."
            )
        try:
            return CWIState.model_validate(data)
        except PydanticValidationError as exc:
            raise StateError(f"Invalid CWI state {path}: {exc.errors()[0]['msg']}") from exc

    @staticmethod
    def serialize(state: CWIState) -> str:
        data = state.model_dump(mode="json", exclude_none=True)
        return json.dumps(data, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
