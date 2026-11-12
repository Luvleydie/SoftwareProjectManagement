## 19. Plan de implementación y entrega

El plan siguiente desarrolla la arquitectura propuesta, no amplía el alcance funcional ni añade una estimación de calendario. La implementación conserva un **monolito modular**: React/TypeScript en la interfaz, API FastAPI, PostgreSQL con pgvector, almacenamiento privado de objetos y workers Python que reclaman trabajos persistidos en la base de datos. El piloto mantiene inferencia y generación de embeddings locales; no se introduce Redis ni una arquitectura de microservicios. Los módulos M01–M08 y los contratos definidos en las secciones 4, 8, 10 y 13 son la referencia de implementación.

El orden refleja las dependencias del diseño y las decisiones registradas en [decisión arquitectónica](../decision-arquitectonica.md). Los componentes existentes del prototipo se migran o adaptan donde corresponda; su presencia no se toma como evidencia de que los criterios de salida siguientes ya se cumplieron.

### 19.1 Incrementos y criterios de salida

| Incremento | Componentes y objetivo | Trabajo de implementación | Entregable y criterio de salida |
|---|---|---|---|
| **0. Base ejecutable y decisiones bloqueantes** | M01–M08; configuración común | Fijar versiones compatibles y contratos entre módulos; separar configuración y secretos por entorno; establecer migraciones Alembic y pruebas en CI; formalizar perfiles de trabajo persistente (idempotencia, lease, reintentos y publicación); elegir y probar el modelo local de embeddings y su dimensión antes de crear columnas vectoriales. Conservar React/TypeScript, FastAPI, PostgreSQL y el adaptador local de Ollama previstos para el piloto. | Entornos reproducibles, configuración sin secretos en el repositorio y contratos versionados. Gate: no crear el esquema vectorial hasta decidir el perfil/dimensión y verificar una ejecución local de embeddings. |
| **1. PostgreSQL y persistencia** | M01–M08; infraestructura de datos | Preparar PostgreSQL y habilitar pgvector; convertir el esquema relacional existente y preparar migraciones reversibles; migrar usuarios, sesiones y artefactos conservando identificadores y relaciones; incorporar entidades y restricciones de propiedad; implementar transacciones para crear recursos y jobs juntos; configurar índices, copias de seguridad y procedimiento de restauración. Mantener SQLite únicamente como backend de pruebas si el contrato de acceso a datos lo permite. | Aplicación conectada a PostgreSQL, migración repetible y datos migrados reconciliados. Gate: pruebas de integridad, aislamiento entre propietarios, migración hacia delante/atrás y restauración satisfactoria antes de retirar la base anterior. |
| **2. Catálogo, versiones y publicación de fuentes** | M06, apoyado por M01 y M08 | Crear `legal_sources`, `source_versions` y metadatos de jurisdicción, autoridad, materia, vigencia y procedencia; implementar rutas administrativas autenticadas; conservar versiones históricas; separar borrador, activa, histórica e inactiva; hacer publicación atómica y auditable; impedir que una fuente incompleta o no procesada llegue a recuperación. | Administración puede registrar, versionar, activar, desactivar y retirar fuentes sin sobrescribir historial. Gate: la activación requiere versión procesada, metadatos requeridos y validación humana documentada; las fuentes desactivadas dejan de ser elegibles en nuevas consultas. |
| **3. Trabajos asíncronos e ingesta** | M03 y M06; almacenamiento privado y worker | Implementar el ciclo persistente de jobs y endpoints 202/consulta de estado; configurar almacenamiento de objetos privado mediante la interfaz S3 propuesta; validar contenido, tamaño y seguridad antes de procesar; extraer texto PDF/DOCX/TXT y OCR solo cuando se habilite; conservar hash, procedencia y localizadores; segmentar fuentes jurídicas por artículo y documentos privados por cláusula; generar embeddings con el perfil fijado; indexar en pgvector y publicar el resultado solo al terminar. Mantener corpus legal y documentos del usuario separados. | Ingesta recuperable ante fallo, con estados y errores explícitos; solo contenido validado y procesado queda indexable. Gate: reintentos no duplican resultados, los documentos en cuarentena/rechazados no llegan al índice ni al modelo y el borrado invalida sus derivados. |
| **4. Recuperación y consulta RAG** | M02, M04 y M06; adaptador local de inferencia | Aplicar autorización y contexto (jurisdicción, materia y fecha) antes de recuperar; buscar únicamente versiones activas o históricas temporalmente aplicables; combinar similitud vectorial con búsqueda léxica según la estrategia aprobada y evaluar filtros con los índices reales; registrar evidencia y parámetros por ejecución; aplicar suficiencia/abstención, generación estructurada local, validación de citas contra evidencia recuperada y construcción de citas desde metadatos del servidor; transmitir resultados y estados conforme al contrato REST/SSE. Los documentos privados podrán aportar contexto factual autorizado, pero nunca convertirse en autoridad jurídica. | Una consulta devuelve respuesta respaldada, conflicto identificado o abstención; cada cita corresponde a evidencia recuperada y visible. Gate: pruebas de jurisdicción/fecha, fuente inactiva, aislamiento, falta de evidencia, citas inventadas e inyección en documentos, sin fallos críticos. |
| **5. Análisis documental y generación de borradores** | M05, reutilizando M03/M04 | Implementar análisis por cláusula con localizadores, extracción de obligaciones y hallazgos explícitamente ausentes; recuperar normas por cláusula sin enviar el contrato completo como una sola instrucción; producir hallazgos con evidencia y severidad validada. Incorporar plantillas revisadas, recolección/validación de variables, vista previa editable, control de revisión y aviso de revisión profesional; conservar vínculo entre borrador, ejecución, expediente y evidencia. | Análisis y borradores se almacenan como artefactos versionados, editables y aislados por propietario; ningún campo ausente se inventa. Gate: toda conclusión jurídica del análisis tiene evidencia verificable y un borrador no se presenta como documento final o asesoría profesional. |
| **6. Acceso reforzado y auditoría** | M01 y M08 | Completar MFA obligatorio para administradores, recuperación de cuenta, reautenticación y revocación de sesiones; aplicar controles en servidor y no confiar en rol o propietario enviados por el cliente; registrar eventos administrativos y de seguridad con metadatos mínimos, evitando contraseñas, secretos y contenido contractual; correlacionar peticiones, ejecuciones y jobs con identificadores. | Acceso administrativo protegido por MFA y sesiones revocables; eventos relevantes trazables sin registrar contenido sensible innecesario. Gate: pruebas de acceso anónimo/usuario/admin, CSRF, expiración, revocación, recuperación y controles de acceso a recursos ajenos. |
| **7. Privacidad, ciclo de vida y exportación** | M07, con todos los módulos y almacenamiento | Implementar dependencias entre artefactos y eliminación consistente de binarios, texto, chunks, embeddings, citas, resultados y exportaciones; invalidar acceso desde la aceptación de una eliminación y purgar mediante jobs idempotentes; implementar exportación de datos del usuario y políticas de retención/anonimización aprobadas; mantener comprobantes de solicitud sin reabrir acceso a contenido eliminado. | Exportación y borrado verificables de extremo a extremo, incluyendo fallos y reintentos. Gate: demostrar que los datos purgados no reaparecen en búsquedas, citas, descargas o índices; la retención de datos personales no pasa a producción sin aprobación jurídica de la política. |
| **8. Revisión humana y liberación arquitectónica** | M05, M08 y despliegue completo | Incorporar reconocimiento explícito de hallazgos críticos antes de marcar un documento como listo; finalizar trazas y métricas operativas sin copiar texto sensible; ejecutar evaluación RAG versionada, pruebas de seguridad, accesibilidad, navegadores, carga, latencia y restauración; desplegar la topología propuesta (proxy TLS, frontend, API, worker, PostgreSQL y almacenamiento privado) con servicios de datos no expuestos públicamente y secretos independientes por entorno. | Candidato de liberación con resultados reproducibles, respaldo/restauración documentados y límites visibles. Gate: conjunto de evaluación revisado por especialista, cero fallos críticos de seguridad/citas, criterios de rendimiento medidos y HTTPS/restauración comprobados; resultados pendientes o fuera de objetivo bloquean la liberación correspondiente. |

