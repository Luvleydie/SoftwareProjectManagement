"""Grafo LangGraph del pipeline determinista de ingesta.

Topología:
  sanitize → should_continue → parse → markdown → chunk → persist
                             ↘ END (si sanitize falló)

El grafo es compilable, serializable y se puede componer con otros
grafos LangGraph (retrieval, embeddings, QA) para formar el sistema RAG.
"""
from langgraph.graph import END, StateGraph

from .state import PipelineState
from .nodes import sanitize_node, parse_node, markdown_node, chunk_node, persist_node

PIPELINE_VERSION = '1.0.0'


def _should_continue(state: PipelineState) -> str:
    """Conditional edge: si algún paso falló, ir a END directamente."""
    if state.get('status') == 'failed':
        return 'end'
    return 'continue'


def build_ingestion_graph(*, with_persistence: bool = True) -> StateGraph:
    """Construye el grafo de ingesta.

    Parameters
    ----------
    with_persistence : bool
        Si True, incluye el nodo de persistencia en PostgreSQL.
        Si False, el grafo termina en chunking (modo preview/dry-run).

    Returns
    -------
    StateGraph
        Grafo LangGraph compilable.
    """
    graph = StateGraph(PipelineState)

    # ── Registrar nodos ──────────────────────────────────────────────────
    graph.add_node('sanitize', sanitize_node)
    graph.add_node('parse', parse_node)
    graph.add_node('markdown', markdown_node)
    graph.add_node('chunk', chunk_node)
    if with_persistence:
        graph.add_node('persist', persist_node)

    # ── Entry point ──────────────────────────────────────────────────────
    graph.set_entry_point('sanitize')

    # ── Edges con conditional routing ────────────────────────────────────
    # Después de sanitize: si falló → END, si no → parse
    graph.add_conditional_edges(
        'sanitize',
        _should_continue,
        {'continue': 'parse', 'end': END},
    )

    # Después de parse: si falló → END, si no → markdown
    graph.add_conditional_edges(
        'parse',
        _should_continue,
        {'continue': 'markdown', 'end': END},
    )

    # Después de markdown: si falló → END, si no → chunk
    graph.add_conditional_edges(
        'markdown',
        _should_continue,
        {'continue': 'chunk', 'end': END},
    )

    if with_persistence:
        # Después de chunk: si falló → END, si no → persist
        graph.add_conditional_edges(
            'chunk',
            _should_continue,
            {'continue': 'persist', 'end': END},
        )
        # persist → END
        graph.add_edge('persist', END)
    else:
        # Sin persistencia: chunk → END
        graph.add_edge('chunk', END)

    return graph


def compile_ingestion_graph(*, with_persistence: bool = True):
    """Compila el grafo y lo devuelve listo para invocar.

    Uso:
        app = compile_ingestion_graph()
        result = app.invoke({
            'raw_content': content_bytes,
            'original_filename': 'documento.pdf',
        })
    """
    graph = build_ingestion_graph(with_persistence=with_persistence)
    return graph.compile()


# ── Función de conveniencia ──────────────────────────────────────────────────

def run_pipeline(
    content: bytes,
    filename: str,
    *,
    owner_id: str = '',
    source_version_id: str = '',
    max_file_size: int = 20 * 1024 * 1024,
    chunk_size: int = 1200,
    chunk_overlap: int = 150,
    persist: bool = True,
) -> dict:
    """Ejecuta el pipeline completo de ingesta.

    Punto de entrada principal tanto para la CLI como para FastAPI.
    Devuelve el estado final del grafo.
    """
    import time
    from datetime import datetime, timezone

    app = compile_ingestion_graph(with_persistence=persist)
    pipeline_start = time.monotonic()

    initial_state: PipelineState = {
        'raw_content': content,
        'original_filename': filename,
        'max_file_size': max_file_size,
        'chunk_size': chunk_size,
        'chunk_overlap': chunk_overlap,
        'owner_id': owner_id,
        'source_version_id': source_version_id,
        'steps': [],
        'pipeline_version': PIPELINE_VERSION,
        'status': 'pending',
    }

    result = app.invoke(initial_state)

    # Calcular duración total
    result['duration_total_ms'] = round((time.monotonic() - pipeline_start) * 1000)

    if 'processed_at' not in result or not result.get('processed_at'):
        result['processed_at'] = datetime.now(timezone.utc).isoformat()

    return result
