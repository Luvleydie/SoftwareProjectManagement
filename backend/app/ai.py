"""Real, local-only Ollama inference. No fabricated responses on provider failure."""
import json
import os
import time
from datetime import datetime, timezone
from threading import BoundedSemaphore
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ValidationError

PROMPT_VERSION = 'juridia-local-v1'
_generation_slot = BoundedSemaphore(1)


class AIError(Exception):
    """Safe error that may be shown to the user without upstream internals."""


def model_name() -> str:
    return os.getenv('JURIDIA_AI_MODEL', 'qwen3.5:4b-q4_K_M')


def base_url() -> str:
    value = os.getenv('JURIDIA_OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
    parsed = urlsplit(value)
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        raise AIError('La IA de esta instalación debe usar Ollama en una dirección local.')
    return value


def ai_status() -> dict:
    status = {'available': False, 'provider': 'ollama', 'model': model_name()}
    try:
        response = httpx.get(f'{base_url()}/api/tags', timeout=3, trust_env=False)
        response.raise_for_status()
        installed = response.json().get('models', [])
        status['available'] = any(m.get('name') == model_name() or m.get('model') == model_name() for m in installed)
        status['detail'] = 'Modelo local disponible.' if status['available'] else 'El modelo aún no está descargado. Ejecuta scripts/setup-ai.ps1.'
    except (httpx.HTTPError, ValueError, AIError):
        status['detail'] = 'Ollama no está disponible. Inicia juridIA con iniciar.ps1.'
    return status


def generate_json(system: str, data: dict, schema: type[BaseModel]) -> tuple[BaseModel, dict]:
    """Only the selected, bounded evidence is sent to the local model."""
    if not _generation_slot.acquire(blocking=False):
        raise AIError('La IA está atendiendo otra consulta. Espera a que termine e inténtalo de nuevo.')
    started = time.monotonic()
    try:
        model = model_name()
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(data, ensure_ascii=False)},
            ],
            'format': schema.model_json_schema(),
            'stream': False,
            'think': False,
            'keep_alive': '10m',
            'options': {'temperature': 0.2, 'num_ctx': 8192, 'num_predict': 1400},
        }
        response = httpx.post(f'{base_url()}/api/chat', json=payload, timeout=httpx.Timeout(240, connect=5), trust_env=False)
        response.raise_for_status()
        result = response.json()
        if not result.get('done') or result.get('done_reason') == 'length':
            raise AIError('La respuesta de la IA quedó incompleta. Acorta la consulta e inténtalo de nuevo.')
        parsed = schema.model_validate_json(result['message']['content'])
        metadata = {
            'provider': 'ollama', 'model': model,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'duration_ms': round((time.monotonic() - started) * 1000),
            'prompt_version': PROMPT_VERSION,
        }
        return parsed, metadata
    except httpx.TimeoutException:
        raise AIError('La IA local tardó demasiado en responder. Inténtalo con una consulta más breve.') from None
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            raise AIError('El modelo no está instalado en Ollama. Ejecuta scripts/setup-ai.ps1.') from None
        raise AIError('Ollama no pudo generar una respuesta. Revisa que el modelo local esté disponible.') from None
    except httpx.RequestError:
        raise AIError('No se pudo conectar con Ollama. Inicia el motor local de IA e inténtalo de nuevo.') from None
    except (ValidationError, ValueError, KeyError, TypeError):
        raise AIError('La IA devolvió una respuesta que no pasó la validación. No se ha guardado; puedes reintentar.') from None
    finally:
        _generation_slot.release()
