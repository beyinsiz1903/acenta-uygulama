// frontend/src/lib/tenantContext.js
// Tek kaynaklı tenant anahtarı helper'ı + custom event yayıncısı

const STORAGE_KEY = "acenta_tenant_key";
const EVENT_NAME = "acenta:tenant-changed";

export function getActiveTenantKey() {
  try {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(STORAGE_KEY) || null;
  } catch {
    return null;
  }
}

export function setActiveTenantKey(tenantKey, extra = {}) {
  try {
    if (typeof window === "undefined") return;
    const key = tenantKey || "";
    window.localStorage.setItem(STORAGE_KEY, key);
    const detail = {
      tenantKey: key || null,
      tenantId: extra.tenantId || null,
      orgId: extra.orgId || null,
    };
    window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail }));
  } catch {
    // sessizce yut; kritik değil
  }
}

export function subscribeTenantChange(callback) {
  if (typeof window === "undefined") {
    return () => {};
  }
  const handler = (event) => {
    try {
      callback(event.detail || {});
    } catch {
      // callback içi hatalar UI'ı bozmasın
    }
  };
  window.addEventListener(EVENT_NAME, handler);
  return () => window.removeEventListener(EVENT_NAME, handler);
}

export const TENANT_EVENT_NAME = EVENT_NAME;
