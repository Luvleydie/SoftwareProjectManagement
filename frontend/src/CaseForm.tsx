import { useState } from "react";
import type { Case } from "./types";
import { Modal } from "./components";

export default function CaseForm({
  initial,
  onSave,
  onClose,
  onDelete,
}: {
  initial: Case;
  onSave: (value: Case) => Promise<void>;
  onClose: () => void;
  onDelete?: () => void;
}) {
  const [value, setValue] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const field = (key: keyof Case, text: string) =>
    setValue({ ...value, [key]: text });
  return (
    <Modal
      title={onDelete ? "Detalle del expediente" : "Nuevo expediente"}
      onClose={onClose}
      wide
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (
            !value.name.trim() ||
            !value.region.trim() ||
            !value.locality.trim()
          ) {
            setError("Completa el nombre, el estado y el municipio.");
            return;
          }
          setBusy(true);
          try {
            await onSave({
              ...value,
              name: value.name.trim(),
              country: value.country.trim(),
              region: value.region.trim(),
              locality: value.locality.trim(),
            });
            onClose();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <p className="form-intro">
          Un lugar para reunir el contexto y los documentos de tu evento.
        </p>
        <div className="form-grid">
          <label className="field full">
            Nombre del evento
            <input
              required
              maxLength={120}
              autoFocus
              value={value.name}
              onChange={(e) => field("name", e.target.value)}
              placeholder="Ej. Festival de Primavera"
            />
          </label>
          <label className="field">
            País
            <input
              required
              maxLength={80}
              value={value.country}
              onChange={(e) => field("country", e.target.value)}
            />
          </label>
          <label className="field">
            Estado o región
            <input
              required
              maxLength={100}
              value={value.region}
              onChange={(e) => field("region", e.target.value)}
              placeholder="Ej. Puebla"
            />
          </label>
          <label className="field">
            Municipio o localidad
            <input
              required
              maxLength={100}
              value={value.locality}
              onChange={(e) => field("locality", e.target.value)}
              placeholder="Ej. Puebla"
            />
          </label>
          <label className="field">
            Fecha del evento
            <input
              type="date"
              required
              value={value.date}
              onChange={(e) => field("date", e.target.value)}
            />
          </label>
          <label className="field">
            Materia
            <select
              value={value.matter}
              onChange={(e) => field("matter", e.target.value)}
            >
              {[
                "Contratos con proveedores",
                "Permisos y cumplimiento",
                "Cancelaciones y contingencias",
                "Responsabilidad y seguros",
                "Protección de datos",
              ].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Estado del expediente
            <select
              value={value.status}
              onChange={(e) => field("status", e.target.value)}
            >
              {["En preparación", "En revisión", "Completado"].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label className="field full">
            Contexto del evento
            <textarea
              maxLength={5000}
              rows={3}
              value={value.context}
              onChange={(e) => field("context", e.target.value)}
              placeholder="Tipo de evento, aforo previsto y lo que necesitas revisar…"
            />
          </label>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          {onDelete && (
            <button
              className="text-button danger"
              type="button"
              onClick={onDelete}
            >
              Eliminar expediente
            </button>
          )}
          <button type="button" className="button secondary" onClick={onClose}>
            Cancelar
          </button>
          <button className="button primary" disabled={busy}>
            {busy ? "Guardando…" : "Guardar expediente"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
