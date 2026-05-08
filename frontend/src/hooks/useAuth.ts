import { useState, useCallback } from "react";
import { login as apiLogin } from "../services/api";

interface AuthState {
  token: string | null;
  username: string | null;
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState>(() => {
    const token = sessionStorage.getItem("sh_token");
    const username = sessionStorage.getItem("sh_username");
    return { token, username };
  });

  const login = useCallback(async (username: string) => {
    const token = await apiLogin(username);
    sessionStorage.setItem("sh_token", token);
    sessionStorage.setItem("sh_username", username);
    setAuth({ token, username });
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem("sh_token");
    sessionStorage.removeItem("sh_username");
    setAuth({ token: null, username: null });
  }, []);

  return {
    token: auth.token,
    username: auth.username,
    isAuthenticated: auth.token !== null,
    login,
    logout,
  };
}
