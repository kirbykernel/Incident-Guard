import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchMe, login as apiLogin, logout as apiLogout } from "../services/api";
import type { User } from "../services/types";

// Session lives in an httpOnly cookie set by the backend (routes/auth.py)
// — this app never holds the JWT in JS, closing the XSS-exfiltration gap
// noted in docs/uml/threat-model-stride.md. Mutating requests carry a
// matching CSRF token (double-submit cookie, readable on purpose) echoed
// back as a header — see services/api.ts. All this hook does on mount is
// ask the backend "is there a valid session cookie?" via /auth/me.

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    setUser(await apiLogin(email, password));
  }

  async function logout() {
    await apiLogout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