### 19.2 Dependencias y reglas de ejecución

La ruta crítica es **base de datos → catálogo/versiones → jobs e ingesta → recuperación RAG → análisis/borradores → acceso reforzado y auditoría → privacidad → revisión humana y liberación**. La configuración, pruebas de contrato y observabilidad mínima comienzan en el incremento 0 y continúan en todos los demás. El incremento 5 depende de la ingesta y recuperación del 3–4; el incremento 7 depende del inventario de artefactos y sus relaciones; el 8 no sustituye la aprobación jurídica ni convierte una prueba automatizada en validación legal.

Cada job costoso debe persistirse antes de responder 202, comprobar la propiedad en cada lectura, ser idempotente y publicar resultados solo si conserva un lease válido. Los cambios de esquema e índices se entregan mediante migraciones; cada incremento incluye migración, pruebas de regresión y procedimiento de reversión. Un cambio de modelo, dimensión de embeddings, chunking, prompt o filtros obliga a reindexar cuando corresponda y repetir la evaluación de recuperación/generación.

No se amplía el piloto a nuevas jurisdicciones, proveedores generativos externos, microservicios ni capacidades fuera de las ya descritas en la arquitectura. Las decisiones aún abiertas —en especial el perfil/dimensión de embeddings, la asignación del revisor jurídico y la aprobación de retención— se tratan como gates, no como supuestos resueltos.

