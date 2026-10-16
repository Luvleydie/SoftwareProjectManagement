import { RefreshCw } from "lucide-react";
import type { ServiceHealth } from "./types";

export function aiStatusLabel(health: ServiceHealth | null) {
  if (!health) return "Comprobando disponibilidad de IA local";
  return health.ai.available
    ? `IA local disponible · ${health.ai.model}`
    : `IA local no disponible · ${health.ai.model}`;
}

export default function ServiceStatus({
  health,
  error,
  loading,
  onRefresh,
}: {
  health: ServiceHealth | null;
  error: string;
  loading: boolean;
  onRefresh: () => Promise<void>;
}) {
  return (
    <section className="service-status" aria-label="Estado de conexión">
      <div className="section-heading">
        <h3>Conexión local</h3>
        <button
          type="button"
          className="text-button"
          disabled={loading}
          onClick={() => void onRefresh()}
        >
          <RefreshCw size={14} className={loading ? "is-spinning" : ""} />
          {loading ? "Comprobando…" : "Comprobar conexión"}
        </button>
      </div>
      {error ? (
        <p className="form-error" role="status">{error}</p>
      ) : health ? (
        <>
          <div className="service-status-items">
            <span className={`status ${health.database.connected ? "green" : "amber"}`}>
              {health.database.engine} · {health.database.connected ? "Conectado" : "Sin conexión"}
              {health.database.port ? ` · Puerto ${health.database.port}` : ""}
            </span>
            <span className={`status ${health.ai.available ? "green" : "amber"}`}>
              Ollama · {health.ai.available ? "Disponible" : "No disponible"}
            </span>
          </div>
          <p className="small muted">Modelo: {health.ai.model}</p>
          {!health.ai.available && (
            <p className="small muted">
              {health.ai.detail || "Inicia Ollama y comprueba que el modelo esté descargado para generar respuestas."}
            </p>
          )}
          {!health.database.connected && (
            <p className="small muted">Inicia MySQL en XAMPP para guardar y abrir tus expedientes.</p>
          )}
          {health.ai.available && !health.generation_enabled && (
            <p className="small muted">La generación todavía no está habilitada en el servidor.</p>
          )}
        </>
      ) : (
        <p className="small muted" role="status">Consultando la disponibilidad de la base de datos y la IA…</p>
      )}
    </section>
  );
}
