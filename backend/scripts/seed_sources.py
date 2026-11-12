"""Seed the legal sources catalogue with the Ley de los Institutos Nacionales de Salud.

Run once after the database is created:
    cd backend
    .venv\\Scripts\\python.exe scripts/seed_sources.py

The script is idempotent: it skips sources whose slug already exists.
Embeddings are NOT generated here; set embedding_status='pending' so a future
worker (Incremento 3) can pick them up with scripts/generate_embeddings.py.
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Allow running from the backend/ directory without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault(
    'JURIDIA_DATABASE_URL',
    f'sqlite:///{Path(__file__).resolve().parents[1] / "juridia.db"}',
)

from sqlalchemy import select
from app.database import engine, SessionLocal, Base
from app.models import LegalSource, SourceVersion
import app.main  # noqa: F401 — ensures all tables are registered before create_all

Base.metadata.create_all(engine)

LEY_TEXT = Path(__file__).resolve().parents[2] / 'leyesfederalesSalud.md'

SOURCES = [
    {
        'slug': 'ley-institutos-nacionales-salud',
        'title': 'Ley de los Institutos Nacionales de Salud',
        'country': 'México',
        'jurisdiction': 'Federal',
        'authority': 'Congreso de la Unión',
        'subject': 'Salud',
        'dof_date': '2000-05-26',
        'effective_date': '2000-05-27',
        'last_reform': '2022-04-11',
        'provenance_url': 'https://www.diputados.gob.mx/LeyesBiblio/pdf/LINS.pdf',
        'text_file': LEY_TEXT,
    },
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed():
    with SessionLocal() as db:
        for spec in SOURCES:
            existing = db.scalar(select(LegalSource).where(LegalSource.slug == spec['slug']))
            if existing:
                print(f'[skip] {spec["slug"]} already exists (id={existing.id})')
                continue

            text_path: Path = spec.pop('text_file')
            text = text_path.read_text(encoding='utf-8') if text_path.exists() else ''
            if not text:
                print(f'[warn] text file not found: {text_path}')

            dof = spec.pop('dof_date')
            eff = spec.pop('effective_date')
            ref = spec.pop('last_reform')
            url = spec.pop('provenance_url')

            src = LegalSource(id=str(uuid4()), status='inactive', **spec)
            db.add(src)
            db.flush()

            v = SourceVersion(
                id=str(uuid4()), source_id=src.id, version=1,
                state='draft', text=text,
                dof_date=dof, effective_date=eff, last_reform=ref,
                provenance_url=url,
                embedding_status='pending',
                created_at=now(),
            )
            db.add(v)
            db.commit()
            print(f'[ok] seeded {src.slug} (source={src.id}, version={v.id})')
            print(f'     embedding_status=pending — run scripts/generate_embeddings.py to populate')

    print('Done.')


if __name__ == '__main__':
    seed()
