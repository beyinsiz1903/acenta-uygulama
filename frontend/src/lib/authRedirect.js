const STORAGE_KEYS = Object.freeze({
  postLoginRedirect: "acenta_post_login_redirect",
  sessionExpired: "acenta_session_expired",
});

function readSessionStorage(key) {
  try {
    return window.sessionStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function writeSessionStorage(key, value) {
  try {
    if (!value) {
      window.sessionStorage.removeItem(key);
      return;
    }
    window.sessionStorage.setItem(key, value);
  } catch {
    // ignore storage errors in preview/private mode
  }
}

function normalizePath(locationOrPath) {
  if (typeof locationOrPath === "string") {
    return locationOrPath;
  }

  if (!locationOrPath) {
    return "";
  }

  return `${locationOrPath.pathname || ""}${locationOrPath.search || ""}${locationOrPath.hash || ""}`;
}

function isAllowedPath(pathname, allowedPrefixes) {
  return allowedPrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function rememberPostLoginRedirect(locationOrPath, options = {}) {
  const { overwrite = false } = options;
  const path = normalizePath(locationOrPath);

  if (!path) {
    return "";
  }

  const existing = readSessionStorage(STORAGE_KEYS.postLoginRedirect);
  if (existing && !overwrite) {
    return existing;
  }

  writeSessionStorage(STORAGE_KEYS.postLoginRedirect, path);
  return path;
}

export function clearPostLoginRedirect() {
  writeSessionStorage(STORAGE_KEYS.postLoginRedirect, "");
}

export function peekPostLoginRedirect(options = {}) {
  const { allowedPrefixes = ["/app"] } = options;
  const path = readSessionStorage(STORAGE_KEYS.postLoginRedirect);

  if (!path || !path.startsWith("/") || !isAllowedPath(path, allowedPrefixes)) {
    return "";
  }

  return path;
}

export function consumePostLoginRedirect(fallbackPath, options = {}) {
  const { clearExpired = true, allowedPrefixes = ["/app"] } = options;
  const redirectPath = peekPostLoginRedirect({ allowedPrefixes }) || fallbackPath;

  clearPostLoginRedirect();
  if (clearExpired) {
    clearSessionExpired();
  }

  return redirectPath;
}

export function markSessionExpired() {
  writeSessionStorage(STORAGE_KEYS.sessionExpired, "1");
}

export function clearSessionExpired() {
  writeSessionStorage(STORAGE_KEYS.sessionExpired, "");
}

export function hasSessionExpired() {
  return readSessionStorage(STORAGE_KEYS.sessionExpired) === "1";
}