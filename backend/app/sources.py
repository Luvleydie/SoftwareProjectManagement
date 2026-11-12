"""Administrative routes for the legal sources catalogue (Incremento 2).

State machine per SourceVersion:
  draft -> active      requires text present; previous active -> historical
  active -> inactive   source.status -> inactive if no active version remains
  inactive -> active   same rules as activate

Embedding generation is deferred to Incremento 3. Versions are created with
embedding_status='pending'; run scripts/generate_embeddings.py to populate.
"""
import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Column, Float, String, select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal
from .models import LegalSource, SourceVersion

router = APIRouter(prefix='/api/admin/sources', tags=['sources'])

# Comma-separated admin emails in env; empty = any authenticated user is admin (dev only).
_ADMIN_EMAILS: set[str] = {
    e.strip() for e in os.getenv('JURIDIA_ADMIN_EMAILS', '').split(',') if e.strip()
}


# ── Mirrors to avoid circular import with main.py ────────────────────────────

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


# ── Dependencies ─────────────────────────────────────────────────────────────

def _db():
    with SessionLocal() as db:
        yield db


def _admin(request: Request, db: Session = Depends(_db)) -> _UserRow:
    raw = request.cookies.get('juridia_session', '')
    if not raw:
        raise HTTPException(401, 'Inicia sesión para acceder.')
    session = db.get(_SessionRow, hashlib.sha256(raw.encode()).hexdigest())
    if not session or session.expires_at <= time.time():
        raise HTTPException(401, 'Sesión expirada.')
    user = db.get(_UserRow, session.user_id)
    if not user:
        raise HTTPException(401, 'Sesión no disponible.')
    if _ADMIN_EMAILS and user.email not in _ADMIN_EMAILS:
        raise HTTPException(403, 'Se requiere rol de administrador.')
    return user


# ── Schemas ───────────────────────────────────────────────────────────────────

class SourceIn(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=300)
    country: str = Field(default='México', max_length=80)
    jurisdiction: str = Field(min_length=1, max_length=80)
    authority: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=100)


class VersionIn(BaseModel):
    text: str = Field(min_length=1)
    dof_date: str | None = None
    effective_date: str | None = None
    last_reform: str | None = None
    provenance_url: str | None = None


class StateAction(BaseModel):
    action: Literal['activate', 'deactivate']


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_source(db: Session, slug: str) -> LegalSource:
    src = db.scalar(select(LegalSource).where(LegalSource.slug == slug))
    if not src:
        raise HTTPException(404, 'Fuente no encontrada.')
    return src


def _get_version(db: Session, version_id: str) -> SourceVersion:
    v = db.get(SourceVersion, version_id)
    if not v:
        raise HTTPException(404, 'Versión no encontrada.')
    return v


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get('')
def list_sources(db: Session = Depends(_db), admin=Depends(_admin)):
    sources = db.scalars(select(LegalSource)).all()
    return [
        {
            'id': s.id, 'slug': s.slug, 'title': s.title, 'status': s.status,
            'jurisdiction': s.jurisdiction, 'subject': s.subject,
            'versions': [
                {'id': v.id, 'version': v.version, 'state': v.state,
                 'embedding_status': v.embedding_status, 'last_reform': v.last_reform}
                for v in s.versions
            ],
        }
        for s in sources
    ]


@router.post('', status_code=201)
def create_source(body: SourceIn, db: Session = Depends(_db), admin=Depends(_admin)):
    if db.scalar(select(LegalSource).where(LegalSource.slug == body.slug)):
        raise HTTPException(409, 'Ya existe una fuente con ese slug.')
    src = LegalSource(id=str(uuid4()), status='inactive', **body.model_dump())
    db.add(src)
    db.commit()
    return {'id': src.id, 'slug': src.slug}


@router.post('/{slug}/versions', status_code=201)
def add_version(slug: str, body: VersionIn, db: Session = Depends(_db), admin=Depends(_admin)):
    src = _get_source(db, slug)
    next_num = max((v.version for v in src.versions), default=0) + 1
    v = SourceVersion(
        id=str(uuid4()), source_id=src.id, version=next_num,
        state='draft', text=body.text,
        dof_date=body.dof_date, effective_date=body.effective_date,
        last_reform=body.last_reform, provenance_url=body.provenance_url,
        embedding_status='pending', created_at=_now(),
    )
    db.add(v)
    db.commit()
    return {'id': v.id, 'version': v.version, 'state': v.state,
            'embedding_status': v.embedding_status}


@router.post('/{slug}/versions/{version_id}/state')
def change_state(slug: str, version_id: str, body: StateAction,
                 db: Session = Depends(_db), admin=Depends(_admin)):
    src = _get_source(db, slug)
    v = _get_version(db, version_id)
    if v.source_id != src.id:
        raise HTTPException(404, 'Versión no pertenece a esta fuente.')

    if body.action == 'activate':
        if not v.text:
            raise HTTPException(422, 'La versión no tiene texto; no puede activarse.')
        for other in src.versions:
            if other.id != v.id and other.state == 'active':
                other.state = 'historical'
        v.state = 'active'
        v.activated_at = _now()
        v.activated_by = admin.id
        src.status = 'active'

    elif body.action == 'deactivate':
        if v.state not in ('active', 'draft'):
            raise HTTPException(422, f'No se puede desactivar una versión en estado "{v.state}".')
        v.state = 'inactive'
        v.deactivated_at = _now()
        if not any(ov.state == 'active' for ov in src.versions if ov.id != v.id):
            src.status = 'inactive'

    db.commit()
    return {'id': v.id, 'version': v.version, 'state': v.state, 'source_status': src.status}


@router.get('/{slug}/versions/{version_id}')
def get_version(slug: str, version_id: str, db: Session = Depends(_db), admin=Depends(_admin)):
    src = _get_source(db, slug)
    v = _get_version(db, version_id)
    if v.source_id != src.id:
        raise HTTPException(404, 'Versión no pertenece a esta fuente.')
    return {
        'id': v.id, 'source_id': v.source_id, 'version': v.version,
        'state': v.state, 'dof_date': v.dof_date, 'last_reform': v.last_reform,
        'provenance_url': v.provenance_url, 'embedding_status': v.embedding_status,
        'created_at': v.created_at, 'activated_at': v.activated_at,
        'text_length': len(v.text) if v.text else 0,
    }
