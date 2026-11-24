"""Source file validator.

Checks existence, UTF-8 encoding, size limit and computes SHA-256 over the
original bytes.  The source file is never modified.
"""
import hashlib
from dataclasses import dataclass
from pathlib import Path

_MAX_BYTES = 10 * 1024 * 1024  # 10 MB hard limit


@dataclass(frozen=True)
class SourceInfo:
    path: Path
    sha256: str
    size_bytes: int
    text: str  # decoded UTF-8 content — do not mutate


def validate(path: Path) -> SourceInfo:
    """Validate *path* and return a SourceInfo.

    Raises RuntimeError with a descriptive message on any failure.
    """
    if not path.exists():
        raise RuntimeError(f"Source file not found: {path}")
    if not path.is_file():
        raise RuntimeError(f"Source path is not a regular file: {path}")

    raw = path.read_bytes()

    if len(raw) == 0:
        raise RuntimeError(f"Source file is empty: {path}")
    if len(raw) > _MAX_BYTES:
        raise RuntimeError(
            f"Source file exceeds size limit "
            f"({len(raw):,} bytes > {_MAX_BYTES:,}): {path}"
        )

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Source file is not valid UTF-8: {path} — {exc}"
        ) from exc

    sha256 = hashlib.sha256(raw).hexdigest()
    return SourceInfo(path=path, sha256=sha256, size_bytes=len(raw), text=text)
