import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth";
import { RouteSkeleton } from "./PageSkeletons";

export function LoadingScreen() {
  return (
    <div className="screen-center">
      <div className="loading-card" aria-busy="true">
        <span className="visually-hidden">Caricamento…</span>
        <div className="skeleton loading-card-title" aria-hidden="true" />
        <div className="skeleton loading-bar" aria-hidden="true" />
        <div className="skeleton loading-bar short" aria-hidden="true" />
        <div className="skeleton loading-bar tiny" aria-hidden="true" />
      </div>
    </div>
  );
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <RouteSkeleton />;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export function AdminRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) return <RouteSkeleton />;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_global_admin) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function ProfileRoute({
  children,
  fallback,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { user, loading } = useAuth();

  if (loading) return fallback ?? <RouteSkeleton />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.is_global_admin) return <Navigate to="/admin" replace />;
  return <>{children}</>;
}
