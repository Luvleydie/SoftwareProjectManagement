# Matriz de trazabilidad inicial — juridIA

Fecha: generado al iniciar ejecución del plan.  
Fuente de requisitos: SRS `docs/fuentes/02-requisitos-proyecto.txt`.  
Diseño de referencia: `docs/secciones/05-trazabilidad.md` (§16).  
Estado del prototipo: Incremento 0.3 — [`Documentation/VERIFICACION-IMPLEMENTACION.md`](../Documentation/VERIFICACION-IMPLEMENTACION.md).

Esta matriz conecta cada requisito Must con su historia de usuario, el módulo de diseño, los componentes del prototipo actual y la evidencia de prueba prevista. La columna **Estado** refleja el prototipo 0.3; se actualiza con cada incremento.

Leyenda de estado:
- ✅ Implementado y probado
- 🔶 Parcialmente implementado
- ❌ No implementado
- 🔒 Gate de producción (no puede cerrarse sin aprobación externa)

---

## FR — Requisitos funcionales Must

| Req | Descripción resumida | Historia | Módulo | Componentes prototipo 0.3 | Prueba prevista | Estado |
|---|---|---|---|---|---|---|
| FR-01 | Registro, login, logout, recuperación y revocación de sesiones | US-A1, US-A2, US-A3 | M01 | `main.py`: `/api/auth/*`, `SessionRow`, `UserRow` | AC-01: cada operación; revocación; recuperación con token | 🔶 Falta recuperación y revocación individual |
| FR-02 | Roles User/Administrator; privilegios en servidor | US-A1 | M01, M06 | `main.py`: `identity()`, sin rol admin aún | AC-01/02: admin rechazado sin MFA; usuario ordinario rechazado en `/admin/*` | ❌ Sin rol admin ni MFA |
| FR-03 | Consulta natural con respuesta estructurada y evidencia | US-D1–D4 | M04 | `legal.py`: `prepare_answer()`, `ai.py`: `generate_json()` | AC-04: respuesta vinculada a contexto y fuentes | 🔶 Funciona con documentos privados; sin corpus oficial |
| FR-04 | Captura de jurisdicción, fecha y contexto antes de respuesta | US-D4 | M02, M04 | `main.py`: `CaseInput`, `consult()` | AC-04: contexto visible; contexto incompleto → solicitud de aclaración | 🔶 Contexto capturado; sin validación de jurisdicción en RAG |
| FR-05 | Carga, listado, apertura, organización y borrado de PDF, DOCX y TXT | US-B1 | M03 | `main.py`: `post_document()` — solo TXT | AC-03: cada formato; archivos inválidos; autorización | 🔶 Solo TXT implementado |
| FR-07 | Identificación y etiquetado de cláusulas con ubicación | US-E1 | M05 | No implementado | AC-05: contrato representativo; etiquetas y referencias | ❌ |
| FR-08 | Extracción de partes, obligaciones, fechas, pagos, penalizaciones | US-E2 | M05 | No implementado | AC-05: campos presentes/ausentes sin inventar | ❌ |
| FR-09 | Señalar inconsistencias, cláusulas faltantes y riesgos | US-E3 | M05 | No implementado | AC-05: casos con contradicciones y omisiones | ❌ |
| FR-10 | Borradores preliminares editables | — | M05 | `legal.py`: `prepare_draft()`, `prepare_template()` | AC-06: generar, editar, aviso de revisión | ✅ |
| FR-11 | Información con fuentes sobre cancelación, fuerza mayor | US-D1 | M04, M06 | `legal.py`: `official_legal_sources: []` vacío | AC-07: escenarios con evidencia disponible | ❌ Sin corpus |
| FR-12 | Orientación sobre permisos y cumplimiento por localidad | US-D1 | M02, M04, M06 | Idem | AC-07: protección civil, aforo, música, alcohol, ruido | ❌ Sin corpus |
| FR-14 | Orientación sobre datos personales y consentimiento | US-D1 | M04, M06 | Idem | AC-07: bases de asistentes, imagen/video | ❌ Sin corpus |
| FR-15 | Citas con nombre, artículo/sección, jurisdicción, vigencia, versión | US-D1–D4 | M04, M05, M06 | `legal.py`: citas de documentos privados con `document_id`, `title`, `locator` | AC-08: reconstruir cita hasta versión y pasaje | 🔶 Solo documentos privados; sin fuentes oficiales |
| FR-17 | Exportación de datos y solicitud de eliminación | US-G1, US-G2 | M07 | `main.py`: `export_workspace()` — exportación parcial | AC-12: exportación completa, borrado, excepciones de retención | 🔶 Exportación básica; sin solicitud de eliminación formal |
| FR-18 | Alta, actualización, desactivación y reindexado de fuentes | US-C1, US-C2 | M06 | No implementado | AC-13: metadatos preservados; versiones trazables | ❌ |
| FR-20 | Aviso obligatorio de apoyo preliminar | — | M04, M05, M07 | `legal.py`: `DISCLAIMER` en todas las respuestas | AC-06 y revisión de chat, borradores y exportaciones | ✅ |

