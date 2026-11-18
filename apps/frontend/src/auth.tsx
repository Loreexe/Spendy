import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, type LoginResult, type User } from "./api";
import { syncThemeFromProfile } from "./theme";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  login: (identifier: string, password: string) => Promise<LoginResult>;
  completeTwoFactor: (challenge: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await api.me();
      setUser(data.user);
      if (data.user && !data.user.is_global_admin) {
        await syncThemeFromProfile();
      }
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(async (identifier: string, password: string) => {
    const data = await api.login(identifier, password);
    if ("two_factor_required" in data && data.two_factor_required) {
      return data;
    }
    setUser(data.user);
    if (!data.user.is_global_admin) {
      await syncThemeFromProfile();
    }
    return data;
  }, []);

  const completeTwoFactor = useCallback(
    async (challenge: string, code: string) => {
      const data = await api.verifyTwoFactor(challenge, code);
      setUser(data.user);
      if (!data.user.is_global_admin) {
        await syncThemeFromProfile();
      }
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      refresh,
      login,
      completeTwoFactor,
      logout,
      setUser,
    }),
    [user, loading, refresh, login, completeTwoFactor, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth deve essere usato dentro AuthProvider");
  }
  return context;
}
