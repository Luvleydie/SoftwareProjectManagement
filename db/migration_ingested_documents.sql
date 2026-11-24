-- Migración: agregar tabla ingested_documents para el pipeline RAG.
-- Esta tabla almacena el resultado completo de cada ingesta:
-- Markdown, chunks, metadatos y trazabilidad del pipeline.

CREATE TABLE IF NOT EXISTS ingested_documents (
    id VARCHAR(36) PRIMARY KEY,

    -- Archivo original
    original_filename VARCHAR(500) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    detected_type VARCHAR(10) NOT NULL,       -- pdf | docx | txt | md
    file_size INTEGER NOT NULL,

    -- Metadatos del parsing
    title VARCHAR(500),
    total_pages INTEGER NOT NULL DEFAULT 0,
    word_count INTEGER NOT NULL DEFAULT 0,
    char_count INTEGER NOT NULL DEFAULT 0,
    sections_count INTEGER NOT NULL DEFAULT 0,
    language_hint VARCHAR(10) NOT NULL DEFAULT 'es',

    -- Markdown generado
    markdown TEXT NOT NULL,
    markdown_size INTEGER NOT NULL DEFAULT 0,

    -- Chunks para embeddings (JSON: list[ChunkData])
    chunks JSON,
    total_chunks INTEGER NOT NULL DEFAULT 0,
    avg_chunk_size INTEGER NOT NULL DEFAULT 0,

    -- Pipeline
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    pipeline_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    steps JSON,
    duration_total_ms INTEGER NOT NULL DEFAULT 0,

    -- Error
    error_code VARCHAR(50),
    error_message TEXT,

    -- Relaciones
    owner_id VARCHAR(36),
    source_version_id VARCHAR(36),

    -- Timestamps
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Embedding status (integración futura con pgvector)
    embedding_status VARCHAR(20) NOT NULL DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS ix_ingested_documents_sha256
    ON ingested_documents (sha256);

CREATE INDEX IF NOT EXISTS ix_ingested_documents_owner_id
    ON ingested_documents (owner_id);

CREATE INDEX IF NOT EXISTS ix_ingested_documents_source_version_id
    ON ingested_documents (source_version_id);

CREATE INDEX IF NOT EXISTS ix_ingested_documents_status
    ON ingested_documents (status);
