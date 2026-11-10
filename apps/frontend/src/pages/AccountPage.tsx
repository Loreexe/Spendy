import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { Camera, KeyRound, Trash2, UserRound } from "lucide-react";
import { api, type UserStatus } from "../api";
import { useAuth } from "../auth";
import { InlineMessage } from "../components/InlineMessage";

const STATUS_LABEL: Record<UserStatus, string> = {
  pending: "In attesa di approvazione",
  active: "Attivo",
  rejected: "Rifiutato",
  disabled: "Disabilitato",
};

/** Ridimensiona l'immagine nel browser: l'avatar resta sotto i 300 KB. */
async function shrinkAvatar(file: File): Promise<File> {
  const bitmap = await createImageBitmap(file);
  const max = 512;
  const scale = Math.min(1, max / Math.max(bitmap.width, bitmap.height));
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return file;
  context.drawImage(bitmap, 0, 0, width, height);
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/webp", 0.85),
  );
  if (!blob) return file;
  return new File([blob], "avatar.webp", { type: "image/webp" });
}

function initials(user: { first_name: string; last_name: string; display_name: string }) {
  const name = `${user.first_name} ${user.last_name}`.trim() || user.display_name;
  const parts = name.split(/[\s._@-]+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "?";
}

export function AccountPage() {
  const { user, setUser, logout } = useAuth();
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [editing, setEditing] = useState(false);
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [username, setUsername] = useState(user?.username ?? "");

  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    new_password_confirm: "",
  });

  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [accessMessage, setAccessMessage] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [avatarMessage, setAvatarMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [accessError, setAccessError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!user) return null;

  const avatarSrc = user.has_avatar
    ? `/api/auth/avatar/?v=${encodeURIComponent(user.avatar_updated_at ?? "")}`
    : null;

  async function handlePersonal(event: FormEvent) {
    event.preventDefault();
    setProfileError(null);
    setProfileMessage(null);
    setBusy(true);
    try {
      const data = await api.updateProfile({ first_name: firstName, last_name: lastName });
      setUser(data.user);
      setEditing(false);
      setProfileMessage("Dati personali aggiornati.");
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : "Aggiornamento non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function handleAccess(event: FormEvent) {
    event.preventDefault();
    setAccessError(null);
    setAccessMessage(null);
    setBusy(true);
    try {
      const data = await api.updateProfile({
        email,
        ...(user?.is_global_admin ? {} : { username }),
      });
      setUser(data.user);
      setUsername(data.user.username ?? "");
      setAccessMessage("Dati di accesso aggiornati.");
    } catch (err) {
      setAccessError(err instanceof Error ? err.message : "Aggiornamento non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function handlePassword(event: FormEvent) {
    event.preventDefault();
    setPasswordError(null);
    setPasswordMessage(null);
    setBusy(true);
    try {
      await api.changePassword(passwordForm);
      setPasswordForm({
        current_password: "",
        new_password: "",
        new_password_confirm: "",
      });
      setPasswordMessage("Password aggiornata.");
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : "Cambio password non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function handleAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setAvatarError(null);
    setAvatarMessage(null);
    setBusy(true);
    try {
      const optimized = await shrinkAvatar(file);
      const data = await api.uploadAvatar(optimized);
      setUser(data.user);
      setAvatarMessage("Foto aggiornata.");
    } catch (err) {
      setAvatarError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function removeAvatar() {
    setAvatarError(null);
    setAvatarMessage(null);
    setBusy(true);
    try {
      const data = await api.deleteAvatar();
      setUser(data.user);
      setAvatarMessage("Foto rimossa.");
    } catch (err) {
      setAvatarError(err instanceof Error ? err.message : "Rimozione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack-page profile-page">
      <section className="profile-hero">
        <div className="profile-avatar-wrapper">
          <span className="profile-avatar-large">
            {avatarSrc ? (
              <img src={avatarSrc} alt="Foto profilo" />
            ) : (
              initials(user)
            )}
          </span>
          <button
            type="button"
            className="avatar-edit"
            title="Cambia foto profilo"
            aria-label="Cambia foto profilo"
            onClick={() => fileRef.current?.click()}
            disabled={busy}
          >
            <Camera size={15} aria-hidden="true" />
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            hidden
            onChange={(event) => void handleAvatar(event)}
          />
        </div>

        <div className="profile-identity">
          <p className="eyebrow">Profilo</p>
          <h1>{user.display_name || user.email || user.username}</h1>
          <p className="muted small">
            {user.email ?? "Nessuna email"}
            {user.username ? ` · @${user.username}` : ""}
          </p>
          <div className="profile-badges">
            <span className={`badge ${user.status}`}>
              {STATUS_LABEL[user.status]}
            </span>
            <span className="badge">
              {user.is_global_admin ? "Amministratore globale" : "Utente"}
            </span>
            <span className="muted small">
              Iscritto il{" "}
              {new Date(user.date_joined).toLocaleDateString("it-IT")}
            </span>
          </div>
          {avatarMessage && <InlineMessage tone="success">{avatarMessage}</InlineMessage>}
          {avatarError && <InlineMessage tone="error">{avatarError}</InlineMessage>}
        </div>

        <div className="profile-hero-actions">
          <button
            type="button"
            className="secondary"
            onClick={() => void logout()}
          >
            Esci
          </button>
        </div>
      </section>

      <section className="profile-section">
        <div className="section-heading">
          <h2>
            <UserRound size={18} aria-hidden="true" /> Dati personali
          </h2>
          {!editing && (
            <button
              type="button"
              className="secondary small-button"
              onClick={() => {
                setFirstName(user.first_name);
                setLastName(user.last_name);
                setEditing(true);
              }}
            >
              Modifica
            </button>
          )}
        </div>

        {editing ? (
          <form onSubmit={handlePersonal} className="stack">
            <div className="form-grid">
              <label>
                Nome
                <input
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                  maxLength={80}
                  autoComplete="given-name"
                  placeholder="Facoltativo"
                />
              </label>
              <label>
                Cognome
                <input
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                  maxLength={80}
                  autoComplete="family-name"
                  placeholder="Facoltativo"
                />
              </label>
            </div>
            {user.has_avatar && (
              <button
                type="button"
                className="secondary small-button"
                onClick={() => void removeAvatar()}
                disabled={busy}
              >
                <Trash2 size={14} aria-hidden="true" /> Rimuovi foto
              </button>
            )}
            {profileError && <InlineMessage tone="error">{profileError}</InlineMessage>}
            <div className="actions">
              <button type="submit" disabled={busy}>
                {busy ? "Salvataggio…" : "Salva"}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setEditing(false);
                  setProfileError(null);
                }}
                disabled={busy}
              >
                Annulla
              </button>
            </div>
          </form>
        ) : (
          <>
            <dl className="facts profile-facts">
              <div>
                <dt>Nome</dt>
                <dd>{user.first_name || "—"}</dd>
              </div>
              <div>
                <dt>Cognome</dt>
                <dd>{user.last_name || "—"}</dd>
              </div>
            </dl>
            {profileMessage && <InlineMessage tone="success">{profileMessage}</InlineMessage>}
          </>
        )}
      </section>

      <section className="profile-section">
        <div className="section-heading">
          <h2>Accesso</h2>
        </div>
        <form onSubmit={handleAccess} className="stack">
          <div className="form-grid">
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required={!user.is_global_admin}
                autoComplete="email"
              />
            </label>
            {!user.is_global_admin && (
              <label>
                Nome utente
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  maxLength={150}
                  placeholder="Facoltativo"
                  autoComplete="username"
                />
              </label>
            )}
          </div>
          {accessMessage && <InlineMessage tone="success">{accessMessage}</InlineMessage>}
          {accessError && <InlineMessage tone="error">{accessError}</InlineMessage>}
          <div className="actions">
            <button type="submit" disabled={busy}>
              {busy ? "Salvataggio…" : "Salva accesso"}
            </button>
          </div>
        </form>
      </section>

      <section className="profile-section">
        <div className="section-heading">
          <h2>
            <KeyRound size={18} aria-hidden="true" /> Password
          </h2>
        </div>
        <form onSubmit={handlePassword} className="stack">
          <label>
            Password attuale
            <input
              type="password"
              value={passwordForm.current_password}
              onChange={(event) =>
                setPasswordForm({
                  ...passwordForm,
                  current_password: event.target.value,
                })
              }
              autoComplete="current-password"
              required
            />
          </label>
          <div className="form-grid">
            <label>
              Nuova password
              <input
                type="password"
                value={passwordForm.new_password}
                onChange={(event) =>
                  setPasswordForm({
                    ...passwordForm,
                    new_password: event.target.value,
                  })
                }
                autoComplete="new-password"
                required
              />
            </label>
            <label>
              Ripeti nuova password
              <input
                type="password"
                value={passwordForm.new_password_confirm}
                onChange={(event) =>
                  setPasswordForm({
                    ...passwordForm,
                    new_password_confirm: event.target.value,
                  })
                }
                autoComplete="new-password"
                required
              />
            </label>
          </div>
          {passwordMessage && <InlineMessage tone="success">{passwordMessage}</InlineMessage>}
          {passwordError && <InlineMessage tone="error">{passwordError}</InlineMessage>}
          <div className="actions">
            <button type="submit" disabled={busy}>
              {busy ? "Aggiornamento…" : "Cambia password"}
            </button>
          </div>        </form>
      </section>
    </div>
  );
}
