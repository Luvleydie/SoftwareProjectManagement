# Reporte de diseño de solución de software

**Proyecto:** juridIA, asistente jurídico preliminar para eventos. Nombre oficial del proyecto.

**Versión del diseño:** DSD-1.1, integración y revisión de consistencia. **Fecha:** 5 de octubre de 2026. **Estado:** propuesta documental, previa a implementación.

**Documentos de entrada:** el adjunto 1, «Activity Purpose», establece la actividad de diseño; el adjunto 2, «System Scope and Purpose», contiene el alcance y los requisitos. La especificación no declara versión. Para esta entrega se identifica como **RQ-recibida-2026-09-29**, etiqueta local que no implica una aprobación nueva. Ambos originales se conservan íntegros en `fuentes/`.

## 1. Introducción y alcance

### 1.1 Necesidad que atiende el proyecto

Un organizador de eventos trabaja con contratos de proveedores, condiciones de cancelación, permisos, responsabilidades y datos personales. Esa información puede encontrarse en documentos distintos y depender del lugar y de la fecha del evento. El problema que se busca resolver es localizar y organizar información pertinente, relacionarla con los documentos del usuario y reconocer los asuntos que necesitan revisión profesional.

Se diseña una aplicación web de apoyo informativo preliminar. Permitirá consultar fuentes jurídicas controladas, cargar documentos propios, identificar cláusulas y obligaciones, señalar inconsistencias y preparar borradores editables. Cada respuesta jurídica mostrará contexto territorial y temporal, evidencia disponible y limitaciones. La herramienta no representa al usuario ni sustituye a un abogado autorizado.

### 1.2 Objetivos del diseño

El diseño establece responsabilidades de componentes, contratos de intercambio, estructuras persistentes y comportamientos ante errores. También define cómo verificar privacidad, calidad de recuperación y trazabilidad. Su propósito es permitir que un equipo implemente la solución sin tener que inventar el alcance durante el desarrollo.

Los requisitos recibidos contienen **54 enunciados definidos: 20 funcionales, 17 no funcionales, 9 reglas de negocio y 8 de IA**. Se identifican **44 Must y 10 Should**, junto con **24 criterios de aceptación**. La aprobación académica que declara el documento original se conserva como antecedente; no constituye una certificación del producto.

### 1.3 Usuarios, roles y límites

El público comprende organizadores, personal administrativo, pequeñas empresas, equipos de proyecto y revisores autorizados. Se implementarán los dos roles requeridos:

| Actor | Necesidad | Permisos previstos |
|---|---|---|
| Usuario | Preparar consultas y revisar documentos de sus eventos | Acceso a sus expedientes, conversaciones, documentos, borradores y solicitudes de privacidad |
| Administrador | Mantener la calidad y vigencia del corpus | Administrar fuentes y revisar comentarios compartidos; requiere MFA |

Ser administrador no concede acceso general a documentos o conversaciones de otras cuentas. La colaboración entre usuarios no está definida para la primera versión. Los revisores profesionales pueden trabajar como usuarios o asumir funciones administrativas autorizadas; no se introduce un tercer rol por inferencia.

Se incluyen consultas sobre contratos, contingencias, permisos, responsabilidad y protección de datos vinculadas a eventos. El sistema no firma, presenta solicitudes, paga permisos, cancela eventos ni toma decisiones vinculantes. Las preguntas ajenas al dominio reciben una indicación de alcance.

FR-06, FR-13, FR-16 y FR-19 mantienen prioridad Should: OCR, seguros/responsabilidad, historial y comentarios. Se diseña su integración para evitar incompatibilidades posteriores; su existencia en el diseño no las convierte en obligaciones Must.

### 1.4 Puntos abiertos de la especificación

AI-09 y AI-10 aparecen en referencias de AC-22 y AC-23, pero no tienen un enunciado propio. El diseño implementable de auditoría de IA y evaluación se deriva directamente de esos criterios; ambos identificadores requieren formalización en la siguiente revisión de requisitos. No se suman al inventario de 54.

