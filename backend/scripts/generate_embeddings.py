"""Generate embeddings for source versions with embedding_status='pending'.

NOT YET ACTIVE — deferred to Incremento 3.

How to activate
---------------
1. Decide the embedding model and dimension, e.g.:
       model = 'nomic-embed-text'   # via Ollama
       dim   = 768

2. Enable pgvector in PostgreSQL:
       CREATE EXTENSION IF NOT EXISTS vector;

3. Replace the JSON placeholder column in SourceVersion with a real vector:
   In a new Alembic migration:
       from pgvector.sqlalchemy import Vector
       op.add_column('source_versions', sa.Column('embedding', Vector(768)))
       op.drop_column('source_versions', 'embedding_json')
       op.drop_column('source_versions', 'embedding_model')

4. Add an index (choose one):
       CREATE INDEX ON source_versions USING ivfflat (embedding vector_cosine_ops)
           WITH (lists = 100);
       -- or hnsw for faster queries at higher memory cost:
       CREATE INDEX ON source_versions USING hnsw (embedding vector_cosine_ops)
           WITH (m = 16, ef_construction = 64);

5. Uncomment and complete the worker loop below, then run:
       cd backend
       .venv\\Scripts\\python.exe scripts/generate_embeddings.py

6. Update retrieve_passages() in legal.py to use pgvector similarity search
   instead of (or combined with) the current keyword scan.

Worker skeleton (fill in after step 3)
---------------------------------------
import httpx
from sqlalchemy import select
from app.database import SessionLocal
from app.models import SourceVersion

OLLAMA_URL = 'http://127.0.0.1:11434'
MODEL      = 'nomic-embed-text'

def embed(text: str) -> list[float]:
    r = httpx.post(f'{OLLAMA_URL}/api/embeddings',
                   json={'model': MODEL, 'prompt': text}, timeout=120)
    r.raise_for_status()
    return r.json()['embedding']

def run():
    with SessionLocal() as db:
        pending = db.scalars(
            select(SourceVersion).where(SourceVersion.embedding_status == 'pending')
        ).all()
        for v in pending:
            try:
                # Chunk the text first (see Incremento 3 chunking strategy).
                vector = embed(v.text[:8000])   # placeholder — use chunks instead
                # v.embedding = vector          # uncomment after migration
                v.embedding_model = MODEL
                v.embedding_status = 'ready'
                db.commit()
                print(f'[ok] {v.id} version={v.version}')
            except Exception as exc:
                v.embedding_status = 'failed'
                db.commit()
                print(f'[err] {v.id}: {exc}')

if __name__ == '__main__':
    run()
"""
print('Este script es un placeholder. Lee los comentarios internos para activar embeddings.')
