import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

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
        <Link to="/" className="brand">
          Spendy
        </Link>
        <nav className="app-nav">
          {user && (
            <>
              {!user.is_global_admin && (
                <>
                  <Link to="/">Dashboard</Link>
                  <Link to="/accounts">Conti</Link>
                  <Link to="/savings">Salvadanai</Link>
                  <Link to="/movements">Movimenti</Link>
                  <Link to="/import">Importa</Link>
                </>
              )}
              <Link to="/account">Account</Link>
              {user.is_global_admin && <Link to="/admin">Amministrazione</Link>}
              <button type="button" className="link-button" onClick={handleLogout}>
                Esci
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
