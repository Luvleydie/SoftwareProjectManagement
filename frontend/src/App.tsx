import {
  Scale,
  MessagesSquare,
  FolderOpen,
  Files,
  FilePenLine,
  LibraryBig,
  Settings2,
  Plus,
  ShieldCheck,
  X,
} from "lucide-react";
import { API_MODE } from "./api";
import { useWorkspace } from "./useWorkspace";
import CaseForm from "./CaseForm";
import ConsultationView from "./ConsultationView";
import AuthView from "./AuthView";
import {
  CasesView,
  DocumentsView,
  DraftsView,
  SettingsView,
  SourcesView,
} from "./WorkspaceViews";
import { Modal } from "./components";
import ServiceStatus from "./ServiceStatus";

const navigation = [
  { id: "consultas", label: "Chat", icon: MessagesSquare },
  { id: "expedientes", label: "Expedientes", icon: FolderOpen },
  { id: "documentos", label: "Documentos", icon: Files },
  { id: "borradores", label: "Borradores", icon: FilePenLine },
  { id: "fuentes", label: "Fuentes jurídicas", icon: LibraryBig },
] as const;

export default function App() {
  const w = useWorkspace();
  const {
    view,
    data,
    navigate,
  } = w;
  const initials = w.user?.name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "J";
  if (w.loading)
    return (
      <div className="loading-screen">
        <Scale size={35} />
        <h1>juridIA</h1>
        <p>Preparando tu espacio…</p>
      </div>
    );
  if (API_MODE && !w.user)
    return <AuthView onAuthenticated={(u) => void w.authenticated(u)} health={w.health} healthError={w.healthError} healthLoading={w.healthLoading} onRefreshHealth={w.refreshHealth} />;
  if (w.loadError)
    return (
      <div className="loading-screen">
        <h1>No se pudo abrir tu espacio</h1>
        <p role="alert">{w.loadError}</p>
        <button
          className="button primary"
          onClick={() => w.user && void w.authenticated(w.user)}
        >
          Reintentar
        </button>
      </div>
    );
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Saltar al contenido
      </a>
      <aside className="sidebar">
        <a className="brand" href="#inicio" onClick={() => navigate("inicio")}>
          <span className="brand-mark">
            <Scale size={25} />
          </span>
          <span>
            juridIA
          </span>
        </a>
        <nav aria-label="Navegación principal">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              aria-label={label}
              onClick={() => navigate(id)}
              className={`nav-item ${(view === id || (id === "consultas" && view === "inicio")) ? "active" : ""}`}
              aria-current={(view === id || (id === "consultas" && view === "inicio")) ? "page" : undefined}
            >
              <Icon size={19} />
              {label}
              {id === "expedientes" && (
                <span className="nav-count">{data.cases.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <button
            className={`nav-item ${view === "ajustes" ? "active" : ""}`}
            onClick={() => navigate("ajustes")}
          >
            <Settings2 size={19} /> Configuración
          </button>
          <div className="profile">
            <span className="avatar">{initials}</span>
            <div>
              <strong>
                {API_MODE ? w.user?.name : "Espacio de demostración"}
              </strong>
              <span>{API_MODE ? "Mi cuenta" : "Versión inicial"}</span>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <main id="main-content">
          <div className="page-heading">
            <div>
              <h1>
                {view === "inicio"
                  ? "Chat"
                  : (navigation.find((n) => n.id === view)?.label ??
                    "Configuración")}
              </h1>
            </div>
            {view === "expedientes" && <button className="button primary" onClick={w.createCase}>
              <Plus size={17} /> Nuevo expediente
            </button>}
          </div>
          {API_MODE && view !== "ajustes" && (w.healthError || (w.health && !w.health.database.connected)) && (
            <ServiceStatus health={w.health} error={w.healthError} loading={w.healthLoading} onRefresh={w.refreshHealth} />
          )}
          {view === "expedientes" && (
            <CasesView
              data={data}
              search={w.search}
              setSearch={w.setSearch}
              onCreate={w.createCase}
              onEdit={w.setCaseForm}
              onAsk={w.askAbout}
            />
          )}
          {view === "documentos" && (
            <DocumentsView
              data={data}
              onSave={w.saveDocument}
              onDelete={w.deleteDocument}
              notify={w.notify}
              caseFilter={w.caseFilter}
              setCaseFilter={w.setCaseFilter}
            />
          )}
          {view === "borradores" && (
            <DraftsView
              data={data}
              onSave={w.saveDraft}
              onGenerate={w.generateDraft}
              onDelete={w.deleteDraft}
              notify={w.notify}
              onHistory={w.getDraftVersions}
              health={w.health}
            />
          )}
          {(view === "consultas" || view === "inicio") && (
            <ConsultationView
              data={data}
              selectedCase={w.chatCase}
              setSelectedCase={w.setChatCase}
              question={w.question}
              setQuestion={w.setQuestion}
              onSubmit={w.submitQuery}
              onCreateCase={w.createCase}
              notify={w.notify}
              health={w.health}
            />
          )}
          {view === "fuentes" && <SourcesView />}
          {view === "ajustes" && (
            <SettingsView
              onExport={w.exportWorkspace}
              demo={!API_MODE}
              onReset={w.reset}
              onLogout={w.logout}
              health={w.health}
              healthError={w.healthError}
              healthLoading={w.healthLoading}
              onRefreshHealth={w.refreshHealth}
            />
          )}
          <footer className="page-footer">
            <span>
              <Scale size={14} /> juridIA · Apoyo jurídico para eventos
            </span>
            <span>Las respuestas requieren revisión profesional.</span>
          </footer>
        </main>
      </div>
      {w.caseForm && (
        <CaseForm
          initial={w.caseForm}
          onSave={w.saveCase}
          onClose={() => w.setCaseForm(null)}
          onDelete={
            data.cases.some((c) => c.id === w.caseForm!.id)
              ? () => w.deleteCase(w.caseForm!)
              : undefined
          }
        />
      )}
      {w.confirm && (
        <Modal
          title={w.confirm.title}
          onClose={() => {
            if (!w.confirmBusy) w.setConfirm(null);
          }}
        >
          <p className="confirm-description">{w.confirm.description}</p>
          <div className="modal-actions">
            <button
              className="button secondary"
              disabled={w.confirmBusy}
              onClick={() => w.setConfirm(null)}
            >
              Cancelar
            </button>
            <button
              className="button destructive"
              disabled={w.confirmBusy}
              onClick={async () => {
                w.setConfirmBusy(true);
                try {
                  await w.confirm!.action();
                  w.setConfirm(null);
                } catch (e) {
                  w.notify((e as Error).message);
                } finally {
                  w.setConfirmBusy(false);
                }
              }}
            >
              {w.confirmBusy ? "Eliminando…" : "Confirmar eliminación"}
            </button>
          </div>
        </Modal>
      )}
      {w.toast && (
        <div className="toast" role="status">
          <ShieldCheck size={18} />
          <span>{w.toast}</span>
          <button
            className="icon-button"
            aria-label="Cerrar aviso"
            onClick={() => w.setToast("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
