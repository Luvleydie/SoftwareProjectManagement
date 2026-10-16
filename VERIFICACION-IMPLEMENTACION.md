# Verificación de la base local · 15 de octubre de 2026

Incremento 0.3: historial persistente de borradores y recuperación como nueva revisión; búsqueda documental y plantillas sin IA seleccionables; navegación por URL; mejoras de sesión y conexión; interfaz refinada en escritorio y móvil; arranque local con cuentas por defecto y parada de procesos registrados.

| Comprobación | Resultado |
|---|---|
| `npm run build` | TypeScript y compilación correctos |
| `npm test` | 4 pruebas de dominio aprobadas |
| `python -m pytest -q` | 12 pruebas de API aprobadas; SQLite temporal aislado |
| `python scripts/verify_browser.py` | 12 recorridos aprobados contra la API real con MySQL, incluida la exportación del historial |
| Historial persistente | Crear, editar, recargar, consultar y recuperar una versión como v3 |
| Aislamiento y borrado de versiones | Historial privado; conflicto de revisión rechazado; limpieza al eliminar borrador o expediente |
| Consultas sin IA | No invocan al proveedor; solo documentos seleccionados; borrado invalida también entradas sin citas |
| Generación simulada en pruebas | Citas válidas admitidas; citas inventadas y fallos del proveedor rechazados sin guardar |
| Navegador | 0 errores JavaScript; 0 infracciones axe WCAG 2 A/AA en inicio y acceso |
| Móvil | Sin desbordamiento a 390 y 320 px en las pantallas comprobadas |
| Dependencias Python | `pip check` sin incompatibilidades; PyMySQL y python-dotenv incorporados al lock |
| Modelo local real | `verify_ai.py`: qwen3.5:4b-q4_K_M generó una revisión con 2 citas literales verificadas en 148.8 s, incluyendo la carga inicial |
| Inicio y parada | Se verificó la liberación de 5173, 8000 y 11434 al detener los procesos propios, incluidos sus hijos |
| Estado final | Reinicio correcto; frontend HTTP 200; API 0.3.0 en estado `ok`, MySQL conectado y modelo local disponible |

Las comprobaciones de navegador crean una cuenta temporal y eliminan únicamente sus propios registros al terminar. Capturas: `tmp/juridia-desktop-verified.png`, `tmp/juridia-mobile-390.png`, `tmp/juridia-mobile-320.png`, `tmp/juridia-login.png` y las variantes móviles del acceso. Informe: `tmp/browser-results.json`. Se inspeccionaron visualmente escritorio, acceso y móvil.

La suite Python conserva un aviso de deprecación del cliente de pruebas Starlette/httpx. No afecta al resultado. La inspección automática no certifica accesibilidad completa. PDF/DOCX/OCR, corpus jurídico, MFA y despliegue productivo siguen pendientes. Las versiones históricas que no se almacenaron en entregas anteriores no se pueden reconstruir; se conserva la versión disponible al comenzar a editar con esta base.

## Evidencia histórica de la primera implementación

Fecha: 7 de octubre de 2026. Esta evidencia corresponde al código inicial, no a la certificación de los 24 criterios de aceptación del diseño completo.

Publicación privada confirmada por Sites con estado `succeeded`: https://bautista-legal.dtm123.chatgpt.site. Commit del frontend: `0f02aec595974bab2c5d73c37eea99f6aeb73bc1`. El empaquetador se ejecutó con Git Bash y rutas POSIX por incompatibilidad del comando Bash predeterminado de Windows; se conservó el mismo código compilado y enviado.

## Comprobaciones ejecutadas

| Comprobación | Resultado | Cobertura |
|---|---|---|
| `npm run build` | Correcto | TypeScript y compilación Vite de la interfaz |
| `npm test` | 4 pruebas aprobadas | Abstención, citas privadas literales, filtro por expediente, contexto histórico y avisos en plantilla |
| `python -m pytest -q` | 8 pruebas aprobadas | Sesión, CSRF, origen, acceso entre cuentas, límites, borrado dependiente, conflicto de revisiones y validación de documentos |
| `node scripts/verify-browser.mjs` | 7 recorridos aprobados | Crear/buscar expediente; cargar/revisar TXT; consultar/citar/exportar; crear/editar/exportar borrador; eliminación dependiente; móvil a 390 y 320 px |
| axe-core, pantalla inicial | 0 infracciones detectadas en reglas WCAG 2 A/AA | Comprobación automatizada en Chromium; no certifica accesibilidad completa |
| Errores JavaScript durante los recorridos | 0 | Navegador Chromium en modo de pruebas |
| Revisión visual | Realizada en escritorio; capturas móviles generadas | Capturas en `tmp/`, fuera del paquete publicado |

Se corrigieron dos casos negativos durante la revisión del backend: CSRF con caracteres no ASCII (rechazado con 403) e intento de reutilizar un UUID documental de otra cuenta (404 sin confirmar existencia).

El único aviso de la suite de Python es una deprecación de Starlette sobre el uso de `httpx` en su cliente de pruebas. No se presentaron fallos de pruebas.

Los adjuntos original y reenviado son idénticos por SHA-256: `49A4BE576E2E545B477CAADED752A428D55483A4B6109C479EAC8B0E7A65BE89`.

## Alcance y límites

- Se comprobó la API mediante su cliente de pruebas y SQLite. La interfaz se recorrió en modo demostración. PostgreSQL y un despliegue remoto de FastAPI no se han verificado.
- El navegador integrado no estaba disponible. La revisión visual y de interacción se realizó con Chromium local de Playwright.
- WebMCP tiene registro opcional con validación de entrada y un único comando para preparar una consulta; no envía la consulta. La API experimental del navegador no estaba disponible para validación nativa. Su ausencia no afecta las funciones normales.
- La carga activa admite exclusivamente TXT UTF-8, hasta 1 MB. No se ejecutan archivos ni instrucciones contenidas en documentos.
- La búsqueda de fragmentos es determinista. No se midieron generación, calidad de embeddings, recuperación vectorial o evaluación de un LLM porque no están conectados.
- No se realizaron pruebas de carga, restauración, antivirus, MFA, OCR, compatibilidad multinavegador ni certificación WCAG.
- La exportación descargada ya está bajo control del usuario. El borrado interno no elimina archivos previamente descargados.
- Las revisiones de borrador conservan el texto original y el número de la última versión; no existe todavía un historial recuperable de todas las versiones.
- Conservación, acceso administrativo, corpus, RAG, cifrado y operación productiva siguen pendientes conforme a `README.md` y al diseño original.

## Trazabilidad de este incremento

| Área del diseño | Estado de esta base |
|---|---|
| M01 Identidad | Registro, acceso, sesión, CSRF, Argon2id y aislamiento local; recuperación/MFA pendientes |
| M02 Expedientes | Crear, editar, buscar, contexto territorial/temporal y borrado asociado |
| M03 Documentos | TXT, visualización, validación básica y borrado; no ingesta binaria/worker |
| M04 Consultas | Contexto, referencias privadas, abstención y exportación; sin modelo ni corpus |
| M05 Borradores | Plantilla, edición, versión actual y exportación TXT |
| M06 Fuentes | Vista informativa de estado; no administración ni fuentes cargadas |
| M07 Privacidad | Exportación del espacio y eliminación local de artefactos; flujos de cuenta/retención pendientes |
| M08 Auditoría/evaluación | Pruebas automatizadas y correlación HTTP; auditoría completa y evaluación RAG pendientes |
