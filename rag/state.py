"""Estado tipado compartido entre todos los nodos del grafo LangGraph.

Define el TypedDict que fluye a través del pipeline. Cada nodo lee lo que
necesita y escribe sus resultados. LangGraph se encarga de la inmutabilidad
y el checkpointing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class PipelineStatus(str, Enum):
    PENDING = 'pending'
    SANITIZING = 'sanitizing'
    PARSING = 'parsing'
    CONVERTING = 'converting'
    CHUNKING = 'chunking'
    PERSISTING = 'persisting'
    COMPLETED = 'completed'
    FAILED = 'failed'


class DocumentType(str, Enum):
    PDF = 'pdf'
    DOCX = 'docx'
    TXT = 'txt'
    MD = 'md'


MIME_TO_DOCTYPE: dict[str, DocumentType] = {
    'application/pdf': DocumentType.PDF,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DocumentType.DOCX,
    'text/plain': DocumentType.TXT,
}


# ── Modelos inmutables para resultados intermedios ───────────────────────────

@dataclass(frozen=True, slots=True)
class Section:
    """Sección lógica del documento (capítulo, artículo, párrafo, etc.)."""
    level: int            # 0 = título, 1 = capítulo, 2 = sección, 3 = artículo/párrafo
    heading: str          # Encabezado de la sección (vacío para cuerpo sin título)
    body: str             # Contenido textual
    page: int | None = None


@dataclass(frozen=True, slots=True)
class ChunkData:
    """Un fragmento de texto listo para embedding."""
    chunk_id: str               # Hash determinista del contenido + posición
    index: int                  # Posición ordinal en el documento
    text: str                   # Texto de cita (lo que se mostrará)
    embedding_text: str         # Texto contextualizado para el modelo de embedding
    char_count: int
    estimated_tokens: int       # ~4 chars/token para español
    section_heading: str
    section_level: int
    hierarchy: dict             # {titulo, capitulo, seccion, articulo}
    locator: str                # "Artículo 5, Fracción III"
    content_hash: str           # SHA-256 del texto de cita
    page: int | None = None


@dataclass(frozen=True, slots=True)
class StepResult:
    """Resultado de un paso individual del pipeline."""
    step: str
    status: Literal['ok', 'error']
    duration_ms: int
    detail: str = ''


# ── Estado del grafo LangGraph ───────────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    """Estado completo que fluye entre los nodos del grafo.

    Cada nodo lee sus inputs y escribe sus outputs. LangGraph gestiona
    la reducción y el checkpointing.
    """
    # ── Input (inmutable una vez inyectado) ──────────────────────────────
    raw_content: bytes                # Bytes del archivo original
    original_filename: str            # Nombre del archivo subido
    max_file_size: int                # Límite en bytes (default 20 MB)
    chunk_size: int                   # Tamaño objetivo de chunk en caracteres
    chunk_overlap: int                # Overlap entre chunks
    owner_id: str                     # ID del usuario que sube el archivo
    source_version_id: str            # ID de source_version asociada (opcional)

    # ── Sanitización (nodo: sanitize) ────────────────────────────────────
    detected_mime: str                # Tipo MIME real detectado por magic bytes
    detected_type: str                # pdf | docx | txt | md
    sha256: str                       # Hash SHA-256 del contenido original
    file_size: int                    # Tamaño en bytes

    # ── Parsing (nodo: parse) ────────────────────────────────────────────
    sections: list[dict]              # list[Section] serializado como dicts
    title: str                        # Título extraído del documento
    total_pages: int
    word_count: int
    char_count: int
    language_hint: str                # 'es' | 'other'
    parse_warnings: list[str]         # Advertencias de OCR, formato, etc.

    # ── Markdown (nodo: convert_markdown) ────────────────────────────────
    markdown: str                     # Markdown limpio y estructurado
    markdown_size: int

    # ── Chunking (nodo: chunk) ───────────────────────────────────────────
    chunks: list[dict]                # list[ChunkData] serializado como dicts
    total_chunks: int
    avg_chunk_size: int

    # ── Embedding (nodo: embed) ──────────────────────────────────────────
    generate_embeddings: bool         # True para activar el nodo embed
    embedding_model: str              # Nombre del modelo usado (e.g. all-minilm:latest)
    embedding_model_digest: str       # Digest del modelo para idempotencia
    embedding_status: str             # pending | ready | partial | failed
    embedded_count: int               # Chunks con embedding exitoso

    # ── Persistencia (nodo: persist) ─────────────────────────────────────
    document_id: str                  # UUID asignado al documento
    ingestion_run_id: str             # UUID de la ejecución de ingesta
    persisted: bool                   # True si se guardó en PostgreSQL

    # ── Control del pipeline ─────────────────────────────────────────────
    status: str                       # PipelineStatus.value
    steps: list[dict]                 # list[StepResult] serializado
    error_code: str                   # Código del error (si aplica)
    error_message: str                # Mensaje del error (si aplica)
    pipeline_version: str
    processed_at: str                 # ISO-8601
    duration_total_ms: int


# ── Pydantic models para respuesta de API ────────────────────────────────────

class ChunkMeta(BaseModel):
    """Metadatos de un chunk para la respuesta de API."""
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    index: int
    text: str
    char_count: int
    estimated_tokens: int
    section_heading: str = ''
    section_level: int = 3
    hierarchy: dict = Field(default_factory=dict)
    locator: str = ''
    content_hash: str = ''
    page: int | None = None


class PipelineStepResult(BaseModel):
    step: str
    status: str
    duration_ms: int
    detail: str = ''


class IngestionResult(BaseModel):
    """Resultado completo de la ingesta, devuelto al cliente."""
    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: str
    original_filename: str
    sha256: str
    detected_type: str
    file_size: int
    title: str = ''
    total_pages: int = 0
    word_count: int = 0
    char_count: int = 0
    sections_count: int = 0
    language_hint: str = 'es'
    markdown: str = ''
    markdown_size: int = 0
    total_chunks: int = 0
    avg_chunk_size: int = 0
    chunks: list[ChunkMeta] = Field(default_factory=list)
    status: str = 'completed'
    pipeline_version: str = '1.0.0'
    steps: list[PipelineStepResult] = Field(default_factory=list)
    processed_at: str = ''
    duration_total_ms: int = 0
    error_code: str | None = None
    error_message: str | None = None


class IngestionSummary(BaseModel):
    """Resumen ligero para listados."""
    document_id: str
    original_filename: str
    sha256: str
    detected_type: str
    file_size: int
    title: str = ''
    total_pages: int = 0
    word_count: int = 0
    total_chunks: int = 0
    status: str
    processed_at: str = ''
    error_message: str | None = None
