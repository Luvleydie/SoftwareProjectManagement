"""Local development API. Production controls and full design are tracked in README."""
import hashlib
import os
import re
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from threading import Lock
from typing import Literal
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import JSON, Column, Float, Integer, String, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, DATABASE_URL, engine, SessionLocal, database_status
from .ai import AIError, ai_status
from .legal import prepare_answer, prepare_draft, prepare_document_review, prepare_template
from . import models as _models  # noqa: F401 — registers LegalSource/SourceVersion with Base
from .sources import router as sources_router

ALLOWED_ORIGINS = set(os.getenv('JURIDIA_ALLOWED_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000,http://testserver').split(','))
SECURE_COOKIE = os.getenv('JURIDIA_SECURE_COOKIES', 'false').lower() == 'true'
COOKIE_NAME = 'juridia_session'
hasher = PasswordHasher()
dummy_hash = hasher.hash(secrets.token_hex(20))


class UserRow(Base):
    __tablename__ = 'users'
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)


class SessionRow(Base):
    __tablename__ = 'sessions'
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    csrf = Column(String(64), nullable=False)
    # MySQL FLOAT defaults to 32 bits, which rounds Unix timestamps by minutes.
    expires_at = Column(Float(53), nullable=False)


class Artifact(Base):
    __tablename__ = 'artifacts'
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(36), nullable=False, index=True)
    case_id = Column(String(36), nullable=False, index=True)
    kind = Column(String(32), nullable=False)
    data = Column(JSON, nullable=False)


class DraftVersion(Base):
    __tablename__ = 'draft_versions'
    draft_id = Column(String(36), primary_key=True)
    version = Column(Integer, primary_key=True)
    owner_id = Column(String(36), nullable=False, index=True)
    case_id = Column(String(36), nullable=False, index=True)
    data = Column(JSON, nullable=False)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title='juridIA API', version='0.3.0', lifespan=lifespan)
app.include_router(sources_router)
attempts: dict[str, deque] = defaultdict(deque)
attempt_lock = Lock()


@app.middleware('http')
async def security_checks(request: Request, call_next):
    correlation_id = str(uuid4())
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('origin')
        if origin and origin not in ALLOWED_ORIGINS:
            return JSONResponse({'detail': 'Origen no autorizado.', 'code': 'INVALID_ORIGIN', 'request_id': correlation_id}, status_code=403)
        try:
            if int(request.headers.get('content-length', '0')) > 2 * 1024 * 1024:
                return JSONResponse({'detail': 'La solicitud supera el límite de 2 MB.', 'code': 'TOO_LARGE'}, status_code=413)
        except ValueError:
            return JSONResponse({'detail': 'Solicitud no válida.'}, status_code=400)
        if request.url.path in {'/api/auth/login', '/api/auth/register', '/api/consultations', '/api/drafts/generate'}:
            key = f'{request.client.host if request.client else "unknown"}:{request.url.path}'
            with attempt_lock:
                now = time.monotonic()
                for stale_key in list(attempts):
                    if not attempts[stale_key] or attempts[stale_key][-1] <= now - 60:
                        del attempts[stale_key]
                queue = attempts[key]
                while queue and queue[0] <= now - 60:
                    queue.popleft()
                if len(queue) >= (30 if request.url.path == '/api/consultations' else 10):
                    return JSONResponse({'detail': 'Demasiados intentos. Espera un minuto.'}, status_code=429, headers={'Retry-After': '60'})
                queue.append(now)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Request-ID'] = correlation_id
    return response


def db_session():
    with SessionLocal() as db:
        yield db


