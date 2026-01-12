import axios from "axios";

// Backend base URL: prefer REACT_APP_BACKEND_URL from env, fallback to same-origin /api
// This prevents broken URLs like "undefined/api" when env is not set in certain environments.
const backendEnv =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.REACT_APP_BACKEND_URL)
    || process.env.REACT_APP_BACKEND_URL
    || "";

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

// If backendEnv is empty, axios will call relative to current origin.
// Ayrıca: Eğer REACT_APP_BACKEND_URL localhost'u gösteriyor ama uygulama
// başka bir hosttan (örn. preview/prod domain) çalışıyorsa, bu değeri yok
// sayıp aynı origin /api üzerinden çağrı yaparız.
let resolvedBaseURL = "/api";
if (backendEnv) {
  const isBrowser = typeof window !== "undefined";
  if (isBrowser) {
    const host = window.location.hostname;
    const backendIsLocalhost = backendEnv.includes("://localhost") || backendEnv.includes("://127.0.0.1");
    const originIsLocalhost = host === "localhost" || host === "127.0.0.1";
    if (!backendIsLocalhost || originIsLocalhost) {
      resolvedBaseURL = `${backendEnv}/api`;
    }
  } else {
    // Node/test ortamında env'i doğrudan kullan
    resolvedBaseURL = `${backendEnv}/api`;
  }
}

export const api = axios.create({
  baseURL: resolvedBaseURL,
});

api.interceptors.request.use((config) => {
  const url = config.url || "";
  const isAuthRoute =
    url.includes("/auth/login") ||
    url.includes("/auth/register") ||
    url.includes("/auth/refresh");

  if (!isAuthRoute) {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } else if (config.headers && config.headers.Authorization) {
    // Login/register isteklerinde eski token taşınmasın
    delete config.headers.Authorization;
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
      try {
        if (typeof window !== "undefined") {
          const { pathname, search, hash, origin } = window.location;

          // Public routes (my-booking) must never redirect to login on 401
          if (pathname.startsWith("/my-booking")) {
            return Promise.reject(err);
          }

          // 1) return-to: only set when not already on /login and do not overwrite existing
          if (!pathname.startsWith("/login")) {
            const from = `${pathname}${search}${hash}`;
            const existing = window.sessionStorage.getItem("acenta_post_login_redirect");
            if (!existing) {
              window.sessionStorage.setItem("acenta_post_login_redirect", from);
            }
            window.sessionStorage.setItem("acenta_session_expired", "1");
          } else {
            // On login, still keep the flag for UX messaging
            window.sessionStorage.setItem("acenta_session_expired", "1");
          }

          // 2) Token cleanup
          try {
            clearToken();
          } catch {
            // ignore
          }

          // 3) Normalize login URL with reason parameter
          const current = new URL(window.location.href);
          const isLogin = current.pathname.startsWith("/login");
          const hasReason = current.searchParams.get("reason") === "session_expired";

          if (!isLogin || !hasReason) {
            const url = new URL("/login", origin);
            url.searchParams.set("reason", "session_expired");
            window.location.replace(url.toString());
          }
        }
      } catch {
        // ignore any navigation/storage errors
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

// SCALE v1: approval tasks helpers
export async function getApprovalTasks(params = {}) {
  const search = new URLSearchParams();
  const status = params.status || "pending";
  const limit = params.limit || 50;
  if (status) search.set("status", status);
  if (limit) search.set("limit", String(limit));
  const res = await api.get(`/admin/approval-tasks?${search.toString()}`);
  return res.data;
}

export async function approveApprovalTask(id, body = {}) {
  const res = await api.post(`/admin/approval-tasks/${id}/approve`, body);
  return res.data;
}

export async function rejectApprovalTask(id, body = {}) {
  const res = await api.post(`/admin/approval-tasks/${id}/reject`, body);
  return res.data;
}

// Demo harness: SCALE UI proof helpers
export async function runScaleUIProof(matchId) {
  const payload = matchId ? { match_id: matchId } : {};
  const res = await api.post("/admin/demo/scale-ui-proof/run", payload);
  return res.data;
}

export async function approveScaleUIProof(taskId, note) {
  const payload = { task_id: taskId };
  if (note) payload.note = note;
  const res = await api.post("/admin/demo/scale-ui-proof/approve", payload);
  return res.data;
}
