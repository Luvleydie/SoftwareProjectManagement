# Decisión arquitectónica — Paso 2 del plan

Fecha: generado tras recibir respuestas del equipo.  
Fuente de decisiones: `seguimiento.md` (respuestas del responsable del proyecto).  
Referencia de diseño: `docs/secciones/05-trazabilidad.md` §17 (ADR-01 a ADR-08).  
Contexto: proyecto académico; alcance piloto México · Durango · Victoria de Durango.

Este documento registra las cuatro decisiones previas que desbloqueaban la implementación. Cada decisión actualiza o reemplaza el ADR correspondiente de la línea base de diseño. Las consecuencias de migración se listan explícitamente para que el siguiente incremento no asuma que el prototipo 0.3 es compatible sin cambios.

---

## Decisión 1 — Base de datos: migrar a PostgreSQL + pgvector

**ADR actualizado:** ADR-03.

### Decisión
Migrar de MySQL (XAMPP/MariaDB) a **PostgreSQL con la extensión pgvector**.

### Justificación
- Búsqueda híbrida en una sola consulta: similitud vectorial + filtrado SQL exacto por `estado`, `estatus` y `fecha_vigencia`. Crítico para el corpus legal de Durango.
- Metadatos de fuentes, texto (chunks) y embeddings en una sola base de datos; elimina la necesidad de un motor vectorial separado.
- pgvector es el estándar de facto para RAG relacional; compatible con LangChain y LlamaIndex si se incorporan en fases posteriores.

### Impacto de migración sobre el prototipo 0.3

| Componente | Cambio requerido |
|---|---|
| `backend/app/database.py` | Cambiar driver de `mysql+pymysql` a `postgresql+psycopg2`; ajustar `connect_args` |
| `backend/requirements.txt` | Reemplazar `PyMySQL` por `psycopg2-binary` (o `psycopg[binary]`) |
| `backend/app/main.py` | Sin cambios en lógica; SQLAlchemy abstrae el dialecto |
| Tablas existentes | Migración de esquema: `users`, `sessions`, `artifacts`, `draft_versions` se recrean en PostgreSQL |
| Tablas nuevas | `legal_sources`, `source_versions`, `chunks` con columna `embedding vector(N)` e índice HNSW |
| Scripts de inicio | `iniciar.ps1` y `detener.ps1` deben apuntar a PostgreSQL en lugar de XAMPP |
| `.env.example` | Reemplazar variables `JURIDIA_MYSQL_*` por `JURIDIA_DATABASE_URL` con URL de PostgreSQL |

### Consecuencias operativas
- XAMPP deja de ser dependencia. PostgreSQL se instala localmente o en contenedor Docker.
- La extensión `pgvector` debe habilitarse con `CREATE EXTENSION IF NOT EXISTS vector;` antes de crear tablas.
- Los tests que usan SQLite como override (`JURIDIA_DATABASE_URL=sqlite:///...`) siguen funcionando sin cambios.

---

## Decisión 2 — Periodos de retención (LFPDPPP)

**ADR actualizado:** ADR-07. **Gate desbloqueado:** NFR-12, AC-12, AC-24.

### Política aprobada

| Clase de dato | Retención | Acción al vencer |
|---|---|---|
| Logs de consultas y prompts (texto claro) | 3–6 meses | Anonimizar: eliminar nombre, correo, ubicaciones específicas. Retención analítica indefinida del dato anonimizado. |
| Corpus legal e historial normativo | Indefinida | Las fuentes derogadas/reformadas **no se eliminan**; se etiquetan con `estatus: derogada` y `fecha_fin_vigencia`. |
| Datos contractuales o de facturación de clientes | 5–10 años | Almacenados en tablas separadas del contexto del LLM; no accesibles por el pipeline RAG. |
| Documentos privados del usuario | A definir por usuario en solicitud de eliminación | Borrado consistente: archivo, texto extraído, chunks, embeddings, referencias en consultas. |
| Auditoría (`audit_events`) | Mínimo 1 año (pendiente de confirmar con responsable jurídico) | Solo metadatos operativos; sin contraseñas ni contenido confidencial. |

### Impacto sobre el prototipo 0.3

