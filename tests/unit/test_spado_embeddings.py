import io
import json
import sys
import types

import pytest

from spado.runtime.config import Embeddings
from spado.runtime.embeddings import Embedder


def test_external_embeddings_reorder_and_validate_batch(monkeypatch):
    import urllib.request

    monkeypatch.setenv("SPADO_EMBEDDING_API_KEY", "fixture-not-a-real-key")
    seen = []

    def request(req, timeout):
        seen.append(json.loads(req.data))
        return io.BytesIO(
            json.dumps(
                {
                    "data": [
                        {"index": 1, "embedding": [0.0, 1.0]},
                        {"index": 0, "embedding": [1.0, 0.0]},
                    ]
                }
            ).encode()
        )

    monkeypatch.setattr(urllib.request, "urlopen", request)
    encoder = Embedder(Embeddings(backend="external", model="chosen-model"))
    assert encoder.encode(["one", "two"]) == [[1.0, 0.0], [0.0, 1.0]]
    assert seen == [{"model": "chosen-model", "input": ["one", "two"]}]


def test_local_embeddings_load_once_and_disable_remote_code(monkeypatch):
    calls = []

    class Model:
        def __init__(self, model, trust_remote_code):
            calls.append((model, trust_remote_code))

        def encode(self, texts, normalize_embeddings):
            assert normalize_embeddings
            return types.SimpleNamespace(tolist=lambda: [[1.0, 0.5] for _ in texts])

    monkeypatch.setitem(
        sys.modules, "sentence_transformers", types.SimpleNamespace(SentenceTransformer=Model)
    )
    encoder = Embedder(Embeddings(backend="local", model="local-model"))
    encoder.encode(["one"])
    encoder.encode(["two"])
    assert calls == [("local-model", False)]


def test_provider_rejects_missing_key_and_plaintext_remote_endpoint(monkeypatch):
    monkeypatch.delenv("SPADO_EMBEDDING_API_KEY", raising=False)
    with pytest.raises(ValueError, match="SPADO_EMBEDDING_API_KEY"):
        Embedder(Embeddings(backend="external", model="test")).encode(["query"])
    with pytest.raises(ValueError, match="HTTPS"):
        Embedder(
            Embeddings(
                backend="external", model="test", endpoint="http://remote.invalid/embeddings"
            )
        ).encode(["query"])


def test_model_change_selects_a_different_index():
    first = Embedder(Embeddings(backend="local", model="one"))
    second = Embedder(Embeddings(backend="local", model="two"))
    assert first.identity != second.identity