No se han fijado jurisdicción de lanzamiento, corpus inicial, modelo generativo, proveedor de infraestructura, carga de prueba ni plazos de conservación. Las elecciones y cifras adicionales de este documento son propuestas técnicas identificadas como tales. Se puede avanzar con el diseño general mientras se resuelven estas decisiones; la liberación de las funciones afectadas necesita que estén concretadas.

La sección 7 del adjunto de requisitos describe otra actividad: comparar estrategias de auditoría con LLM. No aporta resultados experimentales. Esta entrega desarrolla el documento de diseño solicitado por el adjunto 1 y no atribuye precisión, recall ni mejoras a experimentos que no se ejecutaron.

## 2. Arquitectura de la solución

### 2.1 Estilo y distribución de responsabilidades

Se propone una arquitectura cliente-servidor con **monolito modular**. El frontend presenta formularios y resultados; la API aplica autorización, reglas de negocio y validación; PostgreSQL almacena relaciones y vectores; un almacenamiento privado conserva los binarios. Un worker del mismo backend ejecuta las tareas extensas.

Las capas son presentación, aplicación, dominio e infraestructura. Cada módulo tiene servicios de aplicación y repositorios definidos, aunque todos se desplieguen inicialmente desde un solo repositorio. Esto evita distribuir transacciones y políticas de acceso entre muchos servicios durante una primera implementación académica.

La ingesta, inferencia, exportación y purga se procesan mediante trabajos persistentes. La API responde 202 al aceptar una tarea y ofrece consulta de estado. El worker reclama trabajos mediante bloqueo transaccional, establece un arrendamiento con vencimiento y registra reintentos. Las operaciones son idempotentes: repetir un trabajo no duplica documentos ni publica dos resultados.

### 2.2 Recorrido general

```text
Usuario / Administrador
          |
      HTTPS, navegador
          v
Interfaz React + TypeScript
          |
       REST / SSE
          v
Proxy TLS -> API FastAPI modular
                 |          |           |
                 v          v           v
       PostgreSQL/pgvector  Archivos    Correo de
       + cola de trabajos  privados    recuperación
                 ^          ^
                 |          |
              Worker asíncrono
                 |
      +----------+-----------+
      v          v           v
 Extracción   Embeddings   Adaptador de
 / OCR        locales      modelo generativo
```

SSE comunica estados y resultados de consulta. Los eventos de progreso no cuentan como respuesta útil para medir NFR-03. Las afirmaciones jurídicas solo se emiten después de validar su estructura y evidencia.

### 2.3 Despliegue, confianza y crecimiento

Para el piloto se propone una VM Linux con Docker Compose, proxy HTTPS, frontend estático, API y workers. Base y almacenamiento no se exponen a Internet. Las copias se guardan fuera de la VM. El host único es un riesgo documentado: esta arquitectura no garantiza por sí sola la disponibilidad requerida.

El sistema permite separar workers y base administrada si las mediciones de carga lo justifican. Primero se evaluarán consultas, índices, longitud de contextos y concurrencia. La complejidad de microservicios u orquestación distribuida no está justificada todavía por una escala medida.

Se consideran no confiables el navegador, los archivos cargados y los textos recuperados. El servidor obtiene el propietario desde la sesión validada. El modelo no recibe credenciales de infraestructura ni autorización para ejecutar acciones vinculantes. Desarrollo, pruebas y producción tendrán credenciales y datos distintos.

## 3. Tecnologías y justificación

Se fijarán versiones compatibles y soportadas al iniciar implementación. La siguiente tabla propone tecnologías; no describe instalaciones ya realizadas.

