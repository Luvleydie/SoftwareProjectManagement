import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.embedder import check_model
from rag.parser import parse


def test_model_check_uses_digest_from_local_ollama_tags(monkeypatch):
    monkeypatch.setenv("JURIDIA_EMBED_MODEL", "all-minilm:latest")
    monkeypatch.setattr("rag.embedder.ollama_url", lambda: "http://127.0.0.1:11434")

    def handle(request):
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"name": "all-minilm:latest"})
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "all-minilm:latest", "digest": "verified-digest"}
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        assert check_model(client) == "verified-digest"


def test_parser_recognizes_bold_article_headings_and_keeps_preamble():
    units, warnings = parse(
        "Preambulo legal.\n\n"
        "# **TÍTULO PRIMERO Disposiciones generales**\n"
        "## **Capítulo Único**\n"
        "**ARTÍCULO 1.** Texto del primer artículo.\n"
        "# **TÍTULO SEGUNDO**\n"
        "Texto introductorio del segundo título.\n"
        "**ARTÍCULO 7 bis.-** Texto del artículo adicional."
    )

    assert [unit.locator for unit in units] == [
        "Preámbulo",
        "Art. 1",
        "Texto introductorio",
        "Art. 7 bis",
    ]
    assert units[1].hierarchy["titulo"] == "TÍTULO PRIMERO Disposiciones generales"
    assert units[1].hierarchy["capitulo"] == "Capítulo Único"
    assert units[1].citation_text == "Artículo 1. Texto del primer artículo."
    assert units[2].hierarchy["titulo"] == "TÍTULO SEGUNDO"
    assert units[2].citation_text == "Texto introductorio del segundo título."
    assert units[3].citation_text == "Artículo 7 bis. Texto del artículo adicional."
    assert warnings == []
