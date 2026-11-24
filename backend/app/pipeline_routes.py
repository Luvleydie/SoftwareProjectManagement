"""Rutas FastAPI para el pipeline de ingesta RAG (via LangGraph).

Endpoints:
  POST /api/pipeline/ingest         — Sube y procesa archivo (PDF/DOCX/TXT)
  GET  /api/pipeline/documents      — Lista documentos ingestados
  GET  /api/pipeline/documents/{id} — Detalle completo
  GET  /api/pipeline/documents/{id}/markdown — Solo Markdown
  GET  /api/pipeline/documents/{id}/chunks   — Chunks para embeddings
  DELETE /api/pipeline/documents/{id}        — Eliminar documento

La lógica del pipeline vive en rag/; estas rutas solo son el adaptador HTTP.
"""
import hashlib
import os
import sys
import time

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import Column, Float, String, select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal
from .pipeline_models import IngestedDocument

# Agregar rag/ al path para importar el grafo
_rag_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _rag_dir not in sys.path:
    sys.path.insert(0, _rag_dir)


router = APIRouter(prefix='/api/pipeline', tags=['pipeline'])

MAX_UPLOAD_SIZE = int(os.getenv('JURIDIA_MAX_UPLOAD_MB', '20')) * 1024 * 1024


# ── Auth mirrors (evitar import circular con main.py) ────────────────────────

class _UserRow(Base):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    id = Column(String(36), primary_key=True)
    email = Column(String(254))


class _SessionRow(Base):
    __tablename__ = 'sessions'
    __table_args__ = {'extend_existing': True}
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(String(36))
    expires_at = Column(Float(53))


def _db():
    with SessionLocal() as db:
        yield db


def _auth(request: Request, db: Session = Depends(_db)) -> _UserRow:
    raw = request.cookies.get('juridia_session', '')
    if not raw:
        raise HTTPException(401, 'Inicia sesión para acceder.')
    session = db.get(_SessionRow, hashlib.sha256(raw.encode()).hexdigest())
    if not session or session.expires_at <= time.time():
        raise HTTPException(401, 'Sesión expirada.')
    user = db.get(_UserRow, session.user_id)
    if not user:
        raise HTTPException(401, 'Sesión no disponible.')
    return user


# ── POST /api/pipeline/ingest ────────────────────────────────────────────────

@router.post('/ingest', status_code=201)
async def ingest_document(
    file: UploadFile = File(..., description='Archivo PDF, DOCX o TXT'),
    source_version_id: str | None = Query(None),
    db: Session = Depends(_db),
    user: _UserRow = Depends(_auth),
):
    """Pipeline determinista de ingesta via LangGraph.

    Pasos del grafo:
    1. **sanitize** — validación por magic bytes, tamaño, extensión, SHA-256
    2. **parse** — extracción determinista de texto y estructura
    3. **markdown** — conversión a Markdown con front-matter y TOC
    4. **chunk** — segmentación con overlap, IDs deterministas
    5. **persist** — guardado en PostgreSQL

    Cada paso puede cortocircuitar a END si falla.
    """
    content = await file.read()
    filename = file.filename or 'unknown'

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f'Excede el límite de {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.')

    # Deduplicación rápida
    sha256 = hashlib.sha256(content).hexdigest()
    existing = db.scalar(
        select(IngestedDocument).where(
            IngestedDocument.sha256 == sha256,
            IngestedDocument.owner_id == user.id,
            IngestedDocument.status == 'completed',
        )
    )
    if existing:
        raise HTTPException(409, f'Archivo ya procesado (doc {existing.id}).')

    # Ejecutar grafo LangGraph
    from rag.graph import run_pipeline

    result = run_pipeline(
        content,
        filename,
        owner_id=user.id,
        source_version_id=source_version_id or '',
        max_file_size=MAX_UPLOAD_SIZE,
        persist=True,
    )

    if result.get('status') == 'failed':
        raise HTTPException(422, {
            'detail': result.get('error_message', 'Error en el pipeline.'),
            'code': result.get('error_code', 'PIPELINE_ERROR'),
            'steps': result.get('steps', []),
        })

    # Respuesta limpia (sin raw_content)
    return {
        'document_id': result.get('document_id'),
        'original_filename': result.get('original_filename'),
        'sha256': result.get('sha256'),
        'detected_type': result.get('detected_type'),
        'file_size': result.get('file_size'),
        'title': result.get('title', ''),
        'total_pages': result.get('total_pages', 0),
        'word_count': result.get('word_count', 0),
        'char_count': result.get('char_count', 0),
        'sections_count': len(result.get('sections', [])),
        'language_hint': result.get('language_hint', 'es'),
        'markdown_size': result.get('markdown_size', 0),
        'total_chunks': result.get('total_chunks', 0),
        'avg_chunk_size': result.get('avg_chunk_size', 0),
        'status': result.get('status'),
        'pipeline_version': result.get('pipeline_version'),
        'steps': result.get('steps', []),
        'duration_total_ms': result.get('duration_total_ms', 0),
        'processed_at': result.get('processed_at', ''),
    }


