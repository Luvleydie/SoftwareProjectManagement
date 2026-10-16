import os
import tempfile
from uuid import uuid4

os.environ['JURIDIA_DATABASE_URL'] = f'sqlite:///{tempfile.gettempdir().replace(chr(92), "/")}/juridia-test-{uuid4()}.db'

import pytest
from fastapi.testclient import TestClient
from app.main import app, attempts, engine, Base


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.create_all(engine)
    attempts.clear()
    yield
    Base.metadata.drop_all(engine)


def account(client, name='Ana'):
    response = client.post('/api/auth/register', json={'name': name, 'email': f'{name.lower()}@example.com', 'password': 'UnaClaveDePrueba123!'}, headers={'Origin': 'http://testserver'})
    assert response.status_code == 201, response.text
    return {'X-CSRF-Token': response.json()['csrf']}


def create_case(client, headers, **updates):
    value = {'id': str(uuid4()), 'name': 'Festival de prueba', 'country': 'México', 'region': 'Puebla', 'locality': 'Puebla', 'date': '2026-11-21', 'matter': 'Contratos', 'context': '', 'status': 'En preparación', **updates}
    result = client.put(f'/api/cases/{value["id"]}', json=value, headers=headers)
    assert result.status_code == 200, result.text
    return value


def create_document(client, headers, case):
    doc = {'id': str(uuid4()), 'case_id': case['id'], 'name': 'contrato.txt', 'text': 'Partes: Ana y Proveedor.\n\nCancelación: anticipo por acordar.', 'size': 1, 'created_at': '2026-10-07T00:00:00Z'}
    result = client.post('/api/documents', json=doc, headers=headers)
    assert result.status_code == 201, result.text
    return doc


def test_session_csrf_logout_and_origin():
    with TestClient(app) as c:
        assert c.get('/api/workspace').status_code == 401
        headers = account(c)
        assert 'HttpOnly' in c.post('/api/auth/login', json={'email': 'ana@example.com', 'password': 'UnaClaveDePrueba123!'}).headers['set-cookie']
        headers = {'X-CSRF-Token': c.get('/api/auth/me').json()['csrf']}
        assert c.post('/api/auth/logout').status_code == 403
        assert c.post('/api/auth/logout', headers={b'X-CSRF-Token': b'\xff'}).status_code == 403
        assert c.post('/api/auth/logout', headers={**headers, 'Origin': 'https://untrusted.example'}).status_code == 403
        assert c.post('/api/auth/logout', headers=headers).status_code == 204
        assert c.get('/api/workspace').status_code == 401


def test_private_resource_isolation():
    with TestClient(app) as a, TestClient(app) as b:
        ah = account(a, 'Ana'); bh = account(b, 'Beto')
        case = create_case(a, ah); doc = create_document(a, ah, case)
        assert b.get('/api/workspace').json()['cases'] == []
        assert b.put(f'/api/cases/{case["id"]}', json=case, headers=bh).status_code == 404
        assert b.delete(f'/api/documents/{doc["id"]}', headers=bh).status_code == 404
        assert b.post('/api/consultations', json={'case_id': case['id'], 'question': 'cancelación', 'document_ids': [doc['id']]}, headers=bh).status_code == 404
        other_case = create_case(b, bh)
        assert b.post('/api/documents', json={**doc, 'case_id': other_case['id']}, headers=bh).status_code == 404
        assert b.post('/api/consultations', json={'case_id': other_case['id'], 'question': 'cancelación', 'document_ids': [doc['id']]}, headers=bh).status_code == 404


def test_evidence_is_private_context_is_snapshot_and_deletion_invalidates():
    with TestClient(app) as c:
        headers = account(c); case = create_case(c, headers); doc = create_document(c, headers, case)
        answer = c.post('/api/consultations', json={'case_id': case['id'], 'question': '¿Qué dice sobre la cancelación?', 'mode': 'document', 'document_ids': [doc['id']]}, headers=headers)
        assert answer.status_code == 201, answer.text
        result = answer.json()
        assert result['outcome'] == 'INSUFFICIENT_EVIDENCE'
        assert result['citations'][0]['passage'] == 'Cancelación: anticipo por acordar.'
        assert result['citations'][0]['origin'] == 'private'
        assert 'profesional' in result['disclaimer']
        create_case(c, headers, **{**case, 'locality': 'Atlixco'})
        assert c.get('/api/workspace').json()['consultations'][0]['context']['locality'] == 'Puebla'
        assert c.delete(f'/api/documents/{doc["id"]}', headers=headers).status_code == 204
        workspace = c.get('/api/workspace').json()
        assert workspace['documents'] == []
        assert workspace['consultations'] == []


