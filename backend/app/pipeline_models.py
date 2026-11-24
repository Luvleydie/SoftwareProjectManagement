"""Modelo SQLAlchemy para documentos ingestados por el pipeline RAG.

Tabla `ingested_documents`: almacena el resultado completo de la ingesta
incluyendo Markdown, chunks y metadatos de trazabilidad.

Este modelo se importa tanto desde la CLI (rag/) como desde las rutas
FastAPI (backend/) para mantener una sola definición.
"""
from sqlalchemy import Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.sql import func

import sys
import os

# Reutilizar Base del backend
_backend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.database import Base


class IngestedDocument(Base):
    """Documento procesado por el pipeline de ingesta RAG."""
    __tablename__ = 'ingested_documents'

    id = Column(String(36), primary_key=True)

    # Archivo original
    original_filename = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    detected_type = Column(String(10), nullable=False)  # pdf | docx | txt | md
    file_size = Column(Integer, nullable=False)

    # Metadatos del parsing
    title = Column(String(500), nullable=True)
    total_pages = Column(Integer, nullable=False, default=0)
    word_count = Column(Integer, nullable=False, default=0)
    char_count = Column(Integer, nullable=False, default=0)
    sections_count = Column(Integer, nullable=False, default=0)
    language_hint = Column(String(10), nullable=False, default='es')

    # Markdown generado
    markdown = Column(Text, nullable=False)
    markdown_size = Column(Integer, nullable=False, default=0)

    # Chunks para embeddings (JSON: list[ChunkData])
    chunks = Column(JSON, nullable=True)
    total_chunks = Column(Integer, nullable=False, default=0)
    avg_chunk_size = Column(Integer, nullable=False, default=0)

    # Pipeline
    status = Column(String(20), nullable=False, default='completed')
    pipeline_version = Column(String(20), nullable=False, default='1.0.0')
    steps = Column(JSON, nullable=True)
    duration_total_ms = Column(Integer, nullable=False, default=0)

    # Error
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relaciones
    owner_id = Column(String(36), nullable=True, index=True)
    source_version_id = Column(String(36), nullable=True, index=True)

    # Timestamps
    processed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Embedding status (integración futura con pgvector)
    embedding_status = Column(String(20), nullable=False, default='pending')
