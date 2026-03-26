import axios from "axios";
import { getActiveTenantId } from "./tenantContext";
import { buildApiUrl, getApiBaseUrl } from "./backendUrl";
import {
  clearToken,
  getUser,
  persistRefreshSession,
  setUser,
} from "./authSession";
import { markSessionExpired, rememberPostLoginRedirect } from "./authRedirect";

export { clearToken, getUser, setUser };
const resolvedBaseURL = getApiBaseUrl();

export const api = axios.create({
  baseURL: resolvedBaseURL,
  withCredentials: true,
});

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function isNetworkError(err) {
  return Boolean(
    !err?.response &&
      (String(err?.message || "").toLowerCase().includes("network error") || err?.code === "ERR_NETWORK")
  );
}

async function requestWithNetworkFallback(method, url, options = {}) {
  const attemptPrimary = () => api.request({
    method,
    url,
    ...options,
  });

  try {
    return await attemptPrimary();
  } catch (err) {
    if (!isNetworkError(err)) {
      throw err;
    }

    await sleep(700);

    try {
      return await attemptPrimary();
    } catch (retryErr) {
      if (!isNetworkError(retryErr) || typeof window === "undefined") {
        throw retryErr;
      }

      const fallbackHeaders = {
        "X-Client-Platform": "web",
        ...(options.headers || {}),
      };

      return axios.request({
        method,
        url: buildApiUrl(url),
        withCredentials: true,
        ...options,
        headers: fallbackHeaders,
      });
    }
  }
}

export function apiGetWithNetworkFallback(url, options = {}) {
  return requestWithNetworkFallback("get", url, options);
}

export function apiPostWithNetworkFallback(url, data, options = {}) {
  return requestWithNetworkFallback("post", url, {
    ...options,
    data,
  });
}

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
  if (!config.headers) {
    config.headers = {};
  }

  config.withCredentials = true;
  config.headers["X-Client-Platform"] = "web";

  const url = config.url || "";
  const isAuthRoute =
    url.includes("/auth/login") ||
    url.includes("/auth/register") ||
    url.includes("/auth/refresh");

  if (!isAuthRoute) {
    if (config.headers.Authorization) {
      delete config.headers.Authorization;
    }

    // 1) Tenant header: first try runtime-selected tenant from localStorage,
    // then fall back to a default tenant id provided via env (build-time).
    let tenantId = getActiveTenantId();

    if (!tenantId) {
      // Support both Vite-style and CRA-style env access
      const envDefault =
        (typeof import.meta !== "undefined" &&
          import.meta.env &&
          import.meta.env.REACT_APP_DEFAULT_TENANT_ID) ||
        process.env.REACT_APP_DEFAULT_TENANT_ID;

      if (envDefault) {
        tenantId = envDefault;
        // NOTA: preview/prod ortamlarında multi-user karışıklığı olmaması için
        // artık localStorage'a yazmıyoruz; sadece header'da kullanıyoruz.
      }
    }

    if (tenantId) {
      config.headers["X-Tenant-Id"] = tenantId;
    } else {
      // Final fallback: use organization_id from cached user for tenant-scoped features
      try {
        const cachedUser = getUser();
        if (cachedUser?.organization_id) {
          config.headers["X-Tenant-Id"] = cachedUser.organization_id;
        }
      } catch { /* */ }
    }
  } else if (config.headers && config.headers.Authorization) {
    // Login/register isteklerinde eski token taşınmasın
    delete config.headers.Authorization;
  }

  // Correlation-Id: her istete client-side bir id ret ve hem header'a hem de config'e yaz
  const cid = generateCorrelationId();
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

// Track refresh in progress to avoid multiple simultaneous refreshes
let isRefreshing = false;
let refreshSubscribers = [];

function onRefreshed() {
  refreshSubscribers.forEach(cb => cb());
  refreshSubscribers = [];
}

function addRefreshSubscriber(cb) {
  refreshSubscribers.push(cb);
}

api.interceptors.response.use(
  (resp) => {
    // Auto-unwrap standard { ok, data, meta } envelope from backend middleware
    if (resp.data && typeof resp.data === "object" && "ok" in resp.data && "data" in resp.data) {
      resp.data = resp.data.data;
    }
    return resp;
  },
  async (err) => {
    const originalRequest = err.config;

    if (err?.response?.status === 401 && !originalRequest._retry) {
      const skipAuthRefresh = Boolean(originalRequest?.skipAuthRefresh);
      const skipAuthRedirect = Boolean(originalRequest?.skipAuthRedirect);

      // Skip refresh for login/auth routes and my-booking
      const url = originalRequest?.url || "";
      if (url.includes("/auth/login") || url.includes("/auth/refresh") || url.includes("/auth/register")) {
        return Promise.reject(err);
      }

      const canAttemptRefresh = !skipAuthRefresh && typeof window !== "undefined" && !window.location.pathname.startsWith("/my-booking");
      if (canAttemptRefresh) {
        if (isRefreshing) {
          // Wait for the refresh to complete
          return new Promise((resolve) => {
            addRefreshSubscriber(() => {
              originalRequest.headers = originalRequest.headers || {};
              if (originalRequest.headers.Authorization) {
                delete originalRequest.headers.Authorization;
              }
              resolve(api(originalRequest));
            });
          });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const refreshResp = await axios.post(
            buildApiUrl("/auth/refresh"),
            {},
            {
              headers: {
                "Content-Type": "application/json",
                "X-Client-Platform": "web",
              },
              withCredentials: true,
              skipAuthRefresh: true,
              skipAuthRedirect: true,
            }
          );

          persistRefreshSession(refreshResp.data);

          isRefreshing = false;
          onRefreshed();

          originalRequest.headers = originalRequest.headers || {};
          if (originalRequest.headers.Authorization) {
            delete originalRequest.headers.Authorization;
          }
          return api(originalRequest);
        } catch (refreshErr) {
          isRefreshing = false;
          refreshSubscribers = [];
          // Refresh failed, fall through to normal 401 handling
        }
      }

      // Normal 401 handling (no refresh token or refresh failed)
      if (skipAuthRedirect) {
        return Promise.reject(err);
      }

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
            rememberPostLoginRedirect(from);
            markSessionExpired();
          } else {
            // On login, still keep the flag for UX messaging
            markSessionExpired();
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
  if (isNetworkError(err)) {
    return "Ağ bağlantısı kurulamadı. Sunucu kısa süreli yeniden başlıyor olabilir; lütfen 2-3 saniye sonra tekrar deneyin.";
  }

  const errorPayload = err?.response?.data?.error;
  const detail = err?.response?.data?.detail;

  if (typeof errorPayload?.message === "string" && errorPayload.message.trim()) {
    return errorPayload.message;
  }

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
