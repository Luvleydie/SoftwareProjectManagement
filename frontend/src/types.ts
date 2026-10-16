export type View =
  | "inicio"
  | "consultas"
  | "expedientes"
  | "documentos"
  | "borradores"
  | "fuentes"
  | "ajustes";
export interface Case {
  id: string;
  name: string;
  country: string;
  region: string;
  locality: string;
  date: string;
  matter: string;
  context: string;
  status: "En preparación" | "En revisión" | "Completado";
}
export interface Document {
  id: string;
  case_id: string;
  name: string;
  size: number;
  text: string;
  created_at: string;
}
export interface Citation {
  document_id: string;
  title: string;
  passage: string;
  locator: string;
  origin: "private";
}
export interface GenerationMetadata {
  provider: string;
  model: string;
  generated_at: string;
}
export interface ServiceHealth {
  status: "ok" | "degraded";
  version: string;
  database: { connected: boolean; engine: string; port: number | null };
  ai: { available: boolean; provider: "ollama"; model: string; detail?: string };
  generation_enabled: boolean;
  legal_corpus_ready: boolean;
}
export interface Consultation {
  conversation_id?: string;
  id: string;
  case_id: string;
  question: string;
  answer: string;
  citations: Citation[];
  context: Case;
  created_at: string;
  outcome: "DOCUMENT_REVIEW" | "INSUFFICIENT_EVIDENCE" | "OUT_OF_SCOPE";
  disclaimer: string;
  generation?: GenerationMetadata;
  limitations?: string[];
  input_document_ids?: string[];
}
export interface DraftInput {
  case_id: string;
  kind: string;
  parties: string;
  terms: string;
  mode?: "ai" | "template";
}
export interface Draft {
  id: string;
  case_id: string;
  title: string;
  kind: string;
  text: string;
  original_text: string;
  version: number;
  updated_at: string;
  generation?: GenerationMetadata;
}
export interface Workspace {
  cases: Case[];
  documents: Document[];
  consultations: Consultation[];
  drafts: Draft[];
}
export interface User {
  name: string;
  email: string;
}
