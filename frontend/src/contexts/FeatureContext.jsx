import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { api } from "../lib/api";
import { getActiveTenantId, subscribeTenantChange } from "../lib/tenantContext";

const FeatureContext = createContext({
  features: [],
  loading: true,
  hasFeature: () => false,
  quotaAlerts: [],
});

export function FeatureProvider({ children }) {
  const [features, setFeatures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [quotaAlerts, setQuotaAlerts] = useState([]);

  const fetchFeatures = useCallback(async () => {
    const tenantId = getActiveTenantId();
    if (!tenantId) {
      setFeatures([]);
      setQuotaAlerts([]);
      setLoading(false);
      return;
    }
    try {
      const res = await api.get("/tenant/features");
      setFeatures(res.data?.features || []);
    } catch {
      setFeatures([]);
    }

    // Best-effort quota fetch
    try {
      const qRes = await api.get("/tenant/quota-status");
      const alerts = (qRes.data?.quotas || []).filter((q) => q.ratio >= 0.8);
      setQuotaAlerts(alerts);
    } catch {
      setQuotaAlerts([]);
    }

    setLoading(false);
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
    () => ({ features, loading, hasFeature, quotaAlerts }),
    [features, loading, hasFeature, quotaAlerts],
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
