## 11. Seguridad, privacidad y conservación

### 11.1 Identidad y permisos

Las contraseñas se guardarán como hashes Argon2id con sal por cuenta, siguiendo una configuración revisada y calibrada en el servidor. OWASP recomienda ese algoritmo para nuevas implementaciones. [Guía de almacenamiento de contraseñas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).

La sesión será un token aleatorio opaco cuyo hash se conserva en el servidor. El navegador recibe una cookie `Secure`, `HttpOnly` y `SameSite=Lax`. La API requiere protección CSRF y comprobación de origen para operaciones que cambian estado, incluido el acceso. Cerrar sesión, recuperar contraseña y eliminar cuenta revocan las sesiones correspondientes. Se proponen 30 minutos de inactividad y 8 horas de duración absoluta, ajustables después de validar usabilidad y riesgo. Las cookies protegidas no sustituyen controles CSRF. [Guía de sesiones de OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

El administrador completa TOTP antes de obtener una sesión con permisos administrativos. Su secreto se cifra; los códigos de recuperación son de un solo uso y se almacenan como hashes en `mfa_recovery_codes`. Recuperar MFA requiere contraseña válida y un código de recuperación, revoca las sesiones y obliga a enrolar y verificar un nuevo TOTP antes de recuperar permisos. Un desafío MFA no sirve como sesión de usuario. La primera cuenta administradora se crea mediante una operación de despliegue auditada y enrolamiento obligatorio, nunca desde un selector público de rol. El contrato de identidad de §10 define recuperación, reautenticación y consumo transaccional de los códigos.

Los enlaces de recuperación se proponen con vigencia de 15 minutos, token de un solo uso y respuesta genérica tanto para cuentas existentes como inexistentes. La protección frente a intentos combina límites por cuenta y dirección de origen. Como punto inicial se propone aplicar espera progresiva después de cinco fallos de acceso en quince minutos, límites también en MFA y un máximo configurable de dos trabajos de IA simultáneos por cuenta. Las cifras son decisiones operativas propuestas, no umbrales del adjunto.

La API verifica propietario en toda operación sobre contenido privado. PostgreSQL aplica además políticas de seguridad por fila. La cuenta de aplicación no será superusuario, propietaria de tablas ni poseerá `BYPASSRLS`; los workers usarán contexto de propietario validado dentro de cada transacción. Ese contexto no debe persistir entre usuarios al reutilizar conexiones. PostgreSQL documenta las excepciones que tienen los roles privilegiados. [Seguridad por fila](https://www.postgresql.org/docs/17/ddl-rowsecurity.html).

### 11.2 Protección de contenido y archivos

El tráfico de producción usa HTTPS con una configuración TLS soportada. Se cifran los volúmenes de base de datos, los objetos, los temporales y las copias. Los secretos se cargan desde el entorno de despliegue o un almacén de secretos; no se incluyen en código, repositorios, mensajes de error ni registros.

La protección contra inyección SQL combina consultas parametrizadas y validación de tipos. El texto de IA se representa como contenido no confiable: HTML restringido o texto escapado, sanitización de enlaces y CSP. El origen permitido del frontend se define explícitamente; CORS no sustituye autenticación ni CSRF.

Los archivos ingresan a cuarentena. Se comprueban extensión, MIME real, estructura y límites antes de extraer contenido. Se propone comenzar con 20 MiB y 200 páginas para formatos paginados; DOCX se controla además por tamaño descomprimido y TXT por longitud. El antivirus se complementa con aislamiento, procesos sin privilegios, límites de CPU/memoria/tiempo y salida de red restringida. Un escáner indisponible no provoca que se omita el control.

Las URLs de fuentes son referencias verificadas, no instrucciones para que el servidor descargue cualquier dirección. El piloto usa carga administrada. Si se añade importación remota posteriormente, requerirá validación de destinos y protección contra SSRF.

### 11.3 Información personal y conservación

| Información | Finalidad | Acceso | Política operativa propuesta |
|---|---|---|---|
| Correo y datos de autenticación | Identificar y recuperar la cuenta | Usuario y módulo de identidad; secretos solo servidor | Durante la vida de la cuenta; purga según solicitud y política |
| Documentos, partes, consultas y borradores | Ejecutar las funciones solicitadas | Propietario y procesos autorizados | Máximo inicial de 180 días sin actividad, o borrado anterior |
| Fragmento y nota compartidos al reportar | Revisar una respuesta | Usuario y administrador del reporte | 90 días después de resolver, sujeto a borrado de dependencias |
| Exportaciones | Entregar información al titular | Propietario autenticado | 24 horas; invalidación anterior si se elimina el origen |
| Eventos técnicos | Seguridad y seguimiento de operaciones | Personal de operación autorizado | 90 días con datos mínimos |
| Copias de respaldo cifradas | Recuperación | Operación con credenciales separadas | Rotación de hasta 30 días |
| Fuentes jurídicas públicas | Evidencia y control de versiones | Usuarios según estado; administración | Mientras pertenezcan al corpus; metadatos según política de retiro |

Estos plazos son propuestas que deben validarse para el contexto de lanzamiento. No se atribuyen a una ley ni se presupone un país. La política final debe indicar inicio del cómputo, excepciones justificadas y cómo se informa al usuario.

Al aceptar un borrado se invalida el contenido y se impiden nuevas descargas, recuperaciones y publicaciones derivadas. El grafo persistente de dependencias identifica mensajes, análisis, borradores y exportaciones afectados. Se propone completar la purga de sistemas activos en 24 horas; una falla mantiene el bloqueo y activa reintentos. Las copias salen por rotación. Después de restaurar se reaplican las eliminaciones antes de reabrir el servicio. La cuenta de operación no debe poder restaurar accidentalmente un documento como si nunca se hubiera borrado.

Los reportes de respuesta solo comparten el fragmento elegido expresamente por el usuario. No habilitan acceso administrativo al resto de la conversación. Las exportaciones legibles conservan fuentes, contexto, aviso y carácter preliminar; sus versiones TXT y DOCX son editables para revisión humana.

La primera versión no tiene un flujo de entrenamiento con contenido privado. La configuración del proveedor generativo debe respetar esa restricción y la política de conservación. Aceptar términos generales no equivale a consentimiento separado de entrenamiento.

## 12. Requisitos no funcionales y verificación prevista

| Requisito | Objetivo y prioridad originales | Respuesta del diseño | Cómo verificar |
|---|---|---|---|
| NFR-01 | Must: flujos principales adaptables, sin desplazamiento horizontal | Paneles apilables y una columna en móvil | Ejecutar consulta, carga, revisión e historial en escritorio, tableta y móvil |
| NFR-02 | Must: al menos 95% de solicitudes no IA en ≤3 segundos, excluida transferencia | Índices, paginación y tareas largas fuera de peticiones breves | Prueba de carga: proporción total y por ruta; contar errores como incumplimiento |
| NFR-03 | Should: al menos 90% de IA ordinaria sin OCR empieza a responder en ≤15 segundos | Modelo preparado, cola acotada y emisión de texto validado | Medir del envío al primer contenido útil; incluir espera en cola |
| NFR-04 | Should: disponibilidad mensual ≥99%, excluyendo mantenimiento anunciado | Supervisión externa, reinicios y recuperación ensayada | Cociente de tiempo disponible sobre tiempo observado elegible, con registro de exclusiones |
| NFR-05 | Must: HTTPS y TLS soportado | Terminación TLS y cifrado de conexiones remotas | Inspección y prueba de configuración de producción |
| NFR-06 | Must: hash adaptativo y MFA administrativo | Argon2id, TOTP y recuperación controlada | Verificar hashes, MFA, caducidades y revocación |
| NFR-07 | Must: datos confidenciales protegidos en reposo | Cifrado en volúmenes, objetos, temporales y copias | Inspeccionar despliegue, claves y restauración |
| NFR-08 | Must: aislamiento entre usuarios | Autorización por recurso y RLS | Intercambiar IDs entre dos cuentas en lectura, búsqueda, descarga, jobs y SSE |
| NFR-09 | Must: tipo/tamaño y análisis o aislamiento de archivos | Cuarentena y extractor restringido | Tipos falsos, tamaño excesivo, archivos dañados y carga de prueba maliciosa |
| NFR-10 | Must: límites y protección temporal de acceso | Contadores de intentos y cuotas | Ráfagas controladas, 429 y recuperación después de espera |
| NFR-11 | Must: secretos fuera del código | Configuración externa y revisión de repositorio | Buscar secretos en archivos e historial antes de publicar |
| NFR-12 | Must: plazos definidos y restricción de entrenamiento | Política versionada, caducidad y borrado con dependencias | Ensayar vencimiento, purga y configuración del proveedor |
| NFR-13 | Should: criterios aplicables WCAG 2.1 AA | Etiquetas, contraste, teclado, foco y mensajes claros | axe-core más inspección manual con teclado y lector de pantalla |
| NFR-14 | Should: dos últimas versiones estables de Chrome, Edge, Firefox y Safari | Funciones web compatibles y pruebas por navegador | Registrar versiones vigentes al liberar; incluir Safari real |
| NFR-15 | Must: auditoría sin secretos o texto confidencial innecesario | Eventos con lista de campos permitidos | Provocar fallos, cambios de fuente, ingestas y borrados; revisar logs |
| NFR-16 | Must: copias programadas y restauración documentada | Copias diarias cifradas fuera del host como propuesta | Restaurar base, objetos y metadatos y comprobar integridad y borrados |
| NFR-17 | Should: pruebas críticas y configuración separada | CI para acceso, permisos, borrado, recuperación y citas | Ejecutar suite y conservar resultados reproducibles |

Los criterios de accesibilidad se contrastarán con [WCAG 2.1](https://www.w3.org/TR/WCAG21/). La automatización cubre una parte de la evaluación; no se declara conformidad completa a partir de una puntuación automática.

**Carga propuesta para comenzar:** 20 usuarios simultáneos, 1.000 documentos y aproximadamente 20.000 fragmentos; 5 minutos de calentamiento y 20 de medición. Mezcla inicial: 60% lecturas, 20% escrituras breves y 20% consultas de IA. El informe deberá registrar hardware, revisiones de modelos, red, tamaño de preguntas, caché, configuración de cola y errores. La ingesta se evalúa también en un escenario concurrente separado para medir interferencia.

La carga no figura cuantificada en el adjunto y debe acordarse como escenario de verificación. Los tiempos anteriores son metas del producto; no hay resultados medidos. Un evento «procesando» no satisface el inicio de respuesta de NFR-03. Como objetivos operativos iniciales se proponen RPO de 24 horas y RTO de 4 horas; requieren ensayo y ajuste antes de producción.

## 13. Diseño de inteligencia artificial y RAG

### 13.1 Entradas y preparación

Las entradas son pregunta, jurisdicción, fecha de referencia, materia, contexto del evento y documentos propios autorizados. El corpus contiene fuentes cargadas por administradores, con tipo, autoridad conocida, versión, estado, ámbito territorial y vigencia cuando estén disponibles.

La ingesta sigue: validar → aislar → extraer → aplicar OCR si está incluido y es necesario → limpiar sin perder referencias → dividir por estructura jurídica → generar vectores → almacenar metadatos → publicar generación de índice. Se conserva texto de origen y localizador de página, cláusula o artículo. Fechas ambiguas no se convierten en plazos inequívocos sin señalar la limitación.

Se ensayan fragmentos de 400–800 tokens y solapamiento de 10–15%, parámetros iniciales tomados del adjunto. Se ajustan mediante evaluación, respetando el límite del tokenizador y evitando dividir una cláusula sin contexto. El perfil de embeddings guarda modelo, revisión, dimensión y preparación de texto.

### 13.2 Recuperación, generación y salida

1. Autenticar, validar recursos seleccionados y comprobar que la pregunta pertenece al ámbito de eventos.
2. Solicitar contexto si falta jurisdicción o fecha necesaria para una respuesta específica.
3. Obtener el vector de consulta con el mismo perfil del índice y recuperar evidencia con filtros obligatorios de propietario, estado, jurisdicción y aplicabilidad temporal.
4. Dar preferencia a fuentes primarias y de autoridad superior cuando esa metadata sea conocida. Un contrato privado describe hechos y acuerdos; no se clasifica como ley.
5. Evaluar relevancia, cobertura y discrepancias. La puntuación de similitud no es una probabilidad de corrección jurídica.
6. Enviar al generador la pregunta minimizada, contexto y evidencia con identificadores permitidos. Separar instrucciones del sistema de texto no confiable; los documentos no habilitan herramientas ni acceso a secretos.
7. Validar esquema, pertenencia de citas a la evidencia recuperada, permisos aún vigentes y respaldo de afirmaciones. Si falla la validación, efectuar un reintento acotado o abstenerse.
8. Registrar ejecución y presentar respuesta, fuentes, jurisdicción/fecha, límites, posibles conflictos y aviso de revisión.

Para consultas actuales se prefieren versiones activas aplicables. Para preguntas sobre fechas anteriores se admite la versión histórica correspondiente, claramente identificada. Una fecha de vigencia desconocida no se presenta como comprobada. Las fuentes retiradas o desactivadas no entran en nuevas recuperaciones.

Se propone comenzar con búsqueda exacta filtrada y comparar su desempeño antes de incorporar índices aproximados. Si se utiliza HNSW, se verifica la recuperación con los filtros reales: pgvector documenta que esos filtros pueden reducir la cantidad de resultados de un índice aproximado. [Documentación de pgvector](https://github.com/pgvector/pgvector).

La salida diferencia afirmaciones respaldadas, información explicativa general e inferencias sobre documentos. Las citas se construyen con metadatos recuperados, no con URLs inventadas por el modelo. Una validación de identificadores demuestra procedencia, pero no prueba por sí sola que un pasaje respalde semánticamente una afirmación; eso requiere evaluación adicional.

```text
DATOS: pregunta + contexto + fuentes y documentos autorizados
  -> RECUPERACIÓN: permisos + jurisdicción + fecha + relevancia
  -> MODELO: instrucciones controladas + evidencia no confiable
  -> VALIDACIÓN: citas, respaldo, conflictos y acceso vigente
  -> SALIDA: información preliminar o abstención
  -> ACCIÓN: revisión y decisión del usuario/profesional
```

### 13.3 Modelo, entrenamiento y mantenimiento

EmbeddingGemma transforma texto en vectores; el modelo generativo redacta. Son funciones distintas. El generador se seleccionará mediante el conjunto de evaluación y las condiciones de privacidad, recursos y latencia. El uso externo estará deshabilitado si su configuración o condiciones impiden cumplir los requisitos de datos.

No se planifica entrenamiento ni ajuste fino en la primera versión. La actualización de conocimiento se realiza cambiando fuentes e índices. Una nueva revisión de embeddings exige reindexación en un perfil separado; no se mezclan vectores incompatibles. El cambio de modelo, prompt o fragmentación obliga a repetir pruebas de regresión. La publicación de un índice es atómica y conserva una ruta de reversión que respete las eliminaciones ya solicitadas.

### 13.4 Evaluación y auditoría

AC-22 pide identificar modelo/revisión, plantilla, parámetros de recuperación, fuentes y momento de ejecución. Ese registro no almacenará razonamiento privado del modelo ni duplicará innecesariamente documentos en logs. Una ejecución se crea como PENDING antes de aceptar el trabajo, pasa a RUNNING y termina respondida, abstenida o fallida.

Para AC-23 se propone un conjunto inicial de 150 casos revisados por una persona del dominio: 75 consultas respaldables, 15 sin evidencia, 15 históricas, 15 con conflictos, 15 con instrucciones maliciosas dentro de documentos y 15 fuera de alcance. El conjunto reservado para evaluación se separa de los ejemplos usados para ajustar el sistema. Cada caso define fuentes pertinentes y condiciones aceptables de respuesta o abstención.

| Métrica | Cálculo | Criterio propuesto |
|---|---|---|
| Recall@10 | Evidencias relevantes recuperadas / relevantes anotadas | Promedio ≥0,85, con desglose por materia; pendiente de validación |
| Procedencia de citas | Citas pertenecientes a evidencia autorizada de la ejecución / total | 100% en la suite |
| Respaldo semántico | Afirmaciones citadas sustentadas por su pasaje / afirmaciones revisadas | Revisar todos los fallos; cero errores críticos de liberación |
| Cobertura | Afirmaciones jurídicas verificables con evidencia adecuada / total revisado | La meta de diseño es respaldar todas; registrar incumplimientos |
| Abstención | Casos insuficientes correctamente abstenidos / casos insuficientes | Meta inicial ≥90%; registrar también abstenciones injustificadas |
| Conflictos y temporalidad | Casos correctamente identificados / casos anotados | Sin errores críticos en el conjunto de liberación |
| Aislamiento e inyección | Exposiciones o cambios de comportamiento indebidos | Cero fallos en la suite; no equivale a una garantía absoluta |
| Latencia | Tiempo al primer contenido validado y al final | Medir NFR-03 con la carga definida |

Los denominadores y tamaños de muestra deben publicarse junto a los porcentajes; cuando no existan casos aplicables se indica «no aplicable». Son criterios propuestos y no resultados. La comparación Zero-Shot/Few-Shot/Multi-Step del adjunto es una evaluación diferente, centrada en requisitos. Para ejecutarla hace falta una referencia humana correspondiente exactamente a la versión evaluada y conservar las salidas reales.

## 14. Integraciones

| Sistema | Propósito y comunicación | Datos intercambiados | Autenticación | Fallo y tratamiento |
|---|---|---|---|---|
| Correo transaccional | Recuperar cuenta mediante API HTTPS del proveedor por seleccionar | Correo y enlace temporal; sin contratos | Credencial de servicio protegida | Reintentos limitados; nunca mostrar tokens en logs |
| Objetos privados | Guardar originales, temporales y exportaciones por API HTTPS | Binarios y metadatos mínimos | Identidad de servicio de mínimo privilegio | No confirmar una purga ni una exportación antes de éxito real |
| Inferencia generativa | Adaptador local o API HTTPS elegida | Pregunta minimizada y fragmentos permitidos | Credencial externa si corresponde | Tiempo agotado o cuota: estado fallido y reintento; sin cambio silencioso de proveedor |
| Distribución del modelo de embeddings | Preparar entorno y descargar pesos | Pesos y configuración, sin datos de usuarios | Acceso/licencia según distribución | Resolver disponibilidad antes de iniciar ingesta; uso normal local |
| Fuentes jurídicas | Carga administrada y referencia verificable | Texto público y metadatos | Según origen de la fuente | Cambios de versión, URL o vigencia requieren revisión |
| Respaldo externo | Copias cifradas fuera del host | Base, archivos y metadatos | Credencial separada del servicio web | Alertar fallos y repetir restauración hasta obtener evidencia válida |

Los proveedores concretos y regiones se elegirán después de definir privacidad, presupuesto y cobertura. No se requieren pasarelas de pago ni sistemas de trámites para las funciones del alcance recibido.

## 15. Errores y recuperación

| Condición | Respuesta del sistema | Mensaje o estado visible | Recuperación |
|---|---|---|---|
| Acceso o MFA inválido | Rechazar sin revelar detalles; auditar; limitar intentos | No fue posible verificar el acceso | Reintento limitado o recuperación |
| Contexto insuficiente | No generar una afirmación específica | Señalar los campos requeridos | Completar sin perder la pregunta |
| Recurso ajeno | Responder sin revelar existencia o contenido | Recurso no disponible | Volver a recursos propios |
| Archivo inválido, corrupto o demasiado grande | Rechazo o cuarentena | Tipo, límite o causa segura | Cargar una versión aceptable |
| Escáner o extractor indisponible | Mantener aislamiento y tarea fallida/reintentable | Documento todavía no disponible | Restaurar dependencia y reintentar |
| PDF sin texto, OCR no incluido | No indexar como documento vacío | Se necesita una versión con texto | Cargar documento legible |
| Documento no listo | Impedir análisis prematuro | Estado de procesamiento | Consultar progreso sin duplicar tarea |
| Base u objetos indisponibles | No confirmar cambios inexistentes | Servicio temporalmente no disponible | Reintento idempotente |
| Modelo caído o solicitud agotada | Marcar fallo y conservar entrada autorizada | No se pudo generar la respuesta | Reintento acotado; no inventar respuesta de respaldo |
| Evidencia insuficiente | `state=SUCCEEDED`, `outcome=INSUFFICIENT_EVIDENCE` como resultado válido | Limitación y contexto o fuente faltante | Solicitar información o revisión profesional |
| Fuentes en conflicto | Presentar discrepancia y referencias | Evidencias que requieren revisión | Revisión humana |
| Evidencia eliminada durante generación | Invalidar salida antes de publicación | La evidencia cambió | Repetir recuperación si el usuario lo solicita |
| Exportación invalidada o vencida | Bloquear descarga | Archivo ya no disponible | Generar otra solo con contenido vigente |
| Desconexión del navegador | Mantener trabajo dentro de límites | Reconectando / consultar estado | Reanudar SSE autorizado o consultar API |
| Purga incompleta | Conservar inaccesibilidad, reintentar y alertar | Eliminación en proceso | Completar purga sin restaurar acceso |
| Restauración fallida | Impedir declarar recuperación verificada | Incidente para operación | Corregir copias y repetir ensayo |

Los errores usan códigos estables y un identificador de correlación. No incluyen pilas, secretos, SQL ni rutas internas. Un fallo posterior a una aceptación 202 se comunica mediante el estado del trabajo y no cambia retroactivamente el resultado HTTP inicial.
