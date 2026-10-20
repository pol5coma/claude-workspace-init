"""The local `spado ui` HTTP server: read-only JSON API and static app."""

import http.client
import json
import threading

import pytest

from spado.ui.demo import DemoSource
from spado.ui.server import make_server
from tests.helpers import REAL_CATALOG


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    static = tmp_path_factory.mktemp("static")
    (static / "index.html").write_text("<!doctype html><title>app</title>")
    (static / "assets").mkdir()
    (static / "assets" / "app.js").write_text("console.log(1)")
    source = DemoSource(REAL_CATALOG, step=0)
    server = make_server(source, 0, static)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1], source
    server.shutdown()
    server.server_close()


def request(port, path, method="GET", host=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    connection.putrequest(method, path, skip_host=True)
    connection.putheader("Host", host or f"127.0.0.1:{port}")
    connection.endheaders()
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response.status, response.getheader("Content-Type"), body


def get_json(port, path):
    status, content_type, body = request(port, path)
    assert status == 200, body
    assert content_type.startswith("application/json")
    return json.loads(body)


def test_every_endpoint_answers(served):
    port, source = served
    base = f"/api/runs/{source.run_id}"
    assert get_json(port, "/api/source") == {"label": "demo"}
    assert get_json(port, "/api/runs")[0]["id"] == source.run_id
    overview = get_json(port, base)
    assert overview["scope"] == {"kind": "phase", "id": "1"}
    assert overview["scope_subphases"] == ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6"]
    assert overview["workflow"]["subphases"]["1.1"]["owners"] == ["CEAO", "CPAO"]
    assert get_json(port, f"{base}/pulse")["event_count"] == len(source.events(source.run_id))
    assert len(get_json(port, f"{base}/organization")["tiers"]) == 4
    messages = get_json(port, f"{base}/messages")
    assert {m["source"] for m in messages["messages"]} == {"db", "transcript"}
    stamps = [m["timestamp"] for m in messages["messages"]]
    assert stamps == sorted(stamps)
    documents = get_json(port, f"{base}/documents")
    assert all("content" not in d for d in documents)
    official = next(d for d in documents if d["official"])
    assert "Unknowns" in get_json(port, f"{base}/documents/{official['id']}")["content"]
    assert get_json(port, f"{base}/db")["spado_events"] == len(source.events(source.run_id))
    for table in ("runs", "events", "actors", "embeddings"):
        assert isinstance(get_json(port, f"{base}/db/{table}"), list)


def test_responses_never_contain_credentials(served):
    port, source = served
    actors = get_json(port, f"/api/runs/{source.run_id}/db/actors")
    assert actors and all("token_hash" not in a for a in actors)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_writes_are_refused(served, method):
    port, _ = served
    status, _, _ = request(port, "/api/runs", method=method)
    assert status == 405


def test_foreign_host_header_is_rejected(served):
    port, _ = served
    status, _, _ = request(port, "/api/runs", host="evil.test")
    assert status == 403
    assert request(port, "/api/runs", host=f"localhost:{port}")[0] == 200


def test_unknown_run_and_route_are_404(served):
    port, source = served
    assert request(port, "/api/runs/nope")[0] == 404
    assert request(port, f"/api/runs/{source.run_id}/secrets")[0] == 404


def test_static_files_and_spa_fallback_stay_inside_the_bundle(served):
    port, _ = served
    status, content_type, body = request(port, "/assets/app.js")
    assert status == 200 and "javascript" in content_type
    for path in ("/", "/run/anything", "/../../etc/passwd", "/%2e%2e/%2e%2e/etc/passwd"):
        status, _, body = request(port, path)
        assert status == 200 and b"<title>app</title>" in body


def test_demo_reveals_events_progressively():
    source = DemoSource(REAL_CATALOG, step=3600)
    assert len(source.events(source.run_id)) == 1
    assert source.run(source.run_id).version == 0
    assert [a["level"] for a in source.actors(source.run_id)] == ["human"]
