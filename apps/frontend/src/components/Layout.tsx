import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import {
  Clock,
  Download,
  House,
  LogOut,
  PiggyBank,
  ReceiptText,
  Settings,
  ShieldCheck,
  Trash2,
  TrendingUp,
  User,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { NavLink, Link, useLocation, useNavigate } from "react-router-dom";
import type { User as UserProfile } from "../api";
import { useAuth } from "../auth";

function NavItem({
  to,
  end,
  icon: Icon,
  label,
}: {
  to: string;
  end?: boolean;
  icon: LucideIcon;
  label: string;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        isActive ? "nav-item active" : "nav-item"
      }
      title={label}
      aria-label={label}
    >
      <Icon size={24} strokeWidth={2} aria-hidden="true" />
      <span className="nav-label">{label}</span>
    </NavLink>
  );
}

/** Iniziali dell'avatar: nome e cognome, altrimenti display name, email o username. */
function avatarInitials(user: UserProfile): string {
  const name =
    `${user.first_name} ${user.last_name}`.trim() ||
    user.display_name ||
    user.email ||
    user.username ||
    "";
  const parts = name.split(/[\s._@-]+/).filter(Boolean);
  const letters = parts.slice(0, 2).map((part) => part[0]?.toUpperCase() ?? "");
  return letters.join("") || "?";
}

/** Nome e cognome nella testata del menu, con fallback sui dati disponibili. */
function menuDisplayName(user: UserProfile): string {
  return (
    `${user.first_name} ${user.last_name}`.trim() ||
    user.display_name ||
    user.email ||
    user.username ||
    "Profilo"
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [brokenAvatarVersion, setBrokenAvatarVersion] = useState<string | null>(
    null,
  );
  const menuRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const focusFirstOnOpen = useRef(false);

  const avatarVersion = user?.avatar_updated_at ?? "";
  const avatarSrc =
    user?.has_avatar && brokenAvatarVersion !== avatarVersion
      ? `/api/auth/avatar/?v=${encodeURIComponent(avatarVersion)}`
      : null;
  const initials = user ? avatarInitials(user) : "?";

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const onPointer = (event: MouseEvent | TouchEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("touchstart", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("touchstart", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!menuOpen || !focusFirstOnOpen.current) return;
    focusFirstOnOpen.current = false;
    dropdownRef.current
      ?.querySelector<HTMLElement>('[role="menuitem"]')
      ?.focus();
  }, [menuOpen]);

  function handleMenuKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(
      dropdownRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ??
        [],
    );
    if (items.length === 0) return;
    const current = items.indexOf(document.activeElement as HTMLElement);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      items[current < 0 ? 0 : (current + 1) % items.length]?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      items[current <= 0 ? items.length - 1 : current - 1]?.focus();
    } else if (event.key === "Home") {
      event.preventDefault();
      items[0]?.focus();
    } else if (event.key === "End") {
      event.preventDefault();
      items[items.length - 1]?.focus();
    } else if (event.key === "Tab") {
      setMenuOpen(false);
    }
  }

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand" aria-label="Spendy — home">
          <img
            className="brand-logo brand-logo-dark"
            src="/logo/spendy-lockup-h-black-on-dark.svg"
            alt="Spendy"
          />
          <img
            className="brand-logo brand-logo-light"
            src="/logo/spendy-lockup-h-black-on-light.svg"
            alt=""
            aria-hidden="true"
          />
        </Link>
        <nav className="app-nav" aria-label="Navigazione principale">
          {user && (
            <>
              {!user.is_global_admin && (
                <>
                  <NavItem to="/" end icon={House} label="Home" />
                  <NavItem
                    to="/movements"
                    icon={ReceiptText}
                    label="Movimenti"
                  />
                  <NavItem to="/accounts" icon={Wallet} label="Conti" />
                  <NavItem to="/savings" icon={PiggyBank} label="Salvadanai" />
                  <NavItem
                    to="/automations"
                    icon={Clock}
                    label="Automazioni"
                  />
                  <NavItem
                    to="/investments"
                    icon={TrendingUp}
                    label="Investimenti"
                  />
                </>
              )}
              {user.is_global_admin && (
                <NavItem
                  to="/admin"
                  icon={ShieldCheck}
                  label="Amministrazione"
                />
              )}
            </>
          )}
        </nav>
        {user && (
          <div className="profile-menu" ref={menuRef}>
            <button
              ref={triggerRef}
              type="button"
              className="profile-button"
              aria-label="Apri il menu del profilo"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-controls="profile-menu"
              onClick={() => setMenuOpen((value) => !value)}
              onKeyDown={(event) => {
                if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                  event.preventDefault();
                  focusFirstOnOpen.current = true;
                  setMenuOpen(true);
                }
              }}
            >
              <span className="profile-avatar">
                {avatarSrc ? (
                  <img
                    src={avatarSrc}
                    alt=""
                    onError={() => setBrokenAvatarVersion(avatarVersion)}
                  />
                ) : (
                  initials
                )}
              </span>
            </button>
            {menuOpen && (
              <div
                id="profile-menu"
                className="profile-dropdown"
                role="menu"
                aria-label="Menu del profilo"
                ref={dropdownRef}
                onKeyDown={handleMenuKeyDown}
              >
                <div className="profile-menu-head" role="presentation">
                  <span className="profile-menu-avatar">
                    {avatarSrc ? (
                      <img
                        src={avatarSrc}
                        alt=""
                        onError={() => setBrokenAvatarVersion(avatarVersion)}
                      />
                    ) : (
                      initials
                    )}
                  </span>
                  <span className="profile-menu-identity">
                    <strong>{menuDisplayName(user)}</strong>
                    {user.email && (
                      <span className="muted small">{user.email}</span>
                    )}
                  </span>
                </div>
                <NavLink
                  to="/account"
                  className="profile-entry"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                >
                  <User size={18} aria-hidden="true" />
                  <span>Profilo</span>
                </NavLink>
                <NavLink
                  to="/settings"
                  className="profile-entry"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                >
                  <Settings size={18} aria-hidden="true" />
                  <span>Impostazioni</span>
                </NavLink>
                {!user.is_global_admin && (
                  <>
                    <Link
                      to="/settings#import-export"
                      className="profile-entry"
                      role="menuitem"
                      onClick={() => setMenuOpen(false)}
                    >
                      <Download size={18} aria-hidden="true" />
                      <span>Import/Export</span>
                    </Link>
                    <NavLink
                      to="/trash"
                      className="profile-entry"
                      role="menuitem"
                      onClick={() => setMenuOpen(false)}
                    >
                      <Trash2 size={18} aria-hidden="true" />
                      <span>Cestino</span>
                    </NavLink>
                  </>
                )}
                {user.is_global_admin && (
                  <NavLink
                    to="/admin"
                    className="profile-entry"
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                  >
                    <ShieldCheck size={18} aria-hidden="true" />
                    <span>Amministrazione</span>
                  </NavLink>
                )}
                <button
                  type="button"
                  className="profile-entry"
                  role="menuitem"
                  onClick={() => void handleLogout()}
                >
                  <LogOut size={18} aria-hidden="true" />
                  <span>Esci</span>
                </button>
              </div>
            )}
          </div>
        )}
      </header>
      <main className="app-main">{children}</main>
      <footer className="app-footer">Spendy · v{__APP_VERSION__}</footer>
    </div>
  );
}
