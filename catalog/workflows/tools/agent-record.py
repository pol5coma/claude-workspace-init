"""Authenticated facade for agents to record work and read permitted workflow state.

Run with the Python environment containing SPADO. Credentials are read from
SPADO_ACTOR_TOKEN_FILE or SPADO_ACTOR_TOKEN; a role supplied in JSON is never identity.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from spado.runtime.commands import record_request, select_run, session
from spado.workflows.engine import authorize, status


def record(root: Path, run_id: str, request: dict) -> dict:
    return record_request(root, request, run_id)


def read_status(root: Path, run_id: str) -> dict:
    _, store, token = session(root)
    run, actor = store.load(token, select_run(store, token, run_id))
    authorize(run, actor, coordinator=True)
    return status(run)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["record", "status"])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--run", required=True)
    parser.add_argument("--request", type=Path)
    args = parser.parse_args()
    if args.operation == "record" and not args.request:
        parser.error("record requires --request")
    request = json.loads(args.request.read_text()) if args.request else None
    try:
        result = (
            record(args.root, args.run, request) if request else read_status(args.root, args.run)
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "persisted": False,
                    "status": "pending" if request else "unavailable",
                    "error_type": type(exc).__name__,
                    "event_id": request.get("event_id") if request else None,
                }
            )
        )
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
