import { useEffect, useRef, useState } from "react";
import {
  ArrowLeftRight,
  LayoutDashboard,
  LogOut,
  PiggyBank,
  Repeat,
  Settings,
  ShieldCheck,
  Trash2,
  TrendingUp,
  UserRound,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { NavLink, Link, useNavigate } from "react-router-dom";
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

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const onPointer = (event: MouseEvent | TouchEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
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

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    navigate("/login", { replace: true });
  }

  const initial = (user?.email ?? user?.username ?? "?").charAt(0).toUpperCase();

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
                  <NavItem to="/" end icon={LayoutDashboard} label="Dashboard" />
                  <NavItem
                    to="/movements"
                    icon={ArrowLeftRight}
                    label="Movimenti"
                  />
                  <NavItem to="/accounts" icon={Wallet} label="Conti" />
                  <NavItem to="/savings" icon={PiggyBank} label="Salvadanai" />
                  <NavItem
                    to="/automations"
                    icon={Repeat}
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
              type="button"
              className="profile-button"
              aria-label="Profilo e impostazioni"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((value) => !value)}
            >
              <span className="profile-avatar">{initial}</span>
            </button>
            {menuOpen && (
              <div className="profile-dropdown" role="menu">
                <NavLink
                  to="/account"
                  className="profile-entry"
                  role="menuitem"
                  onClick={() => setMenuOpen(false)}
                >
                  <UserRound size={18} aria-hidden="true" />
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
                  <NavLink
                    to="/trash"
                    className="profile-entry"
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                  >
                    <Trash2 size={18} aria-hidden="true" />
                    <span>Cestino</span>
                  </NavLink>
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
