## 19. Plan de implementación y entrega

Esta entrega termina en la fase **Requisitos → Diseño**. La actividad indica que todavía no se debe programar. La estructura creada contiene fuentes, reporte y diagramas; no contiene una aplicación ejecutable ni un despliegue.

La implementación se propone en seis incrementos, sin asignar fechas o estimaciones que no se hayan calculado:

1. Identidad, permisos, esquema inicial, migraciones y configuración de secretos.
2. Carga segura, extracción, almacenamiento, estados de ingesta y eliminación coherente.
3. Administración de fuentes, versiones, perfiles de embeddings y recuperación filtrada.
4. Consultas con evidencia, análisis separados, borradores y avisos de revisión.
5. Exportación y privacidad; funciones Should según la prioridad acordada para la entrega.
6. Pruebas RAG, seguridad, carga, accesibilidad, navegadores y restauración antes de liberar.

Cada incremento debe conservar una relación entre requisito, cambio y evidencia de prueba. Los escenarios Should se identifican expresamente si quedan diferidos. Una especificación de pruebas no sustituye su ejecución.

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
