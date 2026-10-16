import { useEffect, useRef, useState } from "react";
import type { Consultation, ServiceHealth, Workspace } from "./types";
import { downloadText, id } from "./domain";
import { API_MODE } from "./api";

type Props = {
  data: Workspace;
  selectedCase: string;
  setSelectedCase: (value: string) => void;
  question: string;
  setQuestion: (value: string) => void;
  onSubmit: (question: string, caseId: string, docs: string[], mode: "ai" | "document", conversationId?: string) => Promise<Consultation>;
  onCreateCase: () => void;
  notify: (message: string) => void;
  health: ServiceHealth | null;
};

export default function ConsultationView({ data, selectedCase, setSelectedCase, question, setQuestion, onSubmit, health }: Props) {
  const [conversation, setConversation] = useState(() => selectedCase ? id() : data.consultations.find(c => c.generation)?.conversation_id || id());
  const [caseId, setCaseId] = useState(() => selectedCase || data.consultations.find(c => c.conversation_id === conversation)?.case_id || "");
  const [documents, setDocuments] = useState<string[]>(() => data.consultations.find(c => c.conversation_id === conversation)?.input_document_ids || []);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const messages = data.consultations.filter(c => (c.conversation_id || c.id) === conversation).sort((a, b) => a.created_at.localeCompare(b.created_at));
  const threads = Array.from(new Map([...data.consultations].reverse().map(c => [c.conversation_id || c.id, c])).entries()).reverse();
  useEffect(() => { setSelectedCase(""); }, [setSelectedCase]);
  useEffect(() => { end.current?.scrollIntoView({ block: "nearest" }); }, [messages.length, busy]);
  async function submit() {
    const text = question.trim();
    if (!text || busy || !API_MODE || !health?.generation_enabled) return;
    setBusy(true); setPending(text); setError(""); setQuestion("");
    try {
      await onSubmit(text, caseId, documents.filter(docId => data.documents.some(d => d.id === docId && d.case_id === caseId)), "ai", conversation);
    } catch (e) {
      setError((e as Error).message); setQuestion(text);
    } finally {
      setBusy(false); setPending(""); input.current?.focus();
    }
  }
  return <div className="chat-layout">
    <aside className="chat-history" aria-label="Conversaciones">
      <button className="button secondary" disabled={busy} onClick={() => { setConversation(id()); setCaseId(""); setDocuments([]); setQuestion(""); setError(""); input.current?.focus(); }}>Nuevo chat</button>
      <h2>Conversaciones</h2>
      {!threads.length && <p>Aquí se guardarán tus chats.</p>}
      {threads.map(([threadId, first]) => <button key={threadId} disabled={busy} className={conversation === threadId ? "selected" : ""} aria-current={conversation === threadId ? "true" : undefined} onClick={() => { setConversation(threadId); setCaseId(first.case_id); setDocuments(first.input_document_ids || []); setQuestion(""); setError(""); }}>{first.question}</button>)}
    </aside>
    <section className="chat-main" aria-label="Chat con juridIA">
      <div className="chat-status" role="status">{!API_MODE ? "El chat requiere la aplicación local con IA." : health?.generation_enabled ? "IA local conectada" : "IA no disponible. Comprueba la conexión en Configuración."}</div>
      <div className="chat-messages" role="log" aria-label="Mensajes del chat" aria-live="polite">
        {!messages.length && !busy && <div className="chat-welcome"><h2>¿En qué puedo ayudarte?</h2><p>Escribe tu pregunta. Puedes añadir un expediente o documentos si los necesitas.</p></div>}
        {messages.map(message => <div key={message.id} className="chat-turn">
          <article className="chat-message user"><strong>Tú</strong><p>{message.question}</p></article>
          <article className="chat-message assistant"><strong>{message.generation ? "juridIA" : "Búsqueda documental anterior · sin IA"}</strong><p>{message.answer}</p>
            <details><summary>Fuentes y detalles</summary>
              {message.generation && <p>Modelo: {message.generation.model}</p>}
              {message.citations.map((citation, i) => <blockquote key={i}><p>{citation.passage}</p><cite>{citation.title} · {citation.locator}</cite></blockquote>)}
              {message.limitations?.map((limit, i) => <p key={i}>{limit}</p>)}
              <button className="button secondary" onClick={() => downloadText("juridia-chat.txt", `${message.question}\n\n${message.answer}\n\n${message.citations.map(c => `${c.title}: ${c.passage}`).join("\n")}\n\n${message.disclaimer}`)}>Exportar respuesta</button>
            </details>
          </article>
        </div>)}
        {busy && <div className="chat-turn"><article className="chat-message user"><strong>Tú</strong><p>{pending}</p></article><p role="status">juridIA está escribiendo… La primera respuesta puede tardar mientras se carga el modelo.</p></div>}
        <div ref={end} />
      </div>
      <form className="chat-composer" onSubmit={e => { e.preventDefault(); void submit(); }}>
        <details className="chat-context"><summary>Contexto y documentos (opcional)</summary>
          <label className="field">Expediente de trabajo<select value={caseId} disabled={busy || messages.length > 0} onChange={e => { setCaseId(e.target.value); setDocuments([]); }}><option value="">Sin expediente</option>{data.cases.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
          {messages.length > 0 && <p className="small">Para cambiar de expediente, inicia un nuevo chat.</p>}
          {data.documents.filter(d => d.case_id === caseId).map(d => <label className="chat-document" key={d.id}><input type="checkbox" disabled={busy} checked={documents.includes(d.id)} onChange={e => setDocuments(e.target.checked ? [...documents, d.id] : documents.filter(value => value !== d.id))} /> {d.name}</label>)}
        </details>
        <label htmlFor="chat-question">Mensaje</label>
        <textarea ref={input} id="chat-question" value={question} maxLength={4000} disabled={busy} onChange={e => setQuestion(e.target.value)} placeholder="Escribe a juridIA…" rows={3} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void submit(); } }} />
        <div className="chat-send"><span>Enter para enviar · Mayús + Enter para nueva línea</span><button className="button primary" disabled={busy || !question.trim() || !API_MODE || !health?.generation_enabled}>{busy ? "Respondiendo…" : "Enviar"}</button></div>
        {error && <p className="form-error" role="alert">{error} Tu mensaje está listo para reintentar.</p>}
        <p className="chat-disclaimer">La IA puede equivocarse. No hay fuentes jurídicas oficiales conectadas; verifica las respuestas.</p>
      </form>
    </section>
  </div>;
}