---

## NFR — Requisitos no funcionales Must

| Req | Descripción resumida | Historia | Módulo | Componentes prototipo 0.3 | Prueba prevista | Estado |
|---|---|---|---|---|---|---|
| NFR-01 | Componentes adaptables sin desplazamiento horizontal | — | M02–M05 | `frontend/src/*.css` | AC-17: escritorio, tableta, móvil | 🔶 Verificado a 390/320 px; pendiente tableta |
| NFR-02 | Índices, paginación y trabajo pesado fuera de solicitudes | — | M01–M08 | `main.py`: operaciones síncronas; sin worker aún | AC-15: ≥95% no IA ≤3 s con carga definida | ❌ Sin worker; carga no definida |
| NFR-05 | HTTPS y TLS soportado en producción | US-I1 | Transversal | No configurado | AC-16: inspección de configuración | 🔒 Gate de producción |
| NFR-06 | Hash adaptativo y MFA para administradores | US-A1 | M01 | `main.py`: Argon2id para contraseñas; sin MFA | AC-01: sesión admin sin MFA → denegada | 🔶 Argon2id ✅; MFA ❌ |
| NFR-07 | Cifrado en reposo de contenido confidencial | — | M01, M03, M04 | MySQL con charset utf8mb4; sin cifrado de columnas | AC-16: inspección de controles de almacenamiento | ❌ Sin cifrado en reposo explícito |
| NFR-08 | Autorización por rol y propiedad en todas las operaciones | US-A3 | M01–M07 | `main.py`: `owned()`, `identity()` | AC-02: acceso cruzado por ID, listado, búsqueda, descarga | 🔶 Propiedad ✅; roles ❌ |
| NFR-09 | Validación de tipo/tamaño y análisis de archivos antes de IA | US-B1, US-B2 | M03 | `main.py`: validación TXT básica | AC-03: MIME discordante, malicioso, fuera de límite | 🔶 Solo TXT; sin análisis de malware |
| NFR-10 | Límites de frecuencia y protección ante fallos repetidos | — | M01, M04, M05 | `main.py`: rate limiting en `/api/auth/*`, `/api/consultations`, `/api/drafts/generate` | AC-16: provocar límites y protección temporal | 🔶 Rate limiting básico ✅; valores configurables pendientes |
| NFR-11 | Secretos fuera de código y control de versiones | US-I2 | Transversal | `.env.example` sin secretos reales; `.gitignore` | AC-16: escaneo de repositorio | 🔶 Estructura correcta; escaneo automatizado pendiente |
| NFR-12 | Política de retención/eliminación y prohibición de entrenamiento sin consentimiento | US-G1–G3 | M07 | Sin política definida | AC-12/24: periodos aprobados; ninguna ruta a entrenamiento | 🔒 Gate: política pendiente de aprobación |
| NFR-15 | Auditoría de eventos de autenticación, fuentes, ingesta, borrado | US-H1 | M08 | Sin `audit_events` | AC-18: cada evento; sin contraseñas ni contenido confidencial | ❌ |
| NFR-16 | Copias programadas y restauración documentada | US-I3 | M08 | Sin procedimiento | AC-19: restauración en entorno de prueba | 🔒 Gate de producción |

---

## BR — Reglas de negocio Must

