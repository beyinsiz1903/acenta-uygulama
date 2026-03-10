function readBackendEnv() {
  if (typeof window !== "undefined") {
    const runtimeValue =
      window.__ACENTA_BACKEND_URL__ ||
      window.importMetaEnvBackendUrl ||
      "";
    if (runtimeValue) {
      return String(runtimeValue).trim();
    }
  }

  const buildTimeValue =
    (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.REACT_APP_BACKEND_URL) ||
    process.env.REACT_APP_BACKEND_URL ||
    "";

  return String(buildTimeValue).trim();
}

function isLocalHost(hostname) {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function parseUrl(value) {
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

export function getBackendOrigin() {
  const backendEnv = readBackendEnv();
  if (!backendEnv) {
    return "";
  }

  const parsedBackend = parseUrl(backendEnv);
  if (!parsedBackend) {
    return "";
  }

  if (typeof window === "undefined") {
    return parsedBackend.origin;
  }

  const currentOrigin = window.location.origin;
  const currentHost = window.location.hostname;
  const currentIsLocal = isLocalHost(currentHost);
  const backendIsLocal = isLocalHost(parsedBackend.hostname);
  const sameOrigin = parsedBackend.origin === currentOrigin;

  if (sameOrigin || currentIsLocal || backendIsLocal) {
    return parsedBackend.origin;
  }

  return "";
}

export function getApiBaseUrl() {
  const backendOrigin = getBackendOrigin();
  return backendOrigin ? `${backendOrigin}/api` : "/api";
}

export function buildApiUrl(path = "") {
  if (!path) {
    return getApiBaseUrl();
  }

  const normalizedPath = path.startsWith("/api/")
    ? path
    : path.startsWith("/")
      ? `/api${path}`
      : `/api/${path}`;

  const backendOrigin = getBackendOrigin();
  return backendOrigin ? `${backendOrigin}${normalizedPath}` : normalizedPath;
}

export function resolveAssetUrl(src = "") {
  if (!src) {
    return "";
  }

  if (/^https?:\/\//i.test(src) || src.startsWith("data:")) {
    return src;
  }

  if (src.startsWith("/api/")) {
    return buildApiUrl(src);
  }

  if (src.startsWith("/")) {
    const backendOrigin = getBackendOrigin();
    return backendOrigin ? `${backendOrigin}${src}` : src;
  }

  return src;
}