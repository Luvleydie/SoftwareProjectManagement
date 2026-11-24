"""CLI del pipeline de ingesta RAG.

Modos de uso:
  python -m rag.main ingest rag/src/leyesfederalesSalud.md     # Ingesta completa
  python -m rag.main preview rag/src/leyesfederalesSalud.md     # Solo parsing + chunks, sin BD
  python -m rag.main ingest documento.pdf                       # PDF externo
  python -m rag.main ingest archivo.docx --owner-id=USER_ID     # Con propietario

El pipeline se ejecuta como un grafo LangGraph determinista:
  sanitize → parse → markdown → chunk → [persist]
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Pipeline determinista de ingesta RAG con LangGraph',
        prog='python -m rag.main',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # ── ingest ───────────────────────────────────────────────────────────
    ingest_parser = subparsers.add_parser('ingest', help='Ingesta completa con persistencia en PostgreSQL')
    ingest_parser.add_argument('file', type=Path, help='Archivo a procesar (PDF, DOCX, TXT, MD)')
    ingest_parser.add_argument('--owner-id', default='', help='ID del usuario propietario')
    ingest_parser.add_argument('--source-version-id', default='', help='ID de source_version asociada')
    ingest_parser.add_argument('--max-size-mb', type=int, default=20, help='Tamaño máximo en MB')
    ingest_parser.add_argument('--chunk-size', type=int, default=1200, help='Tamaño objetivo de chunk')
    ingest_parser.add_argument('--chunk-overlap', type=int, default=150, help='Overlap entre chunks')

    # ── preview ──────────────────────────────────────────────────────────
    preview_parser = subparsers.add_parser('preview', help='Preview sin escritura en PostgreSQL')
    preview_parser.add_argument('file', type=Path, help='Archivo a procesar')
    preview_parser.add_argument('--chunk-size', type=int, default=1200, help='Tamaño objetivo de chunk')
    preview_parser.add_argument('--chunk-overlap', type=int, default=150, help='Overlap entre chunks')
    preview_parser.add_argument('--show-markdown', action='store_true', help='Mostrar Markdown generado')
    preview_parser.add_argument('--show-chunks', action='store_true', help='Mostrar detalle de chunks')

    args = parser.parse_args()

    # Verificar que el archivo existe
    if not args.file.exists():
        print(f'Error: archivo no encontrado: {args.file}', file=sys.stderr)
        sys.exit(1)

    # Leer archivo
    content = args.file.read_bytes()
    filename = args.file.name

    print(f'📄 Archivo: {filename} ({len(content):,} bytes)')
    print(f'🔗 Pipeline: LangGraph determinista v1.0.0')
    print()

    # Importar aquí para no forzar dependencias en --help
    from .graph import run_pipeline

    persist = args.command == 'ingest'

    if persist:
        print('🗄️  Modo: ingesta completa (con persistencia en PostgreSQL)')
    else:
        print('👁️  Modo: preview (sin escritura en base de datos)')

    print()
    print('─' * 60)

    result = run_pipeline(
        content,
        filename,
        owner_id=getattr(args, 'owner_id', ''),
        source_version_id=getattr(args, 'source_version_id', ''),
        max_file_size=getattr(args, 'max_size_mb', 20) * 1024 * 1024,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        persist=persist,
    )

    # ── Resumen ──────────────────────────────────────────────────────────
    print()
    status = result.get('status', 'unknown')
    icon = '✅' if status == 'completed' else '❌'
    print(f'{icon} Estado: {status}')
    print()

    if status == 'failed':
        print(f'   Error: [{result.get("error_code", "?")}] {result.get("error_message", "")}')
        print()
    else:
        print(f'   📋 Título:     {result.get("title", "(sin título)")}')
        print(f'   📝 Tipo:       {result.get("detected_type", "?")}')
        print(f'   🔑 SHA-256:    {result.get("sha256", "")[:20]}…')
        print(f'   📄 Páginas:    {result.get("total_pages", 0)}')
        print(f'   📊 Palabras:   {result.get("word_count", 0):,}')
        print(f'   📐 Caracteres: {result.get("char_count", 0):,}')
        print(f'   📑 Secciones:  {len(result.get("sections", []))}')
        print(f'   🧩 Chunks:     {result.get("total_chunks", 0)}')
        print(f'   📏 Avg chunk:  {result.get("avg_chunk_size", 0)} chars')
        print(f'   📝 Markdown:   {result.get("markdown_size", 0):,} chars')
        print(f'   🌐 Idioma:     {result.get("language_hint", "?")}')

        if persist and result.get('document_id'):
            print(f'   🆔 Doc ID:     {result.get("document_id")}')

    # Warnings
    warnings = result.get('parse_warnings', [])
    if warnings:
        print()
        print('   ⚠️  Advertencias:')
        for w in warnings:
            print(f'      - {w}')

    # Steps
    print()
    print('   📊 Pasos del pipeline:')
    for step in result.get('steps', []):
        icon = '✅' if step['status'] == 'ok' else '❌'
        print(f'      {icon} {step["step"]:12s} {step["duration_ms"]:>5d}ms  {step.get("detail", "")}')

    total_ms = result.get('duration_total_ms', 0)
    print(f'\n   ⏱️  Duración total: {total_ms}ms')

    # Preview extras
    if args.command == 'preview':
        if getattr(args, 'show_markdown', False) and result.get('markdown'):
            print()
            print('═' * 60)
            print('MARKDOWN GENERADO:')
            print('═' * 60)
            print(result['markdown'][:5000])
            if len(result.get('markdown', '')) > 5000:
                print(f'\n... ({len(result["markdown"]) - 5000:,} caracteres más)')

        if getattr(args, 'show_chunks', False) and result.get('chunks'):
            print()
            print('═' * 60)
            print(f'CHUNKS ({result.get("total_chunks", 0)} total):')
            print('═' * 60)
            for chunk in result['chunks'][:10]:
                print(f'\n  [{chunk["index"]}] {chunk["chunk_id"]}')
                print(f'      Locator:  {chunk.get("locator", "")}')
                print(f'      Heading:  {chunk.get("section_heading", "")[:60]}')
                print(f'      Chars:    {chunk["char_count"]}, Tokens: ~{chunk["estimated_tokens"]}')
                print(f'      Hash:     {chunk.get("content_hash", "")[:16]}…')
                preview = chunk['text'][:120].replace('\n', ' ')
                print(f'      Preview:  {preview}…')
            if len(result.get('chunks', [])) > 10:
                print(f'\n  ... y {len(result["chunks"]) - 10} chunks más')

    print()

    # Exit code
    sys.exit(0 if status == 'completed' else 1)


if __name__ == '__main__':
    main()
