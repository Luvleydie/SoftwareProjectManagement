# Estado actual del proyecto juridIA

**Fecha del diagnóstico:** 23 de noviembre de 2026  
**Alcance:** revisión del código y la documentación presentes en el espacio de trabajo. Es un diagnóstico, no una certificación de requisitos ni una prueba de preparación para producción.

## 1. Resumen ejecutivo

juridIA es un **prototipo local funcional** para organizar eventos, guardar expedientes y documentos de texto, consultar esos documentos con búsqueda por palabras clave o con un modelo Ollama local, y preparar borradores editables. Cuenta con una interfaz React/TypeScript, una API FastAPI y persistencia de usuarios y artefactos.

El proyecto todavía **no proporciona orientación jurídica basada en un corpus oficial conectado**. El chat envía al modelo pasajes de documentos privados seleccionados; no consulta las fuentes que se pueden administrar en el backend ni usa los vectores del pipeline RAG. Por tanto, tener código de ingesta, modelos de fuentes o embeddings no significa que el chat ya tenga recuperación jurídica.

También hay dos brechas arquitectónicas relevantes:

1. La aplicación principal usa MySQL/XAMPP por defecto, aunque PostgreSQL + pgvector es la base objetivo y el pipeline RAG de embeddings requiere PostgreSQL.
2. Hay dos caminos de ingesta separados: la ruta HTTP `/api/pipeline` y el pipeline de fuentes de `rag/`. No forman todavía un flujo completo desde carga y publicación de una fuente hasta recuperación en el chat.

**Conclusión:** el núcleo de organización y asistencia sobre documentos privados está implementado parcialmente y es utilizable localmente. La administración del corpus, análisis contractual, privacidad integral, controles administrativos y preparación operativa para producción siguen incompletos.

## 2. Funcionalidades disponibles hoy

- **Interfaz:** acceso, chat, expedientes, documentos, borradores, fuentes informativas y configuración; la demostración puede ejecutarse con datos de ejemplo en memoria.
- **Cuentas locales:** registro, inicio/cierre de sesión, contraseñas con Argon2id y sesiones en cookies HttpOnly; hay protección CSRF, validación de origen y límites de intentos en algunas rutas.
- **Expedientes:** creación/edición, contexto geográfico y temporal, materia, búsqueda en la interfaz y eliminación con los artefactos asociados.
- **Documentos del espacio de trabajo:** incorporación de TXT UTF-8 de hasta 1 MB, visualización y eliminación. Las respuestas dependientes de documentos eliminados se invalidan.
- **Consultas:** modo de búsqueda literal por palabras clave sin IA o modo de generación con Ollama local. Se usan documentos elegidos explícitamente, se guardan las conversaciones y se limita el contexto histórico enviado al modelo.
- **Citas privadas:** el servidor valida que las referencias de la respuesta correspondan a pasajes reales seleccionados; no se sustituyen errores del modelo por respuestas inventadas.
- **Borradores:** plantillas sin IA y generación local, edición, historial persistente y recuperación de una versión anterior como nueva revisión.
- **Exportación y eliminación básica:** exportación del espacio de trabajo a JSON, exportación de textos desde la interfaz, borrado de expedientes/documentos/borradores y limpieza de referencias dependientes.
- **Backend adicional:** hay rutas para administrar fuentes/versiones y un endpoint separado de ingesta de archivos PDF, DOCX y TXT.

Estas capacidades describen el código revisado; no implican que se haya vuelto a ejecutar toda la batería de validación durante este diagnóstico.

## 3. Estado por módulo

