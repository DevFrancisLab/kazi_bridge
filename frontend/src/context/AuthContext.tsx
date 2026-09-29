import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

type UserRole = 'CLIENT' | 'FREELANCER' | '';

export interface UserInfo {
  email: string;
  role: UserRole;
  name?: string;
}

interface AuthContextType {
  token: string | null;
  role: UserRole;
  user: UserInfo | null;
  isAuthenticated: boolean;
  login: (payload: { token: string; role: UserRole; email: string; name?: string; }) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_TOKEN_KEY = 'token';
const AUTH_ROLE_KEY = 'role';
const AUTH_EMAIL_KEY = 'email';

const readStoredAuth = () => {
  const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
  const storedRole = (localStorage.getItem(AUTH_ROLE_KEY) as UserRole) || '';
  const storedEmail = localStorage.getItem(AUTH_EMAIL_KEY) || '';
  if (!storedToken || !storedRole || !storedEmail) {
    return { token: null, role: '' as UserRole, user: null as UserInfo | null };
  }
  return {
    token: storedToken,
    role: storedRole,
    user: { email: storedEmail, role: storedRole } as UserInfo,
  };
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => readStoredAuth().token);
  const [role, setRole] = useState<UserRole>(() => readStoredAuth().role);
  const [user, setUser] = useState<UserInfo | null>(() => readStoredAuth().user);

  useEffect(() => {
    const stored = readStoredAuth();
    setToken(stored.token);
    setRole(stored.role);
    setUser(stored.user);
  }, []);

  const login = (payload: { token: string; role: UserRole; email: string; name?: string }) => {
    console.log("AuthContext login called with:", { role: payload.role, email: payload.email });

    // clear stale auth state before writing new values
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_ROLE_KEY);
    localStorage.removeItem(AUTH_EMAIL_KEY);

    localStorage.setItem(AUTH_TOKEN_KEY, payload.token);
    localStorage.setItem(AUTH_ROLE_KEY, payload.role);
    localStorage.setItem(AUTH_EMAIL_KEY, payload.email);

    console.log("AuthContext setting role to:", payload.role);
    setToken(payload.token);
    setRole(payload.role);
    setUser({ email: payload.email, role: payload.role, name: payload.name });
  };

  const logout = () => {
    console.log("AuthContext logout called - clearing auth state");

    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_ROLE_KEY);
    localStorage.removeItem(AUTH_EMAIL_KEY);

    setToken(null);
    setRole('');
    setUser(null);
  };

  const value = useMemo(
    () => ({
      token,
      role,
      user,
      isAuthenticated: Boolean(token),
      login,
      logout,
    }),
    [token, role, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
