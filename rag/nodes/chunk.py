"""Nodo 4 — Chunking determinista para embeddings.

Estrategia:
  1. Respetar fronteras de sección (artículo = unidad primaria).
  2. Subdividir solo si excede el presupuesto del modelo.
  3. Overlap configurable entre chunks.
  4. Cada chunk incluye texto de cita + texto contextualizado para embedding.
  5. Metadatos de localización para trazabilidad (artículo, fracción, sección).
  6. IDs deterministas basados en SHA-256.
"""
import hashlib
import re
import time
from dataclasses import asdict

from ..state import PipelineState, ChunkData

# ── Configuración ────────────────────────────────────────────────────────────

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150
MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 2000
CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _make_chunk_id(doc_sha256: str, index: int, text: str) -> str:
    raw = f'{doc_sha256}:{index}:{text[:100]}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _split_long(text: str, max_size: int) -> list[str]:
    """Divide texto largo por oraciones, luego por tamaño."""
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])', text)
    if len(sentences) <= 1:
        parts = []
        for i in range(0, len(text), max_size):
            end = min(i + max_size, len(text))
            if end < len(text):
                space = text.rfind(' ', i, end)
                if space > i:
                    end = space
            parts.append(text[i:end].strip())
        return [p for p in parts if p]

    groups: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        if current_len + len(sentence) > max_size and current:
            groups.append(' '.join(current))
            current = []
            current_len = 0
        current.append(sentence)
        current_len += len(sentence) + 1
    if current:
        groups.append(' '.join(current))
    return groups


def _build_hierarchy(heading: str, level: int, parent_hierarchy: dict) -> dict:
    """Construye la jerarquía normativa del chunk."""
    hierarchy = dict(parent_hierarchy)
    if level <= 1:
        hierarchy['titulo'] = heading
        hierarchy.pop('capitulo', None)
        hierarchy.pop('seccion', None)
        hierarchy.pop('articulo', None)
    elif level == 2:
        hierarchy['capitulo'] = heading
        hierarchy.pop('seccion', None)
        hierarchy.pop('articulo', None)
    elif level == 3:
        # Detectar si es artículo
        if re.match(r'^(?:Art[ií]culo|ARTÍCULO|ARTICULO)\s+\d+', heading, re.IGNORECASE):
            hierarchy['articulo'] = heading
        else:
            hierarchy['seccion'] = heading
    return hierarchy


def _make_embedding_text(chunk_text: str, hierarchy: dict, doc_title: str) -> str:
    """Crea el texto contextualizado para el modelo de embedding.

    Antepone la jerarquía para mejorar la relevancia semántica,
    pero este prefijo NO se presenta como parte de la cita.
    """
    context_parts: list[str] = []
    if doc_title:
        context_parts.append(doc_title)
    for key in ('titulo', 'capitulo', 'seccion', 'articulo'):
        value = hierarchy.get(key)
        if value:
            context_parts.append(value)

    if context_parts:
        prefix = ' > '.join(context_parts)
        return f'{prefix}\n\n{chunk_text}'
    return chunk_text


# ── Nodo LangGraph ───────────────────────────────────────────────────────────

