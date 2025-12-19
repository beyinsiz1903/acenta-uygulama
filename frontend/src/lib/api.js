import axios from "axios";

const backendUrl = process.env.REACT_APP_BACKEND_URL;

export function getToken() {
  return localStorage.getItem("acenta_token") || "";
}

export function setToken(token) {
  localStorage.setItem("acenta_token", token);
}

export function clearToken() {
  localStorage.removeItem("acenta_token");
  localStorage.removeItem("acenta_user");
}

export function getUser() {
  try {
    const raw = localStorage.getItem("acenta_user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setUser(user) {
  localStorage.setItem("acenta_user", JSON.stringify(user));
}

export const api = axios.create({
  baseURL: `${backendUrl}/api`,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // FAZ-7: app version for audit origin
  try {
    // lazy import to avoid circular deps issues
    const { APP_VERSION } = require("../utils/appVersion");
    config.headers["X-App-Version"] = APP_VERSION;
  } catch {
    // ignore
  }

  return config;
});

api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    if (err?.response?.status === 401) {
      // Session expired / unauthorized
      try {
        clearToken();
      } catch {
        // ignore
      }

      // Avoid infinite redirect loops
      if (typeof window !== "undefined") {
        const pathname = window.location?.pathname || "";
        if (!pathname.startsWith("/login")) {
          window.location.replace("/login");
        }
      }
    }
    return Promise.reject(err);
  }
);

export function apiErrorMessage(err) {
  return (
    err?.response?.data?.detail ||
    err?.message ||
    "Beklenmeyen bir hata oluştu"
  );
}
