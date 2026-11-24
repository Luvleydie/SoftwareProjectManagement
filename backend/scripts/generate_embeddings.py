"""Generate RAG embeddings using the canonical local ingestion pipeline."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.main import main


if __name__ == "__main__":
    raise SystemExit(main())