Cada incremento conserva la trazabilidad requisito → módulo/cambio → prueba → evidencia. Los escenarios diferidos se registran como pendientes; una especificación o un resultado del prototipo no sustituye la ejecución de la prueba de salida.

### Correspondencia con la actividad

| Apartado solicitado | Ubicación en esta entrega |
|---|---|
| 4.1 Introducción y versión de requisitos | Sección 1 y control de portada |
| 5 Arquitectura | Sección 2, D01 |
| 6 Tecnologías | Sección 3 |
| 7 Componentes | Sección 4, D03 |
| 8 Diagramas UML | Sección 5; casos de uso, componentes, despliegue y cuatro secuencias |
| 9 Interfaces | Sección 6, siete wireframes textuales |
| 10 Navegación | Sección 7, recorridos y diagrama |
| 11 Diccionario de datos | Sección 8 |
| 12 Modelo entidad-relación | Sección 9 |
| 13 API | Sección 10 |
| 14 Seguridad | Sección 11 |
| 15 Requisitos no funcionales | Sección 12 |
| 16 Diseño de IA | Sección 13 |
| 17 Integraciones | Sección 14 |
| 18 Errores y excepciones | Sección 15 |
| 19 Trazabilidad | Sección 16 |
| 20 Decisiones arquitectónicas | Sección 17 |
| 21 Riesgos y preguntas abiertas | Sección 18 |

### Referencias y estado de la evidencia

Las decisiones de alcance se sustentan en los dos adjuntos originales. Las referencias técnicas enlazadas en el texto describen tecnologías; no son fuentes jurídicas para responder consultas de eventos. No se afirma cumplimiento de leyes de un país no seleccionado.

- [Adjunto 1: actividad de diseño](../fuentes/01-actividad-diseno.txt).
- [Adjunto 2: alcance y requisitos](../fuentes/02-requisitos-proyecto.txt).
- [React: componentes e interacción](https://react.dev/learn).
- [FastAPI: características](https://fastapi.tiangolo.com/features/).
- [pgvector: búsqueda y filtros](https://github.com/pgvector/pgvector).
- [PostgreSQL: seguridad por fila](https://www.postgresql.org/docs/17/ddl-rowsecurity.html).
- [EmbeddingGemma: ficha del modelo](https://ai.google.dev/gemma/docs/embeddinggemma/model_card).
- [OWASP: contraseñas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).
- [OWASP: sesiones](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
- [W3C: WCAG 2.1](https://www.w3.org/TR/WCAG21/).

La integridad de las fuentes, la cobertura documental y la generación de diagramas se registran en `VERIFICACION.md`. Las mediciones del producto y de los experimentos de auditoría con LLM permanecen pendientes de una implementación y ejecución reales.
