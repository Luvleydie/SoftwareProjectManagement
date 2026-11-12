# juridIA · Asistente jurídico preliminar para eventos

Base local actualizada el 15 de octubre de 2026. React + TypeScript + FastAPI, con persistencia por cuenta y un adaptador de IA local con Ollama. El diseño de referencia se conserva en `docs/`; esta base no pretende implementar todavía todos sus requisitos de producción.

Publicación histórica anterior al cambio de nombre (no actualizada): [Demostración privada](https://bautista-legal.dtm123.chatgpt.site). La publicación contiene únicamente la interfaz en modo demo; las cuentas y la persistencia se ejecutan localmente con FastAPI.

## Qué se puede usar

- Interfaz en español con escritorio, expedientes, documentos, consultas, borradores, fuentes y configuración; adaptable a móvil.
- Crear y editar expedientes con país, estado, municipio, materia, fecha y contexto.
- Incorporar archivos TXT UTF-8 de hasta 1 MB; ver texto y fragmentos por categorías. PDF, DOCX y OCR aún no están implementados.
- Preparar consultas con selección explícita de documentos, pasajes literales y contexto histórico. El selector permite buscar por palabras clave sin IA o pedir una revisión al modelo local.
- Preparar fichas de acuerdos a partir de plantillas o con IA; editar, consultar el historial y recuperar una versión anterior como una nueva revisión. Las versiones previas a este incremento que ya fueron sobrescritas no pueden recuperarse.
- Exportar borradores y consultas a TXT editable, y el espacio completo a JSON.
- Eliminar documentos y las consultas que los citan; eliminar expedientes con sus recursos asociados.
- API local con registro, acceso, contraseñas Argon2id, sesiones opacas revocables en cookies HttpOnly, CSRF, validación de origen, límites de intentos y aislamiento por usuario.

**La IA es opcional y local. No hay un corpus jurídico verificado.** Las consultas con IA usan pasajes privados y validan las referencias devueltas por el modelo; la recuperación es léxica, sin embeddings. El modo sin IA funciona incluso con Ollama apagado. Si la generación falla se muestra el error, sin sustituirla silenciosamente por una plantilla. Los borradores requieren revisión profesional.

## Inicio rápido

Con las dependencias instaladas y la base de datos configurada:

```powershell
./iniciar.ps1 -SegundoPlano
```

Abre **http://127.0.0.1:5173/**. El inicio normal levanta cuentas y persistencia, comprueba la API y arranca el Ollama portable si ya está instalado. No descarga modelos automáticamente. Registros: `tmp/runtime/`. Para detener únicamente los procesos de esta ejecución: `./detener.ps1`.

También puedes usar `./iniciar.ps1` en primer plano (Ctrl+C para detener), `-Demo` para ejemplos en memoria o `-SinIA` para no arrancar Ollama. `-ConCuenta` sigue siendo compatible y equivale al inicio normal. Los puertos ocupados producen un mensaje explícito.

## Ejecutar la demostración

Requisitos utilizados: Node.js 24 y Python 3.14. Las dependencias JavaScript están fijadas en `frontend/package-lock.json`; las de Python en `backend/requirements.lock.txt`.

Desde PowerShell, en esta carpeta:

```powershell
cd frontend
npm ci
$env:VITE_DATA_MODE = 'demo'
npm run dev
```

Abre `http://127.0.0.1:5173/`. Esta modalidad usa ejemplos ficticios y mantiene todos los cambios únicamente en memoria. Recargar reinicia la demostración. Los archivos cargados no se envían al servidor ni a proveedores de IA. Usa la exportación si quieres conservarlos.

## Ejecutar con cuentas y persistencia

Terminal 1, desde la raíz:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
# Solo si no existe una configuración local:
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, desde la raíz (detén antes cualquier servidor que use 5173):

```powershell
cd frontend
npm ci
$env:VITE_DATA_MODE = 'api'
npm run dev
```

Abre `http://127.0.0.1:5173/`, crea una cuenta y un expediente. La API lee `backend/.env` automáticamente. El ejemplo utiliza SQLite en `backend/juridia.db`; esta instalación usa MySQL de XAMPP. No reemplaces un `.env` existente. Sin `JURIDIA_DATABASE_URL`, se usan las variables `JURIDIA_MYSQL_*` y el puerto 3306. La clave de sesión nunca se guarda en el almacenamiento del navegador. La contraseña debe tener entre 12 y 128 caracteres. La sesión dura 12 horas.

API interactiva: `http://127.0.0.1:8000/docs`. Estado: `http://127.0.0.1:8000/api/health`.

El script no cambia la política de ejecución de PowerShell. Para instalar el runtime y el modelo opcional, usa `./scripts/setup-ai.ps1`; requiere descargar varios GB. El modelo y la dirección local se configuran con `JURIDIA_AI_MODEL` y `JURIDIA_OLLAMA_URL`.

## Base de datos y siguientes incrementos

SQLAlchemy admite PostgreSQL mediante `JURIDIA_DATABASE_URL`, por ejemplo `postgresql+psycopg://usuario:clave@localhost:5432/juridia`. No se incluyen credenciales. Puedes establecer las variables en `backend/.env` o en el proceso; las del proceso tienen prioridad.

El DDL PostgreSQL para las tablas que usa actualmente la aplicación está en [`db/schema.postgresql.sql`](db/schema.postgresql.sql). Para crear las tablas manualmente en una base ya creada: `psql -d juridia -f db/schema.postgresql.sql`. Al iniciar, SQLAlchemy también crea las tablas que falten. Este esquema no incluye pgvector: los embeddings todavía se guardan como JSON y la dimensión vectorial está pendiente de decidir.

El esquema `users`, `sessions`, `artifacts`, `draft_versions` es una simplificación de desarrollo, con recursos JSON y controles de propietario en la API. La nueva tabla de versiones se crea al arrancar, conservando los datos existentes. Aún no implementa el diccionario relacional completo, Alembic, RLS, pgvector, embeddings, S3, extracción aislada, trabajos persistentes ni SSE.

Orden propuesto para continuar:

1. Migraciones y esquema relacional definitivo de PostgreSQL; MFA administrativo, recuperación y privacidad completa.
2. Almacenamiento privado, antivirus/aislamiento, ingesta PDF y DOCX, trabajos y borrado consistente.
3. Elegir jurisdicciones y fuentes primarias, revisar su vigencia y habilitar administración del corpus.
4. Incorporar embeddings locales y ampliar la evaluación del adaptador de modelo y sus citas.
5. Evaluación RAG, pruebas de seguridad, carga, accesibilidad ampliada y recuperación antes de producción.

## Validación

```powershell
# Desde frontend/
npm run build
npm test
npx playwright install chromium
# Con la demo ejecutándose en 127.0.0.1:5173
node scripts/verify-browser.mjs

# Desde backend/
.\.venv\Scripts\python.exe -m pytest -q
# Con la aplicación completa ejecutándose; crea y limpia una cuenta de prueba:
.\.venv\Scripts\python.exe scripts/verify_browser.py
# Opcional: generación real con Ollama, con una cuenta temporal que se limpia:
.\.venv\Scripts\python.exe scripts/verify_ai.py
```

Evidencias y límites de las comprobaciones: [VERIFICACION-IMPLEMENTACION.md](VERIFICACION-IMPLEMENTACION.md).

## Límites de despliegue

La versión compartida con Sites contiene únicamente la demostración estática de React. No publica FastAPI, cuentas, documentos de usuarios ni los archivos originales de diseño. El código fuente del frontend queda en el repositorio privado de ese Site.

La API es una base local de desarrollo: aún no dispone de TLS, cifrado de documentos en reposo, copias verificadas, políticas de conservación, MFA, auditoría completa, límites distribuidos o tratamiento seguro de archivos binarios. Se usan borrados transaccionales de registros activos; no se promete borrado forense del archivo SQLite ni eliminación de exportaciones ya descargadas. No desplegar esta API para datos confidenciales sin completar esas etapas.

El límite de 1 MB/TXT es una decisión reversible del prototipo, no un cambio a los requisitos. Las 54 exigencias y 24 criterios originales siguen siendo la referencia; esta entrega no afirma cumplirlos todos.

Referencias técnicas consultadas: [Vite](https://vite.dev/guide/), [cookies de respuesta de FastAPI](https://fastapi.tiangolo.com/advanced/response-cookies/). No son fuentes jurídicas.

## Revisión del 16 de octubre de 2026

- Acceso en una sola tarjeta y escritorio simplificado: consulta y expedientes recientes, sin estadísticas ni paneles promocionales repetidos.
- Navegación con fondo claro y fuentes del sistema, sin descarga de tipografías externas.
- Los clics en el margen interior de un diálogo ya no lo cierran; el fondo exterior y el botón de cierre conservan su función.
- El filtro de documentos se limpia si su expediente deja de existir.
- Se conserva el inicio local con cuentas, MySQL y Ollama mediante `./iniciar.ps1 -SegundoPlano`.

El proyecto se llama **juridIA**. Las variables de configuración usan el prefijo `JURIDIA_`. Se conservan los identificadores de la base de datos existente en `.env` para mantener cuentas y documentos.

## Chat de IA

El inicio abre el chat de juridIA. Cada mensaje usa el modelo local de Ollama; no hay selector de respuestas preprogramadas ni sustitución por plantillas ante un error. La demostración estática no genera respuestas.

Puedes iniciar un chat sin expediente. En «Contexto y documentos» puedes asociar un expediente y seleccionar archivos antes del primer mensaje. Las conversaciones se guardan por cuenta y admiten seguimiento: el modelo recibe hasta los cuatro turnos anteriores, con longitud limitada. Los turnos basados en documentos solo se reutilizan si esos documentos siguen seleccionados. «Nuevo chat» empieza un historial independiente.

La interfaz conserva un formato sencillo, con lista de conversaciones, mensajes y cuadro de escritura. Enter envía; Mayús + Enter añade una línea. No hay transmisión de tokens: la respuesta aparece cuando termina la generación. El corpus jurídico oficial sigue pendiente; usar un modelo real no implica verificar la vigencia de sus afirmaciones.