| Módulo | Estado | Implementado | Pendiente principal |
|---|---|---|---|
| **M01 Identidad y acceso** | Parcial | Registro, login/logout, sesión, CSRF, Argon2id, límites básicos y aislamiento por propietario. | Roles persistentes, MFA, recuperación de cuenta, revocación individual de sesiones y endurecimiento de permisos de administración. |
| **M02 Expedientes** | Parcial, usable | Guardar/editar y borrar expedientes; contexto de evento y navegación en la interfaz. | No hay un modelo de dominio relacional completo ni una validación de jurisdicción vinculada al uso legal de fuentes. |
| **M03 Documentos** | Parcial; dos flujos separados | TXT dentro del espacio normal; pipeline HTTP aparte con PDF/DOCX/TXT, validación, extracción, Markdown y fragmentación. | Unificar los flujos con expedientes y consultas; almacenamiento privado de originales, análisis antivirus/aislamiento y procesamiento durable. No hay un flujo OCR validado. El límite declarado de 20 MB del pipeline choca con el middleware global de 2 MB. |
| **M04 Consultas y chat** | Parcial | Consulta con o sin IA, historial acotado y citas a documentos privados seleccionados. | El chat no recupera fuentes jurídicas oficiales, ni filtra corpus por vigencia/jurisdicción, ni detecta conflictos entre fuentes. No hay streaming. |
| **M05 Borradores y análisis contractual** | Parcial | Plantillas, borradores generados, edición, versiones y exportación TXT. | No se implementa análisis estructurado de cláusulas, extracción de obligaciones/fechas/pagos, detección de riesgos ni reconocimiento humano obligatorio antes de marcar un documento listo. |
| **M06 Fuentes jurídicas** | Parcial, principalmente backend | CRUD básico de fuentes, versiones y estados draft/active/historical/inactive por API. | No existe administración integrada en la interfaz, un corpus oficial validado y mantenido, auditoría de cambios ni conexión con la recuperación del chat. |
| **M07 Privacidad y ciclo de vida** | Parcial | Exportación básica y borrado de algunos recursos con invalidación de consultas dependientes. | Solicitudes formales de exportación/eliminación, exportación integral de todos los datos, borrado de todos los artefactos del pipeline, retención automatizada, eliminación de cuenta y política operativa completa. |
| **M08 Auditoría y operación** | Incompleto | Endpoint de salud, correlación básica de solicitudes y pruebas automatizadas de algunas rutas. | `audit_events`, registro `ai_runs`, copias y restauración probada, monitoreo, límites distribuidos, tareas durables y pruebas de carga/recuperación. |
| **Pipeline RAG** | Código presente, integración incompleta | Pipeline LangGraph para sanitizar, parsear, convertir, fragmentar y persistir documentos; hay soporte de embeddings local opcional y esquema PostgreSQL/pgvector. | No alimenta las consultas del chat. La ruta HTTP omite la activación de embeddings y usa almacenamiento propio; el camino de persistencia vectorial es otro. La ejecución CLI declarada por `backend/scripts/generate_embeddings.py` importa `main` desde `rag/main.py`, que está vacío en el estado inspeccionado. |

### M01 — Identidad y acceso

El acceso normal está razonablemente cubierto para una instalación local: sesiones opacas revocables al cerrar sesión, cookies HttpOnly, CSRF y hash Argon2id. Sin embargo, la autorización se basa principalmente en propiedad del recurso; no se observa un modelo de roles User/Administrator con MFA. Tampoco se observan flujos de recuperación de contraseña o gestión individual de sesiones.

Además, en `backend/app/sources.py`, si `JURIDIA_ADMIN_EMAILS` está vacío, cualquier usuario autenticado puede usar las rutas administrativas de fuentes. El propio módulo lo identifica como comportamiento de desarrollo; debe cerrarse antes de exponer la API fuera del entorno local.

### M03 y pipeline de ingesta

El flujo de documentos visible para el usuario sigue siendo TXT en el espacio de trabajo. Existe además `/api/pipeline/ingest`, que acepta archivos y ejecuta el grafo de `rag/`; es una superficie de backend separada, no la carga normal de documentos desde la interfaz.

Hay además una discrepancia de límites: el pipeline declara 20 MB, pero el middleware principal rechaza solicitudes cuyo `Content-Length` supera 2 MB. Por ello, las cargas HTTP ordinarias mayores al límite global se rechazan antes de llegar al endpoint.

La ruta HTTP llama al pipeline con persistencia, pero no activa `generate_embeddings`; el estado por defecto del grafo deja los embeddings pendientes. En paralelo, `rag/repository.py` y `db/migrations/001_rag_schema.sql` definen almacenamiento vectorial en `legal_chunks` sobre PostgreSQL/pgvector. La coexistencia de `ingested_documents`, `SourceVersion.chunks`/`embedding_json` y `legal_chunks` necesita una única fuente de verdad y un flujo de integración definido.

### M04 y M06 — Consultas frente a fuentes

El código de consulta en `backend/app/legal.py` recupera fragmentos de los documentos privados pasados a la operación. La solicitud al modelo incluye `official_legal_sources: []`, y la interfaz comunica que el corpus jurídico no está conectado. Por eso las rutas administrativas de fuentes no habilitan todavía respuestas basadas en leyes o reglamentos.

El modo sin IA sí sirve como búsqueda documental y deja claro que no es una conclusión jurídica. El modo con IA restringe la salida a evidencia proporcionada y valida las citas, pero esas protecciones no reemplazan un corpus oficial vigente ni una evaluación jurídica de calidad.

## 4. Faltantes principales y prioridad recomendada

### Prioridad 0 — Cerrar brechas de arquitectura y de seguridad administrativa

1. **Elegir y consolidar la base de datos de la aplicación:** MySQL sigue siendo el valor predeterminado en `backend/app/database.py`; PostgreSQL es una opción por URL y un requisito del RAG vectorial. La migración y el esquema relacional/migratorio no están completos.
2. **Asegurar administración:** establecer autorización explícita y segura por rol; no permitir que una configuración administrativa vacía conceda acceso a cualquier cuenta.
3. **Definir un solo flujo RAG:** decidir qué almacena la ingesta, cómo se versiona/publica una fuente y cómo sus fragmentos llegan a recuperación y citas del chat.

### Prioridad 1 — Habilitar el propósito jurídico con trazabilidad

