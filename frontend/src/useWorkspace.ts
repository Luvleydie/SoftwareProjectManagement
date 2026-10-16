import { useCallback, useEffect, useRef, useState } from "react";
import type {
  Case,
  Consultation,
  Document,
  Draft,
  DraftInput,
  ServiceHealth,
  User,
  View,
  Workspace,
} from "./types";
import {
  blankCase,
  demoWorkspace,
  emptyWorkspace,
  draftText,
  id,
  downloadText,
  DISCLAIMER,
} from "./domain";
import { api, API_MODE, ApiError } from "./api";
import { useWebMcp } from "./useWebMcp";

const views: View[] = ["inicio", "consultas", "expedientes", "documentos", "borradores", "fuentes", "ajustes"];
const hashView = (): View => views.find((v) => window.location.hash === `#${v}`) ?? "inicio";

export function useWorkspace() {
  const [view, setView] = useState<View>(hashView);
  const demoVersions = useRef<Record<string, Draft[]>>({});
  const [mobileMenu, setMobileMenu] = useState(false);
  const [data, setData] = useState<Workspace>(() =>
    API_MODE ? emptyWorkspace() : demoWorkspace(),
  );
  const [user, setUser] = useState<User | null>(
    API_MODE ? null : { name: "Demostración", email: "" },
  );
  const [loading, setLoading] = useState(API_MODE);
  const [loadError, setLoadError] = useState("");
  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [healthError, setHealthError] = useState("");
  const [healthLoading, setHealthLoading] = useState(API_MODE);
  const refreshHealth = useCallback(async () => {
    if (!API_MODE) return;
    setHealthLoading(true);
    try {
      setHealth(await api.health());
      setHealthError("");
    } catch {
      setHealth(null);
      setHealthError("No se pudo comprobar la conexión con el servidor local.");
    } finally {
      setHealthLoading(false);
    }
  }, []);
  const [chatCase, setChatCase] = useState("");
  const [question, setQuestion] = useState("");
  const [selectedCase, setSelectedCase] = useState(API_MODE ? "" : "demo-1");
  const [caseForm, setCaseForm] = useState<Case | null>(null);
  const [search, setSearch] = useState("");
  const [caseFilter, setCaseFilter] = useState("");
  const [toast, setToast] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const [confirm, setConfirm] = useState<{
    title: string;
    description: string;
    action: () => Promise<void>;
  } | null>(null);
  const [confirmBusy, setConfirmBusy] = useState(false);
  const notify = (message: string) => {
    clearTimeout(timer.current);
    setToast(message);
    timer.current = setTimeout(() => setToast(""), 6500);
  };
  const navigate = (next: View) => {
    if (window.location.hash !== `#${next}`) window.location.hash = next;
    setView(next);
    setMobileMenu(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  };
  useWebMcp(data.cases, (caseId, text) => {
    setSelectedCase(caseId);
    setQuestion(text);
    navigate("consultas");
  });
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => {
    const onHash = () => { setView(hashView()); setMobileMenu(false); };
    const onExpired = () => {
      setUser(null); setData(emptyWorkspace()); setCaseForm(null); setConfirm(null);
      setQuestion(""); setLoadError("");
    };
    window.addEventListener("hashchange", onHash);
    window.addEventListener("juridia:session-expired", onExpired);
    return () => {
      window.removeEventListener("hashchange", onHash);
      window.removeEventListener("juridia:session-expired", onExpired);
    };
  }, []);
  useEffect(() => { document.title = `${({ inicio: "Chat", consultas: "Chat", expedientes: "Expedientes", documentos: "Documentos", borradores: "Borradores", fuentes: "Fuentes jurídicas", ajustes: "Configuración" })[view]} · juridIA`; }, [view]);
  useEffect(() => {
    if (!API_MODE) return;
    void refreshHealth();
    const interval = setInterval(() => void refreshHealth(), 30000);
    return () => clearInterval(interval);
  }, [refreshHealth]);
  useEffect(() => {
    if (!API_MODE) return;
    let cancelled = false;
    void api
      .me()
      .then(async (u) => {
        if (!cancelled) setUser(u);
        const next = await api.workspace();
        if (!cancelled) {
          setUser(u);
          setData(next);
          setSelectedCase(next.cases[0]?.id ?? "");
        }
      })
      .catch((error: Error) => {
        if (!cancelled && !(error instanceof ApiError && error.status === 401)) setLoadError(error.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    if (!data.cases.some((c) => c.id === selectedCase))
      setSelectedCase(data.cases[0]?.id ?? "");
  }, [data.cases, selectedCase]);
  useEffect(() => {
    if (caseFilter && !data.cases.some((c) => c.id === caseFilter))
      setCaseFilter("");
  }, [data.cases, caseFilter]);
  async function authenticated(u: User) {
    setUser(u);
    setLoading(true);
    setLoadError("");
    try {
      const next = await api.workspace();
      setData(next);
      setSelectedCase(next.cases[0]?.id ?? "");
    } catch (e) {
      setLoadError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  async function saveCase(value: Case) {
    const saved = API_MODE ? await api.saveCase(value) : value;
    setData((p) => ({
      ...p,
      cases: p.cases.some((c) => c.id === saved.id)
        ? p.cases.map((c) => (c.id === saved.id ? saved : c))
        : [saved, ...p.cases],
    }));
    setSelectedCase(saved.id);
    notify(
      API_MODE
        ? "Expediente guardado."
        : "Expediente añadido a esta demostración.",
    );
  }
  async function exportWorkspace() {
    const exported = API_MODE ? await api.exportWorkspace() : { ...data, draft_versions: Object.values(demoVersions.current).flat().filter((d) => data.drafts.some((current) => current.id === d.id)) };
    downloadText("juridia-mis-datos.json", JSON.stringify({ ...exported, disclaimer: DISCLAIMER }, null, 2), "application/json");
  }
  async function saveDocument(value: Document) {
    const saved = API_MODE ? await api.saveDocument(value) : value;
    setData((p) => ({ ...p, documents: [saved, ...p.documents] }));
  }
  async function saveDraft(value: Draft) {
    const saved = API_MODE ? await api.saveDraft(value) : value;
    rememberDraft(saved);
    return saved;
  }
  function rememberDraft(saved: Draft) {
    if (!API_MODE) demoVersions.current[saved.id] = [saved, ...(demoVersions.current[saved.id] ?? [])];
    setData((p) => ({
      ...p,
      drafts: p.drafts.some((d) => d.id === saved.id)
        ? p.drafts.map((d) => (d.id === saved.id ? saved : d))
        : [saved, ...p.drafts],
    }));
  }
  async function generateDraft(value: DraftInput): Promise<Draft> {
    const context = data.cases.find((c) => c.id === value.case_id);
    if (!context) throw new Error("Selecciona un expediente.");
    let saved: Draft;
    if (API_MODE) {
      // The generation endpoint persists the first version atomically.
      saved = await api.generateDraft(value);
    } else {
      const text = draftText(value.kind, context, value.parties, value.terms);
      saved = {
        id: id(),
        case_id: value.case_id,
        title: `${value.kind} · ${context.name}`,
        kind: value.kind,
        text,
        original_text: text,
        version: 1,
        updated_at: new Date().toISOString(),
      };
    }
    rememberDraft(saved);
    return saved;
  }
  async function submitQuery(
    text: string,
    caseId: string,
    docs: string[],
    mode: "ai" | "document",
    conversationId?: string,
  ): Promise<Consultation> {
    if (!API_MODE) throw new Error("El chat necesita el servidor y el modelo de IA local. Inicia la aplicación con cuentas.");
    const result = await api.consult(caseId, text, docs, mode, conversationId);
    setData((p) => ({ ...p, consultations: [result, ...p.consultations] }));
    return result;
  }
  function deleteCase(value: Case) {
    setConfirm({
      title: "Eliminar expediente",
      description: `Se eliminará “${value.name}” junto con sus documentos, consultas y borradores. Las copias descargadas previamente permanecen en tu equipo.`,
      action: async () => {
        if (API_MODE) await api.deleteCase(value.id);
        setData((p) => ({
          cases: p.cases.filter((c) => c.id !== value.id),
          documents: p.documents.filter((d) => d.case_id !== value.id),
          consultations: p.consultations.filter((c) => c.case_id !== value.id),
          drafts: p.drafts.filter((d) => d.case_id !== value.id),
        }));
        setCaseForm(null);
        notify("Expediente eliminado.");
      },
    });
  }
  function deleteDocument(value: Document) {
    setConfirm({
      title: "Eliminar documento",
      description: `Se eliminará “${value.name}” y las consultas que lo citaron. Sus pasajes dejarán de estar disponibles. Las copias que ya descargaste no se eliminan.`,
      action: async () => {
        if (API_MODE) await api.deleteDocument(value.id);
        setData((p) => ({
          ...p,
          documents: p.documents.filter((d) => d.id !== value.id),
          consultations: p.consultations.filter(
            (c) => !c.input_document_ids?.includes(value.id) && !c.citations.some((cite) => cite.document_id === value.id),
          ),
        }));
        notify("Documento y consultas dependientes eliminados.");
      },
    });
  }
  function deleteDraft(value: Draft) {
    setConfirm({
      title: "Eliminar borrador",
      description: `Se eliminará “${value.title}”. Esta acción no modifica las copias descargadas.`,
      action: async () => {
        if (API_MODE) await api.deleteDraft(value.id);
        setData((p) => ({
          ...p,
          drafts: p.drafts.filter((d) => d.id !== value.id),
        }));
        notify("Borrador eliminado.");
      },
    });
  }
  function askAbout(value: Case) {
    setChatCase(value.id);
    setSelectedCase(value.id);
    setQuestion("");
    navigate("consultas");
  }
  const createCase = () => setCaseForm(blankCase());
  const reset = () =>
    setConfirm({
      title: "Limpiar espacio de demostración",
      description:
        "Se eliminarán de esta pestaña todos los expedientes, documentos, consultas y borradores. Exporta tus datos antes si deseas conservarlos.",
      action: async () => {
        setData(emptyWorkspace());
        notify("Espacio limpio. Puedes crear tu primer expediente.");
      },
    });
  const logout = () =>
    void api
      .logout()
      .then(() => {
        setUser(null);
        setData(emptyWorkspace());
        setQuestion(""); setCaseForm(null); setConfirm(null); setLoadError("");
        navigate("inicio");
      })
      .catch((e) => notify((e as Error).message));
  return {
    view,
    chatCase,
    setChatCase,
    mobileMenu,
    setMobileMenu,
    data,
    user,
    loading,
    loadError,
    health,
    healthError,
    healthLoading,
    refreshHealth,
    authenticated,
    question,
    setQuestion,
    selectedCase,
    setSelectedCase,
    caseForm,
    setCaseForm,
    search,
    setSearch,
    caseFilter,
    setCaseFilter,
    toast,
    setToast,
    confirm,
    setConfirm,
    confirmBusy,
    setConfirmBusy,
    notify,
    navigate,
    saveCase,
    exportWorkspace,
    saveDocument,
    saveDraft,
    getDraftVersions: (draftId: string) => API_MODE ? api.draftVersions(draftId) : Promise.resolve(demoVersions.current[draftId] ?? []),
    generateDraft,
    submitQuery,
    deleteCase,
    deleteDocument,
    deleteDraft,
    askAbout,
    createCase,
    reset,
    logout,
  };
}
