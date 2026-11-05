import {
  ArrowLeftRight,
  LayoutDashboard,
  LogOut,
  PiggyBank,
  Repeat,
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
    >
      <Icon size={20} strokeWidth={2} aria-hidden="true" />
      <span>{label}</span>
    </NavLink>
  );
}

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
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
                  <NavItem to="/" end icon={LayoutDashboard} label="Dashboard" />
                  <NavItem to="/accounts" icon={Wallet} label="Conti" />
                  <NavItem to="/savings" icon={PiggyBank} label="Salvadanai" />
                  <NavItem
                    to="/investments"
                    icon={TrendingUp}
                    label="Investimenti"
                  />
                  <NavItem
                    to="/automations"
                    icon={Repeat}
                    label="Automazioni"
                  />
                  <NavItem
                    to="/movements"
                    icon={ArrowLeftRight}
                    label="Movimenti"
                  />
                  <NavItem to="/trash" icon={Trash2} label="Cestino" />
                </>
              )}
              <NavItem to="/account" icon={UserRound} label="Account" />
              {user.is_global_admin && (
                <NavItem
                  to="/admin"
                  icon={ShieldCheck}
                  label="Amministrazione"
                />
              )}
              <button
                type="button"
                className="nav-item link-button"
                onClick={handleLogout}
              >
                <LogOut size={20} strokeWidth={2} aria-hidden="true" />
                <span>Esci</span>
              </button>
            </>
          )}
        </nav>
      </header>
      <main className="app-main">{children}</main>
      <footer className="app-footer">Spendy · v{__APP_VERSION__}</footer>
    </div>
  );
}
