export const AUTH_TRANSPORT = Object.freeze({
  COOKIE_COMPAT: "cookie_compat",
  LEGACY_BEARER: "bearer",
});

const STORAGE_KEYS = Object.freeze({
  accessToken: "acenta_token",
  refreshToken: "acenta_refresh_token",
  user: "acenta_user",
  tenantId: "acenta_tenant_id",
  authTransport: "acenta_auth_transport",
});

function readStorage(key) {
  try {
    return window.localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function writeStorage(key, value) {
  try {
    if (!value) {
      window.localStorage.removeItem(key);
      return;
    }
    window.localStorage.setItem(key, value);
  } catch {
    // ignore storage errors in preview/private mode
  }
}

function removeStorage(key) {
  try {
    window.localStorage.removeItem(key);
  } catch {
    // ignore storage errors in preview/private mode
  }
}

export function normalizeAuthTransport(value) {
  return value === AUTH_TRANSPORT.COOKIE_COMPAT
    ? AUTH_TRANSPORT.COOKIE_COMPAT
    : AUTH_TRANSPORT.LEGACY_BEARER;
}

export function isCookieAuthTransport(value) {
  return normalizeAuthTransport(value) === AUTH_TRANSPORT.COOKIE_COMPAT;
}

export function getToken() {
  return readStorage(STORAGE_KEYS.accessToken);
}

export function setToken(token) {
  writeStorage(STORAGE_KEYS.accessToken, token || "");
}

export function getRefreshToken() {
  return readStorage(STORAGE_KEYS.refreshToken);
}

export function setRefreshToken(token) {
  writeStorage(STORAGE_KEYS.refreshToken, token || "");
}

export function getUser() {
  try {
    const raw = readStorage(STORAGE_KEYS.user);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setUser(user) {
  if (!user) {
    removeStorage(STORAGE_KEYS.user);
    return;
  }
  writeStorage(STORAGE_KEYS.user, JSON.stringify(user));
}

export function getAuthTransport() {
  return normalizeAuthTransport(readStorage(STORAGE_KEYS.authTransport));
}

export function setAuthTransport(transport) {
  writeStorage(STORAGE_KEYS.authTransport, normalizeAuthTransport(transport));
}

export function clearLegacyTokens() {
  removeStorage(STORAGE_KEYS.accessToken);
  removeStorage(STORAGE_KEYS.refreshToken);
}

export function clearToken() {
  clearLegacyTokens();
  removeStorage(STORAGE_KEYS.user);
  removeStorage(STORAGE_KEYS.tenantId);
  removeStorage(STORAGE_KEYS.authTransport);
}

export function hasStoredSessionCandidate() {
  return Boolean(getToken() || getRefreshToken() || getUser() || isCookieAuthTransport(getAuthTransport()));
}

export function persistBootstrappedUser(user) {
  if (!user) {
    return null;
  }
  setUser(user);
  const tenantId = user.tenant_id || user.organization_id;
  if (tenantId) {
    writeStorage(STORAGE_KEYS.tenantId, tenantId);
  }
  if (!readStorage(STORAGE_KEYS.authTransport)) {
    setAuthTransport(getToken() ? AUTH_TRANSPORT.LEGACY_BEARER : AUTH_TRANSPORT.COOKIE_COMPAT);
  }
  return user;
}

export function persistLoginSession(payload) {
  const transport = normalizeAuthTransport(payload?.auth_transport);
  setAuthTransport(transport);
  if (payload?.user) {
    setUser(payload.user);
  }

  const tenantId = payload?.tenant_id || payload?.user?.tenant_id || payload?.user?.organization_id;
  if (tenantId) {
    writeStorage(STORAGE_KEYS.tenantId, tenantId);
  }

  if (isCookieAuthTransport(transport)) {
    clearLegacyTokens();
    return transport;
  }

  if (payload?.access_token) {
    setToken(payload.access_token);
  }
  if (payload?.refresh_token) {
    setRefreshToken(payload.refresh_token);
  }
  return transport;
}

export function persistRefreshSession(payload) {
  const transport = normalizeAuthTransport(payload?.auth_transport || getAuthTransport());
  setAuthTransport(transport);

  if (isCookieAuthTransport(transport)) {
    clearLegacyTokens();
    return transport;
  }

  if (payload?.access_token) {
    setToken(payload.access_token);
  }
  if (payload?.refresh_token) {
    setRefreshToken(payload.refresh_token);
  }
  return transport;
}