def chunk_node(state: PipelineState) -> dict:
    """Nodo de chunking: segmenta el Markdown respetando estructura.

    Lee: markdown, sha256, title, sections, chunk_size, chunk_overlap
    Escribe: chunks, total_chunks, avg_chunk_size, status, steps
    """
    start = time.monotonic()
    steps = list(state.get('steps', []))

    if state.get('status') == 'failed':
        return {}

    markdown = state.get('markdown', '')
    doc_sha256 = state.get('sha256', '')
    doc_title = state.get('title', '')
    sections = state.get('sections', [])
    chunk_size = state.get('chunk_size', DEFAULT_CHUNK_SIZE)
    chunk_overlap = state.get('chunk_overlap', DEFAULT_CHUNK_OVERLAP)

    if not markdown and not sections:
        elapsed = round((time.monotonic() - start) * 1000)
        steps.append({'step': 'chunk', 'status': 'error', 'duration_ms': elapsed,
                       'detail': 'Sin contenido para segmentar.'})
        return {'status': 'failed', 'error_code': 'NO_CONTENT',
                'error_message': 'Sin contenido para segmentar.', 'steps': steps}

    chunks: list[dict] = []
    chunk_index = 0
    previous_tail = ''
    current_hierarchy: dict = {}

    for section_num, section in enumerate(sections):
        heading = section.get('heading', '')
        body = section.get('body', '')
        level = section.get('level', 3)
        page = section.get('page')

        if not body and not heading:
            continue

        # Actualizar jerarquía
        current_hierarchy = _build_hierarchy(heading, level, current_hierarchy)

        heading_prefix = f'{heading}\n\n' if heading else ''
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]

        if not paragraphs and heading:
            continue

        current_parts: list[str] = []
        current_len = len(heading_prefix)

        for para_num, paragraph in enumerate(paragraphs):
            if len(paragraph) > MAX_CHUNK_SIZE:
                # Flush acumulado
                if current_parts:
                    citation_text = heading_prefix + '\n\n'.join(current_parts)
                    if previous_tail and chunk_overlap > 0:
                        citation_text = previous_tail + '\n\n' + citation_text
                    citation_text = citation_text.strip()

                    locator = heading or f'Sección {section_num + 1}, Párrafo {para_num}'
                    embedding_text = _make_embedding_text(citation_text, current_hierarchy, doc_title)

                    chunks.append({
                        'chunk_id': _make_chunk_id(doc_sha256, chunk_index, citation_text),
                        'index': chunk_index,
                        'text': citation_text,
                        'embedding_text': embedding_text,
                        'char_count': len(citation_text),
                        'estimated_tokens': _estimate_tokens(embedding_text),
                        'section_heading': heading,
                        'section_level': level,
                        'hierarchy': dict(current_hierarchy),
                        'locator': locator,
                        'content_hash': _content_hash(citation_text),
                        'page': page,
                    })
                    previous_tail = citation_text[-chunk_overlap:] if chunk_overlap else ''
                    chunk_index += 1
                    current_parts = []
                    current_len = len(heading_prefix)

                # Subdividir párrafo largo
                sub_parts = _split_long(paragraph, chunk_size - len(heading_prefix))
                for sub in sub_parts:
                    citation_text = (heading_prefix + sub).strip()
                    if previous_tail and chunk_overlap > 0:
                        citation_text = (previous_tail + '\n\n' + citation_text).strip()

                    locator = heading or f'Sección {section_num + 1}, Párrafo {para_num + 1}'
                    embedding_text = _make_embedding_text(citation_text, current_hierarchy, doc_title)

                    chunks.append({
                        'chunk_id': _make_chunk_id(doc_sha256, chunk_index, citation_text),
                        'index': chunk_index,
                        'text': citation_text,
                        'embedding_text': embedding_text,
                        'char_count': len(citation_text),
                        'estimated_tokens': _estimate_tokens(embedding_text),
                        'section_heading': heading,
                        'section_level': level,
                        'hierarchy': dict(current_hierarchy),
                        'locator': locator,
                        'content_hash': _content_hash(citation_text),
                        'page': page,
                    })
                    previous_tail = citation_text[-chunk_overlap:] if chunk_overlap else ''
                    chunk_index += 1
                continue

            # ¿Cabe en el chunk actual?
            if current_len + len(paragraph) + 2 > chunk_size and current_parts:
                # Flush
                citation_text = heading_prefix + '\n\n'.join(current_parts)
                if previous_tail and chunk_overlap > 0:
                    citation_text = previous_tail + '\n\n' + citation_text
                citation_text = citation_text.strip()

                locator = heading or f'Sección {section_num + 1}, Párrafo {para_num + 1}'
                embedding_text = _make_embedding_text(citation_text, current_hierarchy, doc_title)

                chunks.append({
                    'chunk_id': _make_chunk_id(doc_sha256, chunk_index, citation_text),
                    'index': chunk_index,
                    'text': citation_text,
                    'embedding_text': embedding_text,
                    'char_count': len(citation_text),
                    'estimated_tokens': _estimate_tokens(embedding_text),
                    'section_heading': heading,
                    'section_level': level,
                    'hierarchy': dict(current_hierarchy),
                    'locator': locator,
                    'content_hash': _content_hash(citation_text),
                    'page': page,
                })
                previous_tail = citation_text[-chunk_overlap:] if chunk_overlap else ''
                chunk_index += 1
                current_parts = []
                current_len = len(heading_prefix)

            current_parts.append(paragraph)
            current_len += len(paragraph) + 2

        # Flush último acumulado de la sección
        if current_parts:
            citation_text = heading_prefix + '\n\n'.join(current_parts)
            if previous_tail and chunk_overlap > 0:
                citation_text = previous_tail + '\n\n' + citation_text
            citation_text = citation_text.strip()

            locator = heading or f'Sección {section_num + 1}'
            embedding_text = _make_embedding_text(citation_text, current_hierarchy, doc_title)

            if len(citation_text) >= MIN_CHUNK_SIZE or not chunks:
                chunks.append({
                    'chunk_id': _make_chunk_id(doc_sha256, chunk_index, citation_text),
                    'index': chunk_index,
                    'text': citation_text,
                    'embedding_text': embedding_text,
                    'char_count': len(citation_text),
                    'estimated_tokens': _estimate_tokens(embedding_text),
                    'section_heading': heading,
                    'section_level': level,
                    'hierarchy': dict(current_hierarchy),
                    'locator': locator,
                    'content_hash': _content_hash(citation_text),
                    'page': page,
                })
                previous_tail = citation_text[-chunk_overlap:] if chunk_overlap else ''
                chunk_index += 1
            elif chunks:
                # Merge con anterior
                prev = chunks[-1]
                merged = prev['text'] + '\n\n' + citation_text
                merged_emb = _make_embedding_text(merged, current_hierarchy, doc_title)
                chunks[-1] = {
                    **prev,
                    'chunk_id': _make_chunk_id(doc_sha256, prev['index'], merged),
                    'text': merged,
                    'embedding_text': merged_emb,
                    'char_count': len(merged),
                    'estimated_tokens': _estimate_tokens(merged_emb),
                    'content_hash': _content_hash(merged),
                }

    total = len(chunks)
    avg = sum(c['char_count'] for c in chunks) // max(total, 1)

    elapsed = round((time.monotonic() - start) * 1000)
    steps.append({
        'step': 'chunk', 'status': 'ok', 'duration_ms': elapsed,
        'detail': f'{total} chunks, promedio {avg} chars',
    })

    return {
        'chunks': chunks,
        'total_chunks': total,
        'avg_chunk_size': avg,
        'status': 'chunking',
        'steps': steps,
    }
