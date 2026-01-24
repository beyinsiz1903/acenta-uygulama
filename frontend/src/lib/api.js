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

// Simple uuid4 fallback for environments without crypto.randomUUID
function generateCorrelationId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback: RFC4122-ish random string
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

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

  // Correlation-Id: her istete client-side bir id ret ve hem header'a hem de config'e yaz
  const cid = generateCorrelationId();
  if (!config.headers) config.headers = {};
  config.headers["X-Correlation-Id"] = cid;
  // axios < v1 iler iin meta alann kendimiz tar
  config.meta = config.meta || {};
  config.meta.correlationId = cid;

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

export function parseErrorDetails(err) {
  const status = err?.response?.status ?? 0;
  const data = err?.response?.data;
  const headers = err?.response?.headers || {};
  const message = apiErrorMessage(err);

  let code = null;
  if (data?.error?.code) code = data.error.code;

  // Correlation id resolution priority
  let correlationId = null;
  if (data?.error?.details?.correlation_id) {
    correlationId = data.error.details.correlation_id;
  } else if (headers["x-correlation-id"]) {
    correlationId = headers["x-correlation-id"];
  } else if (headers["cf-ray"]) {
    correlationId = headers["cf-ray"];
  } else if (err?.config?.meta?.correlationId) {
    correlationId = err.config.meta.correlationId;
  }

  const isRetryable = status === 0 || status >= 500;

  return {
    status,
    code,
    message,
    correlationId,
    isRetryable,
  };
}

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
          const isLogin = current.pathname.startsWith("/login") || current.pathname.startsWith("/b2b/login");
          const hasReason = current.searchParams.get("reason") === "session_expired";

          if (!isLogin || !hasReason) {
            const from = `${pathname}${search}${hash}`;
            const loginPath = pathname.startsWith("/b2b") ? "/b2b/login" : "/login";
            const url = new URL(loginPath, origin);
            url.searchParams.set("reason", "session_expired");
            // For B2B we also pass explicit next parameter
            if (loginPath === "/b2b/login") {
              url.searchParams.set("next", from);
            }
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
  const detail = err?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  // Pydantic/FastAPI validation errors -> array of objects
  if (Array.isArray(detail) && detail.length) {
    const msg = detail
      .map((d) => {
        if (typeof d?.msg === "string") return d.msg;
        if (typeof d === "string") return d;
        try {
          return JSON.stringify(d);
        } catch {
          return "";
        }
      })
      .filter(Boolean)
      .join("; ");
    if (msg) return msg;
  }

  if (detail && typeof detail === "object") {
    if (typeof detail.message === "string") return detail.message;
    try {
      return JSON.stringify(detail);
    } catch {
      // ignore
    }
  }

  return (
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
