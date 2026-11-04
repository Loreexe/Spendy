import { useEffect, useState, type ReactNode } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { api } from "./api";
import { AuthProvider } from "./auth";
import {
  AdminRoute,
  LoadingScreen,
  ProfileRoute,
  ProtectedRoute,
} from "./components/Guards";
import { Layout } from "./components/Layout";
import { AdminPage } from "./pages/AdminPage";
import { AccountPage } from "./pages/AccountPage";
import { AccountsPage } from "./pages/AccountsPage";
import { AutomationsPage } from "./pages/AutomationsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ImportPage } from "./pages/ImportPage";
import { InvestmentsPage } from "./pages/InvestmentsPage";
import { LoginPage } from "./pages/LoginPage";
import { MovementsPage } from "./pages/MovementsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PendingPage } from "./pages/PendingPage";
import { RegisterPage } from "./pages/RegisterPage";
import { SavingsPage } from "./pages/SavingsPage";
import { SetupPage } from "./pages/SetupPage";

function SetupGate({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [setupRequired, setSetupRequired] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    api
      .setupStatus()
      .then((status) => {
        if (active) setSetupRequired(status.setup_required);
      })
      .catch(() => {
        // Backend non raggiungibile: le pagine mostrano il proprio errore.
        if (active) setSetupRequired(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (setupRequired === null) return <LoadingScreen />;
  if (setupRequired && location.pathname !== "/setup") {
    return <Navigate to="/setup" replace />;
  }
  return <>{children}</>;
}

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Layout>
          <SetupGate>
            <Routes>
              <Route path="/setup" element={<SetupPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/pending" element={<PendingPage />} />
              <Route
                path="/"
                element={
                  <ProfileRoute>
                    <DashboardPage />
                  </ProfileRoute>
                }
              />
              <Route
                path="/accounts"
                element={
                  <ProfileRoute>
                    <AccountsPage />
                  </ProfileRoute>
                }
              />
              <Route
                path="/savings"
                element={
                  <ProfileRoute>
                    <SavingsPage />
                  </ProfileRoute>
                }
              />
              <Route
                path="/investments"
                element={
                  <ProfileRoute>
                    <InvestmentsPage />
                  </ProfileRoute>
                }
              />
              <Route
                path="/automations"
                element={
                  <ProfileRoute>
                    <AutomationsPage />
                  </ProfileRoute>
                }
              />
              <Route
                path="/movements"
                element={
                  <ProfileRoute>
                    <MovementsPage />
                  </ProfileRoute>
                }
              />
              <Route
                path="/import"
                element={
                  <ProfileRoute>
                    <ImportPage />
                  </ProfileRoute>
                }
              />
              <Route
                path="/account"
                element={
                  <ProtectedRoute>
                    <AccountPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin"
                element={
                  <AdminRoute>
                    <AdminPage />
                  </AdminRoute>
                }
              />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </SetupGate>
        </Layout>
      </AuthProvider>
    </BrowserRouter>
  );
}