def identity(request: Request, db: Session = Depends(db_session)) -> tuple[UserRow, SessionRow]:
    raw = request.cookies.get(COOKIE_NAME, '')
    session = db.get(SessionRow, hashlib.sha256(raw.encode()).hexdigest()) if raw else None
    if not session or session.expires_at <= time.time():
        raise HTTPException(401, 'Inicia sesión para acceder a tu espacio.')
    user = db.get(UserRow, session.user_id)
    if not user:
        raise HTTPException(401, 'Sesión no disponible.')
    if request.method not in {'GET', 'HEAD', 'OPTIONS'} and not secrets.compare_digest(request.headers.get('x-csrf-token', '').encode('utf-8'), session.csrf.encode('utf-8')):
        raise HTTPException(403, 'La sesión necesita actualizarse. Recarga la página.')
    return user, session


def owned(db: Session, artifact_id: str, owner_id: str, kind: str | None = None) -> Artifact:
    artifact = db.get(Artifact, artifact_id)
    if not artifact or artifact.owner_id != owner_id or (kind and artifact.kind != kind):
        raise HTTPException(404, 'Recurso no disponible.')
    return artifact


def save_artifact(db: Session, data: dict, user: UserRow, kind: str):
    old = db.get(Artifact, data['id'])
    if old and (old.owner_id != user.id or old.kind != kind):
        raise HTTPException(404, 'Recurso no disponible.')
    if old:
        if old.case_id != data.get('case_id', data['id']):
            raise HTTPException(409, 'No se puede cambiar el expediente de un recurso existente.')
        if kind == 'drafts':
            # Retain the last pre-history revision of existing installations.
            if not db.get(DraftVersion, (old.id, old.data['version'])):
                db.add(DraftVersion(draft_id=old.id, version=old.data['version'], owner_id=user.id, case_id=old.case_id, data=dict(old.data)))
            result = db.execute(update(Artifact).where(
                Artifact.id == old.id, Artifact.owner_id == user.id,
                Artifact.data['version'].as_integer() == data['version'] - 1,
            ).values(data=data).execution_options(synchronize_session=False))
            if result.rowcount != 1:
                db.rollback()
                raise HTTPException(409, 'El borrador cambió. Recarga antes de guardar otra versión.')
        else:
            old.data = data
    else:
        db.add(Artifact(id=data['id'], owner_id=user.id, case_id=data.get('case_id', data['id']), kind=kind, data=data))
    if kind == 'drafts':
        db.add(DraftVersion(draft_id=data['id'], version=data['version'], owner_id=user.id, case_id=data['case_id'], data=dict(data)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'El recurso cambió. Recarga antes de guardar.') from None
    return data


class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Register(Login):
    name: str = Field(min_length=1, max_length=100)


class CaseInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    id: UUID
    name: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=80)
    region: str = Field(min_length=1, max_length=100)
    locality: str = Field(min_length=1, max_length=100)
    date: date
    matter: str = Field(min_length=1, max_length=100)
    context: str = Field(default='', max_length=5000)
    status: Literal['En preparación', 'En revisión', 'Completado']


class DocumentInput(BaseModel):
    id: UUID
    case_id: UUID
    name: str = Field(min_length=1, max_length=255)
    size: int = Field(ge=0, le=1024 * 1024)
    text: str = Field(min_length=1, max_length=1024 * 1024)
    created_at: datetime


class QueryInput(BaseModel):
    case_id: UUID | None = None
    conversation_id: UUID | None = None
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)
    mode: Literal['ai', 'document'] = 'ai'


class DraftInput(BaseModel):
    id: UUID
    case_id: UUID
    title: str = Field(min_length=1, max_length=300)
    kind: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=100000)
    original_text: str = Field(min_length=1, max_length=100000)
    version: int = Field(ge=1)
    updated_at: datetime


class GenerateDraftInput(BaseModel):
    case_id: UUID
    kind: str = Field(min_length=1, max_length=100)
    parties: str = Field(default='', max_length=1000)
    terms: str = Field(default='', max_length=10000)
    mode: Literal['ai', 'template'] = 'ai'


