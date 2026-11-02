import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth";

export function LoadingScreen() {
  return (
    <div className="screen-center">
      <p className="muted">Caricamento…</p>
    </div>
  );
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingScreen />;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export function AdminRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_global_admin) return <Navigate to="/" replace />;
  return <>{children}</>;
}
