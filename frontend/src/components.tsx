import { useEffect, useRef, useId } from "react";
import type { ReactNode } from "react";
import { X, FolderOpen, ShieldCheck, Search } from "lucide-react";
import type { Case } from "./types";
import { DISCLAIMER, dateLabel } from "./domain";

export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const el = ref.current!;
    el.showModal();
    return () => el.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "wide" : ""}`}
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onClick={(e) => {
        if (e.target !== ref.current) return;
        const bounds = e.currentTarget.getBoundingClientRect();
        if (e.clientX < bounds.left || e.clientX > bounds.right ||
            e.clientY < bounds.top || e.clientY > bounds.bottom) onClose();
      }}
      aria-labelledby={titleId}
    >
      <div className="modal-heading">
        <h2 id={titleId}>{title}</h2>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Cerrar ventana"
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Empty({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <FolderOpen size={28} />
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </div>
  );
}
export function Notice({ children }: { children?: ReactNode }) {
  return (
    <div className="notice">
      <ShieldCheck size={18} />
      <p>{children ?? DISCLAIMER}</p>
    </div>
  );
}
export function SearchField({
  value,
  onChange,
  placeholder = "Buscar…",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="search-field">
      <Search size={17} />
      <input
        aria-label={placeholder}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {value && (
        <button aria-label="Limpiar búsqueda" onClick={() => onChange("")}>
          <X size={15} />
        </button>
      )}
    </label>
  );
}
export function ContextChips({ context }: { context: Case }) {
  return (
    <div className="context-chips">
      <span>
        {context.locality}, {context.region} · {context.country}
      </span>
      <span>{dateLabel(context.date, true)}</span>
      <span>{context.matter}</span>
    </div>
  );
}
