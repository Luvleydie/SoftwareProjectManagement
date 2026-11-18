# Guía de herramientas — juridIA

Fuente de verdad para tecnologías y su estado en el proyecto.  
Última actualización: octubre de 2026.  
Decisiones de arquitectura: [`docs/decision-arquitectonica.md`](decision-arquitectonica.md).

---

## Stack objetivo

| Tecnología | Uso | Estado | Configuración |
|---|---|---|---|
| React + TypeScript + Vite | Interfaz web | **Adoptada** | `frontend/vite.config.ts`, `frontend/package.json` |
| FastAPI (Python) | API REST | **Adoptada** | `backend/app/main.py` |
| PostgreSQL + pgvector | Base de datos principal con búsqueda vectorial | **Objetivo** — prototipo usa SQLite/MySQL | `JURIDIA_DATABASE_URL` en `backend/.env` |
| SQLAlchemy 2 | ORM y abstracción de base de datos | **Adoptada** | `backend/app/database.py` |
| Alembic | Migraciones de esquema | **Objetivo** — pendiente de implementar | `backend/requirements.txt` |
| Ollama (local) | Modelo generativo y embeddings | **Adoptada para fase académica** | `JURIDIA_OLLAMA_URL`, `JURIDIA_AI_MODEL` en `backend/.env` |
| Argon2id | Hash de contraseñas | **Adoptada** | `argon2-cffi` en `backend/requirements.txt` |
| psycopg (v3) | Driver PostgreSQL | **Objetivo** — incluido en requirements | `psycopg[binary]` en `backend/requirements.txt` |

## Herramientas de desarrollo y pruebas

| Tecnología | Uso | Estado |
|---|---|---|
| pytest | Pruebas de API backend | Adoptada |
| Playwright / Chromium | Pruebas de navegador | Adoptada |
| Node.js 24 | Runtime frontend | Adoptada |
| Python 3.14 | Runtime backend | Adoptada |
| SQLite | Base de datos en pruebas automatizadas | Adoptada (solo tests) |
| PyMySQL | Driver MySQL — prototipo local con XAMPP | **Prototipo actual** — se retira al migrar a PostgreSQL |

## Decisiones no tomadas (pendientes)

| Decisión | Bloquea | Referencia |
|---|---|---|
| Modelo de embeddings y dimensión del vector | Columna `embedding vector(N)` en pgvector | `decision-arquitectonica.md` §Decisión 4 |
| Política de retención de datos aprobada | US-G1, US-G2, US-G3 | `docs/backlog-must.md` §Bloque G |
| Fuentes jurídicas piloto y permisos | US-C3 | `docs/backlog-must.md` §Bloque C |
| Responsable de revisión jurídica del corpus | Gate de producción | `docs/backlog-must.md` §Gates |

## Herramientas explícitamente excluidas del stack actual

Las siguientes aparecen en documentos de diseño como alternativas o fases futuras.  
No forman parte del stack objetivo de esta fase:

- Redis / Celery / RQ / Arq (cola de trabajos asíncronos)
- S3 / MinIO (almacenamiento de objetos)
- LangChain / LlamaIndex
- Proveedores de IA externos (OpenAI, Anthropic, Google)
- OCR (Tesseract, OCRmyPDF) — pendiente de fase posterior
- Pandoc / WeasyPrint (generación de PDF)
- NestJS (alternativa de backend descartada)

---

## Estado del prototipo vs. stack objetivo

El prototipo 0.3 usa SQLite (tests) y MySQL/XAMPP (desarrollo local).  
La aplicación **no ha migrado a PostgreSQL todavía**.  
El esquema PostgreSQL está en [`db/schema.postgresql.sql`](../db/schema.postgresql.sql).  
Las brechas de implementación están documentadas en [`VERIFICACION-IMPLEMENTACION.md`](../Documentation/VERIFICACION-IMPLEMENTACION.md).
