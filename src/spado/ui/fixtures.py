"""Write the demo run's API responses as JSON fixtures for the web app's tests.

Usage: python -m spado.ui.fixtures ui/src/test/fixtures
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from spado.runtime import config
from spado.ui.demo import DemoSource
from spado.ui.server import Api


def write(target: Path) -> None:
    source = DemoSource(config.default_catalog(), step=0)
    api = Api(source)
    base = f"/api/runs/{source.run_id}"
    documents = api.get(f"{base}/documents")
    responses = {
        "runs": api.get("/api/runs"),
        "overview": api.get(base),
        "organization": api.get(f"{base}/organization"),
        "messages": api.get(f"{base}/messages"),
        "documents": documents,
        "document": api.get(f"{base}/documents/{documents[-1]['id']}"),
        "db": api.get(f"{base}/db"),
        "events": api.get(f"{base}/db/events"),
        "actors": api.get(f"{base}/db/actors"),
    }
    target.mkdir(parents=True, exist_ok=True)
    for name, value in responses.items():
        text = json.dumps(value, ensure_ascii=False, indent=1, default=str) + "\n"
        (target / f"{name}.json").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    write(Path(sys.argv[1] if len(sys.argv) > 1 else "ui/src/test/fixtures"))
