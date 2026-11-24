"""CLI for generating and persisting local legal-source embeddings."""
import argparse
import sys
from pathlib import Path

import httpx
from sqlalchemy.exc import SQLAlchemyError

from .chunker import build_chunks
from .config import embedding_model
from .embedder import check_model, embed
from .parser import parse
from .repository import (
    _engine,
    check_postgres,
    finalize_run,
    get_or_create_run,
    get_or_create_source_version,
    mark_chunk_failed,
    pending_chunks,
    run_summary,
    save_chunks_pending,
    save_vector,
)
from .validator import validate

_LAW_TITLE = "Ley de los Institutos Nacionales de Salud"
_DEFAULT_SOURCE = Path(__file__).resolve().parent / "src" / "leyesfederalesSalud.md"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera embeddings locales y los guarda en PostgreSQL + pgvector."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=_DEFAULT_SOURCE,
        help="Markdown fuente de la ley (por defecto, rag/src/leyesfederalesSalud.md).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida y cuenta los chunks sin conectar ni escribir en la base.",
    )
    return parser


def run(source_path: Path, dry_run: bool = False) -> int:
    source = validate(source_path)
    units, warnings = parse(source.text)
    chunks = build_chunks(units, _LAW_TITLE)
    if not chunks:
        raise RuntimeError("No se generaron chunks; no se escribió en la base.")

    print(f"Fuente: {source.path.name} ({source.size_bytes} bytes, SHA-256 {source.sha256})")
    print(f"Unidades: {len(units)}; chunks: {len(chunks)}")
    for warning in warnings:
        print(f"[aviso] {warning}")

    if dry_run:
        for chunk in chunks[:5]:
            print(f"  {chunk.ordinal}: {chunk.locator}")
        return 0

    model = embedding_model()
    engine = _engine()
    try:
        check_postgres(engine)
        with httpx.Client(trust_env=False) as client:
            digest = check_model(client)
            version_id = get_or_create_source_version(engine, source)
            run_id, already_complete = get_or_create_run(
                engine, version_id, source, model, digest
            )
            if already_complete:
                print(f"[sin cambios] Ejecución {run_id} ya está completa.")
                return 0

            save_chunks_pending(engine, run_id, chunks)
            chunks_by_ordinal = {chunk.ordinal: chunk for chunk in chunks}
            failures = 0
            for pending in pending_chunks(engine, run_id):
                chunk = chunks_by_ordinal.get(pending["ordinal"])
                if chunk is None or chunk.embedding_input_hash != pending["embedding_input_hash"]:
                    raise RuntimeError(
                        f"El chunk {pending['ordinal']} no coincide con la fuente validada."
                    )

                try:
                    vector = embed(client, chunk.embedding_input)
                except (httpx.HTTPError, RuntimeError) as exc:
                    mark_chunk_failed(engine, pending["id"])
                    failures += 1
                    print(
                        f"[error] {pending['locator']} "
                        f"({type(exc).__name__}); queda disponible para reintento."
                    )
                    continue

                save_vector(engine, pending["id"], vector)
                print(f"[ok] {pending['locator']}")

            completed = finalize_run(engine, run_id, version_id)
            summary = run_summary(engine, run_id)
            print(
                f"Resultado: {summary['ready']}/{summary['total']} listos; "
                f"{summary['failed']} fallidos."
            )
            return 0 if completed and failures == 0 else 1
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return run(args.source, args.dry_run)
    except SQLAlchemyError as exc:
        print(
            f"[error] Database operation failed ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return 1
    except (OSError, RuntimeError, httpx.HTTPError) as exc:
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())