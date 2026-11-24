"""Herramientas del pipeline RAG — API pública de utilidades.

Re-exporta las utilidades de los módulos legacy (chunker, parser, embedder,
repository, validator) con una interfaz estable. Los nodos LangGraph importan
desde aquí para evitar acoplar directamente a los módulos internos.

Uso típico
----------
Desde un nodo o script externo:

    from rag.tools import (
        validate_source,
        parse_markdown_law,
        build_chunks,
        embed_chunks,
        save_chunks_to_db,
    )

Desde la CLI:

    from rag.tools import run_pipeline   # pipeline completo via LangGraph
"""
from __future__ import annotations

# ── Validación de archivos fuente (CLI / scripts) ────────────────────────────
from .validator import validate as validate_source, SourceInfo

# ── Parser de leyes en Markdown (versión legacy standalone) ─────────────────
from .parser import parse as parse_markdown_law, ParsedUnit

# ── Chunker basado en unidades parseadas (versión legacy standalone) ─────────
from .chunker import build_chunks, Chunk

# ── Cliente de embeddings Ollama ────────────────────���────────────────────────
from .embedder import embed, check_model as check_embedding_model

# ── Repositorio PostgreSQL (ingestion_runs, legal_chunks, source_versions) ───
from .repository import (
    check_postgres,
    get_or_create_source_version,
    get_or_create_run,
    save_chunks_pending,
    pending_chunks,
    save_vector,
    mark_chunk_failed,
    finalize_run,
    run_summary,
)

# ── Configuración compartida ─────────────────────────────────────────────────
from .config import (
    database_url,
    ollama_url,
    embedding_model,
    EMBEDDING_DIMENSION,
    TOKEN_BUDGET,
    OVERLAP_RATIO,
    PARSER_VERSION,
    CHUNKER_VERSION,
)

# ── Pipeline LangGraph (punto de entrada principal) ──────────────────────────
from .graph import run_pipeline, compile_ingestion_graph, build_ingestion_graph

__all__ = [
    # Validación
    'validate_source',
    'SourceInfo',
    # Parser
    'parse_markdown_law',
    'ParsedUnit',
    # Chunker
    'build_chunks',
    'Chunk',
    # Embedder
    'embed',
    'check_embedding_model',
    # Repositorio
    'check_postgres',
    'get_or_create_source_version',
    'get_or_create_run',
    'save_chunks_pending',
    'pending_chunks',
    'save_vector',
    'mark_chunk_failed',
    'finalize_run',
    'run_summary',
    # Configuración
    'database_url',
    'ollama_url',
    'embedding_model',
    'EMBEDDING_DIMENSION',
    'TOKEN_BUDGET',
    'OVERLAP_RATIO',
    'PARSER_VERSION',
    'CHUNKER_VERSION',
    # Pipeline
    'run_pipeline',
    'compile_ingestion_graph',
    'build_ingestion_graph',
]
