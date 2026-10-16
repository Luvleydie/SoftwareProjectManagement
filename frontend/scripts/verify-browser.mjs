import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const apiMode = process.env.JURIDIA_E2E_API === "1";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });
const errors = [];
const results = [];
page.on("pageerror", (error) => errors.push(error.message));
const out = new URL("../../tmp/", import.meta.url);
await mkdir(out, { recursive: true });
async function check(name, action) {
  await action();
  results.push({ name, status: "passed" });
  console.log(`PASS ${name}`);
}
async function go(name) {
  await page
    .getByRole("navigation")
    .getByRole("button", { name, exact: true })
    .click();
}
try {
  await page.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
  if (apiMode) {
    await check("Registro y acceso con persistencia", async () => {
      await page.getByRole("button", { name: "¿Primera vez? Crea una cuenta" }).click();
      await page.getByLabel("Nombre", { exact: true }).fill("Prueba de juridIA");
      await page.getByLabel("Correo electrónico").fill(process.env.JURIDIA_E2E_EMAIL);
      await page.getByLabel("Contraseña", { exact: true }).fill(process.env.JURIDIA_E2E_PASSWORD);
      await page.getByRole("button", { name: "Crear cuenta", exact: true }).click();
      await page.getByRole("heading", { name: "Chat" }).waitFor();
    });
  }
  await check("Crear expediente y buscarlo", async () => {
    await go("Expedientes");
    await page
      .getByRole("button", { name: "Nuevo expediente", exact: true })
      .click();
    await page.getByLabel("Nombre del evento").fill("Evento QA");
    await page.getByLabel("Estado o región").fill("Puebla");
    await page.getByLabel("Municipio o localidad").fill("Atlixco");
    await page.getByLabel("Fecha del evento").fill("2026-12-20");
    await page.getByRole("button", { name: "Guardar expediente" }).click();
    await go("Expedientes");
    await page.getByLabel("Buscar expedientes…").fill("Evento QA");
    await page
      .getByRole("heading", { name: "Evento QA", exact: true })
      .waitFor();
  });
  await check("Cargar y revisar documento TXT", async () => {
    await go("Documentos");
    await page
      .getByLabel("Expediente para el documento")
      .selectOption({ label: "Evento QA" });
    await page
      .getByLabel("Seleccionar archivo TXT")
      .setInputFiles({
        name: "prueba.txt",
        mimeType: "text/plain",
        buffer: Buffer.from(
          "Partes: Ana y Proveedor.\n\nCancelación: el anticipo se revisará por escrito.\n\nPago: saldo pendiente.",
        ),
      });
    await page.getByRole("button", { name: /^prueba\.txt/ }).waitFor();
    await page.getByRole("button", { name: /^prueba\.txt/ }).click();
    await page.getByRole("button", { name: "Revisión de fragmentos" }).click();
    await page.getByRole("heading", { name: "Pagos", exact: true }).waitFor();
    await page
      .getByRole("button", { name: "Cerrar ventana", exact: true })
      .click();
  });
  await check("Chat con IA real y documentos", async () => {
    await go("Chat");
    await page.getByText("Contexto y documentos (opcional)", {exact:true}).click();
    await page.getByLabel("Expediente de trabajo").selectOption({label:"Evento QA"});
    await page.getByLabel("prueba.txt").check();
    await page.getByLabel("Mensaje", {exact:true}).fill("Resume lo que dice el documento sobre cancelación y anticipo.");
    const response = page.waitForResponse(r => r.url().endsWith('/api/consultations') && r.request().method() === 'POST', {timeout:260000});
    await page.getByRole("button", {name:"Enviar", exact:true}).click();
    const result = await response;
    assert.equal(result.status(), 201, await result.text());
    const answer = await result.json();
    assert.equal(answer.generation.provider, 'ollama');
    assert.ok(answer.citations.length > 0);
    await page.locator('.chat-message.assistant').waitFor();
    await page.getByText("Fuentes y detalles", {exact:true}).click();
    const download = page.waitForEvent("download");
    await page.getByRole("button", {name:"Exportar respuesta"}).click();
    assert.ok((await download).suggestedFilename().endsWith('.txt'));
    await page.reload({waitUntil:'networkidle'});
    await page.locator('.chat-message.assistant').waitFor();
  });
  await check("Crear, editar y exportar borrador", async () => {
    await go("Borradores");
    await page
      .getByRole("button", { name: "Nuevo borrador", exact: true })
      .click();
    await page.getByLabel("Partes involucradas").fill("Ana y proveedor");
    await page
      .getByLabel("Condiciones conocidas")
      .fill("Montaje el día 20. Importe pendiente de acuerdo.");
    await page.getByRole("button", { name: "Crear ficha editable" }).click();
    const editor = page.getByLabel("Contenido editable");
    await editor.waitFor();
    const content = await editor.inputValue();
    assert.ok(content.includes("REVISIÓN PROFESIONAL REQUERIDA"));
    await editor.fill(`${content}\nNota de prueba del usuario.`);
    await page.getByRole("button", { name: "Guardar versión" }).click();
    await page.getByRole("button", { name: "Abrir editor" }).click();
    assert.ok(
      (await editor.inputValue()).includes("Nota de prueba del usuario."),
    );
    const download = page.waitForEvent("download");
    await page
      .getByRole("button", { name: "Exportar TXT", exact: true })
      .click();
    await download;
    await page.getByRole("button", { name: "Cerrar ventana" }).click();
  });
  await check("Consultar historial y restaurar como nueva versión", async () => {
    await page.getByRole("button", { name: "Abrir editor" }).click();
    await page.getByRole("button", { name: "Historial de versiones", exact: true }).click();
    await page.getByRole("button", { name: /^Versión 1/ }).click();
    assert.ok(!(await page.locator(".version-preview pre").innerText()).includes("Nota de prueba del usuario."));
    await page.getByRole("button", { name: "Usar este contenido" }).click();
    await page.getByRole("button", { name: "Guardar versión" }).click();
    await page.getByText("Preliminar · v3", { exact: true }).waitFor();
  });
  if (apiMode) {
    await check("Recarga conserva sesión, sección y datos", async () => {
      await page.reload({ waitUntil: "networkidle" });
      await page.getByRole("heading", { name: "Borradores", exact: true }).waitFor();
      await page.getByText("Preliminar · v3", { exact: true }).waitFor();
      await page.getByRole("button", { name: "Abrir editor" }).click();
      await page.getByRole("button", { name: "Historial de versiones", exact: true }).click();
      await page.getByRole("button", { name: /^Versión 2/ }).click();
      assert.ok((await page.locator(".version-preview pre").innerText()).includes("Nota de prueba del usuario."));
      await page.getByRole("button", { name: "Cerrar ventana" }).click();
    });
    await check("Exportar datos con todo el historial", async () => {
      await page.getByRole("button", { name: "Configuración", exact: true }).click();
      const downloading = page.waitForEvent("download");
      await page.getByRole("button", { name: "Exportar datos", exact: true }).click();
      const downloaded = await downloading;
      const exported = JSON.parse((await readFile(await downloaded.path(), "utf8")).replace(/^\uFEFF/, ""));
      assert.equal(exported.cases.length, 1);
      assert.deepEqual(exported.draft_versions.map(v => v.version).sort(), [1, 2, 3]);
    });
  }
  await check(
    "Eliminar documento e invalidar consulta dependiente",
    async () => {
      await go("Documentos");
      await page
        .getByRole("button", { name: "Eliminar prueba.txt", exact: true })
        .click();
      await page.getByRole("button", { name: "Confirmar eliminación" }).click();
      await page.getByRole("dialog").waitFor({ state: "hidden" });
      await go("Chat");
      await page
        .getByText("Aquí se guardarán tus chats.")
        .waitFor();
    },
  );
  await go("Chat");
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const accessibility = await page.evaluate(
    async () =>
      await window.axe.run(document, {
        runOnly: { type: "tag", values: ["wcag2a", "wcag2aa"] },
      }),
  );
  await writeFile(
    new URL("accessibility.json", out),
    JSON.stringify(accessibility.violations, null, 2),
  );
  console.log(
    "A11Y",
    JSON.stringify(
      accessibility.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          summary: n.failureSummary,
        })),
      })),
    ),
  );
  assert.equal(
    accessibility.violations.length,
    0,
    "La pantalla principal debe pasar las comprobaciones automatizadas de accesibilidad.",
  );
  await page.screenshot({
    path: new URL("juridia-desktop-verified.png", out).pathname.replace(
      /^\/([A-Z]:)/,
      "$1",
    ),
    fullPage: true,
  });
  for (const width of [390, 320]) {
    await check(`Móvil ${width}px sin desbordamiento`, async () => {
      await page.setViewportSize({ width, height: 844 });
      const dims = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        width: innerWidth,
      }));
      assert.ok(dims.scroll <= dims.width + 1, JSON.stringify(dims));
      await go("Expedientes");
      await page.getByLabel("Buscar expedientes…").fill("");
      await page
        .getByRole("heading", { name: "Evento QA", exact: true })
        .waitFor();
      const dims2 = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        width: innerWidth,
      }));
      assert.ok(dims2.scroll <= dims2.width + 1, JSON.stringify(dims2));
      await page.screenshot({
        path: new URL(`juridia-mobile-${width}.png`, out).pathname.replace(
          /^\/([A-Z]:)/,
          "$1",
        ),
        fullPage: true,
      });
      await go("Chat");
    });
  }
  if (apiMode) {
    await check("Cerrar sesión y volver a entrar", async () => {
      await page.setViewportSize({ width: 1440, height: 1080 });
      await page.getByRole("button", { name: "Configuración", exact: true }).click();
      await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
      await page.getByLabel("Correo electrónico").fill(process.env.JURIDIA_E2E_EMAIL);
      await page.getByLabel("Contraseña", { exact: true }).fill(process.env.JURIDIA_E2E_PASSWORD);
      await page.getByRole("button", { name: "Entrar a mi espacio" }).click();
      await page.getByRole("heading", { name: "Chat" }).waitFor();
      await go("Borradores");
      await page.getByText("Preliminar · v3", { exact: true }).waitFor();
      await page.getByRole("button", { name: "Configuración", exact: true }).click();
      await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
      await page.getByRole("heading", { name: "Iniciar sesión" }).waitFor();
      await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
      const authA11y = await page.evaluate(() => window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa"] } }));
      assert.deepEqual(authA11y.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) })), []);
      await page.screenshot({ path: new URL("juridia-login.png", out).pathname.replace(/^\/([A-Z]:)/, "$1"), fullPage: true });
      for (const width of [390, 320]) {
        await page.setViewportSize({ width, height: 844 });
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        await page.screenshot({ path: new URL(`juridia-login-${width}.png`, out).pathname.replace(/^\/([A-Z]:)/, "$1"), fullPage: true });
      }
    });
  }
  assert.deepEqual(errors, []);
  await writeFile(
    new URL("browser-results.json", out),
    JSON.stringify(
      {
        results,
        errors,
        accessibilityViolations: accessibility.violations.length,
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