| Capa | Selección | Propósito y razón técnica |
|---|---|---|
| Interfaz | React, TypeScript y Vite | Componer chat, formularios, panel de evidencia y editor; detectar errores de tipos durante desarrollo |
| Aplicación | Python, FastAPI y Pydantic | Validar entradas y respuestas, publicar un contrato OpenAPI e integrar procesamiento documental |
| Datos | PostgreSQL con pgvector | Mantener relaciones, metadatos, permisos y vectores en la plataforma ya seleccionada por la especificación |
| Acceso a datos | SQLAlchemy y Alembic | Consultas parametrizadas y migraciones que se puedan revisar y ensayar |
| Identidad | Argon2id, sesiones opacas y TOTP | Almacenar hashes, revocar sesiones desde servidor y exigir segundo factor al administrador |
| Archivos | Almacenamiento privado con interfaz S3 | Separar binarios del modelo relacional, controlar acceso y aplicar cifrado/ciclo de vida |
| Extracción | pypdf, python-docx y Tesseract opcional | Extraer según formato y disponer de OCR cuando se incluya FR-06 |
| Aislamiento | Antivirus y contenedores restringidos | Impedir procesamiento directo de archivos no validados y limitar recursos del extractor |
| Vectorización | EmbeddingGemma local | Opción inicial de la especificación; evita transmitir documentos a un proveedor para obtener embeddings |
| Generación | Adaptador de LLM, modelo por seleccionar | Mantener un contrato de salida uniforme mientras se evalúan privacidad, calidad y latencia |
| Tareas | Worker Python y tabla jobs | Persistir y recuperar tareas sin añadir un broker en el piloto |
| Pruebas | pytest, Playwright, axe-core y k6 | Verificar dominio/API, flujos web, controles de accesibilidad y carga |
| Operación | Docker Compose, Nginx, Git y CI | Entornos reproducibles, ingreso TLS, versiones y controles antes de liberar |
| Observación | Logs JSON y métricas OpenTelemetry | Correlacionar errores, duración de trabajos y solicitudes sin copiar contratos completos |

React documenta la composición mediante componentes; FastAPI documenta validación y OpenAPI. Estas capacidades sustentan su selección para la interfaz y el contrato del backend. [React](https://react.dev/learn), [FastAPI](https://fastapi.tiangolo.com/features/).

EmbeddingGemma admite vectores de 768 dimensiones y entradas de hasta 2K tokens. Se propone iniciar con ese tamaño de vector y evaluar recuperación en el idioma y dominio reales. Los prefijos cuentan dentro del límite de entrada; no se truncarán cláusulas silenciosamente. [Ficha del modelo](https://ai.google.dev/gemma/docs/embeddinggemma/model_card).

## 4. Componentes del sistema

| Módulo | Responsabilidad | Requisitos principales | Dependencias |
|---|---|---|---|
| M01 Identidad | Registro, sesiones, recuperación, MFA y autorización | FR-01, FR-02; NFR-06, NFR-08, NFR-10 | Cuentas, sesiones, correo |
| M02 Expedientes | Contexto de jurisdicción, fecha, materia y evento; organización | FR-04, FR-16; BR-03 | M01, base de datos |
| M03 Documentos | Carga, validación, aislamiento, extracción, índice y borrado | FR-05, FR-06; NFR-09; BR-08 | Objetos, jobs, extractor, embeddings |
| M04 Consulta | Recuperación, generación, citas, conflictos y comentarios | FR-03, FR-11 a FR-15, FR-19, FR-20; AI-01 a AI-08 | M01, M02, M03, M06, modelo |
| M05 Análisis y borradores | Cláusulas, obligaciones, riesgos y texto editable | FR-07 a FR-10; BR-07 | Documentos, evidencia, modelo |
| M06 Fuentes | Alta, versiones, activación, retiro y reindexación | FR-18; BR-05; AI-04, AI-05 | M01, M03, metadatos |
| M07 Privacidad | Exportación, conservación y eliminación coherente | FR-17; NFR-12; BR-08, BR-09 | Todos los recursos privados y objetos |
| M08 Auditoría y evaluación | Eventos operativos, métricas, respaldos y evaluación RAG | NFR-15 a NFR-17; AC-22, AC-23 | Todos los módulos |

Los módulos de consulta y análisis utilizan una misma política de evidencia. El corpus jurídico es distinto del conjunto de documentos del usuario: cargar un contrato no lo convierte en autoridad jurídica pública. El aviso de apoyo preliminar se incorpora mediante una plantilla versionada compartida por pantalla y exportación.