| Req | Descripción resumida | Historia | Módulo | Componentes prototipo 0.3 | Prueba prevista | Estado |
|---|---|---|---|---|---|---|
| BR-01 | Alcance restringido a organización de eventos | — | M04, M05 | `legal.py`: `SYSTEM` prompt con restricción de alcance | Prueba complementaria: preguntas dentro/fuera del dominio | 🔶 Prompt restringe; sin prueba formal |
| BR-02 | No presentarse como despacho; revisión profesional para decisiones vinculantes | — | M04, M05, M07 | `legal.py`: `DISCLAIMER`, `out_of_scope` | Revisión de textos de alto impacto | ✅ |
| BR-03 | Jurisdicción y fecha visibles; pedir contexto faltante | US-D4 | M02, M04 | `main.py`: `context_snapshot` en respuesta | AC-04: contexto incompleto → solicitud | 🔶 Contexto en respuesta ✅; solicitud activa pendiente |
| BR-04 | No fabricar autoridad jurídica | US-D2 | M04, M05 | `legal.py`: `ensure_no_invented_authority()` | AC-08/09: citas inexistentes rechazadas | 🔶 Validación activa para artículos/NOM; sin corpus para verificar |
| BR-05 | Metadatos de jurisdicción, vigencia, versión, tipo y autoridad | US-C1, US-C2 | M06 | No implementado | AC-10/13: coexistencia de versiones; distinción primaria/secundaria | ❌ |
| BR-06 | Exponer contradicción de fuentes y sus citas | US-D3 | M04, M05 | No implementado (sin corpus) | AC-11: fuentes enfrentadas; conflicto explícito | ❌ Sin corpus |
| BR-07 | Contratos/cláusulas editables; revisión antes de uso vinculante | US-F1 | M04, M05, M07 | `main.py`: borradores editables; sin estado `ready` | AC-06: aviso antes de firma/trámite/pago | 🔶 Edición ✅; estado `ready` con reconocimiento ❌ |
| BR-08 | Borrado consistente de archivo, texto, chunks, embeddings y referencias | US-G3 | M03, M04, M07 | `main.py`: `delete_document()` invalida consultas dependientes | AC-03: recuperar antes/después; trabajos concurrentes | 🔶 Consultas invalidadas ✅; chunks/embeddings pendientes |
| BR-09 | Sin entrenamiento con contenido privado sin consentimiento | — | M07 | Ollama local; sin pipeline de entrenamiento | AC-24: inspección de flujos y configuración | 🔶 Ollama local no entrena ✅; política formal pendiente |

---

## AI — Requisitos de IA Must

| Req | Descripción resumida | Historia | Módulo | Componentes prototipo 0.3 | Prueba prevista | Estado |
|---|---|---|---|---|---|---|
| AI-01 | Afirmaciones jurídicas fundamentadas y separadas de explicaciones generales | US-D1–D4 | M04, M05 | `legal.py`: `SYSTEM` prompt; `official_legal_sources: []` | AC-08: comparar afirmaciones, pasajes y etiquetas | 🔶 Sin corpus oficial |
| AI-02 | Pasajes o referencias verificables para afirmaciones principales | US-D1–D4 | M04, M05 | `legal.py`: `cited_passage_ids` validados | AC-08: abrir evidencia y localizar fuente/versión/pasaje | 🔶 Solo documentos privados |
| AI-03 | Abstención o solicitud de contexto cuando evidencia es insuficiente | US-D2 | M04, M05 | `legal.py`: `outcome: INSUFFICIENT_EVIDENCE`; `out_of_scope` | AC-09: sin evidencia → limitación sin autoridades inventadas | ✅ |
| AI-04 | Preferir fuentes activas; no presentar versión obsoleta como actual | US-D1, US-C2 | M06, M04 | No implementado (sin corpus) | AC-10: nueva versión publicada; distinción histórica/actual | ❌ Sin corpus |
| AI-06 | Declarar desacuerdos materiales y citar fuentes en competencia | US-D3 | M04, M05 | No implementado (sin corpus) | AC-11: evidencia contradictoria; conflicto explícito | ❌ Sin corpus |
| AI-07 | Archivos y texto recuperado son datos no confiables; no pueden cambiar instrucciones | — | M03, M04, M05 | `legal.py`: `SYSTEM` prompt con instrucción de aislamiento | AC-21: documento con inyección; confirmar aislamiento | 🔶 Prompt activo; prueba formal pendiente |
| AI-08 | Minimizar información personal enviada a terceros | — | M04, M05, M07 | `ai.py`: Ollama local; sin terceros | AC-24: revisión de tráfico | ✅ Ollama local |

---

## Criterios de aceptación — estado de cobertura

