"""Markdown parser for Mexican federal law documents.

Recognises the normative hierarchy:
    título → capítulo → sección → artículo → (body / fracciones)

Rules
-----
- The preamble (text before the first article) is kept as its own unit.
- Repeated headings and OCR artefacts are flagged as warnings, not removed.
- Article text is preserved verbatim; only trailing whitespace is stripped.
- No content is silently discarded.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

_RE_TITULO   = re.compile(r"^#{1,3}\s*\*{0,2}\s*(T[ÍI]TULO\b.*)",    re.IGNORECASE)
_RE_CAPITULO = re.compile(r"^#{1,4}\s*\*{0,2}\s*(CAP[ÍI]TULO\b.*)",  re.IGNORECASE)
_RE_SECCION  = re.compile(r"^#{1,5}\s*\*{0,2}\s*(SECCI[ÓO]N\b.*)",   re.IGNORECASE)
# Matches: ARTÍCULO 1, ARTÍCULO 1 Bis, Artículo 1o., etc.
_RE_ARTICULO = re.compile(
    r"^(?:#{1,6}\s*)?(?:\*{1,2}\s*)?ART[ÍI]CULO\s+"
    r"(\d+\s*(?:BIS|TER|QUÁTER|QUATER)?\.?)\s*"
    r"[.\-–]?\s*(?:\*{1,2}\s*)?(.*)",
    re.IGNORECASE,
)


def _clean_heading(heading: str) -> str:
    return heading.strip().strip("*").strip()


@dataclass
class ParsedUnit:
    hierarchy: dict        # {titulo, capitulo, seccion, articulo}
    locator: str           # human-readable, e.g. "Art. 5"
    citation_text: str     # verbatim text to store and cite
    warnings: list[str] = field(default_factory=list)


def _flush(
    art_label: Optional[str],
    lines: list[str],
    titulo: Optional[str],
    capitulo: Optional[str],
    seccion: Optional[str],
    in_preamble: bool,
    units: list[ParsedUnit],
) -> None:
    body = "\n".join(ln.rstrip() for ln in lines).strip()
    if not body:
        return
    if art_label is None:
        locator = "Preámbulo" if in_preamble else "Texto introductorio"
        hier = (
            {"titulo": None, "capitulo": None, "seccion": None, "articulo": None}
            if in_preamble
            else {
                "titulo": titulo,
                "capitulo": capitulo,
                "seccion": seccion,
                "articulo": None,
            }
        )
    else:
        locator = f"Art. {art_label}"
        hier = {"titulo": titulo, "capitulo": capitulo,
                "seccion": seccion, "articulo": art_label}
    units.append(ParsedUnit(hierarchy=hier, locator=locator, citation_text=body))


def parse(text: str) -> tuple[list[ParsedUnit], list[str]]:
    """Parse *text* into (units, global_warnings).  Never raises."""
    units: list[ParsedUnit] = []
    warnings: list[str] = []

    titulo: Optional[str] = None
    capitulo: Optional[str] = None
    seccion: Optional[str] = None
    current_art: Optional[str] = None
    current_lines: list[str] = []
    preamble_lines: list[str] = []
    in_preamble = True
    seen: dict[str, int] = {}  # heading → first line number

    def _heading_seen(heading: str, lineno: int) -> bool:
        if heading in seen:
            warnings.append(
                f"Line {lineno}: repeated heading '{heading}' "
                f"(first at line {seen[heading]})"
            )
            return True
        seen[heading] = lineno
        return False

    def _leave_preamble(lineno: int) -> None:
        nonlocal in_preamble
        if in_preamble:
            _flush(None, preamble_lines, None, None, None, True, units)
            preamble_lines.clear()
            in_preamble = False

    def _flush_current() -> None:
        _flush(
            current_art, current_lines, titulo, capitulo, seccion, in_preamble, units
        )
        current_lines.clear()

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()

        m = _RE_TITULO.match(line)
        if m:
            heading = _clean_heading(m.group(1))
            _heading_seen(heading, lineno)
            _leave_preamble(lineno)
            _flush_current()
            titulo, capitulo, seccion, current_art = heading, None, None, None
            continue

        m = _RE_CAPITULO.match(line)
        if m:
            heading = _clean_heading(m.group(1))
            _heading_seen(heading, lineno)
            _leave_preamble(lineno)
            _flush_current()
            capitulo, seccion, current_art = heading, None, None
            continue

        m = _RE_SECCION.match(line)
        if m:
            seccion = _clean_heading(m.group(1))
            continue

        m = _RE_ARTICULO.match(line)
        if m:
            _leave_preamble(lineno)
            _flush_current()
            art_num = m.group(1).strip().rstrip(".")
            rest = m.group(2).strip()
            current_art = art_num
            header = f"Artículo {art_num}." + (f" {rest}" if rest else "")
            current_lines.append(header)
            continue

        if in_preamble:
            preamble_lines.append(line)
        else:
            current_lines.append(line)

    # Flush remainder
    if in_preamble:
        _flush(None, preamble_lines, None, None, None, True, units)
    else:
        _flush_current()

    if not units:
        warnings.append("Parser produced zero units — check document format.")

    return units, warnings
