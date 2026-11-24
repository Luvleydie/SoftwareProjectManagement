"""Grafo LangGraph del pipeline determinista de ingesta.

Topología:
  sanitize → parse → markdown → chunk → embed → persist → END

Cada arista es condicional: si algún nodo marca status='failed', el grafo
va directamente a END sin ejecutar los nodos siguientes.

Parámetros de compilación:
  with_persistence   — incluye el nodo persist (False = dry-run / preview).
  with_embeddings    — incluye el nodo embed. Si False, los chunks quedan con
                       embedding_status='pending' para procesamiento posterior.

El grafo es compilable, serializable y se puede componer con otros grafos
LangGraph (retrieval, QA) para formar el sistema RAG completo.
"""
from langgraph.graph import END, StateGraph

from .state import PipelineState
from .nodes import sanitize_node, parse_node, markdown_node, chunk_node, embed_node, persist_node

PIPELINE_VERSION = '1.1.0'


def _should_continue(state: PipelineState) -> str:
    """Conditional edge: si algún paso falló, ir a END directamente."""
    if state.get('status') == 'failed':
        return 'end'
    return 'continue'


def build_ingestion_graph(
    *,
    with_persistence: bool = True,
    with_embeddings: bool = False,
) -> StateGraph:
    """Construye el grafo de ingesta.

    Parameters
    ----------
    with_persistence : bool
        Si True, incluye el nodo persist (guarda en PostgreSQL).
        Si False, el grafo termina después de embed o chunk.
    with_embeddings : bool
        Si True, incluye el nodo embed (genera vectores con Ollama).
        Los chunks deben tener Ollama corriendo con el modelo configurado.
        Si False, los chunks se guardan con embedding_status='pending'.

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
    if with_embeddings:
        graph.add_node('embed', embed_node)
    if with_persistence:
        graph.add_node('persist', persist_node)

    # ── Entry point ──────────────────────────────────────────────────────
    graph.set_entry_point('sanitize')

    # ── Edges con conditional routing ────────────────────────────────────
    graph.add_conditional_edges(
        'sanitize',
        _should_continue,
        {'continue': 'parse', 'end': END},
    )
    graph.add_conditional_edges(
        'parse',
        _should_continue,
        {'continue': 'markdown', 'end': END},
    )
    graph.add_conditional_edges(
        'markdown',
        _should_continue,
        {'continue': 'chunk', 'end': END},
    )

    # Después de chunk: embed (opcional) → persist (opcional) → END
    if with_embeddings:
        graph.add_conditional_edges(
            'chunk',
            _should_continue,
            {'continue': 'embed', 'end': END},
        )
        if with_persistence:
            graph.add_conditional_edges(
                'embed',
                _should_continue,
                {'continue': 'persist', 'end': END},
            )
            graph.add_edge('persist', END)
        else:
            graph.add_edge('embed', END)
    elif with_persistence:
        graph.add_conditional_edges(
            'chunk',
            _should_continue,
            {'continue': 'persist', 'end': END},
        )
        graph.add_edge('persist', END)
    else:
        graph.add_edge('chunk', END)

    return graph


def compile_ingestion_graph(
    *,
    with_persistence: bool = True,
    with_embeddings: bool = False,
):
    """Compila el grafo y lo devuelve listo para invocar.

    Uso:
        app = compile_ingestion_graph()
        result = app.invoke({
            'raw_content': content_bytes,
            'original_filename': 'documento.pdf',
        })
    """
    graph = build_ingestion_graph(
        with_persistence=with_persistence,
        with_embeddings=with_embeddings,
    )
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
    generate_embeddings: bool = False,
) -> dict:
    """Ejecuta el pipeline completo de ingesta.

    Punto de entrada principal tanto para la CLI como para FastAPI.
    Devuelve el estado final del grafo.

    Parameters
    ----------
    content : bytes
        Bytes del archivo a ingestar.
    filename : str
        Nombre original del archivo (incluida extensión).
    owner_id : str
        UUID del usuario propietario (para deduplicación y auditoría).
    source_version_id : str
        UUID de la SourceVersion asociada (opcional).
    max_file_size : int
        Tamaño máximo en bytes (default 20 MB).
    chunk_size : int
        Tamaño objetivo de chunk en caracteres (default 1200).
    chunk_overlap : int
        Overlap entre chunks en caracteres (default 150).
    persist : bool
        Si True, persiste el resultado en PostgreSQL.
    generate_embeddings : bool
        Si True, genera vectores de embedding con Ollama antes de persistir.
        Requiere Ollama corriendo con el modelo JURIDIA_EMBED_MODEL disponible.
    """
    import time
    from datetime import datetime, timezone

    app = compile_ingestion_graph(
        with_persistence=persist,
        with_embeddings=generate_embeddings,
    )
    pipeline_start = time.monotonic()

    initial_state: PipelineState = {
        'raw_content': content,
        'original_filename': filename,
        'max_file_size': max_file_size,
        'chunk_size': chunk_size,
        'chunk_overlap': chunk_overlap,
        'owner_id': owner_id,
        'source_version_id': source_version_id,
        'generate_embeddings': generate_embeddings,
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
