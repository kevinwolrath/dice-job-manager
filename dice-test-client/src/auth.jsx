import { createContext, useContext, useState, useCallback } from "react";
import { userApi } from "./api.js";
import { decodeJwt } from "./jwt.js";

// Auth state lives only in React state (memory), not localStorage — this is
// a deliberate testing convenience: closing or reloading a tab logs you out,
// which makes it easy to open two tabs, log each into a different demo
// user, and be sure they really are two independent sessions rather than
// one tab's leftover token bleeding into the other.
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const [claims, setClaims] = useState(null);
  const [error, setError] = useState(null);

  const login = useCallback(async (username, password) => {
    setError(null);
    try {
      const { access_token } = await userApi.login(username, password);
      setToken(access_token);
      setClaims(decodeJwt(access_token));
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setClaims(null);
    setError(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, claims, error, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
