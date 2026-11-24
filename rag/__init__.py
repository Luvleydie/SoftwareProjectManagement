"""Pipeline determinista de ingesta RAG con LangGraph.

Topología del grafo:
  sanitize → parse → markdown → chunk → [embed] → [persist] → END

Nodos opcionales:
  embed   — genera vectores con Ollama (activar con generate_embeddings=True)
  persist — guarda en PostgreSQL (activar con persist=True, default True)

Punto de entrada rápido:
    from rag import run_pipeline

    result = run_pipeline(
        content=open('ley.pdf', 'rb').read(),
        filename='ley.pdf',
        owner_id='uuid-del-usuario',
        generate_embeddings=False,   # True cuando Ollama tenga el modelo embed
    )

Acceso a todas las herramientas y utilidades:
    from rag.tools import build_chunks, embed, check_postgres, ...
"""
from .graph import run_pipeline, compile_ingestion_graph, build_ingestion_graph, PIPELINE_VERSION

__all__ = [
    'run_pipeline',
    'compile_ingestion_graph',
    'build_ingestion_graph',
    'PIPELINE_VERSION',
]
