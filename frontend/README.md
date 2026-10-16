# juridIA web

React + TypeScript + Vite. Interfaz de apoyo jurídico preliminar para organizar eventos. El sitio alojado es una demostración estática con datos ficticios y cambios en memoria.

```sh
npm ci
npm run dev
npm run build
npm test
```

El modo predeterminado conecta a FastAPI mediante el proxy local de Vite en `/api`. Para la demostración y para una publicación estática, establece `VITE_DATA_MODE=demo` explícitamente al ejecutar o compilar. Las instrucciones completas están en el README de la carpeta padre.

La versión local permite elegir búsqueda documental sin IA o revisión con Ollama. Los borradores admiten plantillas, generación local e historial de versiones. El corpus legal aún no está conectado; el contenido requiere revisión profesional.

Verificación del navegador: con la demo activa, ejecutar `node scripts/verify-browser.mjs`. Capturas e informe temporal se guardan fuera del frontend, en `../tmp/`.
