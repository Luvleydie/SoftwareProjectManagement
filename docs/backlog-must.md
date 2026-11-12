# Backlog Must — juridIA · Incremento 1

Fecha: generado al iniciar ejecución del plan.  
Base: SRS `docs/fuentes/02-requisitos-proyecto.txt` (44 Must, 10 Should, 24 AC).  
Estado del prototipo: Incremento 0.3 — ver `VERIFICACION-IMPLEMENTACION.md`.  
Jurisdicción piloto: México · Durango · Victoria de Durango.

---

## Criterios de priorización

1. **Bloqueante de seguridad o privacidad** — sin esto no se puede liberar.
2. **Bloqueante funcional** — sin esto otro Must no puede completarse.
3. **Must sin implementación** — requisito Must que el prototipo no cubre.
4. **Must parcialmente implementado** — el prototipo tiene base pero falta completar.

Las historias Should y Could no aparecen aquí; se planifican en fases posteriores.

---

## Historias Must — ordenadas por prioridad

### Bloque A · Identidad y acceso (M01)

| ID | Historia | Criterios de aceptación mínimos | Requisitos SRS | Prioridad |
|---|---|---|---|---|
| US-A1 | Como administrador, necesito MFA obligatorio para que ninguna sesión administrativa sea válida sin segundo factor. | Login admin sin TOTP → 401. Login admin con TOTP válido → sesión. Sesión sin MFA no accede a `/admin/*`. | NFR-06, FR-02, AC-01 | Bloqueante seguridad |
| US-A2 | Como usuario registrado, necesito recuperar acceso a mi cuenta mediante correo verificado para no quedar bloqueado permanentemente. | Solicitar recuperación → correo con token de un solo uso. Token expirado → rechazado. Token válido → permite cambiar contraseña. Sesiones activas revocadas al cambiar contraseña. | FR-01, AC-01 | Bloqueante funcional |
| US-A3 | Como usuario, necesito poder revocar sesiones activas individualmente para controlar el acceso desde dispositivos. | `GET /api/auth/sessions` lista sesiones propias. `DELETE /api/auth/sessions/{id}` revoca la sesión indicada. La sesión revocada no puede usarse. | FR-01, NFR-08, AC-01 | Must sin implementación |

### Bloque B · Documentos (M03)

| ID | Historia | Criterios de aceptación mínimos | Requisitos SRS | Prioridad |
|---|---|---|---|---|
| US-B1 | Como productor de eventos, necesito cargar contratos en PDF y DOCX para que el sistema pueda analizarlos. | PDF con texto → extrae texto, asocia al expediente. DOCX → extrae texto. PDF sin texto → estado `pending_ocr` (OCR es Should; el fallo es explícito, no silencioso). Archivo con extensión/MIME discordante → 415. Archivo > límite configurado → 413. Archivo con contenido malicioso → rechazado antes de entrar al índice. | FR-05, NFR-09, AC-03 | Bloqueante funcional |
| US-B2 | Como sistema, necesito validar tipo, tamaño y contenido de archivos antes de procesarlos para evitar que contenido malicioso entre al pipeline de IA. | Validación de MIME real (no solo extensión). Archivos con macros/scripts → rechazados. Nada rechazado entra al índice ni al modelo. Evidencia de exclusión tras borrado. | NFR-09, BR-08, AC-03 | Bloqueante seguridad |

### Bloque C · Fuentes jurídicas (M06)

| ID | Historia | Criterios de aceptación mínimos | Requisitos SRS | Prioridad |
|---|---|---|---|---|
| US-C1 | Como administrador, necesito dar de alta fuentes jurídicas con jurisdicción, autoridad, vigencia, estado y versión para que el corpus sea trazable. | `POST /api/admin/sources` crea fuente con metadatos requeridos. Fuente sin jurisdicción o fecha efectiva → 422. Fuente creada queda en estado `draft` hasta publicación. Acción registrada en `audit_events`. | FR-18, BR-05, AC-13 | Bloqueante funcional |
| US-C2 | Como administrador, necesito publicar, actualizar, desactivar y retirar fuentes conservando historial para mantener la trazabilidad del corpus. | Publicar fuente → estado `active`, disponible para RAG. Actualizar → nueva versión; versión anterior conserva metadatos. Desactivar → no aparece en recuperación; metadatos preservados. Retirar → igual que desactivar + marca `retired`. Cambios auditados. | FR-18, BR-05, AI-04, AC-10, AC-13 | Bloqueante funcional |
| US-C3 | Como administrador, necesito cargar el corpus piloto de Durango (reglamentos municipales, leyes estatales aplicables a eventos) para que las consultas tengan evidencia real. | Al menos una fuente activa por cada materia cubierta: protección civil, aforo, ruido, derechos musicales, alcohol. Fuentes con metadatos completos. Consulta de prueba devuelve cita verificable. | FR-18, BR-05, R-02 del plan | Bloqueante funcional |

