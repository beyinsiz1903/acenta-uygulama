export const AUTH_TRANSPORT = Object.freeze({
  COOKIE_COMPAT: "cookie_compat",
  LEGACY_BEARER: "bearer",
});

const STORAGE_KEYS = Object.freeze({
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
  return "";
}

export function setToken(token) {
  return token || "";
}

export function getRefreshToken() {
  return "";
}

export function setRefreshToken(token) {
  return token || "";
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
  return;
}

export function clearToken() {
  clearLegacyTokens();
  removeStorage(STORAGE_KEYS.user);
  removeStorage(STORAGE_KEYS.tenantId);
  removeStorage(STORAGE_KEYS.authTransport);
}

export function hasStoredSessionCandidate() {
  return Boolean(getUser() || readStorage(STORAGE_KEYS.tenantId) || isCookieAuthTransport(getAuthTransport()));
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
  setAuthTransport(AUTH_TRANSPORT.COOKIE_COMPAT);
  return user;
}

export function persistLoginSession(payload) {
  const transport = payload?.auth_transport
    ? normalizeAuthTransport(payload.auth_transport)
    : AUTH_TRANSPORT.COOKIE_COMPAT;
  setAuthTransport(transport);
  if (payload?.user) {
    setUser(payload.user);
  }

  const tenantId = payload?.tenant_id || payload?.user?.tenant_id || payload?.user?.organization_id;
  if (tenantId) {
    writeStorage(STORAGE_KEYS.tenantId, tenantId);
  }

  clearLegacyTokens();
  return transport;
}

export function persistRefreshSession(payload) {
  const transport = payload?.auth_transport
    ? normalizeAuthTransport(payload.auth_transport)
    : AUTH_TRANSPORT.COOKIE_COMPAT;
  setAuthTransport(transport);

  clearLegacyTokens();
  return transport;
}