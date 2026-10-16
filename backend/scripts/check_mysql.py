"""Verify MySQL persistence, Unicode JSON, and timestamp precision with isolated rows.

Run from backend: .venv/Scripts/python.exe scripts/check_mysql.py
Only this script's randomly identified test rows are removed after the check.
"""
import sys
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import database_status, engine  # noqa: E402
from app.main import Artifact, Base, SessionRow, UserRow  # noqa: E402


def main():
    if engine.dialect.name not in {'mysql', 'mariadb'}:
        raise RuntimeError('Esta verificación requiere MySQL/MariaDB.')
    Base.metadata.create_all(engine)
    user_id, artifact_id = str(uuid4()), str(uuid4())
    session_id = uuid4().hex + uuid4().hex
    expires_at = time.time() + 43200.125
    payload = {'text': 'Contrato: México, cláusula, niño, ⚖️. ' * 5000, 'ids': [artifact_id], 'version': 1}
    try:
        with Session(engine) as db, db.begin():
            db.add(UserRow(id=user_id, name='Comprobación MySQL', email=f'check-{user_id}@example.invalid', password_hash='disabled-test-account'))
            db.add(Artifact(id=artifact_id, owner_id=user_id, case_id=artifact_id, kind='cases', data=payload))
            db.add(SessionRow(token_hash=session_id, user_id=user_id, csrf='test-only', expires_at=expires_at))
        with Session(engine) as db:
            assert db.get(Artifact, artifact_id).data == payload, 'No se conservó el documento JSON/Unicode.'
            assert abs(db.get(SessionRow, session_id).expires_at - expires_at) < 0.001, 'La caducidad perdió precisión.'
            assert db.get(UserRow, user_id).name == 'Comprobación MySQL'
        print(database_status())
        print('OK: escritura y lectura entre sesiones, JSON mayor a 64 KB, Unicode y precisión de caducidad.')
    finally:
        with Session(engine) as db, db.begin():
            db.execute(delete(Artifact).where(Artifact.id == artifact_id, Artifact.owner_id == user_id))
            db.execute(delete(SessionRow).where(SessionRow.token_hash == session_id, SessionRow.user_id == user_id))
            db.execute(delete(UserRow).where(UserRow.id == user_id))


if __name__ == '__main__':
    main()
