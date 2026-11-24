-- Migración 001: pipeline de ingesta RAG
-- Aplicar sobre la base juridIA con pgvector instalado.
-- psql -d juridia -f db/migrations/001_rag_schema.sql

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE source_versions
    ADD COLUMN IF NOT EXISTS original_sha256 CHAR(64);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY,
    source_version_id VARCHAR(36) NOT NULL
        REFERENCES source_versions(id) ON DELETE CASCADE,
    source_sha256     CHAR(64)     NOT NULL,
    parser_version    VARCHAR(40)  NOT NULL,
    chunker_version   VARCHAR(40)  NOT NULL,
    embedding_model   VARCHAR(100) NOT NULL,
    embedding_digest  VARCHAR(100) NOT NULL,
    embedding_dimension SMALLINT   NOT NULL CHECK (embedding_dimension = 384),
    status            VARCHAR(20)  NOT NULL DEFAULT 'pending',
    started_at        TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ,
    UNIQUE (
        source_version_id, source_sha256, parser_version, chunker_version,
        embedding_model, embedding_digest, embedding_dimension
    )
);

ALTER TABLE source_versions
    ADD COLUMN IF NOT EXISTS active_ingestion_run_id UUID
        REFERENCES ingestion_runs(id);

CREATE TABLE IF NOT EXISTS legal_chunks (
    id                   UUID        PRIMARY KEY,
    ingestion_run_id     UUID        NOT NULL REFERENCES ingestion_runs(id) ON DELETE CASCADE,
    ordinal              INTEGER     NOT NULL,
    hierarchy            JSONB       NOT NULL,
    locator              TEXT        NOT NULL,
    citation_text        TEXT        NOT NULL,
    content_hash         CHAR(64)    NOT NULL,
    embedding_input_hash CHAR(64)    NOT NULL,
    embedding            vector(384),
    embedding_status     VARCHAR(20) NOT NULL DEFAULT 'pending',
    CHECK (embedding_status <> 'ready' OR embedding IS NOT NULL),
    UNIQUE (ingestion_run_id, ordinal)
);

CREATE INDEX IF NOT EXISTS ix_legal_chunks_run
    ON legal_chunks (ingestion_run_id);

CREATE INDEX IF NOT EXISTS ix_legal_chunks_embedding_hnsw
    ON legal_chunks USING hnsw (embedding vector_cosine_ops);