# ── GET /api/pipeline/documents ──────────────────────────────────────────────

@router.get('/documents')
def list_documents(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(_db),
    user: _UserRow = Depends(_auth),
):
    query = select(IngestedDocument).where(IngestedDocument.owner_id == user.id)
    if status:
        query = query.where(IngestedDocument.status == status)
    query = query.order_by(IngestedDocument.processed_at.desc()).offset(offset).limit(limit)

    return [
        {
            'document_id': d.id,
            'original_filename': d.original_filename,
            'sha256': d.sha256,
            'detected_type': d.detected_type,
            'file_size': d.file_size,
            'title': d.title or '',
            'total_pages': d.total_pages,
            'word_count': d.word_count,
            'total_chunks': d.total_chunks,
            'status': d.status,
            'processed_at': d.processed_at.isoformat() if d.processed_at else '',
        }
        for d in db.scalars(query).all()
    ]


# ── GET /api/pipeline/documents/{id} ─────────────────────────────────────────

@router.get('/documents/{document_id}')
def get_document(document_id: str, db: Session = Depends(_db), user: _UserRow = Depends(_auth)):
    doc = db.get(IngestedDocument, document_id)
    if not doc or doc.owner_id != user.id:
        raise HTTPException(404, 'Documento no encontrado.')
    return {
        'document_id': doc.id,
        'original_filename': doc.original_filename,
        'sha256': doc.sha256,
        'detected_type': doc.detected_type,
        'file_size': doc.file_size,
        'title': doc.title or '',
        'total_pages': doc.total_pages,
        'word_count': doc.word_count,
        'char_count': doc.char_count,
        'sections_count': doc.sections_count,
        'language_hint': doc.language_hint,
        'markdown': doc.markdown,
        'markdown_size': doc.markdown_size,
        'total_chunks': doc.total_chunks,
        'avg_chunk_size': doc.avg_chunk_size,
        'chunks': doc.chunks or [],
        'status': doc.status,
        'pipeline_version': doc.pipeline_version,
        'steps': doc.steps or [],
        'duration_total_ms': doc.duration_total_ms,
        'processed_at': doc.processed_at.isoformat() if doc.processed_at else '',
    }


# ── GET /api/pipeline/documents/{id}/markdown ────────────────────────────────

@router.get('/documents/{document_id}/markdown')
def get_markdown(document_id: str, db: Session = Depends(_db), user: _UserRow = Depends(_auth)):
    doc = db.get(IngestedDocument, document_id)
    if not doc or doc.owner_id != user.id:
        raise HTTPException(404, 'Documento no encontrado.')
    return {'document_id': doc.id, 'title': doc.title, 'markdown': doc.markdown}


# ── GET /api/pipeline/documents/{id}/chunks ──────────────────────────────────

@router.get('/documents/{document_id}/chunks')
def get_chunks(document_id: str, db: Session = Depends(_db), user: _UserRow = Depends(_auth)):
    doc = db.get(IngestedDocument, document_id)
    if not doc or doc.owner_id != user.id:
        raise HTTPException(404, 'Documento no encontrado.')
    return {
        'document_id': doc.id,
        'total_chunks': doc.total_chunks,
        'avg_chunk_size': doc.avg_chunk_size,
        'embedding_status': doc.embedding_status,
        'chunks': doc.chunks or [],
    }


# ── DELETE /api/pipeline/documents/{id} ──────────────────────────────────────

@router.delete('/documents/{document_id}', status_code=204)
def delete_document(document_id: str, db: Session = Depends(_db), user: _UserRow = Depends(_auth)):
    doc = db.get(IngestedDocument, document_id)
    if not doc or doc.owner_id != user.id:
        raise HTTPException(404, 'Documento no encontrado.')
    db.delete(doc)
    db.commit()
