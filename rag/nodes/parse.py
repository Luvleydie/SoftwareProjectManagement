"""Nodo 2 — Extracción determinista de texto y estructura.

Parsers para PDF (PyMuPDF), DOCX (python-docx) y TXT/MD.
Cada parser produce una lista de Section con heading, body, level y page.
"""
import io
import re
import time
from dataclasses import asdict

from ..state import PipelineState, Section

# ── Patrones para estructura legal mexicana ──────────────────────────────────

_HEADING_PATTERNS = [
    (1, re.compile(
        r'^(?:TÍTULO|CAPITULO|CAPÍTULO)\s+[IVXLCDM\d]+[\.\-\s]*(.*)$',
        re.IGNORECASE | re.MULTILINE,
    )),
    (2, re.compile(
        r'^(?:SECCIÓN|SECCION|Sección)\s+[IVXLCDM\d]+[\.\-\s]*(.*)$',
        re.IGNORECASE | re.MULTILINE,
    )),
    (3, re.compile(
        r'^(?:Art[ií]culo|ARTÍCULO|ARTICULO)\s+\d+[\w\s\.\-]*[\.\-]',
        re.IGNORECASE | re.MULTILINE,
    )),
    (1, re.compile(r'^([A-ZÁÉÍÓÚÑ\s]{12,})$', re.MULTILINE)),
]

_ES_STOPWORDS = frozenset({
    'de', 'la', 'el', 'en', 'los', 'las', 'del', 'que', 'por', 'con',
    'para', 'una', 'se', 'su', 'al', 'es', 'lo', 'como', 'más', 'pero',
    'sus', 'le', 'ya', 'o', 'este', 'entre', 'también', 'fue', 'esta',
    'son', 'dos', 'ser', 'ha', 'y', 'a',
})


def _detect_language(text: str) -> str:
    words = text.lower().split()[:500]
    if not words:
        return 'unknown'
    es_count = sum(1 for w in words if w in _ES_STOPWORDS)
    return 'es' if es_count / len(words) > 0.15 else 'other'


def _clean_text(text: str) -> str:
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _detect_sections(text: str) -> list[Section]:
    lines = text.split('\n')
    sections: list[Section] = []
    current_heading = ''
    current_level = 3
    current_body: list[str] = []

    def flush():
        body = '\n'.join(current_body).strip()
        if body or current_heading:
            sections.append(Section(level=current_level, heading=current_heading, body=body))

    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_body.append('')
            continue

        matched = False
        for level, pattern in _HEADING_PATTERNS:
            if pattern.match(stripped):
                flush()
                current_heading = stripped
                current_level = level
                current_body = []
                matched = True
                break

        if not matched:
            current_body.append(line)

    flush()
    if not sections:
        sections = [Section(level=3, heading='', body=text)]
    return sections


# ── Parsers ──────────────────────────────────────────────────────────────────

