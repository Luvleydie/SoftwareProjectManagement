"""Assemble the design fragments into an offline HTML reader and Markdown report."""
from __future__ import annotations

import base64
import html
import re
import unicodedata
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
SECTIONS = ['01-proyecto.md', '02-diagramas.md', '02b-interfaz.md',
            '03-datos-api.md', '04-calidad-ia.md', '05-trazabilidad.md', '06-entrega.md']


def slug(value: str) -> str:
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', value).strip('-')


def normalize_links(text: str, source: Path) -> str:
    def replace(match: re.Match) -> str:
        url = match[2]
        if re.match(r'^(?:[a-z]+:|#)', url):
            return match[0]
        target = (source.parent / url).resolve()
        if not target.is_relative_to(DOCS):
            raise ValueError(f'Enlace fuera de docs: {source.name}: {url}')
        if not target.is_file():
            raise FileNotFoundError(f'{source.name}: {url}')
        return match[1] + target.relative_to(DOCS).as_posix() + match[3]
    return re.sub(r'(!?\[[^\]]*\]\()([^\s)]+)(\))', replace, text)


def uri(path: Path) -> str:
    mime = {'svg': 'image/svg+xml', 'png': 'image/png'}.get(path.suffix[1:], 'text/plain;charset=utf-8')
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def figure(source: str, caption: str) -> str:
    path = DOCS / source
    if path.suffix == '.png' and path.with_suffix('.svg').exists():
        path = path.with_suffix('.svg')
    title = html.escape(caption)
    return (f'<figure class="figure"><img src="{uri(path)}" alt="{title}" loading="lazy">'
            f'<figcaption><span>{title}</span><button type="button" class="enlarge" '
            f'aria-label="Ampliar {title}">Ampliar</button></figcaption></figure>')


def build() -> None:
    fragments = []
    for name in SECTIONS:
        source = DOCS / 'secciones' / name
        fragments.append(normalize_links(source.read_text(encoding='utf-8').strip(), source))
    content = '\n\n'.join(fragments) + '\n'
    headings = re.findall(r'^## (.+)$', content, re.M)
    toc = '\n'.join(f'- [{x}](#{slug(x)})' for x in headings)
    insertion = content.index('\n## 1.')
    report = content[:insertion] + '\n\n## Índice\n\n' + toc + '\n' + content[insertion:]
    (DOCS / 'DISENO-SOLUCION.md').write_text(report, encoding='utf-8')

    md = MarkdownIt('commonmark', {'html': True}).enable('table')
    tokens = md.parse(content)
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            token.attrSet('id', slug(tokens[i + 1].content))
    body = md.renderer.render(tokens, md.options, {})
    body = body.replace('<table>', '<div class="table-scroll" tabindex="0" role="region" aria-label="Tabla de diseño"><table>')
    body = body.replace('</table>', '</table></div>')

    def replace_image(match: re.Match) -> str:
        return figure(html.unescape(match[1]), html.unescape(match[2]))
    body = re.sub(r'<p><img src="([^"]+)" alt="([^"]*)"\s*/?></p>', replace_image, body)

    def replace_mermaid(match: re.Match) -> str:
        code = html.unescape(match[1])
        diagram = 'D09-modelo-datos' if code.lstrip().startswith('erDiagram') else 'D10-navegacion'
        caption = 'D09 · Modelo entidad-relación' if diagram.startswith('D09') else 'D10 · Navegación y recorridos'
        return (figure(f'diagramas/{diagram}.svg', caption)
                + '<details class="source-code"><summary>Ver fuente Mermaid editable</summary>'
                + f'<pre><code>{html.escape(code)}</code></pre></details>')
    body = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>', replace_mermaid, body, flags=re.S)

    # Source downloads remain usable when the reader is copied as a single file.
    def embed_link(match: re.Match) -> str:
        target = html.unescape(match[1])
        if re.match(r'^(?:[a-z]+:|#)', target):
            return match[0]
        path = DOCS / target
        if path.is_file():
            return f'<a href="{uri(path)}" download="{html.escape(path.name)}">'
        raise FileNotFoundError(target)
    body = re.sub(r'<a href="([^"]+)">', embed_link, body)
    nav = ''.join(f'<li><a href="#{slug(x)}">{html.escape(x)}</a></li>' for x in headings)
    style = (DOCS / 'assets' / 'reporte.css').read_text(encoding='utf-8')
    script = """
const modal = document.querySelector('dialog');
const zoom = modal.querySelector('img');
let opener;
document.querySelectorAll('.enlarge').forEach(button => button.addEventListener('click', () => {
  opener = button;
  const original = button.closest('figure').querySelector('img');
  zoom.src = original.src; zoom.alt = original.alt;
  modal.querySelector('#zoom-title').textContent = original.alt;
  zoom.style.width = 'auto'; modal.showModal();
}));
modal.querySelector('.close').addEventListener('click', () => modal.close());
modal.querySelector('.fit').addEventListener('click', () => { zoom.style.width = zoom.style.width === '100%' ? 'auto' : '100%'; });
modal.addEventListener('close', () => opener?.focus());
"""
    output = f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Diseño de solución de juridIA: requisitos, arquitectura, datos, API, interfaces y trazabilidad.">
<title>juridIA · Diseño de solución DSD-1.1</title><style>{style}</style></head>
<body><a class="skip" href="#contenido">Saltar al contenido</a><div class="layout">
<aside class="sidebar"><div class="brand">juridIA</div><div class="edition">Documento de diseño · 1.1</div>
<nav aria-label="Índice del documento"><ol>{nav}</ol></nav>
<div class="tools"><a href="{uri(DOCS / 'DISENO-SOLUCION.md')}" download="DISENO-SOLUCION.md">Descargar Markdown</a>
<span class="edition">5 octubre 2026</span></div></aside>
<main id="contenido"><header class="cover"><div class="eyebrow">Requisitos → Diseño</div>
<h1>Una base técnica<br>para juridIA.</h1><p class="lead">Asistente jurídico preliminar para la organización de eventos.</p>
<p>Arquitectura, interfaces, datos y decisiones para la siguiente fase del proyecto.</p>
<div class="chips"><span>54 requisitos definidos</span><span>24 criterios de aceptación</span><span>7 pantallas</span><span>Propuesta previa a implementación</span></div></header>
<article>{body}</article><footer class="endnote">DSD-1.1 · 5 de octubre de 2026. Documento generado desde las secciones editables del proyecto.
Las verificaciones de esta entrega son documentales; las pruebas de la aplicación permanecen pendientes.</footer></main></div>
<dialog aria-labelledby="zoom-title"><div class="zoom-bar"><strong id="zoom-title">Diagrama</strong><div><button type="button" class="fit">Ajustar / tamaño original</button> <button type="button" class="close">Cerrar</button></div></div><div class="zoom-content"><img alt=""></div></dialog>
<script>{script}</script></body></html>'''
    (DOCS / 'DISENO-SOLUCION.html').write_text(output, encoding='utf-8')
    print(f'Reporte generado: {len(headings)} capítulos, Markdown y HTML sin dependencias de red.')


if __name__ == '__main__':
    build()
