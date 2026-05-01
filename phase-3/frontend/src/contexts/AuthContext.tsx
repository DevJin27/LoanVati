import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import { useNavigate } from "react-router-dom";

import { api, clearToken, getToken } from "../lib/api";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  authenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren): JSX.Element {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(Boolean(getToken()));
  const navigate = useNavigate();

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    navigate("/login", { replace: true });
  }, [navigate]);

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    try {
      setUser(await api.me());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  useEffect(() => {
    window.addEventListener("loanvati:unauthorized", logout);
    return () => window.removeEventListener("loanvati:unauthorized", logout);
  }, [logout]);

  const login = useCallback(
    async (email: string, password: string) => {
      await api.login({ email, password });
      setUser(await api.me());
    },
    [],
  );

  const register = useCallback(async (fullName: string, email: string, password: string) => {
    await api.register({ full_name: fullName, email, password });
    setUser(await api.me());
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      authenticated: Boolean(user),
      login,
      register,
      logout,
      refreshUser,
    }),
    [loading, login, logout, refreshUser, register, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