def _parse_pdf(content: bytes) -> tuple[list[Section], str, int, list[str]]:
    try:
        import fitz
    except ImportError:
        raise RuntimeError('PyMuPDF no está instalado. Ejecuta: pip install pymupdf')

    try:
        doc = fitz.open(stream=content, filetype='pdf')
    except Exception:
        raise ValueError('No se pudo abrir el PDF. El archivo puede estar corrupto o protegido.')

    all_text: list[str] = []
    page_texts: list[tuple[int, str]] = []
    warnings: list[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text('text')
        if text.strip():
            all_text.append(text)
            page_texts.append((page_num + 1, text))

    doc.close()

    if not all_text:
        raise ValueError(
            'El PDF no contiene texto extraíble. Puede ser un PDF de imagen (escaneado).'
        )

    full_text = _clean_text('\n\n'.join(all_text))
    sections = _detect_sections(full_text)

    # Asignar páginas a secciones
    for section in sections:
        for page_num, page_text in page_texts:
            if section.body[:80] in page_text or section.heading in page_text:
                object.__setattr__(section, 'page', page_num)
                break

    # Título
    title = ''
    try:
        meta = fitz.open(stream=content, filetype='pdf').metadata
        title = (meta.get('title') or '').strip()
    except Exception:
        pass
    if not title:
        title = next((s.heading for s in sections if s.heading), '')

    return sections, title, len(page_texts) or 1, warnings


def _parse_docx(content: bytes) -> tuple[list[Section], str, int, list[str]]:
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError('python-docx no está instalado. Ejecuta: pip install python-docx')

    try:
        doc = Document(io.BytesIO(content))
    except Exception:
        raise ValueError('No se pudo abrir el archivo DOCX. Puede estar corrupto.')

    sections: list[Section] = []
    current_heading = ''
    current_level = 3
    body_parts: list[str] = []
    warnings: list[str] = []

    def flush():
        body = '\n'.join(body_parts).strip()
        if body or current_heading:
            sections.append(Section(level=current_level, heading=current_heading, body=body))

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            body_parts.append('')
            continue

        style_name = (paragraph.style.name or '').lower()

        if 'heading' in style_name or 'título' in style_name:
            flush()
            level_match = re.search(r'(\d)', style_name)
            current_level = int(level_match.group(1)) if level_match else 1
            current_heading = text
            body_parts = []
        else:
            matched = False
            for level, pattern in _HEADING_PATTERNS:
                if pattern.match(text):
                    flush()
                    current_heading = text
                    current_level = level
                    body_parts = []
                    matched = True
                    break
            if not matched:
                body_parts.append(text)

    flush()

    # Tablas
    for i, table in enumerate(doc.tables):
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(' | '.join(cells))
        if rows:
            sections.append(Section(level=3, heading=f'Tabla {i + 1}', body='\n'.join(rows)))

    if not sections:
        full_text = _clean_text('\n'.join(p.text for p in doc.paragraphs if p.text.strip()))
        if not full_text:
            raise ValueError('El documento DOCX está vacío.')
        sections = [Section(level=3, heading='', body=full_text)]

    title = ''
    try:
        title = (doc.core_properties.title or '').strip()
    except Exception:
        pass
    if not title:
        title = next((s.heading for s in sections if s.heading), '')

    return sections, title, 0, warnings


def _parse_txt(content: bytes) -> tuple[list[Section], str, int, list[str]]:
    text = None
    warnings: list[str] = []
    for encoding in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
        try:
            text = content.decode(encoding)
            break
        except (UnicodeDecodeError, ValueError):
            continue

    if text is None:
        raise ValueError('No se pudo decodificar el archivo de texto.')

    text = _clean_text(text)
    if not text:
        raise ValueError('El archivo de texto está vacío.')

    # Detectar artefactos de OCR/HTML
    ocr_artifacts = re.findall(r'<!\-\-.*?\-\->', text)
    if ocr_artifacts:
        warnings.append(f'{len(ocr_artifacts)} artefactos HTML/OCR detectados, conservados sin eliminar.')

    repeated_headers = re.findall(
        r'^(?:O\s*R\s*D\s*E\s*N|Ley de los Institutos).*$', text, re.MULTILINE | re.IGNORECASE
    )
    if len(repeated_headers) > 2:
        warnings.append(f'{len(repeated_headers)} encabezados repetidos detectados (posible OCR de páginas).')

    sections = _detect_sections(text)

    title = ''
    if sections and sections[0].heading:
        title = sections[0].heading
    else:
        first_line = text.split('\n', 1)[0].strip()
        if 5 <= len(first_line) <= 200:
            title = first_line

    return sections, title, 0, warnings


PARSERS: dict[str, callable] = {
    'application/pdf': _parse_pdf,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': _parse_docx,
    'text/plain': _parse_txt,
}


# ── Nodo LangGraph ───────────────────────────────────────────────────────────

def parse_node(state: PipelineState) -> dict:
    """Nodo de parsing: extrae texto estructurado del documento.

    Lee: raw_content, detected_mime, status
    Escribe: sections, title, total_pages, word_count, char_count,
             language_hint, parse_warnings, status, steps
    """
    start = time.monotonic()
    steps = list(state.get('steps', []))

    # Si ya falló en un paso anterior, no procesar
    if state.get('status') == 'failed':
        return {}

    content = state['raw_content']
    mime = state['detected_mime']

    def _fail(msg: str, code: str) -> dict:
        elapsed = round((time.monotonic() - start) * 1000)
        steps.append({'step': 'parse', 'status': 'error', 'duration_ms': elapsed, 'detail': msg})
        return {'status': 'failed', 'error_code': code, 'error_message': msg, 'steps': steps}

    parser = PARSERS.get(mime)
    if not parser:
        return _fail(f'Tipo no soportado: {mime}', 'UNSUPPORTED_TYPE')

    try:
        sections, title, total_pages, warnings = parser(content)
    except (ValueError, RuntimeError) as exc:
        code = 'PARSE_ERROR'
        if 'instalado' in str(exc):
            code = 'MISSING_DEPENDENCY'
        return _fail(str(exc), code)

    # Serializar secciones como dicts para el estado
    sections_dicts = [
        {'level': s.level, 'heading': s.heading, 'body': s.body, 'page': s.page}
        for s in sections
    ]

    full_text = '\n\n'.join(
        f'{s.heading}\n{s.body}' if s.heading else s.body for s in sections
    )
    full_text = _clean_text(full_text)
    word_count = len(full_text.split())

    elapsed = round((time.monotonic() - start) * 1000)
    steps.append({
        'step': 'parse', 'status': 'ok', 'duration_ms': elapsed,
        'detail': f'{len(sections)} secciones, {word_count} palabras, {len(warnings)} advertencias',
    })

    return {
        'sections': sections_dicts,
        'title': title,
        'total_pages': total_pages,
        'word_count': word_count,
        'char_count': len(full_text),
        'language_hint': _detect_language(full_text),
        'parse_warnings': warnings,
        'status': 'parsing',
        'steps': steps,
    }