def test_empty_corpus_abstains_and_does_not_read_unselected_documents():
    with TestClient(app) as c:
        headers = account(c); case = create_case(c, headers); create_document(c, headers, case)
        answer = c.post('/api/consultations', json={'case_id': case['id'], 'question': 'cancelación', 'mode': 'document', 'document_ids': []}, headers=headers).json()
        assert answer['outcome'] == 'INSUFFICIENT_EVIDENCE'
        assert answer['citations'] == []


def test_documents_cannot_be_rewritten_or_attached_to_another_case_query():
    with TestClient(app) as c:
        headers = account(c); case = create_case(c, headers); doc = create_document(c, headers, case)
        assert c.post('/api/documents', json={**doc, 'text': 'Texto reemplazado'}, headers=headers).status_code == 409
        second = create_case(c, headers)
        assert c.post('/api/consultations', json={'case_id': second['id'], 'question': 'cancelación', 'document_ids': [doc['id']]}, headers=headers).status_code == 404


def test_reject_unsupported_binary_and_empty_context():
    with TestClient(app) as c:
        headers = account(c); case = create_case(c, headers)
        template = {'id': str(uuid4()), 'case_id': case['id'], 'name': 'archivo.pdf', 'text': 'text', 'size': 4, 'created_at': '2026-10-07T00:00:00Z'}
        assert c.post('/api/documents', json=template, headers=headers).status_code == 415
        assert c.post('/api/documents', json={**template, 'name': 'a.txt', 'text': '\u0000'}, headers=headers).status_code == 415
        assert c.post('/api/documents', json={**template, 'name': 'a.txt', 'text': 'á' * 600000}, headers=headers).status_code == 413
        assert c.put(f'/api/cases/{case["id"]}', json={**case, 'locality': '   '}, headers=headers).status_code == 422


def test_draft_revision_conflict_and_case_cascade():
    with TestClient(app) as c:
        headers = account(c); case = create_case(c, headers); create_document(c, headers, case)
        draft = {'id': str(uuid4()), 'case_id': case['id'], 'kind': 'Recinto', 'title': 'Borrador', 'text': 'Texto inicial', 'original_text': 'Texto inicial', 'version': 1, 'updated_at': '2026-10-07T00:00:00Z'}
        url = f'/api/drafts/{draft["id"]}'
        assert c.put(url, json=draft, headers=headers).status_code == 200
        assert c.put(url, json=draft, headers=headers).status_code == 409
        result = c.put(url, json={**draft, 'text': 'Editado', 'original_text': 'Manipulado', 'version': 2}, headers=headers)
        assert result.status_code == 200
        assert result.json()['original_text'] == 'Texto inicial'
        assert c.delete(f'/api/cases/{case["id"]}', headers=headers).status_code == 204
        assert c.get('/api/workspace').json() == {'cases': [], 'documents': [], 'drafts': [], 'consultations': []}


def test_authentication_rate_limit():
    with TestClient(app) as c:
        for _ in range(10):
            assert c.post('/api/auth/login', json={'email': 'nobody@example.com', 'password': 'UnaClaveDePrueba123!'}).status_code == 401
        response = c.post('/api/auth/login', json={'email': 'nobody@example.com', 'password': 'UnaClaveDePrueba123!'})
        assert response.status_code == 429
        assert response.headers['Retry-After'] == '60'


def test_template_history_restore_conflict_and_private_access(monkeypatch):
    from app import legal
    from app.main import DraftVersion, SessionLocal
    from sqlalchemy import select
    monkeypatch.setattr(legal, 'generate_json', lambda *args: pytest.fail('Template mode must not call AI'))
    with TestClient(app) as a, TestClient(app) as b:
        ah = account(a, 'Ana'); account(b, 'Beto')
        case = create_case(a, ah)
        response = a.post('/api/drafts/generate', json={'case_id': case['id'], 'kind': 'Recinto', 'parties': 'Ana y Proveedor', 'terms': '', 'mode': 'template'}, headers=ah)
        assert response.status_code == 201, response.text
        first = response.json()
        assert 'generation' not in first and '[PENDIENTE:' in first['text']
        url = f'/api/drafts/{first["id"]}'
        assert b.get(f'{url}/versions').status_code == 404
        second = a.put(url, json={**first, 'version': 2, 'text': 'Edición manual'}, headers=ah)
        assert second.status_code == 200
        assert a.put(url, json={**first, 'version': 2, 'text': 'Edición obsoleta'}, headers=ah).status_code == 409
        versions = a.get(f'{url}/versions').json()
        assert [v['version'] for v in versions] == [2, 1]
        assert versions[1]['text'] == first['text']
        restored = a.put(url, json={**second.json(), 'version': 3, 'text': versions[1]['text']}, headers=ah)
        assert restored.status_code == 200
        assert [v['version'] for v in a.get(f'{url}/versions').json()] == [3, 2, 1]
        exported = a.get('/api/workspace/export').json()
        assert sorted(v['version'] for v in exported['draft_versions']) == [1, 2, 3]
        assert b.get('/api/workspace/export').json()['draft_versions'] == []
        assert a.delete(url, headers=ah).status_code == 204
        assert a.get(f'{url}/versions').status_code == 404
        with SessionLocal() as db:
            assert db.scalar(select(DraftVersion)) is None