| Componente | Cambio requerido |
|---|---|
| `backend/app/main.py` | Añadir campo `created_at` con timestamp a `Artifact` para aplicar retención |
| Tabla `artifacts` | Añadir columna `expires_at` nullable para documentos y consultas |
| Worker (nuevo) | Job periódico que anonimiza consultas > 6 meses y borra documentos expirados |
| `POST /api/privacy-requests` | Nuevo endpoint para solicitudes de exportación y eliminación (US-G1, US-G2) |
| Fuentes derogadas | Nunca `DELETE`; siempre `UPDATE estatus = 'derogada'` con `fecha_fin_vigencia` |

### Nota de cumplimiento
Esta política se basa en LFPDPPP y Código de Comercio/CFF. **Requiere revisión y firma del responsable jurídico del proyecto antes de producción.** El gate NFR-12 permanece abierto hasta esa firma.

---

## Decisión 3 — Fuentes jurídicas piloto y proceso de validación

**ADR actualizado:** ADR-05 (corpus). **Gate desbloqueado:** R-02 del plan.

### Fuentes a incorporar (jerarquía)

| Nivel | Fuente oficial | Materias cubiertas para el piloto |
|---|---|---|
| Federal | Diario Oficial de la Federación (DOF) | LFPDPPP, Ley Federal de Protección al Consumidor, LFT (cláusulas laborales en contratos de eventos) |
| Federal | Portal Cámara de Diputados | Versiones vigentes de leyes federales aplicables |
| Estatal | Periódico Oficial del Estado de Durango | Ley de Protección Civil del Estado, Ley de Espectáculos Públicos |
| Municipal | Gaceta Municipal / Portal de Transparencia del Ayuntamiento de Victoria de Durango | Bando de Policía y Gobierno, Reglamento de Espectáculos, Reglamento de Desarrollo Urbano |

### Proceso de validación (Human in the Loop)

1. **Extracción:** Ingeniero de datos extrae y limpia PDFs/HTMLs oficiales. Los artículos no deben cortarse en medio de un chunk; el chunking respeta límites de artículo.
2. **Carga inicial:** Administrador carga fuentes en estado `draft` mediante `POST /api/admin/sources`.
3. **Validación jurídica:** Abogado especialista en derecho administrativo o corporativo local revisa el corpus antes de publicar cada fuente.
4. **Publicación:** Solo tras validación jurídica, el administrador cambia el estado a `active`.
5. **Mantenimiento:** El abogado revisor monitorea reformas en gacetas y notifica al administrador para actualizar versiones. Las reformas generan una nueva `source_version`; la anterior queda con `estatus: derogada`.

### Responsable de validación jurídica
**Pendiente de asignar.** Este es un gate de producción: ninguna fuente puede publicarse sin validación jurídica firmada. El sistema no puede determinar por sí solo si un reglamento municipal fue derogado.

### Impacto sobre el prototipo 0.3

| Componente | Cambio requerido |
|---|---|
| Nuevas tablas | `legal_sources`, `source_versions`, `chunks` (con embeddings en pgvector) |
| Nuevo endpoint | `POST /api/admin/sources` y familia de administración (US-C1, US-C2) |
| `legal.py` | `official_legal_sources: []` → recuperación real desde `chunks` filtrada por jurisdicción, vigencia y materia |
| Pipeline de ingesta | Extracción de texto de PDF/DOCX, chunking por artículo, generación de embeddings, inserción en pgvector |
| Modelo de embeddings | A definir (ver Decisión 4); debe correr localmente para no enviar corpus a terceros |

---

## Decisión 4 — Modelo generativo: local para fase académica, evaluación para producción

**ADR actualizado:** ADR-05 (modelo generativo).

### Decisión para la fase académica actual
**Mantener Ollama local** (qwen3.5:4b-q4_K_M o equivalente disponible). El proyecto es puramente académico; la privacidad absoluta de los prompts es un requerimiento que impide usar APIs en la nube en esta fase.

### Limitaciones conocidas y mitigaciones

| Limitación | Mitigación en el diseño |
|---|---|
| Modelos < 14B pierden instrucciones en prompts largos | Limitar contexto enviado al modelo: máximo 6 500 caracteres de pasajes (ya implementado en `legal.py`) |
| Propensos a alucinar artículos plausibles | `ensure_no_invented_authority()` activo; validación de `cited_passage_ids` contra pasajes reales |
| Dificultad para seguir reglas estrictas de citación | Formato JSON estructurado con schema Pydantic; respuesta rechazada si no valida |