### Bloque D · Consultas y RAG (M04)

| ID | Historia | Criterios de aceptación mínimos | Requisitos SRS | Prioridad |
|---|---|---|---|---|
| US-D1 | Como productor, necesito que las consultas recuperen solo fuentes activas aplicables a la jurisdicción y fecha del expediente para no recibir orientación obsoleta o de otra jurisdicción. | Consulta con expediente de Durango → solo fuentes activas de Durango. Fuente desactivada no aparece en citas. Fuente de otra jurisdicción no aparece. | AI-04, BR-05, AC-10 | Must sin implementación |
| US-D2 | Como productor, necesito que el sistema declare explícitamente cuando no tiene evidencia suficiente en lugar de inventar autoridad jurídica. | Pregunta sin evidencia → `outcome: INSUFFICIENT_EVIDENCE`, sin artículos inventados. `ensure_no_invented_authority` activo en producción. Limitación visible en UI. | AI-03, BR-04, AC-09 | Must parcialmente implementado |
| US-D3 | Como productor, necesito que el sistema identifique y cite fuentes en conflicto cuando existen para no recibir una respuesta que silencia una contradicción. | Dos fuentes con posiciones contrarias → respuesta menciona el conflicto y cita ambas. | AI-06, BR-06, AC-11 | Must sin implementación |
| US-D4 | Como productor, necesito ver la jurisdicción y fecha usadas en cada respuesta para poder verificar que aplica a mi evento. | Cada respuesta muestra `context.country`, `context.region`, `context.locality`, `context.date`. Si falta jurisdicción → sistema pide contexto antes de responder. | FR-04, BR-03, AC-04 | Must parcialmente implementado |

### Bloque E · Análisis contractual (M05)

| ID | Historia | Criterios de aceptación mínimos | Requisitos SRS | Prioridad |
|---|---|---|---|---|
| US-E1 | Como productor, necesito que el sistema identifique y etiquete cláusulas relevantes en contratos cargados para saber qué cubre y qué falta. | `POST /api/documents/{id}/analyses` → devuelve cláusulas etiquetadas con ubicación en el documento. Tipos mínimos: cancelación, indemnización, fuerza mayor, responsabilidad, pago, terminación. Ausencias explícitas, sin completar datos imaginados. | FR-07, AC-05 | Must sin implementación |
| US-E2 | Como productor, necesito que el sistema extraiga partes, obligaciones, fechas y condiciones de pago de contratos para tener un resumen estructurado. | Análisis devuelve partes, obligaciones, fechas, plazos, pagos y penalizaciones cuando existen literalmente. Campos ausentes marcados como `null` o `"no encontrado"`, nunca inventados. | FR-08, AC-05 | Must sin implementación |
| US-E3 | Como productor, necesito que el sistema señale inconsistencias, cláusulas faltantes y áreas de riesgo para saber qué revisar con un abogado. | Análisis devuelve lista de riesgos con severidad y referencia al texto. Riesgos clasificados como `Compliant`, `Conditional` o `Critical Risk` con rationale y evidencia. | FR-09, BR-10, AC-05 | Must sin implementación |

### Bloque F · Revisión humana (M05/M04)

| ID | Historia | Criterios de aceptación mínimos | Requisitos SRS | Prioridad |
|---|---|---|---|---|
| US-F1 | Como revisor, necesito reconocer explícitamente cada hallazgo `Critical Risk` antes de que un documento pueda marcarse como listo para ejecución. | Documento con `Critical Risk` sin reconocer → no puede cambiar a estado `ready`. Reconocimiento registrado con usuario, fecha y acción. Sin reconocimiento de IA automático. | FR-21 (SRS), BR-07, AC-06 | Must sin implementación |

### Bloque G · Privacidad y ciclo de vida (M07)

| ID | Historia | Criterios de aceptación mínimos | Requisitos SRS | Prioridad |
|---|---|---|---|---|
| US-G1 | Como usuario, necesito solicitar la exportación de todos mis datos personales y contenido asociado para ejercer mis derechos. | `POST /api/privacy-requests` con tipo `export` → trabajo asíncrono. `GET /api/exports/{id}/download` → archivo con casos, documentos, consultas, borradores. Sin contenido de otros usuarios. | FR-17, NFR-12, AC-12 | Must sin implementación |
| US-G2 | Como usuario, necesito solicitar la eliminación de mi cuenta y contenido para ejercer el derecho al olvido. | `POST /api/privacy-requests` con tipo `deletion` → elimina documentos, texto extraído, chunks, embeddings, consultas, borradores y cuenta. Conserva solo auditoría justificada. Política de retención aprobada como gate. | FR-17, NFR-12, BR-08, AC-12, AC-24 | Must sin implementación |
| US-G3 | Como sistema, necesito que el borrado de un documento elimine también sus chunks, embeddings y referencias en consultas para mantener consistencia. | Borrar documento → chunks eliminados del índice vectorial. Consultas que citaban ese documento → invalidadas o marcadas. Trabajos en curso sobre ese documento → cancelados. | BR-08, AC-03 | Must parcialmente implementado |

