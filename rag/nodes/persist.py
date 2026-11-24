"""Nodo 5 — Persistencia en PostgreSQL.

Guarda el resultado del pipeline en la tabla `ingested_documents` y, cuando
hay conexión a pgvector, prepara los chunks para embedding posterior.

Este nodo usa la misma conexión que el backend (via JURIDIA_DATABASE_URL)
para garantizar una sola base de verdad.
"""
import time
from datetime import datetime, timezone
from uuid import uuid4

from ..state import PipelineState


def persist_node(state: PipelineState) -> dict:
    """Nodo de persistencia: guarda documento + chunks en PostgreSQL.

    Lee: todo el estado del pipeline
    Escribe: document_id, ingestion_run_id, persisted, status, steps

    Importa SQLAlchemy solo cuando se ejecuta, para permitir ejecución
    en modo preview (sin BD) saltando este nodo.
    """
    start = time.monotonic()
    steps = list(state.get('steps', []))

    if state.get('status') == 'failed':
        return {}

    document_id = str(uuid4())
    ingestion_run_id = str(uuid4())
    now = datetime.now(timezone.utc)

    def _fail(msg: str, code: str) -> dict:
        elapsed = round((time.monotonic() - start) * 1000)
        steps.append({'step': 'persist', 'status': 'error', 'duration_ms': elapsed, 'detail': msg})
        return {
            'document_id': document_id,
            'status': 'failed',
            'error_code': code,
            'error_message': msg,
            'steps': steps,
            'persisted': False,
        }

    try:
        import sys
        import os
        # Agregar el directorio del backend al path para reutilizar la BD
        backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend')
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

        from app.database import SessionLocal, engine, Base
        from app.pipeline_models import IngestedDocument

        # Asegurar que la tabla existe
        Base.metadata.create_all(engine, tables=[IngestedDocument.__table__], checkfirst=True)
    except ImportError as exc:
        return _fail(f'No se pudo importar la configuración de BD: {exc}', 'DB_IMPORT_ERROR')
    except Exception as exc:
        return _fail(f'Error de conexión a BD: {exc}', 'DB_CONNECTION_ERROR')

    try:
        with SessionLocal() as db:
            # Verificar deduplicación por SHA-256
            from sqlalchemy import select
            sha256 = state.get('sha256', '')
            owner_id = state.get('owner_id', '')

            if sha256 and owner_id:
                existing = db.scalar(
                    select(IngestedDocument).where(
                        IngestedDocument.sha256 == sha256,
                        IngestedDocument.owner_id == owner_id,
                        IngestedDocument.status == 'completed',
                    )
                )
                if existing:
                    return _fail(
                        f'Archivo ya procesado (documento {existing.id}). '
                        'Elimínalo primero para reprocesarlo.',
                        'DUPLICATE_FILE',
                    )

            detected_type = state.get('detected_type', 'txt')

            doc_row = IngestedDocument(
                id=document_id,
                original_filename=state.get('original_filename', 'unknown'),
                sha256=sha256,
                detected_type=detected_type,
                file_size=state.get('file_size', 0),
                title=state.get('title', ''),
                total_pages=state.get('total_pages', 0),
                word_count=state.get('word_count', 0),
                char_count=state.get('char_count', 0),
                sections_count=len(state.get('sections', [])),
                language_hint=state.get('language_hint', 'es'),
                markdown=state.get('markdown', ''),
                markdown_size=state.get('markdown_size', 0),
                chunks=state.get('chunks', []),
                total_chunks=state.get('total_chunks', 0),
                avg_chunk_size=state.get('avg_chunk_size', 0),
                status='completed',
                pipeline_version=state.get('pipeline_version', '1.0.0'),
                steps=steps,  # Se actualiza al final
                duration_total_ms=0,  # Se actualiza al final
                owner_id=owner_id or None,
                source_version_id=state.get('source_version_id') or None,
                processed_at=now,
            )
            db.add(doc_row)
            db.commit()

    except Exception as exc:
        return _fail(f'Error al persistir: {exc}', 'PERSIST_ERROR')

    elapsed = round((time.monotonic() - start) * 1000)
    steps.append({
        'step': 'persist', 'status': 'ok', 'duration_ms': elapsed,
        'detail': f'Documento {document_id} guardado en PostgreSQL',
    })

    return {
        'document_id': document_id,
        'ingestion_run_id': ingestion_run_id,
        'persisted': True,
        'status': 'completed',
        'steps': steps,
        'processed_at': now.isoformat(),
    }
