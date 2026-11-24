"""Nodo 1 — Sanitización del binario no confiable.

Verificaciones deterministas (sin heurísticas ni IA):
  1. Tamaño máximo (configurable, default 20 MB).
  2. Detección de tipo real por magic bytes (no confiar en Content-Type).
  3. Extensión coherente con el tipo detectado.
  4. Rechazo de archivos con patrones peligrosos (macros, scripts embebidos).
  5. Hash SHA-256 para deduplicación e integridad.
"""
import hashlib
import time

from ..state import PipelineState, MIME_TO_DOCTYPE

# ── Magic bytes ──────────────────────────────────────────────────────────────

MAGIC_SIGNATURES: dict[str, list[tuple[int, bytes]]] = {
    'application/pdf': [(0, b'%PDF')],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [
        (0, b'PK\x03\x04'),
    ],
}

MIME_TO_EXTENSIONS: dict[str, set[str]] = {
    'application/pdf': {'.pdf'},
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {'.docx'},
    'text/plain': {'.txt', '.md', '.text'},
}

DANGEROUS_PATTERNS: list[tuple[str, bytes]] = [
    ('vba_macro', b'VBAProject'),
    ('vba_macro', b'_VBA_PROJECT'),
    ('javascript', b'/JavaScript'),
    ('javascript', b'/JS'),
    ('launch_action', b'/Launch'),
    ('openaction', b'/OpenAction'),
    ('embedded_file', b'/EmbeddedFile'),
    ('acroform', b'/AcroForm'),
]

DEFAULT_MAX_SIZE = 20 * 1024 * 1024


def _detect_mime(content: bytes, filename: str) -> str:
    """Detecta el tipo MIME real basándose en magic bytes."""
    for mime, signatures in MAGIC_SIGNATURES.items():
        for offset, magic in signatures:
            if content[offset:offset + len(magic)] == magic:
                if mime.startswith('application/vnd.openxmlformats'):
                    if b'word/' not in content[:4096]:
                        continue
                return mime
    # Intentar detectar como texto plano
    try:
        content[:8192].decode('utf-8')
        if content.count(b'\x00') / max(len(content), 1) < 0.01:
            return 'text/plain'
    except UnicodeDecodeError:
        pass
    raise ValueError(
        'No se pudo identificar el tipo de archivo. Solo se aceptan PDF, DOCX y TXT.'
    )


def _scan_dangerous(content: bytes) -> list[str]:
    """Busca patrones binarios peligrosos."""
    return list({label for label, pattern in DANGEROUS_PATTERNS if pattern in content})


# ── Nodo LangGraph ───────────────────────────────────────────────────────────

def sanitize_node(state: PipelineState) -> dict:
    """Nodo de sanitización: valida el binario y extrae metadatos básicos.

    Lee: raw_content, original_filename, max_file_size
    Escribe: detected_mime, detected_type, sha256, file_size, status, steps
    """
    start = time.monotonic()
    content = state['raw_content']
    filename = state.get('original_filename', 'unknown')
    max_size = state.get('max_file_size', DEFAULT_MAX_SIZE)
    steps = list(state.get('steps', []))

    def _fail(msg: str, code: str) -> dict:
        elapsed = round((time.monotonic() - start) * 1000)
        steps.append({'step': 'sanitize', 'status': 'error', 'duration_ms': elapsed, 'detail': msg})
        return {
            'status': 'failed',
            'error_code': code,
            'error_message': msg,
            'steps': steps,
            'file_size': len(content),
        }

    # 1. Vacío
    if len(content) == 0:
        return _fail('El archivo está vacío.', 'EMPTY_FILE')

    # 2. Tamaño
    if len(content) > max_size:
        return _fail(
            f'El archivo excede el límite de {max_size // (1024 * 1024)} MB.',
            'TOO_LARGE',
        )

    # 3. Tipo real
    try:
        detected_mime = _detect_mime(content, filename)
    except ValueError as exc:
        return _fail(str(exc), 'UNKNOWN_TYPE')

    # 4. Extensión coherente
    ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    allowed = MIME_TO_EXTENSIONS.get(detected_mime, set())
    if ext and allowed and ext not in allowed:
        return _fail(
            f'La extensión "{ext}" no coincide con el contenido detectado ({detected_mime}).',
            'EXTENSION_MISMATCH',
        )

    # 5. Patrones peligrosos
    threats = _scan_dangerous(content)
    if threats:
        return _fail(
            f'Contenido potencialmente peligroso: {", ".join(sorted(threats))}.',
            'DANGEROUS_CONTENT',
        )

    # 6. Hash SHA-256
    sha256 = hashlib.sha256(content).hexdigest()

    # Determinar tipo de documento
    doc_type = MIME_TO_DOCTYPE.get(detected_mime, 'txt')
    if hasattr(doc_type, 'value'):
        doc_type = doc_type.value

    elapsed = round((time.monotonic() - start) * 1000)
    steps.append({
        'step': 'sanitize', 'status': 'ok', 'duration_ms': elapsed,
        'detail': f'Tipo: {detected_mime}, SHA-256: {sha256[:12]}…, {len(content)} bytes',
    })

    return {
        'detected_mime': detected_mime,
        'detected_type': doc_type,
        'sha256': sha256,
        'file_size': len(content),
        'status': 'sanitizing',
        'steps': steps,
    }
