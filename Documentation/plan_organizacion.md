# Plan: organización del proyecto y definición del stack

## Problema y enfoque

La documentación y los archivos de configuración describen estados distintos del proyecto: el README aún presenta MySQL/XAMPP como opción principal, mientras que las decisiones y el diseño más recientes seleccionan PostgreSQL con pgvector. También hay alternativas arquitectónicas redactadas como opciones abiertas, manifiestos de dependencias con distintos alcances y dos áreas de documentación cuyo propósito no está explicado desde un punto de entrada común.

Organizar el proyecto sin introducir una migración funcional. Establecer qué carpetas contienen código, documentación académica, decisiones técnicas, base de datos y scripts; definir un documento breve como fuente de verdad para herramientas y tecnologías; y alinear documentación del backend y la raíz con las decisiones confirmadas. Mantener el estado actual del prototipo claramente separado del stack objetivo.

## Alcance confirmado

- Incluir backend, estructura raíz, documentación técnica/académica y descripción de herramientas.
- Excluir el frontend del análisis y de cualquier cambio.
- Usar como stack objetivo React + TypeScript/Vite, FastAPI, PostgreSQL + pgvector, SQLAlchemy/Alembic y Ollama local, conforme a las decisiones recientes. La referencia a frontend solo contextualiza la arquitectura; no se inspeccionará ni modificará.
- No realizar migración MySQL→PostgreSQL, cambios de runtime, refactor de backend, instalación de herramientas ni reubicación masiva de archivos en esta etapa.
- Preservar el contenido académico y los cambios preexistentes del usuario; documentar discrepancias de implementación como pendientes.

## Trabajo propuesto

1. Auditar el inventario no relacionado con frontend y clasificar su responsabilidad: entrada del proyecto, entregables académicos, documentación de ingeniería, backend, SQL y scripts.
2. Definir una guía de herramientas con tecnología, uso, estado (adoptada, actual del prototipo, opcional o pendiente) y fuente de configuración. Registrar explícitamente el stack objetivo, herramientas de desarrollo/pruebas y decisiones no tomadas, sin añadir dependencias.
3. Ajustar el README de raíz y los documentos técnicos directamente relacionados para quitar contradicciones entre stack elegido, alternativas futuras y prototipo actual. Añadir referencias entre documentos sin fusionar ni mover los entregables académicos.
4. Verificar enlaces, nombres de rutas y consistencia de las afirmaciones del stack; reportar por separado las discrepancias que requieren cambios funcionales posteriores.

## Consideraciones

- `Documentation/` contiene entregables de arquitectura/requisitos, mientras `docs/` contiene material técnico de trabajo; conservar ambas áreas y aclarar su propósito, en lugar de mezclarlas.
- El repositorio incluye cambios previos sin confirmar; integrar solo ediciones puntuales que no los sobrescriban.
- El esquema PostgreSQL recién añadido y los documentos con decisiones no implican que la aplicación ya haya migrado desde MySQL.
- No se seleccionará modelo/dimensión de embeddings, ni se incorporarán Redis, proveedores de IA externos, OCR, object storage u otras herramientas que estén descritas solo como alternativas o fases futuras.

## Criterios de salida

- Una persona puede identificar dónde empezar y dónde encontrar cada clase de documentación.
- Hay una lista clara de herramientas objetivo y su estado, sin confundirlas con las usadas efectivamente por el prototipo.
- Los documentos de entrada relevantes concuerdan sobre PostgreSQL como objetivo y Ollama local para el piloto, y señalan las brechas de implementación sin afirmar que ya están resueltas.
- No se modifican archivos del frontend ni se introduce migración funcional.
