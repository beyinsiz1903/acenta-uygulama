import React, { useState, useCallback, useEffect } from "react";
import { Calculator, Layers, Tag, Globe, Shield } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { TooltipProvider } from "../components/ui/tooltip";
import { toast } from "sonner";

import { pricingApi } from "./pricing/lib/pricingApi";
import { StatCards } from "./pricing/StatCards";
import { AlertBanner } from "./pricing/AlertBanner";
import { CacheStatsBar } from "./pricing/CacheStatsBar";
import { PricingSimulatorTab } from "./pricing/PricingSimulatorTab";
import { DistributionRulesTab } from "./pricing/DistributionRulesTab";
import { ChannelsTab } from "./pricing/ChannelsTab";
import { PromotionsTab } from "./pricing/PromotionsTab";
import { GuardrailsTab } from "./pricing/GuardrailsTab";

export default function PricingEnginePage() {
  const [stats, setStats] = useState({});
  const [metadata, setMetadata] = useState(null);
  const [activeTab, setActiveTab] = useState("simulator");
  const [cacheStats, setCacheStats] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [showTelemetry, setShowTelemetry] = useState(false);
  const [diagnostics, setDiagnostics] = useState(null);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [alerts, setAlerts] = useState(null);
  const [warmingLoading, setWarmingLoading] = useState({});

  const loadCacheStats = useCallback(() => {
    pricingApi("/cache/stats").then(setCacheStats).catch(() => {});
  }, []);

  const loadTelemetry = useCallback(() => {
    pricingApi("/cache/telemetry").then(setTelemetry).catch(() => {});
  }, []);

  const loadDiagnostics = useCallback(() => {
    pricingApi("/cache/diagnostics").then(setDiagnostics).catch(() => {});
  }, []);

  const loadAlerts = useCallback(() => {
    pricingApi("/cache/alerts").then(setAlerts).catch(() => {});
  }, []);

  useEffect(() => {
    pricingApi("/dashboard").then(setStats).catch(() => {});
    pricingApi("/metadata").then(setMetadata).catch(() => {});
    loadCacheStats();
    loadAlerts();
  }, [loadCacheStats, loadAlerts]);

  const clearCache = async () => {
    await pricingApi("/cache/clear", { method: "POST" });
    toast.success("Pricing cache temizlendi");
    loadCacheStats();
    loadAlerts();
    if (showTelemetry) loadTelemetry();
    if (showDiagnostics) loadDiagnostics();
  };

  const invalidateSupplier = async (supplier) => {
    try {
      const res = await pricingApi(`/cache/invalidate/${supplier}`, { method: "POST" });
      toast.success(`${supplier} cache temizlendi (${res.cleared} entry)`);
      loadCacheStats();
      loadAlerts();
      if (showTelemetry) loadTelemetry();
    } catch {
      toast.error("Invalidation basarisiz");
    }
  };

  const warmSupplier = async (supplier) => {
    setWarmingLoading(prev => ({ ...prev, [supplier]: true }));
    try {
      const res = await pricingApi(`/cache/warm/${supplier}`, { method: "POST" });
      toast.success(`${supplier}: ${res.warmed} rota onbelleklendi`);
      loadCacheStats();
      if (showTelemetry) loadTelemetry();
    } catch {
      toast.error("Cache warming basarisiz");
    }
    setWarmingLoading(prev => ({ ...prev, [supplier]: false }));
  };

  const clearAlerts = async () => {
    await pricingApi("/cache/alerts/clear", { method: "POST" });
    toast.success("Alert gecmisi temizlendi");
    loadAlerts();
  };

  const toggleTelemetry = () => {
    const next = !showTelemetry;
    setShowTelemetry(next);
    if (next) loadTelemetry();
  };

  const toggleDiagnostics = () => {
    const next = !showDiagnostics;
    setShowDiagnostics(next);
    if (next) loadDiagnostics();
  };

  const hasActiveAlerts = alerts?.active_alerts?.length > 0;

  const onSimulated = () => {
    loadCacheStats();
    loadAlerts();
    if (showTelemetry) loadTelemetry();
    if (showDiagnostics) loadDiagnostics();
  };

  return (
    <TooltipProvider>
      <div className="space-y-6" data-testid="pricing-engine-page">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Pricing & Distribution Engine</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Supplier fiyatlarini kanal, acente ve promosyon kurallariyla donusturun
          </p>
        </div>

        <StatCards stats={stats} />

        <AlertBanner alerts={alerts} onClear={clearAlerts} />

        <CacheStatsBar
          cacheStats={cacheStats}
          hasActiveAlerts={hasActiveAlerts}
          showDiagnostics={showDiagnostics}
          showTelemetry={showTelemetry}
          diagnostics={diagnostics}
          telemetry={telemetry}
          warmingLoading={warmingLoading}
          onToggleDiagnostics={toggleDiagnostics}
          onToggleTelemetry={toggleTelemetry}
          onRefreshCache={() => { loadCacheStats(); loadAlerts(); }}
          onClearCache={clearCache}
          onRefreshDiagnostics={loadDiagnostics}
          onWarmSupplier={warmSupplier}
          onInvalidateSupplier={invalidateSupplier}
        />

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="simulator" data-testid="tab-simulator">
              <Calculator className="w-3.5 h-3.5 mr-1.5" /> Simulasyon
            </TabsTrigger>
            <TabsTrigger value="rules" data-testid="tab-rules">
              <Layers className="w-3.5 h-3.5 mr-1.5" /> Kurallar
            </TabsTrigger>
            <TabsTrigger value="channels" data-testid="tab-channels">
              <Globe className="w-3.5 h-3.5 mr-1.5" /> Kanallar
            </TabsTrigger>
            <TabsTrigger value="promotions" data-testid="tab-promotions">
              <Tag className="w-3.5 h-3.5 mr-1.5" /> Promosyonlar
            </TabsTrigger>
            <TabsTrigger value="guardrails" data-testid="tab-guardrails">
              <Shield className="w-3.5 h-3.5 mr-1.5" /> Guardrails
            </TabsTrigger>
          </TabsList>

          <TabsContent value="simulator" className="mt-4">
            <PricingSimulatorTab metadata={metadata} onSimulated={onSimulated} />
          </TabsContent>
          <TabsContent value="rules" className="mt-4">
            <DistributionRulesTab />
          </TabsContent>
          <TabsContent value="channels" className="mt-4">
            <ChannelsTab />
          </TabsContent>
          <TabsContent value="promotions" className="mt-4">
            <PromotionsTab />
          </TabsContent>
          <TabsContent value="guardrails" className="mt-4">
            <GuardrailsTab />
          </TabsContent>
        </Tabs>
      </div>
    </TooltipProvider>
  );
}