def start_session(db: Session, user: UserRow, response: Response):
    raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.execute(delete(SessionRow).where(SessionRow.expires_at <= time.time()))
    db.add(SessionRow(token_hash=hashlib.sha256(raw.encode()).hexdigest(), user_id=user.id, csrf=csrf, expires_at=time.time() + 43200))
    db.commit()
    response.set_cookie(COOKIE_NAME, raw, httponly=True, secure=SECURE_COOKIE, samesite='strict', max_age=43200, path='/api')
    return {'user': {'name': user.name, 'email': user.email}, 'csrf': csrf}


@app.get('/api/health')
def health():
    database = database_status()
    ai = ai_status()
    return {'status': 'ok' if database['connected'] and ai['available'] else 'degraded', 'version': '0.3.0', 'mode': 'local', 'database': database, 'ai': ai, 'generation_enabled': ai['available'], 'legal_corpus_ready': False}


@app.post('/api/auth/register', status_code=201)
def register(body: Register, response: Response, db: Session = Depends(db_session)):
    if not body.name.strip():
        raise HTTPException(422, 'Escribe tu nombre.')
    user = UserRow(id=str(uuid4()), name=body.name.strip(), email=str(body.email).lower(), password_hash=hasher.hash(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'No se pudo crear la cuenta con esos datos.') from None
    return start_session(db, user, response)


@app.post('/api/auth/login')
def login(body: Login, response: Response, db: Session = Depends(db_session)):
    user = db.scalar(select(UserRow).where(UserRow.email == str(body.email).lower()))
    try:
        hasher.verify(user.password_hash if user else dummy_hash, body.password)
    except (VerificationError, InvalidHashError):
        raise HTTPException(401, 'Correo o contraseña incorrectos.') from None
    if not user:
        raise HTTPException(401, 'Correo o contraseña incorrectos.')
    return start_session(db, user, response)


@app.get('/api/auth/me')
def me(auth=Depends(identity)):
    user, session = auth
    return {'user': {'name': user.name, 'email': user.email}, 'csrf': session.csrf}


@app.post('/api/auth/logout', status_code=204)
def logout(response: Response, auth=Depends(identity), db: Session = Depends(db_session)):
    db.delete(auth[1]); db.commit()
    response.delete_cookie(COOKIE_NAME, path='/api', secure=SECURE_COOKIE, httponly=True, samesite='strict')


@app.get('/api/workspace')
def workspace(auth=Depends(identity), db: Session = Depends(db_session)):
    result = {'cases': [], 'documents': [], 'consultations': [], 'drafts': []}
    for artifact in db.scalars(select(Artifact).where(Artifact.owner_id == auth[0].id)):
        result[artifact.kind].append(artifact.data)
    for kind, field in [('documents', 'created_at'), ('consultations', 'created_at'), ('drafts', 'updated_at')]:
        result[kind].sort(key=lambda item: item.get(field, ''), reverse=True)
    return result


@app.get('/api/workspace/export')
def export_workspace(auth=Depends(identity), db: Session = Depends(db_session)):
    result = workspace(auth, db)
    revisions = {(row.draft_id, row.version): row.data for row in db.scalars(
        select(DraftVersion).where(DraftVersion.owner_id == auth[0].id))}
    for draft in result['drafts']:
        revisions[(draft['id'], draft['version'])] = draft
    return {**result, 'draft_versions': list(revisions.values())}


@app.put('/api/cases/{case_id}')
def put_case(case_id: UUID, body: CaseInput, auth=Depends(identity), db: Session = Depends(db_session)):
    if case_id != body.id:
        raise HTTPException(422, 'Identificador inconsistente.')
    return save_artifact(db, body.model_dump(mode='json'), auth[0], 'cases')


@app.delete('/api/cases/{case_id}', status_code=204)
def delete_case(case_id: UUID, auth=Depends(identity), db: Session = Depends(db_session)):
    owned(db, str(case_id), auth[0].id, 'cases')
    db.execute(delete(DraftVersion).where(DraftVersion.owner_id == auth[0].id, DraftVersion.case_id == str(case_id)))
    db.execute(delete(Artifact).where(Artifact.owner_id == auth[0].id, Artifact.case_id == str(case_id)))
    db.commit()


@app.post('/api/documents', status_code=201)
def post_document(body: DocumentInput, auth=Depends(identity), db: Session = Depends(db_session)):
    owned(db, str(body.case_id), auth[0].id, 'cases')
    if not body.name.lower().endswith('.txt') or any(c in body.name for c in ('/', '\\')) or not body.text.strip() or re.search(r'[\x00-\x08\x0e-\x1f]', body.text):
        raise HTTPException(415, 'Solo se admiten documentos TXT legibles en esta versión.')
    actual_size = len(body.text.encode('utf-8'))
    if actual_size > 1024 * 1024:
        raise HTTPException(413, 'El documento supera el límite de 1 MB.')
    if db.get(Artifact, str(body.id)):
        owned(db, str(body.id), auth[0].id, 'documents')
        raise HTTPException(409, 'El documento ya existe. Crea uno nuevo para conservar la trazabilidad.')
    data = body.model_dump(mode='json')
    data.update(size=actual_size, created_at=datetime.now(timezone.utc).isoformat())
    return save_artifact(db, data, auth[0], 'documents')


@app.delete('/api/documents/{document_id}', status_code=204)
def delete_document(document_id: UUID, auth=Depends(identity), db: Session = Depends(db_session)):
    document = owned(db, str(document_id), auth[0].id, 'documents')
    # Invalidate entire dependent answers, including their copied passages.
    for consultation in db.scalars(select(Artifact).where(Artifact.owner_id == auth[0].id, Artifact.kind == 'consultations')):
        if str(document_id) in consultation.data.get('input_document_ids', []) or any(c['document_id'] == str(document_id) for c in consultation.data.get('citations', [])):
            db.delete(consultation)
    db.delete(document); db.commit()


@app.post('/api/consultations', status_code=201)
def consult(body: QueryInput, auth=Depends(identity), db: Session = Depends(db_session)):
    context = owned(db, str(body.case_id), auth[0].id, 'cases') if body.case_id else None
    if not body.question.strip():
        raise HTTPException(422, 'Escribe una consulta.')
    documents = [owned(db, str(doc_id), auth[0].id, 'documents') for doc_id in dict.fromkeys(body.document_ids)]
    if any(d.case_id != str(body.case_id) for d in documents):
        raise HTTPException(404, 'Recurso no disponible.')
    owner_id, token_hash = auth[0].id, auth[1].token_hash
    context_snapshot = dict(context.data) if context else {'id': '', 'name': 'Chat general', 'country': '', 'region': '', 'locality': '', 'date': '', 'matter': '', 'context': '', 'status': 'En preparación'}
    conversation_id = str(body.conversation_id) if body.conversation_id else str(uuid4())
    previous = [dict(row.data) for row in db.scalars(select(Artifact).where(
        Artifact.owner_id == owner_id, Artifact.kind == 'consultations', Artifact.case_id == context_snapshot['id']))
        if row.data.get('conversation_id') == conversation_id and row.data.get('generation')]
    previous.sort(key=lambda item: item['created_at'])
    # Old document claims are included only when their source documents are selected again.
    selected_ids = {str(value) for value in body.document_ids}
    history = [{'question': item['question'][:1000], 'answer': item['answer'][:1500]}
               for item in previous[-4:] if set(item.get('input_document_ids', [])).issubset(selected_ids)]
    document_snapshots = [dict(d.data) for d in documents]
    # Do not hold a MySQL transaction open while local inference is running.
    db.rollback()
    try:
        answer = (prepare_answer(body.question.strip(), context_snapshot, document_snapshots, history)
                  if body.mode == 'ai' else prepare_document_review(body.question.strip(), context_snapshot, document_snapshots))
        answer['conversation_id'] = conversation_id
    except AIError as error:
        raise HTTPException(503, str(error)) from None
    user = validate_publication(db, owner_id, token_hash, context_snapshot['id'], [d['id'] for d in document_snapshots])
    return save_artifact(db, answer, user, 'consultations')


def validate_publication(db: Session, owner_id: str, token_hash: str, case_id: str, document_ids: list[str]) -> UserRow:
    """Recheck fresh rows; deletion/revocation during inference invalidates output."""
    db.rollback()
    session = db.scalar(select(SessionRow).where(SessionRow.token_hash == token_hash).with_for_update())
    if not session or session.user_id != owner_id or session.expires_at <= time.time():
        raise HTTPException(401, 'La sesión terminó durante la generación. Inicia sesión otra vez.')
    user = db.get(UserRow, owner_id)
    if not user:
        raise HTTPException(401, 'Sesión no disponible.')
    for artifact_id in ([case_id] if case_id else []) + sorted(set(document_ids)):
        current = db.scalar(select(Artifact).where(Artifact.id == artifact_id).with_for_update())
        if not current or current.owner_id != owner_id or current.case_id != case_id:
            raise HTTPException(409, 'El expediente o sus documentos cambiaron durante la generación. La respuesta no se ha guardado.')
    return user


@app.post('/api/drafts/generate', status_code=201)
def generate_draft(body: GenerateDraftInput, auth=Depends(identity), db: Session = Depends(db_session)):
    context = owned(db, str(body.case_id), auth[0].id, 'cases')
    owner_id, token_hash, snapshot = auth[0].id, auth[1].token_hash, dict(context.data)
    db.rollback()
    try:
        prepare = prepare_draft if body.mode == 'ai' else prepare_template
        draft = prepare(snapshot, body.kind, body.parties, body.terms)
    except AIError as error:
        raise HTTPException(503, str(error)) from None
    user = validate_publication(db, owner_id, token_hash, str(body.case_id), [])
    return save_artifact(db, draft, user, 'drafts')


@app.put('/api/drafts/{draft_id}')
def put_draft(draft_id: UUID, body: DraftInput, auth=Depends(identity), db: Session = Depends(db_session)):
    if draft_id != body.id:
        raise HTTPException(422, 'Identificador inconsistente.')
    owned(db, str(body.case_id), auth[0].id, 'cases')
    previous = db.scalar(select(Artifact).where(Artifact.id == str(draft_id)).with_for_update())
    data = body.model_dump(mode='json')
    if previous:
        owned(db, str(draft_id), auth[0].id, 'drafts')
        if body.version != previous.data['version'] + 1:
            raise HTTPException(409, 'El borrador cambió. Recarga antes de guardar otra versión.')
        data['original_text'] = previous.data['original_text']
        if 'generation' in previous.data:
            data['generation'] = previous.data['generation']
    else:
        data['version'] = 1
        data['original_text'] = body.text
    data['updated_at'] = datetime.now(timezone.utc).isoformat()
    return save_artifact(db, data, auth[0], 'drafts')


@app.get('/api/drafts/{draft_id}/versions')
def draft_versions(draft_id: UUID, auth=Depends(identity), db: Session = Depends(db_session)):
    current = owned(db, str(draft_id), auth[0].id, 'drafts')
    versions = {row.version: row.data for row in db.scalars(select(DraftVersion).where(
        DraftVersion.draft_id == str(draft_id), DraftVersion.owner_id == auth[0].id))}
    versions[current.data['version']] = current.data
    return [versions[v] for v in sorted(versions, reverse=True)]


@app.delete('/api/drafts/{draft_id}', status_code=204)
def delete_draft(draft_id: UUID, auth=Depends(identity), db: Session = Depends(db_session)):
    draft = owned(db, str(draft_id), auth[0].id, 'drafts')
    db.execute(delete(DraftVersion).where(DraftVersion.draft_id == str(draft_id), DraftVersion.owner_id == auth[0].id))
    db.delete(draft); db.commit()
