"""Nodo 6 — Generación de embeddings con Ollama (all-minilm).

Itera sobre los chunks producidos por el nodo de chunking y genera un
vector de embedding para cada uno usando el cliente local de Ollama.

Este nodo es OPCIONAL en el grafo: si `generate_embeddings` es False
en el estado inicial, se salta y los chunks quedan con status 'pending'.

Dependencias:
  - Ollama corriendo localmente con el modelo configurado descargado.
  - httpx (incluido en requirements.txt).
  - rag/embedder.py — cliente HTTP validado para /api/embed.
"""
import time
from typing import Any

import httpx

from ..state import PipelineState


# ── Nodo LangGraph ───────────────────────────────────────────────────────────

def embed_node(state: PipelineState) -> dict:
    """Nodo de embedding: genera vectores para cada chunk del documento.

    Lee: chunks, generate_embeddings, status
    Escribe: chunks (con campo 'embedding'), embedding_model,
             embedding_status, embedded_count, steps

    Cada chunk en el estado recibe un campo 'embedding' con el vector
    de floats, o se marca con 'embedding_error' si falla para ese chunk.
    El nodo no falla globalmente por errores de chunks individuales;
    solo falla si Ollama no está disponible en absoluto.
    """
    start = time.monotonic()
    steps = list(state.get('steps', []))

    if state.get('status') == 'failed':
        return {}

    # Si no se pidió generar embeddings, saltar silenciosamente.
    if not state.get('generate_embeddings', False):
        elapsed = round((time.monotonic() - start) * 1000)
        steps.append({
            'step': 'embed', 'status': 'skipped', 'duration_ms': elapsed,
            'detail': 'generate_embeddings=False — embeddings omitidos',
        })
        return {
            'embedding_status': 'pending',
            'embedded_count': 0,
            'steps': steps,
        }

    chunks: list[dict] = list(state.get('chunks', []))
    if not chunks:
        elapsed = round((time.monotonic() - start) * 1000)
        steps.append({
            'step': 'embed', 'status': 'skipped', 'duration_ms': elapsed,
            'detail': 'Sin chunks para embedir',
        })
        return {'embedding_status': 'pending', 'embedded_count': 0, 'steps': steps}

    def _fail(msg: str, code: str) -> dict:
        elapsed = round((time.monotonic() - start) * 1000)
        steps.append({'step': 'embed', 'status': 'error', 'duration_ms': elapsed, 'detail': msg})
        return {
            'status': 'failed',
            'error_code': code,
            'error_message': msg,
            'embedding_status': 'failed',
            'steps': steps,
        }

    # Importar utilidades del módulo embedder legacy
    try:
        from ..embedder import check_model, embed, _assert_loopback
        from ..config import ollama_url, embedding_model as get_model_name
    except ImportError as exc:
        return _fail(f'No se pudo importar el cliente de embeddings: {exc}', 'EMBED_IMPORT_ERROR')

    # Verificar que Ollama y el modelo estén disponibles
    try:
        with httpx.Client() as client:
            model_digest = check_model(client)
    except RuntimeError as exc:
        return _fail(str(exc), 'EMBED_MODEL_UNAVAILABLE')
    except Exception as exc:
        return _fail(f'Error al verificar el modelo de embedding: {exc}', 'EMBED_CHECK_ERROR')

    model_name = get_model_name()

    # Generar embeddings chunk a chunk
    enriched: list[dict] = []
    embedded_count = 0
    failed_count = 0

    with httpx.Client() as client:
        for chunk in chunks:
            text = chunk.get('embedding_text') or chunk.get('text', '')
            if not text:
                enriched.append({**chunk, 'embedding_error': 'Texto de embedding vacío'})
                failed_count += 1
                continue

            try:
                vector = embed(client, text)
                enriched.append({**chunk, 'embedding': vector})
                embedded_count += 1
            except RuntimeError as exc:
                enriched.append({**chunk, 'embedding_error': str(exc)})
                failed_count += 1

    elapsed = round((time.monotonic() - start) * 1000)

    if embedded_count == 0 and failed_count > 0:
        steps.append({
            'step': 'embed', 'status': 'error', 'duration_ms': elapsed,
            'detail': f'Todos los embeddings fallaron ({failed_count} chunks)',
        })
        return {
            'chunks': enriched,
            'embedding_model': model_name,
            'embedding_status': 'failed',
            'embedded_count': 0,
            'steps': steps,
            'status': 'failed',
            'error_code': 'EMBED_ALL_FAILED',
            'error_message': f'No se pudo generar ningún embedding ({failed_count} fallos).',
        }

    final_status = 'ready' if failed_count == 0 else 'partial'
    detail = f'{embedded_count}/{len(chunks)} embeddings generados (modelo: {model_name})'
    if failed_count:
        detail += f', {failed_count} fallidos'

    steps.append({'step': 'embed', 'status': 'ok', 'duration_ms': elapsed, 'detail': detail})

    return {
        'chunks': enriched,
        'embedding_model': model_name,
        'embedding_model_digest': model_digest,
        'embedding_status': final_status,
        'embedded_count': embedded_count,
        'steps': steps,
    }
