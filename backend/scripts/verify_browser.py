"""Exercise the running local app with a disposable account and remove only its rows."""
import os
import secrets
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import Artifact, DraftVersion, SessionRow, UserRow, SessionLocal
from sqlalchemy import select, delete

email = f'qa-{uuid4()}@example.com'
env = {**os.environ, 'JURIDIA_E2E_API': '1', 'JURIDIA_E2E_EMAIL': email,
       'JURIDIA_E2E_PASSWORD': secrets.token_urlsafe(24)}
try:
    result = subprocess.run(['node', 'scripts/verify-browser.mjs'],
                            cwd=Path(__file__).resolve().parents[2] / 'frontend', env=env)
finally:
    with SessionLocal() as db, db.begin():
        user = db.scalar(select(UserRow).where(UserRow.email == email))
        if user:
            db.execute(delete(DraftVersion).where(DraftVersion.owner_id == user.id))
            db.execute(delete(Artifact).where(Artifact.owner_id == user.id))
            db.execute(delete(SessionRow).where(SessionRow.user_id == user.id))
            db.delete(user)
sys.exit(result.returncode)
