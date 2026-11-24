"""Pipeline determinista de ingesta RAG con LangGraph.

Cada paso de ingesta es un nodo LangGraph:
  sanitize → parse → markdown → chunk → persist

El grafo es compilable, serializable, determinista e idempotente.
Diseñado para conectarse con otros grafos LangGraph (retrieval, QA, etc.).
"""
