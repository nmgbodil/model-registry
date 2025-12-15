import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";
import { apiClient } from "@/lib/api";
import { User, AuthState } from "@/types";

interface AuthContextType extends AuthState {
  login: (name: string, password: string, isAdmin?: boolean) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>(() => {
    const storedToken = sessionStorage.getItem("auth_token");
    const storedUser = sessionStorage.getItem("auth_user");
    
    if (storedToken && storedUser) {
      apiClient.setToken(storedToken);
      return {
        token: storedToken,
        user: JSON.parse(storedUser),
        isAuthenticated: true,
      };
    }
    
    return {
      token: null,
      user: null,
      isAuthenticated: false,
    };
  });

  const login = useCallback(async (name: string, password: string, isAdmin = false) => {
    const token = await apiClient.login(name, password);
    const cleanToken = token.replace(/^"bearer\s*/i, "").replace(/"$/, "");
    
    apiClient.setToken(cleanToken);
    
    const user: User = { name, isAdmin };
    
    sessionStorage.setItem("auth_token", cleanToken);
    sessionStorage.setItem("auth_user", JSON.stringify(user));
    
    setAuthState({
      token: cleanToken,
      user,
      isAuthenticated: true,
    });
  }, []);

  const logout = useCallback(() => {
    apiClient.setToken(null);
    sessionStorage.removeItem("auth_token");
    sessionStorage.removeItem("auth_user");
    
    setAuthState({
      token: null,
      user: null,
      isAuthenticated: false,
    });
  }, []);

  return (
    <AuthContext.Provider value={{ ...authState, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
