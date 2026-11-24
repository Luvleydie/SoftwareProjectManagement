"""Ollama embedding client.

Calls the local Ollama instance at /api/embed.
Validates that the host is loopback, the model exists, and every returned
vector has exactly EMBEDDING_DIMENSION finite components.
Never sends content to external services.
"""
import math
from urllib.parse import urlparse

import httpx

from .config import EMBEDDING_DIMENSION, embedding_model, ollama_url

_TIMEOUT = 60.0  # seconds per request


def _assert_loopback(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError(
            f"Ollama URL must point to loopback for security. Got host: {host!r}"
        )


def check_model(client: httpx.Client) -> str:
    """Verify the embedding model exists and return its digest.

    Raises RuntimeError if the model is not found or Ollama is unreachable.
    """
    base = ollama_url()
    _assert_loopback(base)
    model = embedding_model()
    try:
        resp = client.post(f"{base}/api/show", json={"name": model}, timeout=10.0)
        tags_resp = client.get(f"{base}/api/tags", timeout=10.0)
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Cannot connect to Ollama at {base}. "
            "Make sure Ollama is running: ollama serve"
        ) from exc

    if resp.status_code == 404:
        raise RuntimeError(
            f"Embedding model '{model}' not found in Ollama. "
            f"Pull it first: ollama pull {model}"
        )
    resp.raise_for_status()
    tags_resp.raise_for_status()
    models = tags_resp.json().get("models", [])
    model_info = next(
        (item for item in models if item.get("name") == model),
        None,
    )
    if model_info is None:
        raise RuntimeError(
            f"Embedding model '{model}' is not listed by Ollama."
        )
    digest = model_info.get("digest")
    if not isinstance(digest, str) or not digest.strip():
        raise RuntimeError(
            f"Ollama did not provide a digest for embedding model '{model}'."
        )
    return digest


def embed(client: httpx.Client, text: str) -> list[float]:
    """Generate an embedding for *text* and validate the result.

    Returns a list of EMBEDDING_DIMENSION finite floats.
    Raises RuntimeError on any failure; never returns a fabricated vector.
    """
    base = ollama_url()
    model = embedding_model()
    try:
        resp = client.post(
            f"{base}/api/embed",
            json={"model": model, "input": text},
            timeout=_TIMEOUT,
        )
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"Ollama request timed out after {_TIMEOUT}s") from exc
    except httpx.ConnectError as exc:
        raise RuntimeError(f"Lost connection to Ollama at {base}") from exc

    resp.raise_for_status()
    data = resp.json()

    # /api/embed returns {"embeddings": [[...]], ...}
    embeddings = data.get("embeddings")
    if not embeddings or not isinstance(embeddings, list):
        raise RuntimeError(
            f"Unexpected Ollama response shape: {list(data.keys())}"
        )
    vector = embeddings[0]

    if not isinstance(vector, list) or len(vector) == 0:
        raise RuntimeError("Ollama returned an empty embedding vector.")
    if len(vector) != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Expected {EMBEDDING_DIMENSION}-dimensional vector, "
            f"got {len(vector)} dimensions."
        )
    for i, v in enumerate(vector):
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise RuntimeError(
                f"Non-finite value at index {i} in embedding vector: {v!r}"
            )

    return [float(v) for v in vector]
