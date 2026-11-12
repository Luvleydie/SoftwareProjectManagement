-- Esquema PostgreSQL del prototipo actual de juridIA.
-- Las columnas de embedding siguen siendo JSON; pgvector se añadirá cuando
-- se defina el modelo y la dimensión de embeddings.

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    csrf VARCHAR(64) NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_sessions_user_id
    ON sessions (user_id);

CREATE TABLE IF NOT EXISTS artifacts (
    id VARCHAR(36) PRIMARY KEY,
    owner_id VARCHAR(36) NOT NULL,
    case_id VARCHAR(36) NOT NULL,
    kind VARCHAR(32) NOT NULL,
    data JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_artifacts_owner_id
    ON artifacts (owner_id);

CREATE INDEX IF NOT EXISTS ix_artifacts_case_id
    ON artifacts (case_id);

CREATE TABLE IF NOT EXISTS draft_versions (
    draft_id VARCHAR(36) NOT NULL,
    version INTEGER NOT NULL,
    owner_id VARCHAR(36) NOT NULL,
    case_id VARCHAR(36) NOT NULL,
    data JSON NOT NULL,
    PRIMARY KEY (draft_id, version)
);

CREATE INDEX IF NOT EXISTS ix_draft_versions_owner_id
    ON draft_versions (owner_id);

CREATE INDEX IF NOT EXISTS ix_draft_versions_case_id
    ON draft_versions (case_id);

CREATE TABLE IF NOT EXISTS legal_sources (
    id VARCHAR(36) PRIMARY KEY,
    slug VARCHAR(120) NOT NULL,
    title VARCHAR(300) NOT NULL,
    country VARCHAR(80) NOT NULL DEFAULT 'México',
    jurisdiction VARCHAR(80) NOT NULL,
    authority VARCHAR(200) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'inactive'
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_legal_sources_slug
    ON legal_sources (slug);

CREATE TABLE IF NOT EXISTS source_versions (
    id VARCHAR(36) PRIMARY KEY,
    source_id VARCHAR(36) NOT NULL
        REFERENCES legal_sources (id),
    version INTEGER NOT NULL,
    state VARCHAR(20) NOT NULL DEFAULT 'draft',
    dof_date VARCHAR(20),
    effective_date VARCHAR(20),
    last_reform VARCHAR(20),
    provenance_url VARCHAR(500),
    text TEXT NOT NULL,
    chunks JSON,
    embedding_json JSON,
    embedding_model VARCHAR(100),
    embedding_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at VARCHAR(30) NOT NULL,
    activated_at VARCHAR(30),
    deactivated_at VARCHAR(30),
    activated_by VARCHAR(36)
);

CREATE INDEX IF NOT EXISTS ix_source_versions_source_id
    ON source_versions (source_id);