| AC | Requisitos | Estado prototipo 0.3 | Próximo incremento |
|---|---|---|---|
| AC-01 | FR-01, FR-02, NFR-06 | 🔶 Falta MFA y recuperación | US-A1, US-A2, US-A3 |
| AC-02 | FR-02, NFR-08 | 🔶 Propiedad ✅; roles ❌ | US-A1 |
| AC-03 | FR-05, FR-06, BR-08, NFR-09 | 🔶 Solo TXT; sin análisis malware | US-B1, US-B2 |
| AC-04 | FR-03, FR-04, BR-03 | 🔶 Sin corpus oficial | US-D4, US-C3 |
| AC-05 | FR-07, FR-08, FR-09 | ❌ | US-E1, US-E2, US-E3 |
| AC-06 | FR-10, FR-20, BR-07 | 🔶 Sin estado `ready` con reconocimiento | US-F1 |
| AC-07 | FR-11, FR-12, FR-13, FR-14 | ❌ Sin corpus | US-C3, US-D1 |
| AC-08 | FR-15, AI-01, AI-02, BR-04 | 🔶 Solo documentos privados | US-C3, US-D1 |
| AC-09 | BR-04, AI-03 | ✅ | — |
| AC-10 | BR-05, AI-04 | ❌ Sin corpus | US-C1, US-C2 |
| AC-11 | BR-06, AI-06 | ❌ Sin corpus | US-D3, US-C3 |
| AC-12 | FR-16, FR-17, NFR-12 | 🔶 Exportación básica | US-G1, US-G2 |
| AC-13 | FR-18, BR-05 | ❌ | US-C1, US-C2 |
| AC-14 | FR-19 | ❌ (Should) | Fase posterior |
| AC-15 | NFR-02, NFR-03 | ❌ Sin carga definida | Gate de producción |
| AC-16 | NFR-05, NFR-07, NFR-10, NFR-11 | 🔶 Rate limiting ✅; HTTPS/cifrado ❌ | US-I1, US-I2 |
| AC-17 | NFR-01, NFR-13, NFR-14 | 🔶 Móvil básico ✅; WCAG completo pendiente | Fase posterior (Should) |
| AC-18 | NFR-15 | ❌ | US-H1 |
| AC-19 | NFR-16 | ❌ | US-I3 |
| AC-20 | NFR-17 | 🔶 Pruebas básicas ✅; críticas pendientes | US-H1, US-H2 |
| AC-21 | AI-07 | 🔶 Prompt activo; prueba formal pendiente | Prueba complementaria |
| AC-22 | AI-09 (sin definición) | ❌ | US-H2 |
| AC-23 | AI-10 (sin definición) | ❌ | Gate: corpus + evaluación |
| AC-24 | BR-09, NFR-12, AI-08 | 🔶 Ollama local ✅; política formal pendiente | US-G1, US-G2 |

---

## Resumen de estado por módulo

| Módulo | Must cubiertos | Must parciales | Must pendientes |
|---|---|---|---|
| M01 Identidad | FR-20 (aviso), AI-03, AI-08 | FR-01, FR-03, FR-04, NFR-06, NFR-08, NFR-10 | FR-02, US-A1, US-A2, US-A3 |
| M02 Expedientes | FR-04 (captura) | BR-03 | — |
| M03 Documentos | BR-08 (parcial) | FR-05, NFR-09 | US-B1, US-B2 |
| M04 Consultas | AI-03, AI-07, AI-08, BR-02, BR-04 (parcial) | FR-03, FR-04, FR-15, BR-03, BR-04 | FR-11, FR-12, FR-14, AI-01, AI-02, AI-04, AI-06, BR-06 |
| M05 Análisis/borradores | FR-10, FR-20, BR-02 | BR-07 | FR-07, FR-08, FR-09, US-E1–E3, US-F1 |
| M06 Fuentes | — | — | FR-18, BR-05, AI-04, US-C1–C3 |
| M07 Privacidad | BR-09 (parcial) | FR-17, NFR-12 | US-G1, US-G2 |
| M08 Auditoría | — | NFR-10, NFR-11 | NFR-15, NFR-16, US-H1, US-H2 |

---

## Control de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | Inicio del plan | Creación inicial basada en prototipo 0.3 y SRS |
| 1.1 | Paso 2 del plan | Decisiones arquitectónicas incorporadas: PostgreSQL+pgvector, retención LFPDPPP, corpus Durango, modelo local. ADR-03, ADR-05, ADR-07 actualizados. Ver `docs/decision-arquitectonica.md`. |

## Decisiones arquitectónicas que afectan la implementación

Estas decisiones cambian componentes del prototipo 0.3 antes de poder implementar nuevas historias:

| Decisión | Componentes afectados | Bloquea |
|---|---|---|
| Migrar a PostgreSQL + pgvector | `database.py`, `requirements.txt`, `.env.example`, `iniciar.ps1` | Todo el bloque C, D, E, H |
| Retención LFPDPPP (3–6 meses consultas; indefinida corpus) | `main.py`: campo `expires_at`; worker periódico; `POST /api/privacy-requests` | US-G1, US-G2 |
| Corpus piloto Durango (DOF, Periódico Oficial, Gaceta Municipal) | Nuevas tablas `legal_sources`, `source_versions`, `chunks`; pipeline de ingesta | US-C1–C3, US-D1–D4 |
| Modelo de embeddings local (dimensión a fijar antes del esquema) | Columna `embedding vector(N)` en `chunks`; `ai.py`: `generate_embedding()` | US-C3, US-D1 |

Cada historia completada debe actualizar la columna **Estado** de las filas correspondientes y registrar la versión del incremento en el control de cambios.