def test_case_deletion_cleans_history():
    from app.main import DraftVersion, SessionLocal
    from sqlalchemy import select
    with TestClient(app) as c:
        headers = account(c); case = create_case(c, headers)
        response = c.post('/api/drafts/generate', json={'case_id': case['id'], 'kind': 'Recinto', 'mode': 'template'}, headers=headers)
        assert response.status_code == 201
        assert c.delete(f'/api/cases/{case["id"]}', headers=headers).status_code == 204
        with SessionLocal() as db:
            assert db.scalar(select(DraftVersion)) is None


def test_local_review_never_calls_ai_and_deletes_uncited_inputs(monkeypatch):
    from app import legal
    monkeypatch.setattr(legal, 'generate_json', lambda *args: pytest.fail('Document mode must not call AI'))
    with TestClient(app) as c:
        headers = account(c); case = create_case(c, headers); doc = create_document(c, headers, case)
        result = c.post('/api/consultations', json={'case_id': case['id'], 'question': 'seguros', 'document_ids': [doc['id']], 'mode': 'document'}, headers=headers)
        assert result.status_code == 201
        assert result.json()['citations'] == []
        assert 'generation' not in result.json()
        assert c.delete(f'/api/documents/{doc["id"]}', headers=headers).status_code == 204
        assert c.get('/api/workspace').json()['consultations'] == []


def test_ai_validated_citations_and_provider_failure(monkeypatch):
    from app import legal
    from app.ai import AIError
    with TestClient(app) as c:
        headers = account(c); case = create_case(c, headers); doc = create_document(c, headers, case)
        payload = {'case_id': case['id'], 'question': 'cancelación', 'document_ids': [doc['id']], 'mode': 'ai'}
        def fake_generation(*args):
            return legal.ConsultationOutput(answer='El documento deja el anticipo por acordar.', cited_passage_ids=['p1'], limitations=[], out_of_scope=False), {'provider': 'test', 'model': 'test', 'generated_at': '2026-10-15T00:00:00Z'}
        monkeypatch.setattr(legal, 'generate_json', fake_generation)
        response = c.post('/api/consultations', json=payload, headers=headers)
        assert response.status_code == 201
        assert response.json()['outcome'] == 'DOCUMENT_REVIEW'
        assert response.json()['citations'][0]['passage'] in doc['text']
        def unavailable(*args):
            raise AIError('Motor no disponible.')
        monkeypatch.setattr(legal, 'generate_json', unavailable)
        assert c.post('/api/consultations', json=payload, headers=headers).status_code == 503
        assert len(c.get('/api/workspace').json()['consultations']) == 1
        def invented(*args):
            return legal.ConsultationOutput(answer='Una respuesta sin respaldo.', cited_passage_ids=['inventado'], limitations=[], out_of_scope=False), {}
        monkeypatch.setattr(legal, 'generate_json', invented)
        assert c.post('/api/consultations', json=payload, headers=headers).status_code == 503
        assert len(c.get('/api/workspace').json()['consultations']) == 1

def test_chat_history_is_private_bounded_and_optional_case(monkeypatch):
    from app import legal
    seen = []
    def generate(system, data, schema):
        seen.append(data)
        return legal.ConsultationOutput(answer='Respuesta generada para esta conversación.', cited_passage_ids=[], limitations=[], out_of_scope=False), {'provider': 'test', 'model': 'test'}
    monkeypatch.setattr(legal, 'generate_json', generate)
    with TestClient(app) as a, TestClient(app) as b:
        ah = account(a, 'ChatAna'); bh = account(b, 'ChatBeto')
        thread = str(uuid4())
        payload = {'question': 'Mi evento se llama Aurora.', 'conversation_id': thread}
        first = a.post('/api/consultations', json=payload, headers=ah)
        assert first.status_code == 201
        assert first.json()['case_id'] == ''
        assert seen[-1]['conversation_history'] == []
        assert a.post('/api/consultations', json={**payload, 'question': '¿Cómo se llama mi evento?'}, headers=ah).status_code == 201
        assert seen[-1]['conversation_history'][0]['question'] == payload['question']
        assert b.post('/api/consultations', json=payload, headers=bh).status_code == 201
        assert seen[-1]['conversation_history'] == []
        assert a.post('/api/consultations', json={**payload, 'conversation_id': str(uuid4())}, headers=ah).status_code == 201
        assert seen[-1]['conversation_history'] == []
        assert len(a.get('/api/workspace').json()['cases']) == 0
        case = create_case(a, ah); doc = create_document(a, ah, case)
        assert a.post('/api/consultations', json={**payload, 'document_ids': [doc['id']]}, headers=ah).status_code == 404
