"""Shared configuration for the RAG ingestion pipeline.

Reads the same environment variables as the backend so both processes
connect to the same PostgreSQL database.  Never logs credentials.

Resolution order for the database URL:
  1. JURIDIA_DATABASE_URL  — explicit full URL (used in tests and CI)
  2. DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD  — root .env style
  3. JURIDIA_MYSQL_* present → rejected with a clear error message
"""
import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
# Load root .env then backend/.env; neither overrides an already-set process var.
load_dotenv(_ROOT / ".env", override=False)
load_dotenv(_ROOT / "backend" / ".env", override=False)


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Add it to backend/.env or export it before running the pipeline."
        )
    return value


def database_url() -> str:
    """Return a PostgreSQL connection URL or raise RuntimeError."""
    explicit = os.getenv("JURIDIA_DATABASE_URL", "").strip()
    if explicit:
        if not explicit.startswith("postgresql"):
            raise RuntimeError(
                "JURIDIA_DATABASE_URL must be a PostgreSQL URL for the RAG pipeline. "
                f"Got scheme: {explicit.split('://')[0]!r}"
            )
        return explicit

    if os.getenv("JURIDIA_MYSQL_USER") or os.getenv("JURIDIA_MYSQL_DATABASE"):
        raise RuntimeError(
            "JURIDIA_MYSQL_* variables detected. "
            "The RAG pipeline requires PostgreSQL. "
            "Set JURIDIA_DATABASE_URL=postgresql+psycopg://... in backend/.env."
        )

    host = _require("DB_HOST")
    port = os.getenv("DB_PORT", "5432").strip() or "5432"
    name = _require("DB_NAME")
    user = _require("DB_USER")
    password = _require("DB_PASSWORD")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def ollama_url() -> str:
    return os.getenv("JURIDIA_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")


def embedding_model() -> str:
    # Separate variable from the generative model to avoid mixing responsibilities.
    return os.getenv("JURIDIA_EMBED_MODEL", "all-minilm:latest")


# ── Immutable profile constants ───────────────────────────────────────────────
# Changing any of these requires a new ingestion run (idempotency key).
EMBEDDING_DIMENSION: int = 384
PARSER_VERSION: str = "1.1"
CHUNKER_VERSION: str = "1.0"
# Max tokens per chunk including the context prefix sent to the embedding model.
TOKEN_BUDGET: int = 450
# Overlap ratio applied only between sub-chunks of the same article.
OVERLAP_RATIO: float = 0.10
