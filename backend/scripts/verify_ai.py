"""Optional live local-model smoke test using a disposable account and fixture."""
import secrets
import sys
from pathlib import Path
from uuid import uuid4
import httpx
from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import Artifact, DraftVersion, SessionLocal, SessionRow, UserRow

email = f'qa-ai-{uuid4()}@example.com'
try:
    with httpx.Client(base_url='http://127.0.0.1:8000', timeout=260, trust_env=False) as client:
        registration = client.post('/api/auth/register', json={'name': 'Prueba IA', 'email': email, 'password': secrets.token_urlsafe(24)})
        registration.raise_for_status()
        client.headers['X-CSRF-Token'] = registration.json()['csrf']
        case = {'id': str(uuid4()), 'name': 'Evento ficticio QA', 'country': 'México', 'region': 'Puebla', 'locality': 'Puebla', 'date': '2026-12-20', 'matter': 'Contratos', 'context': 'Prueba con información ficticia.', 'status': 'En preparación'}
        client.put(f'/api/cases/{case["id"]}', json=case).raise_for_status()
        document = {'id': str(uuid4()), 'case_id': case['id'], 'name': 'prueba-ia.txt', 'text': 'Pago: se entregará un anticipo del 30%. El saldo se paga diez días antes del evento.\n\nCancelación: las partes acordarán por escrito el tratamiento del anticipo.', 'size': 1, 'created_at': '2026-10-15T00:00:00Z'}
        client.post('/api/documents', json=document).raise_for_status()
        response = client.post('/api/consultations', json={'case_id': case['id'], 'question': 'Resume lo que dice este documento privado sobre el anticipo y la cancelación, sin evaluar su validez legal.', 'document_ids': [document['id']], 'mode': 'ai'})
        if response.status_code != 201:
            raise RuntimeError(f'Generación no completada: {response.status_code} {response.text}')
        answer = response.json()
        assert answer['generation']['provider'] == 'ollama'
        assert answer['citations'] and all(c['passage'] in document['text'] for c in answer['citations'])
        assert answer['disclaimer'] and answer['limitations']
        print(f'OK: generación local real con {answer["generation"]["model"]}; {len(answer["citations"])} citas literales; {answer["generation"]["duration_ms"]} ms.')
        thread = str(uuid4())
        first = client.post('/api/consultations', json={'question': 'Estoy organizando un evento llamado FarolAzul. Recuerda ese nombre para la siguiente pregunta y confírmalo brevemente.', 'conversation_id': thread})
        first.raise_for_status()
        second = client.post('/api/consultations', json={'question': '¿Cómo se llama el evento que te acabo de mencionar?', 'conversation_id': thread})
        second.raise_for_status()
        assert 'farolazul' in second.json()['answer'].lower(), second.json()['answer']
        assert second.json()['generation']['provider'] == 'ollama'
        assert second.json()['case_id'] == ''
        print('OK: chat sin expediente y seguimiento con memoria real de la conversación.')
finally:
    with SessionLocal() as db, db.begin():
        user = db.scalar(select(UserRow).where(UserRow.email == email))
        if user:
            db.execute(delete(DraftVersion).where(DraftVersion.owner_id == user.id))
            db.execute(delete(Artifact).where(Artifact.owner_id == user.id))
            db.execute(delete(SessionRow).where(SessionRow.user_id == user.id))
            db.delete(user)
