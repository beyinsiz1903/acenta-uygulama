import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { api } from "../lib/api";
import { getActiveTenantId, subscribeTenantChange } from "../lib/tenantContext";

/* ------------------------------------------------------------------ */
/*  Mode ordering                                                       */
/* ------------------------------------------------------------------ */
const MODE_ORDER = { lite: 0, pro: 1, enterprise: 2 };
const DEFAULT_MODE = "enterprise";

const CACHE_KEY = "product_mode_cache";
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

function readCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (Date.now() - parsed.ts > CACHE_TTL) return null;
    return parsed.data;
  } catch {
    return null;
  }
}

function writeCache(data) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ data, ts: Date.now() }));
  } catch { /* localStorage unavailable */ }
}

function clearCache() {
  try { localStorage.removeItem(CACHE_KEY); } catch { /* */ }
}

/* ------------------------------------------------------------------ */
/*  Context                                                             */
/* ------------------------------------------------------------------ */
const ProductModeContext = createContext({
  mode: DEFAULT_MODE,
  loading: true,
  visibleNavGroups: [],
  hiddenNavItems: [],
  labelOverrides: {},
  isAtLeast: () => true,
  isMode: () => false,
  refresh: () => {},
});

export function ProductModeProvider({ children }) {
  const [mode, setMode] = useState(() => {
    const cached = readCache();
    return cached?.product_mode || DEFAULT_MODE;
  });
  const [loading, setLoading] = useState(true);
  const [visibleNavGroups, setVisibleNavGroups] = useState([]);
  const [hiddenNavItems, setHiddenNavItems] = useState([]);
  const [labelOverrides, setLabelOverrides] = useState({});

  const fetchMode = useCallback(async () => {
    // Try cache first
    const cached = readCache();
    if (cached) {
      setMode(cached.product_mode || DEFAULT_MODE);
      setVisibleNavGroups(cached.visible_nav_groups || []);
      setHiddenNavItems(cached.hidden_nav_items || []);
      setLabelOverrides(cached.label_overrides || {});
      setLoading(false);
      return;
    }

    try {
      const res = await api.get("/system/product-mode");
      const data = res.data;
      setMode(data.product_mode || DEFAULT_MODE);
      setVisibleNavGroups(data.visible_nav_groups || []);
      setHiddenNavItems(data.hidden_nav_items || []);
      setLabelOverrides(data.label_overrides || {});
      writeCache(data);
    } catch {
      // Fallback to enterprise on error
      setMode(DEFAULT_MODE);
      setVisibleNavGroups([]);
      setHiddenNavItems([]);
      setLabelOverrides({});
    }
    setLoading(false);
  }, []);

  const refresh = useCallback(() => {
    clearCache();
    setLoading(true);
    fetchMode();
  }, [fetchMode]);

  useEffect(() => {
    fetchMode();
    const unsub = subscribeTenantChange(() => {
      clearCache();
      setLoading(true);
      fetchMode();
    });
    return unsub;
  }, [fetchMode]);

  const isAtLeast = useCallback(
    (requiredMode) => (MODE_ORDER[mode] ?? 2) >= (MODE_ORDER[requiredMode] ?? 0),
    [mode]
  );

  const isMode = useCallback(
    (targetMode) => mode === targetMode,
    [mode]
  );

  const value = useMemo(
    () => ({
      mode,
      loading,
      visibleNavGroups,
      hiddenNavItems,
      labelOverrides,
      isAtLeast,
      isMode,
      refresh,
    }),
    [mode, loading, visibleNavGroups, hiddenNavItems, labelOverrides, isAtLeast, isMode, refresh]
  );

  return (
    <ProductModeContext.Provider value={value}>
      {children}
    </ProductModeContext.Provider>
  );
}

export function useProductMode() {
  return useContext(ProductModeContext);
}

export { MODE_ORDER, DEFAULT_MODE };
