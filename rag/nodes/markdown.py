"""Nodo 3 — Conversión determinista a Markdown limpio y estructurado.

Genera Markdown con:
  - Front-matter YAML con metadatos.
  - Jerarquía de headings respetando la estructura detectada.
  - TOC automática si hay suficientes secciones.
  - Texto limpio sin artefactos.
"""
import re
import time
from datetime import datetime, timezone

from ..state import PipelineState


def _heading_prefix(level: int) -> str:
    return '#' * max(1, min(level + 1, 6))


def _normalize_body(body: str) -> str:
    paragraphs = re.split(r'\n\s*\n', body)
    cleaned: list[str] = []
    for para in paragraphs:
        lines = [line.strip() for line in para.split('\n') if line.strip()]
        if lines:
            cleaned.append(' '.join(lines))
    return '\n\n'.join(cleaned)


def _front_matter(state: PipelineState) -> str:
    title = state.get('title', state.get('original_filename', ''))
    lines = [
        '---',
        f'title: "{title.replace(chr(34), chr(39))}"',
        f'source_file: "{state.get("original_filename", "")}"',
        f'sha256: "{state.get("sha256", "")}"',
        f'word_count: {state.get("word_count", 0)}',
        f'char_count: {state.get("char_count", 0)}',
        f'total_pages: {state.get("total_pages", 0)}',
        f'sections: {len(state.get("sections", []))}',
        f'language: "{state.get("language_hint", "es")}"',
        f'processed_at: "{datetime.now(timezone.utc).isoformat()}"',
        f'pipeline_version: "1.0.0"',
        '---',
    ]
    return '\n'.join(lines)


# ── Nodo LangGraph ───────────────────────────────────────────────────────────

def markdown_node(state: PipelineState) -> dict:
    """Nodo de conversión a Markdown.

    Lee: sections, title, sha256, original_filename, word_count, etc.
    Escribe: markdown, markdown_size, status, steps
    """
    start = time.monotonic()
    steps = list(state.get('steps', []))

    if state.get('status') == 'failed':
        return {}

    sections = state.get('sections', [])
    if not sections:
        elapsed = round((time.monotonic() - start) * 1000)
        steps.append({'step': 'markdown', 'status': 'error', 'duration_ms': elapsed,
                       'detail': 'Sin secciones para convertir.'})
        return {'status': 'failed', 'error_code': 'NO_SECTIONS',
                'error_message': 'No se encontraron secciones.', 'steps': steps}

    parts: list[str] = []

    # Front matter
    parts.append(_front_matter(state))

    # Título principal
    title = state.get('title', '')
    if title:
        parts.append(f'# {title}')

    # TOC
    toc_entries = [s for s in sections if s.get('heading') and s.get('level', 3) <= 2]
    if len(toc_entries) >= 3:
        toc_lines = ['## Contenido', '']
        for s in toc_entries:
            indent = '  ' * max(0, s.get('level', 1) - 1)
            heading = s['heading'].strip()
            anchor = re.sub(r'[^\w\s-]', '', heading.lower())
            anchor = re.sub(r'\s+', '-', anchor.strip())
            label = heading.title() if heading.isupper() and len(heading) > 3 else heading
            toc_lines.append(f'{indent}- [{label}](#{anchor})')
        toc_lines.append('')
        parts.append('\n'.join(toc_lines))

    # Secciones
    for section in sections:
        section_parts: list[str] = []
        heading = section.get('heading', '')
        body = section.get('body', '')
        level = section.get('level', 3)
        page = section.get('page')

        if heading:
            prefix = _heading_prefix(level)
            display = heading.title() if heading.isupper() and len(heading) > 3 else heading
            section_parts.append(f'{prefix} {display}')

        if body:
            section_parts.append(_normalize_body(body))

        if page is not None:
            section_parts.append(f'<!-- página {page} -->')

        md = '\n\n'.join(section_parts)
        if md.strip():
            parts.append(md)

    # Unir y limpiar
    result = '\n\n'.join(parts)
    result = re.sub(r'\n{3,}', '\n\n', result).strip() + '\n'

    elapsed = round((time.monotonic() - start) * 1000)
    steps.append({
        'step': 'markdown', 'status': 'ok', 'duration_ms': elapsed,
        'detail': f'{len(result)} caracteres de Markdown generado',
    })

    return {
        'markdown': result,
        'markdown_size': len(result),
        'status': 'converting',
        'steps': steps,
    }