4. **Incorporar y validar el corpus piloto:** fuentes primarias con autoridad, jurisdicción, materia, procedencia, versión y vigencia; revisión humana antes de publicarlas.
5. **Conectar recuperación a consultas:** filtrar fuentes activas por jurisdicción y fecha, presentar referencias verificables y declarar insuficiencia o conflicto entre fuentes.
6. **Completar documentos:** integrar PDF/DOCX al expediente, definir el tratamiento de PDF escaneado, y agregar controles de archivos maliciosos, almacenamiento privado y borrado consistente.
7. **Completar identidad y privacidad:** MFA administrativo, recuperación de cuenta, gestión de sesiones, exportación/eliminación solicitada por el usuario y política de retención ejecutable.

### Prioridad 2 — Completar capacidades de producto y evaluación

8. **Análisis contractual:** extracción estructurada con evidencia, etiquetado de cláusulas, inconsistencias/riesgos y revisión humana registrada.
9. **Auditoría de negocio e IA:** registrar eventos operativos y metadatos de ejecuciones sin almacenar secretos o contenido innecesario.
10. **Pruebas de integración:** cubrir administración de fuentes, ingestión de extremo a extremo, persistencia vectorial, recuperación por jurisdicción/vigencia, borrado, fallos y citas; añadir un conjunto evaluado por persona experta.

### Prioridad 3 — Gates para producción

HTTPS/TLS, cifrado en reposo, gestión de secretos con controles automatizados, copias de seguridad y restauración probada, monitoreo, políticas de retención aprobadas, pruebas de carga/recuperación y evaluación ampliada de accesibilidad. La aplicación se describe actualmente como local y no apta para datos confidenciales o producción.

## 5. Discrepancias entre documentación y código

- `docs/trazabilidad-must.md` y `docs/backlog-must.md` presentan la administración de fuentes y partes de la ingesta como no implementadas. En el código actual sí existen rutas de fuentes y de pipeline; lo pendiente es su integración funcional, corpus validado y cobertura de pruebas.
- La presencia de `db/migrations/001_rag_schema.sql` y componentes de embeddings no significa que el backend principal se haya migrado a PostgreSQL: la conexión predeterminada sigue configurada para MySQL/XAMPP.
- El diseño de fuentes de `backend/app/models.py` conserva `chunks` y `embedding_json` como JSON placeholders, mientras la migración RAG define una tabla vectorial `legal_chunks`. La documentación debe reflejar con claridad qué esquema está activo y cuál está propuesto o destinado al pipeline.
- `Documentation/VERIFICACION-IMPLEMENTACION.md` registra resultados de pruebas de octubre de 2026. Es evidencia histórica útil, pero no valida automáticamente los cambios presentes en el árbol actual ni los endpoints de fuentes/RAG de extremo a extremo.
- La interfaz de Fuentes muestra estado informativo y “0 fuentes activas”; no consume las rutas administrativas del backend.

## 6. Pruebas y estado del árbol de trabajo

La documentación registra compilación TypeScript, pruebas de frontend/backend y recorridos de navegador ejecutados anteriormente. En los tests visibles actuales, `backend/tests/test_api.py` cubre flujos principales de cuentas, expedientes, documentos, consultas y borradores; `backend/tests/test_rag_pipeline.py` cubre pruebas acotadas de parser y cliente de embeddings. No se encontró cobertura de extremo a extremo para publicación de fuentes, ingesta HTTP, persistencia vectorial y uso de esas fuentes en una consulta.

El árbol de trabajo tenía cambios locales sin confirmar en `rag/` (incluyendo módulos de embeddings/herramientas). Este informe describe el código presente en el espacio de trabajo y no atribuye esos cambios a una versión publicada o confirmada. **No se ejecutó la suite completa como parte de este diagnóstico.**

## 7. Referencias del proyecto

- [README.md](README.md) — uso local, límites y estado general declarado.
- [docs/backlog-must.md](docs/backlog-must.md) — historias Must y gates de producción.
- [docs/trazabilidad-must.md](docs/trazabilidad-must.md) — cobertura de requisitos.
- [docs/decision-arquitectonica.md](docs/decision-arquitectonica.md) — decisiones de arquitectura y corpus.
- [Documentation/VERIFICACION-IMPLEMENTACION.md](Documentation/VERIFICACION-IMPLEMENTACION.md) — evidencia histórica de pruebas.
- [backend/app/main.py](backend/app/main.py) — API principal.
- [backend/app/legal.py](backend/app/legal.py) — recuperación privada y generación de respuestas/borradores.
- [backend/app/sources.py](backend/app/sources.py) — API administrativa de fuentes.
- [backend/app/pipeline_routes.py](backend/app/pipeline_routes.py) — endpoints de ingesta RAG.
- [backend/app/database.py](backend/app/database.py) — configuración de base de datos.
- [rag/arquitecturaRAG.md](rag/arquitecturaRAG.md) — diseño del pipeline de ingesta/vectorización.
- [db/migrations/001_rag_schema.sql](db/migrations/001_rag_schema.sql) — esquema de ingesta y chunks vectoriales.

