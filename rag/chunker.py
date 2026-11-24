"""Chunker: splits ParsedUnit objects into token-budget-sized chunks.

Primary rule: one article per chunk when it fits within TOKEN_BUDGET.
If it exceeds the budget, split by paragraph, then by sentence.
Articles are never mixed across chunks.
The context prefix (law title + hierarchy) is prepended for embedding only;
it is not stored as part of citation_text.
"""
import hashlib
import re
from dataclasses import dataclass

from .config import EMBEDDING_DIMENSION, TOKEN_BUDGET, OVERLAP_RATIO
from .parser import ParsedUnit

# Approximate tokens: split on whitespace (good enough for all-minilm).
def _token_count(text: str) -> int:
    return len(text.split())


@dataclass
class Chunk:
    ordinal: int
    hierarchy: dict
    locator: str
    citation_text: str       # verbatim text to store and cite
    embedding_input: str     # citation_text prefixed with context
    content_hash: str        # sha256 of citation_text
    embedding_input_hash: str  # sha256 of embedding_input


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_prefix(law_title: str, unit: ParsedUnit) -> str:
    h = unit.hierarchy
    parts = [law_title]
    if h.get("titulo"):
        parts.append(h["titulo"])
    if h.get("capitulo"):
        parts.append(h["capitulo"])
    if h.get("seccion"):
        parts.append(h["seccion"])
    parts.append(unit.locator)
    return " | ".join(parts) + "\n"


def _make_chunk(ordinal: int, unit: ParsedUnit, text: str, prefix: str) -> Chunk:
    embedding_input = prefix + text
    return Chunk(
        ordinal=ordinal,
        hierarchy=unit.hierarchy,
        locator=unit.locator,
        citation_text=text,
        embedding_input=embedding_input,
        content_hash=_sha256(text),
        embedding_input_hash=_sha256(embedding_input),
    )


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _pack(
    segments: list[str],
    budget: int,
    overlap_ratio: float,
) -> list[str]:
    """Pack segments into groups that fit within *budget* tokens.

    Overlap is applied between consecutive groups by repeating the last
    ceil(overlap_ratio * group_size) segments at the start of the next group.
    """
    groups: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for seg in segments:
        seg_tokens = _token_count(seg)
        if current and current_tokens + seg_tokens > budget:
            groups.append("\n\n".join(current))
            # Overlap: carry over tail of current group
            overlap_count = max(1, int(len(current) * overlap_ratio))
            current = current[-overlap_count:]
            current_tokens = sum(_token_count(s) for s in current)
        current.append(seg)
        current_tokens += seg_tokens

    if current:
        groups.append("\n\n".join(current))
    return groups


def build_chunks(units: list[ParsedUnit], law_title: str) -> list[Chunk]:
    """Convert ParsedUnit list into Chunk list respecting TOKEN_BUDGET."""
    chunks: list[Chunk] = []
    ordinal = 0

    for unit in units:
        prefix = _make_prefix(law_title, unit)
        prefix_tokens = _token_count(prefix)
        effective_budget = TOKEN_BUDGET - prefix_tokens

        full_tokens = _token_count(unit.citation_text)
        if full_tokens <= effective_budget:
            chunks.append(_make_chunk(ordinal, unit, unit.citation_text, prefix))
            ordinal += 1
            continue

        # Try splitting by paragraph first
        paragraphs = _split_paragraphs(unit.citation_text)
        if len(paragraphs) > 1:
            groups = _pack(paragraphs, effective_budget, OVERLAP_RATIO)
        else:
            # Fall back to sentence splitting
            sentences = _split_sentences(unit.citation_text)
            groups = _pack(sentences, effective_budget, OVERLAP_RATIO)

        for group_text in groups:
            if group_text.strip():
                chunks.append(_make_chunk(ordinal, unit, group_text, prefix))
                ordinal += 1

    return chunks
