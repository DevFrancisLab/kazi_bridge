import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Create a separate instance for auth requests (login/register) that doesn't include auth headers
export const authApi = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

const REFRESH_KEY = 'refresh';

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

let refreshRequest: Promise<string | null> | null = null;

function clearStoredSession() {
  localStorage.removeItem('token');
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem('role');
  localStorage.removeItem('email');
  localStorage.removeItem('first_name');
  localStorage.removeItem('last_name');
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) {
    return null;
  }
  try {
    const response = await authApi.post('token/refresh/', { refresh });
    const access = response.data?.access;
    if (!access) {
      return null;
    }
    localStorage.setItem('token', access);
    if (response.data?.refresh) {
      localStorage.setItem(REFRESH_KEY, response.data.refresh);
    }
    return access;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (error.response?.status !== 401 || !original || original._retry) {
      return Promise.reject(error);
    }
    original._retry = true;
    if (!refreshRequest) {
      refreshRequest = refreshAccessToken().finally(() => {
        refreshRequest = null;
      });
    }
    const access = await refreshRequest;
    if (!access) {
      clearStoredSession();
      if (!window.location.pathname.startsWith('/login')) {
        window.location.assign('/login');
      }
      return Promise.reject(error);
    }
    original.headers.Authorization = `Bearer ${access}`;
    return api(original);
  }
);

export default api;
