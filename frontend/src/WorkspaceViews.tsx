import { useEffect, useRef, useState } from "react";
import {
  BookOpen,
  CalendarDays,
  Check,
  Download,
  FilePenLine,
  FileText,
  FolderOpen,
  MapPin,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
  Upload,
  X,
  LoaderCircle,
  History,
  RotateCcw,
} from "lucide-react";
import type {
  Case,
  Document as PrivateDocument,
  Draft,
  DraftInput,
  ServiceHealth,
  Workspace,
} from "./types";
import {
  analyzeDocument,
  dateLabel,
  DISCLAIMER,
  downloadText,
  id,
} from "./domain";
import { ContextChips, Empty, Modal, Notice, SearchField } from "./components";
import { API_MODE } from "./api";
import ServiceStatus from "./ServiceStatus";

export function CasesView({
  data,
  search,
  setSearch,
  onCreate,
  onEdit,
  onAsk,
}: {
  data: Workspace;
  search: string;
  setSearch: (s: string) => void;
  onCreate: () => void;
  onEdit: (c: Case) => void;
  onAsk: (c: Case) => void;
}) {
  const [filter, setFilter] = useState("Todos");
  const cases = data.cases.filter(
    (c) =>
      (filter === "Todos" || c.status === filter) &&
      `${c.name} ${c.locality} ${c.matter}`
        .toLocaleLowerCase()
        .includes(search.toLocaleLowerCase()),
  );
  return (
    <>
      <div className="view-toolbar">
        <SearchField
          value={search}
          onChange={setSearch}
          placeholder="Buscar expedientes…"
        />
        <select
          aria-label="Filtrar expedientes por estado"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          {["Todos", "En preparación", "En revisión", "Completado"].map((x) => (
            <option key={x}>{x}</option>
          ))}
        </select>
      </div>
      {cases.length ? (
        <div className="case-cards">
          {cases.map((c, i) => (
            <article className="event-card" key={c.id}>
              <div className="section-heading">
                <span className={`case-icon tone-${i % 3}`}>
                  <FolderOpen size={23} />
                </span>
                <span
                  className={`status ${c.status === "En revisión" ? "amber" : c.status === "Completado" ? "green" : "blue"}`}
                >
                  {c.status}
                </span>
              </div>
              <h2>{c.name}</h2>
              <div className="event-meta">
                <span>
                  <MapPin size={15} />
                  {c.locality}, {c.region}
                </span>
                <span>
                  <CalendarDays size={15} />
                  {dateLabel(c.date, true)}
                </span>
              </div>
              <p className="event-context">
                {c.context ||
                  "Añade el contexto de tu evento para preparar tus consultas."}
              </p>
              <div className="event-counts">
                <FileText size={14} />
                {data.documents.filter((d) => d.case_id === c.id).length}{" "}
                documentos<span>·</span>
                {data.drafts.filter((d) => d.case_id === c.id).length}{" "}
                borradores
              </div>
              <div className="event-actions">
                <button className="button secondary" onClick={() => onEdit(c)}>
                  Ver expediente
                </button>
                <button className="button primary" onClick={() => onAsk(c)}>
                  Consultar
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title={
            search ? "Sin coincidencias" : "Tu próximo evento empieza aquí"
          }
          description={
            search
              ? "Prueba con otro nombre o localidad."
              : "Crea un expediente para mantener juntos su contexto, documentos y consultas."
          }
          action={
            <button className="button primary" onClick={onCreate}>
              <Plus size={17} /> Crear expediente
            </button>
          }
        />
      )}
    </>
  );
}

export function DocumentsView({
  data,
  onSave,
  onDelete,
  notify,
  caseFilter,
  setCaseFilter,
}: {
  data: Workspace;
  onSave: (d: PrivateDocument) => Promise<void>;
  onDelete: (d: PrivateDocument) => void;
  notify: (s: string) => void;
  caseFilter: string;
  setCaseFilter: (s: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [opened, setOpened] = useState<PrivateDocument | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploadCase, setUploadCase] = useState(
    caseFilter || data.cases[0]?.id || "",
  );
  const input = useRef<HTMLInputElement>(null);
  const documents = data.documents.filter(
    (d) =>
      (!caseFilter || d.case_id === caseFilter) &&
      d.name.toLowerCase().includes(search.toLowerCase()),
  );
  async function upload(file?: File) {
    if (!file) return;
    if (!uploadCase) {
      notify("Selecciona un expediente para el documento.");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".txt")) {
      notify(
        "Esta primera versión admite TXT. PDF y DOCX están pendientes de integrar con extracción segura.",
      );
      return;
    }
    if (file.size > 1024 * 1024) {
      notify("El archivo supera el límite de 1 MB.");
      return;
    }
    setBusy(true);
    try {
      const text = new TextDecoder("utf-8", { fatal: true }).decode(
        await file.arrayBuffer(),
      );
      if (!text.trim() || /[\x00-\x08\x0E-\x1F]/.test(text))
        throw new Error("Se necesita un archivo de texto UTF-8 legible.");
      await onSave({
        id: id(),
        name: file.name,
        case_id: uploadCase,
        size: file.size,
        text,
        created_at: new Date().toISOString(),
      });
      notify("Documento incorporado al expediente.");
    } catch (e) {
      notify(
        e instanceof TypeError
          ? "No se pudo leer el archivo. Guarda una copia TXT con codificación UTF-8."
          : (e as Error).message,
      );
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }
  return (
    <>
      <div
        className="upload-panel"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (!busy) void upload(e.dataTransfer.files[0]);
        }}
      >
        <span className="upload-icon">
          <Upload size={25} />
        </span>
        <div>
          <h2>Los documentos de tu evento, en orden.</h2>
          <p>Arrastra un archivo de texto o selecciónalo desde tu equipo.</p>
          <span className="muted small">
            TXT UTF-8 · Hasta 1 MB · PDF, DOCX y OCR pendientes
          </span>
        </div>
        <div className="upload-controls">
          <select
            aria-label="Expediente para el documento"
            value={uploadCase}
            onChange={(e) => setUploadCase(e.target.value)}
          >
            <option value="">Selecciona expediente</option>
            {data.cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <button
            className="button primary"
            disabled={busy || !uploadCase}
            onClick={() => input.current?.click()}
          >
            <Plus size={16} />
            {busy ? "Leyendo…" : "Subir documento"}
          </button>
        </div>
        <input
          ref={input}
          type="file"
          accept=".txt,text/plain"
          className="visually-hidden"
          aria-label="Seleccionar archivo TXT"
          onChange={(e) => void upload(e.target.files?.[0])}
        />
      </div>
      <div className="view-toolbar">
        <SearchField
          value={search}
          onChange={setSearch}
          placeholder="Buscar documentos…"
        />
        <select
          aria-label="Filtrar documentos por expediente"
          value={caseFilter}
          onChange={(e) => setCaseFilter(e.target.value)}
        >
          <option value="">Todos los expedientes</option>
          {data.cases.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>
      {documents.length ? (
        <div className="document-list">
          {documents.map((d) => (
            <div className="document-row" key={d.id}>
              <span className="document-icon">
                <FileText size={23} />
              </span>
              <button
                className="document-title"
                onClick={() => {
                  setOpened(d);
                  setAnalyzing(false);
                }}
              >
                <strong>{d.name}</strong>
                <span>
                  {data.cases.find((c) => c.id === d.case_id)?.name} ·{" "}
                  {Math.max(1, Math.ceil(d.size / 1024))} KB
                </span>
              </button>
              <span className="status green">Texto disponible</span>
              <button
                className="button secondary"
                onClick={() => {
                  setOpened(d);
                  setAnalyzing(true);
                }}
              >
                Revisar
              </button>
              <button
                className="icon-button danger"
                aria-label={`Eliminar ${d.name}`}
                onClick={() => onDelete(d)}
              >
                <Trash2 size={17} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <Empty
          title="Tus documentos aparecerán aquí"
          description="Selecciona un expediente y agrega un archivo TXT para consultar sus fragmentos."
        />
      )}
      <Notice>
        Los documentos privados no son fuentes jurídicas. La revisión inicial
        identifica palabras y fragmentos; no evalúa la validez legal del
        contenido.
      </Notice>
      {opened && (
        <Modal title={opened.name} onClose={() => setOpened(null)} wide>
          <div className="document-tabs">
            <button
              className={!analyzing ? "selected" : ""}
              onClick={() => setAnalyzing(false)}
            >
              Texto del documento
            </button>
            <button
              className={analyzing ? "selected" : ""}
              onClick={() => setAnalyzing(true)}
            >
              Revisión de fragmentos
            </button>
          </div>
          {analyzing ? (
            <>
              <p className="form-intro">
                Búsqueda por palabras clave. Los resultados son pasajes
                literales que necesitan revisión, no conclusiones de IA.
              </p>
              <div className="findings">
                {analyzeDocument(opened).map((c) => (
                  <section key={c.title}>
                    <h3>{c.title}</h3>
                    {c.matches.length ? (
                      c.matches.map((m) => (
                        <blockquote key={m.locator}>
                          <span>{m.locator} · Documento privado</span>
                          {m.text}
                        </blockquote>
                      ))
                    ) : (
                      <p className="muted small">
                        No detectado por esta búsqueda. No significa que no
                        exista.
                      </p>
                    )}
                  </section>
                ))}
              </div>
            </>
          ) : (
            <pre className="document-text">{opened.text}</pre>
          )}
          <div className="modal-actions">
            <button
              className="button secondary"
              onClick={() => downloadText(opened.name, opened.text)}
            >
              <Download size={16} /> Descargar texto
            </button>
            <button className="button primary" onClick={() => setOpened(null)}>
              Cerrar
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}

export function DraftsView({
  data,
  onSave,
  onGenerate,
  onDelete,
  notify,
  onHistory,
  health,
}: {
  data: Workspace;
  onSave: (d: Draft) => Promise<Draft>;
  onGenerate: (d: DraftInput) => Promise<Draft>;
  onDelete: (d: Draft) => void;
  notify: (s: string) => void;
  onHistory: (id: string) => Promise<Draft[]>;
  health: ServiceHealth | null;
}) {
  const [create, setCreate] = useState(false);
  const [opened, setOpened] = useState<Draft | null>(null);
  const [caseId, setCaseId] = useState(data.cases[0]?.id || "");
  const [kind, setKind] = useState("Uso de recinto");
  const [parties, setParties] = useState("");
  const [terms, setTerms] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"ai" | "template">("template");
  const [versions, setVersions] = useState<Draft[] | null>(null);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [preview, setPreview] = useState<Draft | null>(null);
  useEffect(() => {
    if (!data.cases.some((c) => c.id === caseId)) setCaseId(data.cases[0]?.id ?? "");
  }, [data.cases, caseId]);
  async function showHistory() {
    if (!opened) return;
    setHistoryBusy(true); setError("");
    try { setVersions(await onHistory(opened.id)); }
    catch (e) { setError((e as Error).message); }
    finally { setHistoryBusy(false); }
  }
  async function generate() {
    if (busy || !caseId) return;
    setBusy(true);
    setError("");
    try {
      const draft = await onGenerate({ case_id: caseId, kind, parties, terms, mode });
      setCreate(false);
      setOpened(draft);
      setVersions(null); setPreview(null);
      notify(draft.generation ? "Borrador generado por IA y guardado." : "Ficha editable creada.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function save(value: Draft) {
    setBusy(true);
    setError("");
    try {
      await onSave(value);
      setOpened(null);
      setCreate(false);
      notify("Versión guardada.");
    } catch (e) {
      setError((e as Error).message);
      notify((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="view-toolbar">
        <p className="muted">
          Fichas editables con historial de versiones para tu revisión.
        </p>
        <button
          className="button primary"
          disabled={!data.cases.length}
          onClick={() => { setError(""); setCreate(true); }}
        >
          <Plus size={17} /> Nuevo borrador
        </button>
      </div>
      {data.drafts.length ? (
        <div className="case-cards">
          {data.drafts.map((d) => (
            <article className="event-card draft-card" key={d.id}>
              <div className="section-heading">
                <span className="case-icon">
                  <FilePenLine size={22} />
                </span>
                <span className="status amber">Preliminar · v{d.version}</span>
              </div>
              <h2>{d.title}</h2>
              <p className="muted small">
                {data.cases.find((c) => c.id === d.case_id)?.name}
              </p>
              <p className="draft-excerpt">{d.text.slice(0, 180)}…</p>
              {d.generation && <p className="small muted">IA · {d.generation.model}</p>}
              <div className="event-actions">
                <button
                  className="button primary"
                  onClick={() => { setError(""); setVersions(null); setPreview(null); setOpened({ ...d }); }}
                >
                  Abrir editor
                </button>
                <button
                  className="icon-button danger"
                  aria-label={`Eliminar ${d.title}`}
                  onClick={() => onDelete(d)}
                >
                  <Trash2 size={17} />
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title="De una idea a un primer borrador"
          description={
            data.cases.length
              ? "Organiza las partes, el servicio y las condiciones antes de redactar un acuerdo con un profesional."
              : "Primero crea un expediente con el contexto de tu evento."
          }
          action={
            data.cases.length ? (
              <button
                className="button primary"
                onClick={() => { setError(""); setCreate(true); }}
              >
                <FilePenLine size={17} /> Preparar borrador
              </button>
            ) : undefined
          }
        />
      )}
      <Notice />
      {create && (
        <Modal
          title="Preparar un borrador"
          onClose={() => { if (!busy) setCreate(false); }}
          wide
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void generate();
            }}
          >
            <p className="form-intro">
              {API_MODE && mode === "ai"
                ? "La IA redactará un borrador usando el contexto de tu expediente, las partes y las condiciones indicadas. Revísalo antes de utilizarlo."
                : "Se creará una ficha a partir de tus datos. Los campos no resueltos quedarán marcados como pendientes."}
            </p>
            <fieldset className="generation-fields" disabled={busy}>
            <div className="form-grid">
              {API_MODE && <label className="field full">
                Método de preparación
                <select value={mode} onChange={(e) => setMode(e.target.value as "ai" | "template")}>
                  <option value="template">Plantilla editable · sin IA</option>
                  <option value="ai" disabled={!health?.generation_enabled}>Redactar con IA local{!health?.generation_enabled ? " · no disponible" : ""}</option>
                </select>
              </label>}
              <label className="field">
                Expediente
                <select
                  required
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                >
                  {data.cases.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Tipo de acuerdo
                <select value={kind} onChange={(e) => setKind(e.target.value)}>
                  {[
                    "Uso de recinto",
                    "Servicio de catering",
                    "Participación de artista",
                    "Equipo y producción",
                    "Otro acuerdo",
                  ].map((k) => (
                    <option key={k}>{k}</option>
                  ))}
                </select>
              </label>
              <label className="field full">
                Partes involucradas
                <input
                  maxLength={1000}
                  value={parties}
                  onChange={(e) => setParties(e.target.value)}
                  placeholder="Organizador y proveedor"
                />
              </label>
              <label className="field full">
                Condiciones conocidas
                <textarea
                  rows={4}
                  maxLength={10000}
                  value={terms}
                  onChange={(e) => setTerms(e.target.value)}
                  placeholder="Describe el servicio, fechas, importes y lo que ya han acordado."
                />
              </label>
            </div>
            </fieldset>
            {busy && API_MODE && mode === "ai" && (
              <p className="generation-progress" role="status">La IA está redactando el borrador. Esto puede tardar unos minutos.</p>
            )}
            {error && <p className="form-error" role="alert">{error}</p>}
            <Notice />
            <div className="modal-actions">
              <button
                type="button"
                className="button secondary"
                disabled={busy}
                onClick={() => setCreate(false)}
              >
                Cancelar
              </button>
              <button className="button primary" disabled={busy}>
                {busy && <LoaderCircle size={16} className="is-spinning" />}
                {busy ? "Preparando…" : API_MODE && mode === "ai" ? "Generar borrador con IA" : "Crear ficha editable"}
              </button>
            </div>
          </form>
        </Modal>
      )}
      {opened && (
        <Modal title={opened.title} onClose={() => { if (!busy) setOpened(null); }} wide>
          <div className="editor-meta">
            <span className="status amber">BORRADOR PRELIMINAR</span>
            <span>
              Versión {opened.version} ·{" "}
              {opened.text !== opened.original_text
                ? "Contiene ediciones del usuario"
                : opened.generation ? `Generado con ${opened.generation.model}` : "Plantilla inicial"}
            </span>
          </div>
          <div className="version-toolbar">
            <button className="text-button" disabled={busy || historyBusy} onClick={() => versions ? setVersions(null) : void showHistory()}>
              <History size={16} /> {historyBusy ? "Cargando versiones…" : versions ? "Ocultar historial" : "Historial de versiones"}
            </button>
            <span className="small muted">Cada guardado conserva la versión anterior.</span>
          </div>
          {versions && <div className="version-panel">
            <div className="version-list" aria-label="Versiones guardadas">
              {versions.map((v) => <button key={v.version} className={preview?.version === v.version ? "selected" : ""} onClick={() => setPreview(v)}>
                Versión {v.version}<span>{dateLabel(v.updated_at, true)}{v.version === opened.version ? " · Actual" : ""}</span>
              </button>)}
            </div>
            {preview && <div className="version-preview">
              <h3>Contenido de la versión {preview.version}</h3>
              <pre>{preview.text}</pre>
              <button className="button secondary" disabled={busy} onClick={() => { setOpened({ ...opened, text: preview.text }); setPreview(null); setVersions(null); notify("Versión cargada en el editor. Guarda para crear una nueva revisión."); }}>
                <RotateCcw size={15} /> Usar este contenido
              </button>
            </div>}
          </div>}
          <Notice>
            Las ediciones manuales no tienen respaldo jurídico automático.
            Conserva los campos pendientes para la revisión profesional.
          </Notice>
          <label className="field">
            <span>Contenido editable</span>
            <textarea
              className="draft-editor"
              value={opened.text}
              maxLength={100000}
              disabled={busy}
              onChange={(e) => setOpened({ ...opened, text: e.target.value })}
            />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="modal-actions">
            <button
              className="button secondary"
              onClick={() =>
                downloadText(
                  `${opened.title}.txt`,
                  `${opened.text}${opened.generation ? `\n\nModelo: ${opened.generation.model} (${opened.generation.provider}). Generado: ${opened.generation.generated_at}.` : ""}\n\n${DISCLAIMER}`,
                )
              }
            >
              <Download size={16} /> Exportar TXT
            </button>
            <button
              className="button primary"
              disabled={busy || !opened.text.trim()}
              onClick={() =>
                void save({
                  ...opened,
                  version: opened.version + 1,
                  updated_at: new Date().toISOString(),
                })
              }
            >
              <Check size={16} /> Guardar versión
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}

export function SourcesView() {
  return (
    <>
      <section className="sources-intro">
        <span className="large-icon">
          <LibraryIcon />
        </span>
        <div className="eyebrow">EVIDENCIA ANTES QUE CONCLUSIONES</div>
        <h2>
          Una respuesta necesita
          <br />
          fuentes que puedas comprobar.
        </h2>
        <p>
          {API_MODE
            ? "La IA local puede ayudarte a revisar documentos y preparar borradores. El corpus jurídico aún no está conectado: las obligaciones y la vigencia de las normas requieren verificación profesional."
            : "Esta demostración organiza documentos y muestra fragmentos. La versión local permite conectar un modelo de IA; el corpus jurídico sigue pendiente de validación."}
        </p>
        <span className="status amber">Corpus pendiente de validación</span>
      </section>
      <div className="info-grid">
        <article>
          <ShieldCheck size={23} />
          <h3>Fuentes jurídicas verificadas</h3>
          <p>
            Deberán incluir jurisdicción, versión, vigencia y el pasaje que
            respalda cada respuesta.
          </p>
          <span className="small muted">0 fuentes activas</span>
        </article>
        <article>
          <FileText size={23} />
          <h3>Documentos privados</h3>
          <p>
            Tus contratos aportan contexto. Sus cláusulas no se convierten en
            leyes al incorporarlas al expediente.
          </p>
          <span className="small muted">
            Referencias identificadas por separado
          </span>
        </article>
        <article>
          <Search size={23} />
          <h3>Límites visibles</h3>
          <p>
            Cuando no hay evidencia suficiente, juridIA lo indica. Una búsqueda
            sin resultados no confirma que no exista una obligación.
          </p>
          <span className="small muted">Revisión profesional requerida</span>
        </article>
      </div>
      <Notice />
    </>
  );
}
function LibraryIcon() {
  return <BookOpen size={32} />;
}

export function SettingsView({
  demo,
  onReset,
  onLogout,
  health,
  healthError,
  healthLoading,
  onRefreshHealth,
  onExport,
}: {
  demo: boolean;
  onReset: () => void;
  onLogout: () => void;
  health: ServiceHealth | null;
  healthError: string;
  healthLoading: boolean;
  onRefreshHealth: () => Promise<void>;
  onExport: () => Promise<void>;
}) {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  return (
    <div className="settings-content">
      <section className="settings-section">
        <h2>Tu espacio y tus datos</h2>
        <p>
          {demo
            ? "Estás en una demostración. Los datos y archivos que añadas permanecen en la memoria de esta pestaña y se descartan al recargar; puedes exportarlos antes. No se envían a un modelo de IA."
            : "Tus datos se guardan en la base de datos local y se vinculan a tu cuenta. Puedes buscar fragmentos y preparar plantillas sin IA, o elegir el modelo local cuando esté disponible."}
        </p>
        <div className="settings-row">
          <div>
            <h3>Exportar mi información</h3>
            <p>
              Descarga expedientes, documentos, consultas e historial de borradores en JSON.
            </p>
          </div>
          <button
            className="button secondary"
            disabled={exporting}
            onClick={async () => {
              setExporting(true); setExportError("");
              try { await onExport(); } catch (e) { setExportError((e as Error).message); }
              finally { setExporting(false); }
            }}
          >
            <Download size={16} /> {exporting ? "Exportando…" : "Exportar datos"}
          </button>
        </div>
        {exportError && <p className="form-error" role="alert">{exportError}</p>}
        {demo ? (
          <div className="settings-row">
            <div>
              <h3>Limpiar demostración</h3>
              <p>
                Elimina todos los datos de esta pestaña y comienza un espacio
                vacío.
              </p>
            </div>
            <button className="button secondary danger" onClick={onReset}>
              <Trash2 size={16} /> Limpiar espacio
            </button>
          </div>
        ) : (
          <div className="settings-row">
            <div>
              <h3>Sesión actual</h3>
              <p>Cierra el acceso desde este navegador.</p>
            </div>
            <button className="button secondary" onClick={onLogout}>
              Cerrar sesión
            </button>
          </div>
        )}
      </section>
      {!demo && <ServiceStatus health={health} error={healthError} loading={healthLoading} onRefresh={onRefreshHealth} />}
      <section className="settings-section">
        <h2>Estado de esta primera versión</h2>
        <div className="capability-list">
          <span>
            <Check size={17} /> Expedientes, documentos TXT y borradores con historial
          </span>
          <span>
            <Check size={17} /> Consulta de fragmentos y contexto visible
          </span>
          <span>
            {demo || !health?.ai.available ? <X size={17} /> : <Check size={17} />}
            {demo ? "Demostración sin generación de IA" : `IA local con Ollama: ${health?.ai.available ? health.ai.model : "pendiente de conexión"}`}
          </span>
          <span>
            <X size={17} /> Corpus jurídico verificado: pendiente
          </span>
          <span>
            <X size={17} /> PDF, DOCX y OCR: pendientes
          </span>
          <span>
            <X size={17} /> MFA, recuperación de cuenta y administración:
            pendientes
          </span>
        </div>
        <p className="muted small">
          La base de desarrollo no está habilitada para operación con
          información confidencial en producción. El diseño completo sigue en
          los documentos del proyecto.
        </p>
      </section>
      <Notice />
    </div>
  );
}

export { ContextChips };
