"""ORM models for the legal sources catalogue (Incremento 2).

Embedding column is intentionally nullable — generation is deferred until
pgvector is available and the embedding profile is decided (Incremento 3).
To activate embeddings later:
  1. Choose model + dimension (e.g. EmbeddingGemma 768-d).
  2. Enable pgvector: CREATE EXTENSION IF NOT EXISTS vector;
  3. Replace the JSON column with Vector(dim) from pgvector.sqlalchemy.
  4. Run the Alembic migration that adds the column and the ivfflat/hnsw index.
  5. Execute scripts/generate_embeddings.py to populate existing versions.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from .database import Base  # shared declarative base


class LegalSource(Base):
    """One law or regulation, independent of its versions."""
    __tablename__ = 'legal_sources'

    id = Column(String(36), primary_key=True)
    # Human-readable identifier, e.g. 'ley-institutos-nacionales-salud'
    slug = Column(String(120), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    # Jurisdiction metadata
    country = Column(String(80), nullable=False, default='México')
    jurisdiction = Column(String(80), nullable=False)   # e.g. 'Federal'
    authority = Column(String(200), nullable=False)     # e.g. 'Congreso de la Unión'
    subject = Column(String(100), nullable=False)       # e.g. 'Salud'
    # active | inactive — controls eligibility for new queries
    status = Column(String(20), nullable=False, default='inactive')

    versions = relationship('SourceVersion', back_populates='source',
                            cascade='all, delete-orphan', order_by='SourceVersion.version')


class SourceVersion(Base):
    """Immutable snapshot of a source at a given version.

    States
    ------
    draft     — being edited, not yet eligible for retrieval
    active    — current authoritative version, eligible for retrieval
    historical — superseded by a newer active version, kept for audit
    inactive  — manually deactivated, not eligible for retrieval

    Embedding slot
    --------------
    embedding_json is a temporary placeholder (list[float] stored as JSON).
    Replace with pgvector Vector(dim) once the embedding profile is fixed.
    Set embedding_status to 'pending' when text is saved; a worker script
    will set it to 'ready' after generating the vector.
    """
    __tablename__ = 'source_versions'

    id = Column(String(36), primary_key=True)
    source_id = Column(String(36), ForeignKey('legal_sources.id'), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    # draft | active | historical | inactive
    state = Column(String(20), nullable=False, default='draft')
    # Publication metadata
    dof_date = Column(String(20), nullable=True)        # DOF publication date
    effective_date = Column(String(20), nullable=True)  # Date the version took effect
    last_reform = Column(String(20), nullable=True)     # Date of last reform included
    provenance_url = Column(String(500), nullable=True) # Source URL for audit
    # Full plain text of the source (TXT, extracted from PDF/DOCX in Incremento 3)
    text = Column(Text, nullable=False)
    # Chunked passages for retrieval (populated by ingestion worker, Incremento 3)
    chunks = Column(JSON, nullable=True)                # list[{chunk_id, text, locator}]
    # Embedding placeholder — replace with pgvector column in Incremento 3
    embedding_json = Column(JSON, nullable=True)        # list[float] | null
    embedding_model = Column(String(100), nullable=True)
    # pending | ready | failed
    embedding_status = Column(String(20), nullable=False, default='pending')
    # Audit timestamps (ISO-8601 strings to stay DB-agnostic for now)
    created_at = Column(String(30), nullable=False)
    activated_at = Column(String(30), nullable=True)
    deactivated_at = Column(String(30), nullable=True)
    # Admin who performed the last state change
    activated_by = Column(String(36), nullable=True)

    source = relationship('LegalSource', back_populates='versions')
