import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { api } from "../lib/api";
import { getActiveTenantId, subscribeTenantChange } from "../lib/tenantContext";

const FeatureContext = createContext({
  features: [],
  loading: true,
  hasFeature: () => false,
});

export function FeatureProvider({ children }) {
  const [features, setFeatures] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchFeatures = useCallback(async () => {
    const tenantId = getActiveTenantId();
    if (!tenantId) {
      setFeatures([]);
      setLoading(false);
      return;
    }
    try {
      const res = await api.get("/tenant/features");
      setFeatures(res.data?.features || []);
    } catch {
      setFeatures([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFeatures();
    const unsub = subscribeTenantChange(() => {
      setLoading(true);
      fetchFeatures();
    });
    return unsub;
  }, [fetchFeatures]);

  const hasFeature = useCallback(
    (key) => features.includes(key),
    [features],
  );

  const value = useMemo(
    () => ({ features, loading, hasFeature }),
    [features, loading, hasFeature],
  );

  return (
    <FeatureContext.Provider value={value}>
      {children}
    </FeatureContext.Provider>
  );
}

export function useFeatures() {
  return useContext(FeatureContext);
}