### Bloque H · Auditoría (M08)

| ID | Historia | Criterios de aceptación mínimos | Requisitos SRS | Prioridad |
|---|---|---|---|---|
| US-H1 | Como sistema, necesito registrar en `audit_events` los eventos de autenticación, cambios de fuentes, ingesta, borrado y acciones de seguridad para poder investigar incidentes. | Cada evento registra: tipo, usuario, timestamp, recurso afectado. Sin contraseñas ni contenido confidencial en el log. Eventos mínimos: login/logout, registro, cambio de fuente, carga de documento, borrado, solicitud de privacidad. | NFR-15, AC-18 | Must sin implementación |
| US-H2 | Como sistema, necesito registrar en `ai_runs` el modelo, versión de prompt, parámetros de recuperación, IDs de fuentes y timestamp de cada ejecución de IA para reproducir y auditar resultados. | Cada llamada a `generate_json` persiste un `ai_run` con los campos requeridos. `ai_run` vinculado a la consulta o borrador generado. | AC-22 (AI-09 pendiente de definición) | Must sin implementación |

### Bloque I · Seguridad de infraestructura (transversal)

| ID | Historia | Criterios de aceptación mínimos | Requisitos SRS | Prioridad |
|---|---|---|---|---|
| US-I1 | Como operador, necesito que todo el tráfico web de producción use HTTPS con TLS soportado para proteger datos en tránsito. | Certificado válido. HTTP redirige a HTTPS. TLS < 1.2 rechazado. | NFR-05, AC-16 | Bloqueante seguridad |
| US-I2 | Como operador, necesito que los secretos (claves de BD, modelo, firma de sesión) estén fuera del código y del control de versiones. | Repositorio sin secretos (escaneo automatizado). Configuración inyectada por variables de entorno o almacén de secretos. | NFR-11, AC-16 | Bloqueante seguridad |
| US-I3 | Como operador, necesito una copia de seguridad programada y una restauración documentada antes de producción. | Procedimiento de backup documentado. Restauración ejecutada en entorno de prueba con acta. | NFR-16, AC-19 | Gate de producción |

---

## Resumen de cobertura

| Bloque | Historias | Must SRS cubiertos |
|---|---|---|
| A · Identidad | 3 | FR-01, FR-02, NFR-06, NFR-08 |
| B · Documentos | 2 | FR-05, NFR-09, BR-08 |
| C · Fuentes | 3 | FR-18, BR-05, AI-04 |
| D · Consultas/RAG | 4 | FR-03, FR-04, AI-03, AI-04, AI-06, BR-03, BR-04, BR-06 |
| E · Análisis contractual | 3 | FR-07, FR-08, FR-09, BR-10 |
| F · Revisión humana | 1 | FR-21, BR-07 |
| G · Privacidad | 3 | FR-17, NFR-12, BR-08, BR-09 |
| H · Auditoría | 2 | NFR-15, AC-18, AC-22 |
| I · Infraestructura | 3 | NFR-05, NFR-11, NFR-16 |
| **Total** | **24** | **44 Must cubiertos** |

---

## Gates de producción (no negociables antes de liberar)

1. Política de retención aprobada por responsable del proyecto (R-05 del plan).
2. Corpus jurídico piloto revisado por persona experta (R-02 del plan).
3. Evaluación RAG documentada con conjunto representativo (AC-23).
4. HTTPS activo y secretos fuera del repositorio (US-I1, US-I2).
5. Restauración de backup documentada (US-I3).
6. MFA administrativo funcional (US-A1).

---

## Decisiones pendientes que bloquean implementación

| Decisión | Bloquea | Responsable |
|---|---|---|
| Periodos de retención por clase de dato | US-G1, US-G2, US-G3 | Responsable del proyecto |
| Tamaño máximo de archivo y formatos exactos | US-B1, US-B2 | Equipo técnico + producto |
| Fuentes jurídicas piloto y permisos de uso | US-C3 | Responsable jurídico |
| Modelo generativo y política de tratamiento de datos | US-D1–D4 | Arquitectura + privacidad |
| Perfil de carga para pruebas de rendimiento | AC-15 | QA + operación |
| Responsable de revisión jurídica del corpus | R-02 del plan | Producto |
