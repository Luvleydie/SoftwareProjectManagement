import type {
  Case,
  Consultation,
  Document,
  Draft,
  DraftInput,
  ServiceHealth,
  User,
  Workspace,
} from "./types";

export const API_MODE = import.meta.env.VITE_DATA_MODE !== "demo";
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
let csrf = "";
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      ...options.headers,
    },
    });
  } catch {
    throw new ApiError("No se pudo conectar con juridIA. Comprueba que el servidor esté en ejecución y vuelve a intentar.", 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (response.status === 401 && !path.startsWith("/auth/")) {
      csrf = "";
      window.dispatchEvent(new Event("juridia:session-expired"));
    }
    throw new ApiError(
      typeof body?.detail === "string"
        ? body.detail
        : "No se pudo completar la operación. Revisa los datos e inténtalo de nuevo.", response.status,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
export const api = {
  health: () => request<ServiceHealth>("/health"),
  async me() {
    const result = await request<{ user: User; csrf: string }>("/auth/me");
    csrf = result.csrf;
    return result.user;
  },
  async authenticate(
    mode: "login" | "register",
    values: { name: string; email: string; password: string },
  ) {
    const result = await request<{ user: User; csrf: string }>(
      `/auth/${mode}`,
      { method: "POST", body: JSON.stringify(values) },
    );
    csrf = result.csrf;
    return result.user;
  },
  async logout() {
    await request("/auth/logout", { method: "POST" });
    csrf = "";
  },
  workspace: () => request<Workspace>("/workspace"),
  exportWorkspace: () => request<Workspace & { draft_versions: Draft[] }>("/workspace/export"),
  saveCase: (value: Case) =>
    request<Case>(`/cases/${value.id}`, {
      method: "PUT",
      body: JSON.stringify(value),
    }),
  deleteCase: (caseId: string) =>
    request<void>(`/cases/${caseId}`, { method: "DELETE" }),
  saveDocument: (value: Document) =>
    request<Document>("/documents", {
      method: "POST",
      body: JSON.stringify(value),
    }),
  deleteDocument: (docId: string) =>
    request<void>(`/documents/${docId}`, { method: "DELETE" }),
  consult: (caseId: string, question: string, documentIds: string[], mode: "ai" | "document", conversationId?: string) =>
    request<Consultation>("/consultations", {
      method: "POST",
      body: JSON.stringify({
        case_id: caseId || null,
        conversation_id: conversationId,
        question,
        document_ids: documentIds,
        mode,
      }),
    }),
  saveDraft: (value: Draft) =>
    request<Draft>(`/drafts/${value.id}`, {
      method: "PUT",
      body: JSON.stringify(value),
    }),
  generateDraft: (value: DraftInput) =>
    request<Draft>("/drafts/generate", {
      method: "POST",
      body: JSON.stringify(value),
    }),
  draftVersions: (draftId: string) => request<Draft[]>(`/drafts/${draftId}/versions`),
  deleteDraft: (draftId: string) =>
    request<void>(`/drafts/${draftId}`, { method: "DELETE" }),
};
