import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { fetchMyProfile } from '@/lib/api/profile';

type UserRole = 'CLIENT' | 'FREELANCER' | '';

export interface UserInfo {
  email: string;
  role: UserRole;
  name?: string;
  firstName?: string;
  lastName?: string;
}

interface AuthContextType {
  token: string | null;
  role: UserRole;
  user: UserInfo | null;
  isAuthenticated: boolean;
  login: (payload: { token: string; role: UserRole; email: string; name?: string; refresh?: string; }) => void;
  logout: () => void;
  updateProfile: (profile: { firstName: string; lastName: string }) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_TOKEN_KEY = 'token';
const AUTH_ROLE_KEY = 'role';
const AUTH_EMAIL_KEY = 'email';
const AUTH_FIRST_NAME_KEY = 'first_name';
const AUTH_LAST_NAME_KEY = 'last_name';
const AUTH_REFRESH_KEY = 'refresh';

const displayName = (firstName: string, lastName: string) =>
  [firstName, lastName].filter((part) => part.trim()).join(' ');

const readStoredAuth = () => {
  const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
  const storedRole = (localStorage.getItem(AUTH_ROLE_KEY) as UserRole) || '';
  const storedEmail = localStorage.getItem(AUTH_EMAIL_KEY) || '';
  const firstName = localStorage.getItem(AUTH_FIRST_NAME_KEY) || '';
  const lastName = localStorage.getItem(AUTH_LAST_NAME_KEY) || '';
  if (!storedToken || !storedRole || !storedEmail) {
    return { token: null, role: '' as UserRole, user: null as UserInfo | null };
  }
  return {
    token: storedToken,
    role: storedRole,
    user: {
      email: storedEmail,
      role: storedRole,
      firstName,
      lastName,
      name: displayName(firstName, lastName) || undefined,
    } as UserInfo,
  };
};

const storeProfileNames = (firstName: string, lastName: string) => {
  localStorage.setItem(AUTH_FIRST_NAME_KEY, firstName);
  localStorage.setItem(AUTH_LAST_NAME_KEY, lastName);
};

const clearProfileNames = () => {
  localStorage.removeItem(AUTH_FIRST_NAME_KEY);
  localStorage.removeItem(AUTH_LAST_NAME_KEY);
  localStorage.removeItem(AUTH_REFRESH_KEY);
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

  const login = (payload: { token: string; role: UserRole; email: string; name?: string; refresh?: string }) => {
    console.log("AuthContext login called with:", { role: payload.role, email: payload.email });

    // clear stale auth state before writing new values
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_ROLE_KEY);
    localStorage.removeItem(AUTH_EMAIL_KEY);
    clearProfileNames();

    localStorage.setItem(AUTH_TOKEN_KEY, payload.token);
    localStorage.setItem(AUTH_ROLE_KEY, payload.role);
    localStorage.setItem(AUTH_EMAIL_KEY, payload.email);
    if (payload.refresh) {
      localStorage.setItem(AUTH_REFRESH_KEY, payload.refresh);
    }

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
    clearProfileNames();

    setToken(null);
    setRole('');
    setUser(null);
  };

  const updateProfile = useCallback((profile: { firstName: string; lastName: string }) => {
    storeProfileNames(profile.firstName, profile.lastName);
    setUser((current) => current ? {
      ...current,
      firstName: profile.firstName,
      lastName: profile.lastName,
      name: displayName(profile.firstName, profile.lastName) || undefined,
    } : current);
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }
    let cancelled = false;
    fetchMyProfile()
      .then((profile) => {
        if (!cancelled) {
          updateProfile({ firstName: profile.first_name || '', lastName: profile.last_name || '' });
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [token, updateProfile]);

  const value = useMemo(
    () => ({
      token,
      role,
      user,
      isAuthenticated: Boolean(token),
      login,
      logout,
      updateProfile,
    }),
    [token, role, user, updateProfile]
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
