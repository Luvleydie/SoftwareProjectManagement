"""PostgreSQL repository for the RAG ingestion pipeline.

Handles idempotent creation of SourceVersion, IngestionRun and LegalChunk
rows.  All state transitions use short transactions; no connection is held
open during Ollama calls.
"""
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from .chunker import Chunk
from .config import (
    CHUNKER_VERSION,
    EMBEDDING_DIMENSION,
    PARSER_VERSION,
    database_url,
)
from .validator import SourceInfo

_MANIFEST = {
    "slug": "ley-institutos-nacionales-salud",
    "title": "Ley de los Institutos Nacionales de Salud",
    "country": "México",
    "jurisdiction": "Federal",
    "authority": "Congreso de la Unión",
    "subject": "Salud",
    "dof_date": "2000-05-26",
    "effective_date": "2000-05-27",
    "last_reform": "2022-04-11",
    "provenance_url": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LINS.pdf",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _engine():
    url = database_url()
    return create_engine(url, pool_pre_ping=True)


def check_postgres(engine) -> None:
    """Verify PostgreSQL is reachable and pgvector is installed."""
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT 1"))
        except Exception as exc:
            raise RuntimeError(f"PostgreSQL is not reachable: {exc}") from exc
        try:
            conn.execute(text("SELECT 'vector'::regtype"))
        except Exception as exc:
            raise RuntimeError(
                "pgvector extension is not installed in this database. "
                "Run: CREATE EXTENSION IF NOT EXISTS vector;"
            ) from exc


def get_or_create_source_version(engine, info: SourceInfo) -> str:
    """Return the id of an existing or newly created SourceVersion.

    If the slug already exists and the SHA-256 matches, reuse it.
    If the SHA-256 differs, create a new version.
    If the slug does not exist, create source + version.
    """
    Session = sessionmaker(bind=engine)
    with Session() as db:
        row = db.execute(
            text("SELECT id FROM legal_sources WHERE slug = :slug"),
            {"slug": _MANIFEST["slug"]},
        ).fetchone()

        if row is None:
            source_id = str(uuid4())
            db.execute(
                text(
                    "INSERT INTO legal_sources "
                    "(id, slug, title, country, jurisdiction, authority, subject, status) "
                    "VALUES (:id, :slug, :title, :country, :jurisdiction, "
                    "        :authority, :subject, 'inactive')"
                ),
                {"id": source_id, **{k: _MANIFEST[k] for k in
                    ("slug", "title", "country", "jurisdiction", "authority", "subject")}},
            )
            db.commit()
        else:
            source_id = row[0]

        # Find existing version with matching SHA-256
        ver_row = db.execute(
            text(
                "SELECT id FROM source_versions "
                "WHERE source_id = :sid AND original_sha256 = :sha "
                "ORDER BY version DESC LIMIT 1"
            ),
            {"sid": source_id, "sha": info.sha256},
        ).fetchone()

        if ver_row:
            return ver_row[0]

        # New version number
        max_ver = db.execute(
            text("SELECT COALESCE(MAX(version), 0) FROM source_versions WHERE source_id = :sid"),
            {"sid": source_id},
        ).scalar()

        version_id = str(uuid4())
        db.execute(
            text(
                "INSERT INTO source_versions "
                "(id, source_id, version, state, dof_date, effective_date, "
                " last_reform, provenance_url, text, original_sha256, "
                " embedding_status, created_at) "
                "VALUES (:id, :sid, :ver, 'draft', :dof, :eff, :ref, :url, "
                "        :text, :sha, 'pending', :now)"
            ),
            {
                "id": version_id,
                "sid": source_id,
                "ver": max_ver + 1,
                "dof": _MANIFEST["dof_date"],
                "eff": _MANIFEST["effective_date"],
                "ref": _MANIFEST["last_reform"],
                "url": _MANIFEST["provenance_url"],
                "text": info.text,
                "sha": info.sha256,
                "now": _now(),
            },
        )
        db.commit()
        return version_id


def get_or_create_run(
    engine,
    version_id: str,
    info: SourceInfo,
    embedding_model: str,
    embedding_digest: str,
) -> tuple[str, bool]:
    """Return (run_id, already_complete).

    If a run with the same idempotency key exists and is 'ready', return it
    as already_complete=True.  Otherwise create or reuse an incomplete run.
    """
    Session = sessionmaker(bind=engine)
    with Session() as db:
        existing = db.execute(
            text(
                "SELECT id, status FROM ingestion_runs "
                "WHERE source_version_id = :vid "
                "  AND source_sha256 = :sha "
                "  AND parser_version = :pv "
                "  AND chunker_version = :cv "
                "  AND embedding_model = :em "
                "  AND embedding_digest = :ed "
                "  AND embedding_dimension = :dim"
            ),
            {
                "vid": version_id,
                "sha": info.sha256,
                "pv": PARSER_VERSION,
                "cv": CHUNKER_VERSION,
                "em": embedding_model,
                "ed": embedding_digest,
                "dim": EMBEDDING_DIMENSION,
            },
        ).fetchone()

        if existing:
            return existing[0], existing[1] == "ready"

        run_id = str(uuid4())
        db.execute(
            text(
                "INSERT INTO ingestion_runs "
                "(id, source_version_id, source_sha256, parser_version, "
                " chunker_version, embedding_model, embedding_digest, "
                " embedding_dimension, status, started_at) "
                "VALUES (:id, :vid, :sha, :pv, :cv, :em, :ed, :dim, "
                "        'processing', :now)"
            ),
            {
                "id": run_id,
                "vid": version_id,
                "sha": info.sha256,
                "pv": PARSER_VERSION,
                "cv": CHUNKER_VERSION,
                "em": embedding_model,
                "ed": embedding_digest,
                "dim": EMBEDDING_DIMENSION,
                "now": _now(),
            },
        )
        db.commit()
        return run_id, False


def save_chunks_pending(engine, run_id: str, chunks: list[Chunk]) -> None:
    """Insert all chunks with status='pending' (idempotent on ordinal)."""
    Session = sessionmaker(bind=engine)
    with Session() as db:
        for chunk in chunks:
            try:
                db.execute(
                    text(
                        "INSERT INTO legal_chunks "
                        "(id, ingestion_run_id, ordinal, hierarchy, locator, "
                        " citation_text, content_hash, embedding_input_hash, "
                        " embedding_status) "
                        "VALUES (:id, :run, :ord, CAST(:hier AS jsonb), :loc, "
                        "        :ct, :ch, :eih, 'pending') "
                        "ON CONFLICT (ingestion_run_id, ordinal) DO NOTHING"
                    ),
                    {
                        "id": str(uuid4()),
                        "run": run_id,
                        "ord": chunk.ordinal,
                        "hier": json.dumps(chunk.hierarchy, ensure_ascii=False),
                        "loc": chunk.locator,
                        "ct": chunk.citation_text,
                        "ch": chunk.content_hash,
                        "eih": chunk.embedding_input_hash,
                    },
                )
            except IntegrityError:
                db.rollback()
                continue
        db.commit()


def pending_chunks(engine, run_id: str) -> list[dict]:
    """Return chunks with status 'pending' or 'failed' for this run."""
    Session = sessionmaker(bind=engine)
    with Session() as db:
        rows = db.execute(
            text(
                "SELECT id, ordinal, locator, embedding_input_hash, "
                "       citation_text "
                "FROM legal_chunks "
                "WHERE ingestion_run_id = :run "
                "  AND embedding_status IN ('pending', 'failed') "
                "ORDER BY ordinal"
            ),
            {"run": run_id},
        ).fetchall()
    return [
        {
            "id": r[0],
            "ordinal": r[1],
            "locator": r[2],
            "embedding_input_hash": r[3],
            "citation_text": r[4],
        }
        for r in rows
    ]


def save_vector(engine, chunk_id: str, vector: list[float]) -> None:
    """Persist a single embedding vector and mark the chunk ready."""
    # pgvector accepts a Python list via the '[...]' literal syntax.
    vec_str = "[" + ",".join(str(v) for v in vector) + "]"
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.execute(
            text(
                "UPDATE legal_chunks "
                "SET embedding = CAST(:vec AS vector), embedding_status = 'ready' "
                "WHERE id = :id"
            ),
            {"vec": vec_str, "id": chunk_id},
        )
        db.commit()


def mark_chunk_failed(engine, chunk_id: str) -> None:
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.execute(
            text(
                "UPDATE legal_chunks SET embedding_status = 'failed' WHERE id = :id"
            ),
            {"id": chunk_id},
        )
        db.commit()


def finalize_run(engine, run_id: str, version_id: str) -> bool:
    """Mark run ready and update active pointer if all chunks succeeded.

    Returns True if the run is now ready, False if there are still failures.
    """
    Session = sessionmaker(bind=engine)
    with Session() as db:
        failed = db.execute(
            text(
                "SELECT COUNT(*) FROM legal_chunks "
                "WHERE ingestion_run_id = :run AND embedding_status != 'ready'"
            ),
            {"run": run_id},
        ).scalar()

        if failed:
            db.execute(
                text(
                    "UPDATE ingestion_runs SET status = 'failed', completed_at = :now "
                    "WHERE id = :id"
                ),
                {"now": _now(), "id": run_id},
            )
            db.execute(
                text(
                    "UPDATE source_versions SET embedding_status = 'failed' "
                    "WHERE id = :vid AND active_ingestion_run_id IS NULL"
                ),
                {"vid": version_id},
            )
            db.commit()
            return False

        db.execute(
            text(
                "UPDATE ingestion_runs "
                "SET status = 'ready', completed_at = :now WHERE id = :id"
            ),
            {"now": _now(), "id": run_id},
        )
        db.execute(
            text(
                "UPDATE source_versions "
                "SET active_ingestion_run_id = :run, embedding_status = 'ready' "
                "WHERE id = :vid"
            ),
            {"run": run_id, "vid": version_id},
        )
        db.commit()
        return True


def run_summary(engine, run_id: str) -> dict:
    Session = sessionmaker(bind=engine)
    with Session() as db:
        total = db.execute(
            text("SELECT COUNT(*) FROM legal_chunks WHERE ingestion_run_id = :run"),
            {"run": run_id},
        ).scalar()
        ready = db.execute(
            text(
                "SELECT COUNT(*) FROM legal_chunks "
                "WHERE ingestion_run_id = :run AND embedding_status = 'ready'"
            ),
            {"run": run_id},
        ).scalar()
        failed = db.execute(
            text(
                "SELECT COUNT(*) FROM legal_chunks "
                "WHERE ingestion_run_id = :run AND embedding_status = 'failed'"
            ),
            {"run": run_id},
        ).scalar()
    return {"total": total, "ready": ready, "failed": failed}