### Criterio de escalado a producción
Si el sistema falla en sintetizar reglas complejas (ej. cruzar un artículo de PROFECO con un reglamento municipal de horarios), evaluar:
- **Opción A (nube):** GPT-4o o Gemini 1.5 Pro por API — requiere resolver tratamiento de datos permitido bajo LFPDPPP antes de enviar cualquier contenido de usuario.
- **Opción B (local robusto):** Llama 3 70B o Command R en Ollama/vLLM — requiere hardware con alta VRAM (≥48 GB para 70B en Q4).

### Modelo de embeddings
El modelo de embeddings para el corpus jurídico debe correr **localmente** para no enviar el corpus a terceros. Candidatos a evaluar antes del incremento de corpus:
- `nomic-embed-text` (Ollama, 768 dims)
- `mxbai-embed-large` (Ollama, 1024 dims)
- `all-MiniLM-L6-v2` (sentence-transformers, 384 dims, muy ligero)

La dimensión del vector determina la columna `embedding vector(N)` en pgvector. **Debe fijarse antes de crear el esquema de chunks.**

### Impacto sobre el prototipo 0.3

| Componente | Cambio requerido |
|---|---|
| `backend/app/ai.py` | Añadir función `generate_embedding(text) -> list[float]` usando Ollama `/api/embeddings` |
| `backend/requirements.txt` | Sin cambios si se usa Ollama para embeddings; añadir `sentence-transformers` si se elige esa opción |
| `legal.py` | `retrieve_passages()` → reemplazar búsqueda por palabras clave con búsqueda vectorial en pgvector + filtros SQL |
| `scripts/setup-ai.ps1` | Añadir descarga del modelo de embeddings elegido |

---

## Resumen de impacto en el backlog

| Historia | Desbloqueada por | Cambio de prioridad |
|---|---|---|
| US-C1, US-C2, US-C3 | Decisiones 3 y 4 | Sin cambio; siguen siendo bloqueantes funcionales |
| US-D1–D4 | Decisiones 3 y 4 | Sin cambio |
| US-G1, US-G2, US-G3 | Decisión 2 | Sin cambio; gate NFR-12 sigue abierto hasta firma jurídica |
| US-B1, US-B2 | Decisión 1 (migración) | Sin cambio; PDF/DOCX requiere migración primero |
| US-H1, US-H2 | Decisión 1 (migración) | Sin cambio |

---

## Orden de implementación recomendado

Dado que la migración a PostgreSQL afecta a todos los módulos, debe ejecutarse primero:

```
1. Migración a PostgreSQL + pgvector          ← desbloquea todo lo demás
2. Esquema de fuentes y chunks                ← US-C1, US-C2
3. Pipeline de ingesta (PDF/DOCX + embeddings)← US-B1, US-B2, US-C3
4. RAG real con filtros de jurisdicción       ← US-D1–D4
5. Análisis contractual                       ← US-E1–E3
6. MFA + recuperación de cuenta              ← US-A1, US-A2
7. Auditoría estructurada                    ← US-H1, US-H2
8. Privacidad y retención                    ← US-G1–G3 (gate: firma jurídica)
9. Revisión humana (estado ready)            ← US-F1
```

---

## Gates aún abiertos tras estas decisiones

| Gate | Condición de cierre | Responsable |
|---|---|---|
| NFR-12 / AC-12 / AC-24 | Firma del responsable jurídico sobre la política de retención | Responsable jurídico del proyecto |
| Corpus piloto | Validación jurídica de cada fuente antes de publicar | Abogado especialista (pendiente de asignar) |
| Modelo de embeddings | Fijar dimensión antes de crear esquema de chunks | Equipo técnico |
| AC-23 (evaluación RAG) | Conjunto representativo revisado por experto antes de liberar funciones jurídicas con IA | Abogado + equipo IA |
| NFR-05 / AC-16 | HTTPS activo en producción | Operación |
| NFR-16 / AC-19 | Restauración de backup documentada | Operación |
