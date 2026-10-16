import { useState } from "react";
import type { ServiceHealth, User } from "./types";
import { Scale, Eye, EyeOff, ArrowRight } from "lucide-react";
import { api } from "./api";
import ServiceStatus from "./ServiceStatus";

export default function AuthView({
  onAuthenticated,
  health,
  healthError,
  healthLoading,
  onRefreshHealth,
}: {
  onAuthenticated: (user: User) => void;
  health: ServiceHealth | null;
  healthError: string;
  healthLoading: boolean;
  onRefreshHealth: () => Promise<void>;
}) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  return (
    <main className="auth-page">
      <div className="auth-story">
        <a className="brand" href="/">
          <span className="brand-mark">
            <Scale size={25} />
          </span>
          <span>
            juridIA
          </span>
        </a>
      </div>
      <div className="auth-form">

        <h1>
          {mode === "login" ? "Iniciar sesión" : "Crear cuenta"}
        </h1>
        <p>
          {mode === "login"
            ? "Accede a tus expedientes."
            : "Guarda tus expedientes y documentos."}
        </p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            try {
              onAuthenticated(
                await api.authenticate(mode, { name, email, password }),
              );
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {mode === "register" && (
            <label className="field">
              Nombre
              <input
                autoComplete="name"
                required
                maxLength={100}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
          )}
          <label className="field">
            Correo electrónico
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              maxLength={254}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="field">
            Contraseña
            <span className="password-control">
            <input
              type={showPassword ? "text" : "password"}
              aria-label="Contraseña"
              required
              minLength={12}
              maxLength={128}
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button type="button" className="icon-button" aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
            </span>
            {mode === "register" && (
              <span className="small muted">Al menos 12 caracteres.</span>
            )}
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="button primary" disabled={busy}>
            {busy
              ? "Un momento…"
              : mode === "login"
                ? "Entrar a mi espacio"
                : "Crear cuenta"}
            {!busy && <ArrowRight size={17} />}
          </button>
        </form>
        <button
          className="text-button auth-switch"
          disabled={busy}
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError("");
          }}
        >
          {mode === "login"
            ? "¿Primera vez? Crea una cuenta"
            : "Ya tengo una cuenta"}
        </button>
        <p className="auth-notice">
          Versión de desarrollo. La recuperación de cuenta y el acceso
          administrativo aún no están disponibles.
        </p>
        {(healthError || (health && !health.database.connected)) && <ServiceStatus health={health} error={healthError} loading={healthLoading} onRefresh={onRefreshHealth} />}
      </div>
    </main>
  );
}
