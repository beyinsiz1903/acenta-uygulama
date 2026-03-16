import React, { useEffect, useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Database, RefreshCw, Search, Loader2, CheckCircle2, XCircle, Clock,
  HardDrive, Layers, ArrowUpDown, Zap, Server, Activity, AlertTriangle,
  Settings, Shield, Play, Trash2, Eye, EyeOff, Heart, TrendingUp,
  BarChart3, Target,
} from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, BarChart, Bar, Cell,
} from "recharts";
import { api } from "../lib/api";

function StatCard({ title, value, subtitle, icon: Icon, variant = "default", testId }) {
  const colors = {
    default: "text-foreground",
    success: "text-emerald-500",
    warning: "text-amber-500",
    danger: "text-red-500",
    info: "text-sky-500",
  };
  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${colors[variant]}`}>{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

function SeverityBadge({ severity }) {
  const map = {
    normal: { label: "Normal", variant: "outline", className: "border-emerald-500 text-emerald-600" },
    warning: { label: "Warning", variant: "outline", className: "border-amber-500 text-amber-600" },
    high: { label: "High", variant: "outline", className: "border-orange-500 text-orange-600" },
    critical: { label: "Critical", variant: "destructive", className: "" },
  };
  const cfg = map[severity] || map.normal;
  return <Badge variant={cfg.variant} className={cfg.className} data-testid={`severity-${severity}`}>{cfg.label}</Badge>;
}

function SyncStatusBadge({ status }) {
  if (status === "completed") return <Badge variant="outline" className="border-emerald-500 text-emerald-600" data-testid="sync-completed">Completed</Badge>;
  if (status === "completed_with_partial_errors") return <Badge variant="outline" className="border-amber-500 text-amber-600" data-testid="sync-partial">Partial Errors</Badge>;
  if (status === "completed_with_errors") return <Badge variant="outline" className="border-amber-500 text-amber-600" data-testid="sync-partial">Partial</Badge>;
  if (status === "running") return <Badge variant="outline" className="border-sky-500 text-sky-600" data-testid="sync-running">Running</Badge>;
  if (status === "pending") return <Badge variant="outline" className="border-slate-400 text-slate-500" data-testid="sync-pending">Pending</Badge>;
  if (status === "failed") return <Badge variant="destructive" data-testid="sync-failed">Failed</Badge>;
  if (status === "retry_scheduled") return <Badge variant="outline" className="border-violet-500 text-violet-600" data-testid="sync-retry">Retry</Badge>;
  if (status === "stuck") return <Badge variant="outline" className="border-red-400 text-red-500 bg-red-500/10" data-testid="sync-stuck">Stuck</Badge>;
  if (status === "cancelled") return <Badge variant="secondary" data-testid="sync-cancelled">Cancelled</Badge>;
  return <Badge variant="secondary" data-testid="sync-never">Never</Badge>;
}

function SandboxModeBadge({ mode, configured }) {
  if (!configured) return <Badge variant="secondary" data-testid="mode-simulation">Simulation</Badge>;
  if (mode === "sandbox") return <Badge variant="outline" className="border-sky-500 text-sky-600 bg-sky-500/10" data-testid="mode-sandbox">Sandbox</Badge>;
  if (mode === "production") return <Badge variant="outline" className="border-emerald-500 text-emerald-600 bg-emerald-500/10" data-testid="mode-production">Production</Badge>;
  return <Badge variant="secondary" data-testid="mode-unknown">{mode}</Badge>;
}

function ValidationStatusBadge({ status }) {
  if (status === "pass") return <Badge variant="outline" className="border-emerald-500 text-emerald-600" data-testid="validation-pass">PASS</Badge>;
  if (status === "partial") return <Badge variant="outline" className="border-amber-500 text-amber-600" data-testid="validation-partial">Partial</Badge>;
  if (status === "fail") return <Badge variant="destructive" data-testid="validation-fail">FAIL</Badge>;
  if (status === "pending") return <Badge variant="outline" className="border-sky-500 text-sky-600" data-testid="validation-pending">Bekliyor</Badge>;
  return <Badge variant="secondary" data-testid="validation-none">Tanimlanmamis</Badge>;
}

function HealthStatusBadge({ status }) {
  if (status === "healthy") return <Badge variant="outline" className="border-emerald-500 text-emerald-600 bg-emerald-500/10" data-testid="health-healthy">Healthy</Badge>;
  if (status === "degraded") return <Badge variant="outline" className="border-amber-500 text-amber-600 bg-amber-500/10" data-testid="health-degraded">Degraded</Badge>;
  if (status === "down") return <Badge variant="destructive" data-testid="health-down">Down</Badge>;
  return <Badge variant="secondary" data-testid="health-unknown">{status || "Unknown"}</Badge>;
}

export default function InventorySyncDashboardPage() {
  const [syncStatus, setSyncStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [searchResults, setSearchResults] = useState(null);
  const [syncJobs, setSyncJobs] = useState(null);
  const [supplierConfigs, setSupplierConfigs] = useState({});
  const [validationResult, setValidationResult] = useState(null);
  const [supplierHealth, setSupplierHealth] = useState(null);
  const [kpiData, setKpiData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState({});
  const [searchDest, setSearchDest] = useState("Antalya");
  const [searching, setSearching] = useState(false);
  const [validating, setValidating] = useState(false);
  const [showConfigForm, setShowConfigForm] = useState(false);
  const [configForm, setConfigForm] = useState({
    supplier: "ratehawk",
    base_url: "https://api-sandbox.worldota.net",
    key_id: "",
    api_key: "",
    mode: "sandbox",
  });
  const [savingConfig, setSavingConfig] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [bookingTestResult, setBookingTestResult] = useState(null);
  const [bookingTestRunning, setBookingTestRunning] = useState({});
  const [bookingTestHistory, setBookingTestHistory] = useState(null);
  const [stabilityReport, setStabilityReport] = useState(null);
  const [regionStatus, setRegionStatus] = useState({});
  const [retryingJob, setRetryingJob] = useState({});
  const [retryingRegion, setRetryingRegion] = useState({});
  const [cancellingJob, setCancellingJob] = useState({});

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, statsRes, jobsRes, configRes, healthRes, kpiRes, stabilityRes] = await Promise.all([
        api.get("/inventory/sync/status"),
        api.get("/inventory/stats"),
        api.get("/inventory/sync/jobs?limit=10"),
        api.get("/inventory/supplier-config"),
        api.get("/inventory/supplier-health"),
        api.get("/inventory/kpi/drift"),
        api.get("/inventory/sync/stability-report"),
      ]);
      setSyncStatus(statusRes.data);
      setStats(statsRes.data);
      setSyncJobs(jobsRes.data);
      setSupplierConfigs(configRes.data?.suppliers || {});
      setSupplierHealth(healthRes.data?.suppliers || {});
      setKpiData(kpiRes.data);
      setStabilityReport(stabilityRes.data);

      // Fetch region status for all suppliers
      const regionPromises = ["ratehawk", "paximum", "wwtatil", "tbo"].map(async (sup) => {
        try {
          const res = await api.get(`/inventory/sync/regions/${sup}`);
          return [sup, res.data];
        } catch { return [sup, null]; }
      });
      const regionResults = await Promise.all(regionPromises);
      const regionMap = {};
      regionResults.forEach(([sup, data]) => { if (data) regionMap[sup] = data; });
      setRegionStatus(regionMap);
    } catch (err) {
      console.error("Inventory data fetch failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const triggerSync = async (supplier) => {
    setSyncing((prev) => ({ ...prev, [supplier]: true }));
    try {
      await api.post("/inventory/sync/trigger", { supplier });
      await fetchData();
    } catch (err) {
      console.error("Sync trigger failed:", err);
    } finally {
      setSyncing((prev) => ({ ...prev, [supplier]: false }));
    }
  };

  const doSearch = async () => {
    if (!searchDest.trim()) return;
    setSearching(true);
    try {
      const res = await api.get(`/inventory/search?destination=${encodeURIComponent(searchDest)}&min_stars=0&limit=15`);
      setSearchResults(res.data);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setSearching(false);
    }
  };

  const saveSupplierConfig = async () => {
    if (!configForm.key_id || !configForm.api_key) return;
    setSavingConfig(true);
    try {
      await api.post("/inventory/supplier-config", configForm);
      setShowConfigForm(false);
      setConfigForm((prev) => ({ ...prev, key_id: "", api_key: "" }));
      await fetchData();
    } catch (err) {
      console.error("Config save failed:", err);
    } finally {
      setSavingConfig(false);
    }
  };

  const removeConfig = async (supplier) => {
    try {
      await api.delete(`/inventory/supplier-config/${supplier}`);
      await fetchData();
    } catch (err) {
      console.error("Config remove failed:", err);
    }
  };

  const runValidation = async (supplier) => {
    setValidating(true);
    setValidationResult(null);
    try {
      const res = await api.post("/inventory/sandbox/validate", { supplier });
      setValidationResult(res.data);
      await fetchData();
    } catch (err) {
      console.error("Validation failed:", err);
    } finally {
      setValidating(false);
    }
  };

  const runBookingTest = async (supplier) => {
    setBookingTestRunning((prev) => ({ ...prev, [supplier]: true }));
    setBookingTestResult(null);
    try {
      const res = await api.post("/inventory/booking/test", { supplier });
      setBookingTestResult(res.data);
    } catch (err) {
      console.error("Booking test failed:", err);
    } finally {
      setBookingTestRunning((prev) => ({ ...prev, [supplier]: false }));
    }
  };

  const fetchTestHistory = async () => {
    try {
      const res = await api.get("/inventory/booking/test/history?limit=10");
      setBookingTestHistory(res.data);
    } catch (err) {
      console.error("Test history fetch failed:", err);
    }
  };

  const retryJob = async (jobId) => {
    setRetryingJob((prev) => ({ ...prev, [jobId]: true }));
    try {
      await api.post(`/inventory/sync/retry/${jobId}`);
      await fetchData();
    } catch (err) {
      console.error("Job retry failed:", err);
    } finally {
      setRetryingJob((prev) => ({ ...prev, [jobId]: false }));
    }
  };

  const retryRegion = async (supplier, regionId) => {
    const key = `${supplier}_${regionId}`;
    setRetryingRegion((prev) => ({ ...prev, [key]: true }));
    try {
      await api.post(`/inventory/sync/retry-region/${supplier}/${regionId}`);
      await fetchData();
    } catch (err) {
      console.error("Region retry failed:", err);
    } finally {
      setRetryingRegion((prev) => ({ ...prev, [key]: false }));
    }
  };

  const cancelJob = async (jobId) => {
    setCancellingJob((prev) => ({ ...prev, [jobId]: true }));
    try {
      await api.post(`/inventory/sync/cancel/${jobId}`);
      await fetchData();
    } catch (err) {
      console.error("Job cancel failed:", err);
    } finally {
      setCancellingJob((prev) => ({ ...prev, [jobId]: false }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="inventory-loading">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">Inventory verileri yukleniyor...</span>
      </div>
    );
  }

  const totals = stats?.totals || {};
  const suppliers = syncStatus?.suppliers || {};
  const cities = stats?.by_city || {};
  const recentRevals = stats?.recent_revalidations || [];
  const redisCache = stats?.redis_cache || {};
  const jobs = syncJobs?.jobs || [];

  return (
    <div className="space-y-6 p-6" data-testid="inventory-sync-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" data-testid="page-title">Inventory Sync Engine</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Travel Inventory Platform - Supplier Sync &amp; Cached Search
          </p>
        </div>
        <Button variant="outline" onClick={fetchData} data-testid="refresh-btn">
          <RefreshCw className="h-4 w-4 mr-2" /> Yenile
        </Button>
      </div>

      {/* Overview KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4" data-testid="kpi-grid">
        <StatCard title="Toplam Otel" value={totals.hotels || 0} icon={HardDrive} testId="kpi-hotels" />
        <StatCard title="Fiyat Kaydi" value={totals.prices || 0} icon={Layers} testId="kpi-prices" />
        <StatCard title="Musaitlik" value={totals.availability || 0} icon={Activity} testId="kpi-availability" />
        <StatCard title="Search Index" value={totals.search_index || 0} icon={Search} variant="info" testId="kpi-index" />
        <StatCard title="Sync Jobs" value={totals.sync_jobs || 0} icon={RefreshCw} testId="kpi-jobs" />
        <StatCard
          title="Redis Cache"
          value={redisCache.status === "connected" ? redisCache.cached_entries : redisCache.status}
          icon={Zap}
          variant={redisCache.status === "connected" ? "success" : "warning"}
          testId="kpi-redis"
        />
      </div>

      {/* Sandbox Configuration Panel */}
      <Card data-testid="sandbox-config-panel">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Shield className="h-5 w-5" /> Sandbox Konfigurasyon
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowConfigForm(!showConfigForm)}
              data-testid="toggle-config-form-btn"
            >
              <Settings className="h-4 w-4 mr-1" />
              {showConfigForm ? "Kapat" : "Credential Ekle"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Supplier Config Status Table */}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Supplier</TableHead>
                <TableHead>Mod</TableHead>
                <TableHead>Durum</TableHead>
                <TableHead>Validasyon</TableHead>
                <TableHead>Base URL</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(supplierConfigs).map(([sup, cfg]) => (
                <TableRow key={sup} data-testid={`config-row-${sup}`}>
                  <TableCell className="font-medium capitalize">{sup}</TableCell>
                  <TableCell>
                    <SandboxModeBadge mode={cfg.mode} configured={cfg.configured} />
                  </TableCell>
                  <TableCell>
                    {cfg.configured ? (
                      <span className="flex items-center gap-1 text-emerald-600 text-sm">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Tanimli
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-muted-foreground text-sm">
                        <XCircle className="h-3.5 w-3.5" /> Tanimlanmamis
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <ValidationStatusBadge status={cfg.validation_status} />
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground font-mono">
                    {cfg.base_url || "-"}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {cfg.configured && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => runValidation(sup)}
                            disabled={validating}
                            data-testid={`validate-btn-${sup}`}
                          >
                            {validating ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                            <span className="ml-1">Test</span>
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-red-500 hover:text-red-700"
                            onClick={() => removeConfig(sup)}
                            data-testid={`remove-config-btn-${sup}`}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Config Form */}
          {showConfigForm && (
            <div className="border rounded-lg p-4 mt-4 space-y-4 bg-muted/30" data-testid="config-form">
              <h3 className="text-sm font-semibold">Supplier Credential Tanimla</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="config-supplier">Supplier</Label>
                  <select
                    id="config-supplier"
                    className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                    value={configForm.supplier}
                    onChange={(e) => setConfigForm((p) => ({ ...p, supplier: e.target.value }))}
                    data-testid="config-supplier-select"
                  >
                    <option value="ratehawk">Ratehawk</option>
                    <option value="paximum">Paximum</option>
                    <option value="wwtatil">WWTatil</option>
                    <option value="tbo">TBO</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="config-mode">Mod</Label>
                  <select
                    id="config-mode"
                    className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                    value={configForm.mode}
                    onChange={(e) => setConfigForm((p) => ({ ...p, mode: e.target.value }))}
                    data-testid="config-mode-select"
                  >
                    <option value="sandbox">Sandbox</option>
                    <option value="production">Production</option>
                  </select>
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="config-base-url">Base URL</Label>
                  <Input
                    id="config-base-url"
                    value={configForm.base_url}
                    onChange={(e) => setConfigForm((p) => ({ ...p, base_url: e.target.value }))}
                    placeholder="https://api-sandbox.worldota.net"
                    data-testid="config-base-url-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="config-key-id">Key ID</Label>
                  <Input
                    id="config-key-id"
                    value={configForm.key_id}
                    onChange={(e) => setConfigForm((p) => ({ ...p, key_id: e.target.value }))}
                    placeholder="Supplier Key ID"
                    data-testid="config-key-id-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="config-api-key">API Key</Label>
                  <div className="relative">
                    <Input
                      id="config-api-key"
                      type={showApiKey ? "text" : "password"}
                      value={configForm.api_key}
                      onChange={(e) => setConfigForm((p) => ({ ...p, api_key: e.target.value }))}
                      placeholder="Supplier API Key"
                      className="pr-10"
                      data-testid="config-api-key-input"
                    />
                    <button
                      type="button"
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      onClick={() => setShowApiKey(!showApiKey)}
                    >
                      {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </div>
              <div className="flex gap-2 pt-2">
                <Button onClick={saveSupplierConfig} disabled={savingConfig || !configForm.key_id || !configForm.api_key} data-testid="save-config-btn">
                  {savingConfig ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Shield className="h-4 w-4 mr-1" />}
                  Kaydet
                </Button>
                <Button variant="ghost" onClick={() => setShowConfigForm(false)}>Iptal</Button>
              </div>
            </div>
          )}

          {/* Validation Result */}
          {validationResult && (
            <div className="border rounded-lg p-4 mt-4 space-y-3" data-testid="validation-result">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">
                  Sandbox Validasyon Sonucu — <span className="capitalize">{validationResult.supplier}</span>
                </h3>
                <Badge
                  variant={validationResult.status === "pass" ? "outline" : validationResult.status === "partial" ? "outline" : "destructive"}
                  className={validationResult.status === "pass" ? "border-emerald-500 text-emerald-600" : validationResult.status === "partial" ? "border-amber-500 text-amber-600" : ""}
                  data-testid="validation-overall-status"
                >
                  {validationResult.tests_passed}/{validationResult.tests_total} PASS
                </Badge>
              </div>
              {validationResult.status === "not_configured" ? (
                <p className="text-sm text-amber-600">{validationResult.message}</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Test</TableHead>
                      <TableHead>Aciklama</TableHead>
                      <TableHead>Sonuc</TableHead>
                      <TableHead>Latency</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {validationResult.tests?.map((t, i) => (
                      <TableRow key={i} data-testid={`validation-test-${i}`}>
                        <TableCell className="font-mono text-xs">{t.test}</TableCell>
                        <TableCell className="text-sm">{t.description}</TableCell>
                        <TableCell>
                          {t.passed ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-red-500" />
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-xs">
                          {t.latency_ms ? `${t.latency_ms}ms` : "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Supplier Health Panel */}
      <Card data-testid="supplier-health-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Heart className="h-5 w-5" /> Supplier Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Supplier</TableHead>
                <TableHead>Durum</TableHead>
                <TableHead>Avg Latency</TableHead>
                <TableHead>Error Rate</TableHead>
                <TableHead>Success Rate</TableHead>
                <TableHead>Availability Rate</TableHead>
                <TableHead>Son Sync</TableHead>
                <TableHead>Son Validasyon</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {supplierHealth && Object.entries(supplierHealth).map(([sup, h]) => (
                <TableRow key={sup} data-testid={`health-row-${sup}`}>
                  <TableCell className="font-medium capitalize">{sup}</TableCell>
                  <TableCell>
                    <HealthStatusBadge status={h.status} />
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {h.latency_avg ? `${h.latency_avg}ms` : "-"}
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    <span className={h.error_rate > 3 ? "text-red-500" : h.error_rate > 0 ? "text-amber-500" : "text-emerald-500"}>
                      {h.error_rate}%
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    <span className={h.success_rate >= 95 ? "text-emerald-500" : h.success_rate >= 80 ? "text-amber-500" : "text-red-500"}>
                      {h.success_rate}%
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{h.availability_rate}%</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {h.last_sync ? new Date(h.last_sync).toLocaleString("tr-TR") : "-"}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {h.last_validation ? new Date(h.last_validation).toLocaleString("tr-TR") : "-"}
                  </TableCell>
                </TableRow>
              ))}
              {(!supplierHealth || Object.keys(supplierHealth).length === 0) && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground">Supplier health verisi yok</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Sync Stability Dashboard — P4.2 */}
      {stabilityReport && (
        <Card data-testid="stability-dashboard-panel">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Shield className="h-5 w-5" /> Sync Stability
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-xs">{stabilityReport.period}</Badge>
                <span className={`text-lg font-bold ${stabilityReport.success_rate >= 95 ? "text-emerald-500" : stabilityReport.success_rate >= 80 ? "text-amber-500" : "text-red-500"}`}>
                  {stabilityReport.success_rate}%
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Stability KPI Row */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="stability-kpis">
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <div className="text-xs text-muted-foreground">Completed</div>
                <div className="text-xl font-bold text-emerald-600">{stabilityReport.job_breakdown?.completed || 0}</div>
              </div>
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <div className="text-xs text-muted-foreground">Partial Errors</div>
                <div className="text-xl font-bold text-amber-600">{stabilityReport.job_breakdown?.partial_errors || 0}</div>
              </div>
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <div className="text-xs text-muted-foreground">Failed</div>
                <div className="text-xl font-bold text-red-600">{stabilityReport.job_breakdown?.failed || 0}</div>
              </div>
              <div className="p-3 rounded-lg bg-violet-500/10 border border-violet-500/20">
                <div className="text-xs text-muted-foreground">Retry Scheduled</div>
                <div className="text-xl font-bold text-violet-600">{stabilityReport.job_breakdown?.retry_scheduled || 0}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-500/10 border border-slate-500/20">
                <div className="text-xs text-muted-foreground">Stuck</div>
                <div className="text-xl font-bold text-slate-600">{stabilityReport.job_breakdown?.stuck || 0}</div>
              </div>
            </div>

            {/* Avg / Max Duration */}
            <div className="flex items-center gap-6 text-sm">
              <span className="text-muted-foreground">Toplam Jobs: <strong className="text-foreground">{stabilityReport.total_jobs}</strong></span>
              <span className="text-muted-foreground">Avg Duration: <strong className="text-foreground font-mono">{stabilityReport.avg_duration_ms}ms</strong></span>
              <span className="text-muted-foreground">Max Duration: <strong className="text-foreground font-mono">{stabilityReport.max_duration_ms}ms</strong></span>
              {stabilityReport.retry_effectiveness && (
                <span className="text-muted-foreground">
                  Retry Success: <strong className={`font-mono ${stabilityReport.retry_effectiveness.retry_success_rate >= 80 ? "text-emerald-500" : "text-amber-500"}`}>
                    {stabilityReport.retry_effectiveness.retry_success_rate}%
                  </strong>
                  <span className="text-xs ml-1">({stabilityReport.retry_effectiveness.retries_succeeded}/{stabilityReport.retry_effectiveness.total_retries})</span>
                </span>
              )}
            </div>

            {/* Per-Supplier Circuit Breaker Status */}
            <div>
              <h3 className="text-sm font-semibold mb-3">Supplier Durumu & Circuit Breaker</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Supplier</TableHead>
                    <TableHead>Jobs (24h)</TableHead>
                    <TableHead>Success Rate</TableHead>
                    <TableHead>Circuit</TableHead>
                    <TableHead>Downtime</TableHead>
                    <TableHead>Cache</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(stabilityReport.supplier_breakdown || {}).map(([sup, data]) => (
                    <TableRow key={sup} data-testid={`stability-supplier-${sup}`}>
                      <TableCell className="font-medium capitalize">{sup}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {data.total_jobs_24h}
                        {data.partial_errors > 0 && <span className="text-amber-500 ml-1">({data.partial_errors} partial)</span>}
                        {data.failed > 0 && <span className="text-red-500 ml-1">({data.failed} fail)</span>}
                      </TableCell>
                      <TableCell>
                        <span className={`font-mono text-sm ${data.success_rate >= 95 ? "text-emerald-500" : data.success_rate >= 80 ? "text-amber-500" : "text-red-500"}`}>
                          {data.success_rate}%
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            data.circuit_state === "closed" ? "border-emerald-500 text-emerald-600" :
                            data.circuit_state === "half_open" ? "border-amber-500 text-amber-600" :
                            "border-red-500 text-red-600"
                          }
                          data-testid={`circuit-${sup}`}
                        >
                          {data.circuit_state}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {data.is_down ? (
                          <span className="flex items-center gap-1 text-red-500 text-sm">
                            <XCircle className="h-3.5 w-3.5" /> Down
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-emerald-500 text-sm">
                            <CheckCircle2 className="h-3.5 w-3.5" /> Up
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm">{data.stale_cache_entries} entries</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Region Sync Status (per supplier) */}
            <div>
              <h3 className="text-sm font-semibold mb-3">Region Sync Durumu</h3>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {Object.entries(regionStatus).map(([sup, data]) => (
                  <div key={sup} className="border rounded-lg p-4" data-testid={`region-panel-${sup}`}>
                    <h4 className="text-sm font-medium capitalize mb-2">{sup} — {data.total_regions} Region</h4>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Region</TableHead>
                          <TableHead>Otel</TableHead>
                          <TableHead>Durum</TableHead>
                          <TableHead></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(data.regions || []).map((r) => {
                          const retryKey = `${sup}_${r.region_id}`;
                          return (
                            <TableRow key={r.region_id} data-testid={`region-row-${sup}-${r.region_id}`}>
                              <TableCell className="text-sm">{r.name} <span className="text-xs text-muted-foreground">({r.country})</span></TableCell>
                              <TableCell className="font-mono text-sm">{r.hotel_count}</TableCell>
                              <TableCell>
                                <SyncStatusBadge status={r.last_sync_status} />
                              </TableCell>
                              <TableCell>
                                {(r.last_sync_status === "failed" || r.last_sync_status === "never" || r.errors > 0) && (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => retryRegion(sup, r.region_id)}
                                    disabled={retryingRegion[retryKey]}
                                    data-testid={`retry-region-${sup}-${r.region_id}`}
                                  >
                                    {retryingRegion[retryKey] ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                                    <span className="ml-1 text-xs">Retry</span>
                                  </Button>
                                )}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* E2E Booking Test Panel */}
      <Card data-testid="booking-test-panel">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Play className="h-5 w-5" /> E2E Booking Test
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchTestHistory}
              data-testid="fetch-test-history-btn"
            >
              <Clock className="h-4 w-4 mr-1" /> Gecmis
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">
            Search &rarr; Detail &rarr; Revalidation &rarr; Booking &rarr; Status Check &rarr; Cancel
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2" data-testid="booking-test-triggers">
            {["ratehawk", "paximum", "tbo", "wwtatil"].map((sup) => (
              <Button
                key={sup}
                size="sm"
                variant={bookingTestRunning[sup] ? "secondary" : "outline"}
                onClick={() => runBookingTest(sup)}
                disabled={bookingTestRunning[sup]}
                data-testid={`booking-test-btn-${sup}`}
              >
                {bookingTestRunning[sup] ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                ) : (
                  <Play className="h-3.5 w-3.5 mr-1.5" />
                )}
                <span className="capitalize">{sup}</span>
              </Button>
            ))}
          </div>

          {/* Active Test Result */}
          {bookingTestResult && (
            <div className="border rounded-lg p-4 space-y-3" data-testid="booking-test-result">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">
                  E2E Test — <span className="capitalize">{bookingTestResult.supplier}</span>
                  <Badge variant="outline" className="ml-2 text-xs">
                    {bookingTestResult.mode}
                  </Badge>
                </h3>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground font-mono">
                    {bookingTestResult.duration_ms}ms
                  </span>
                  <Badge
                    variant={bookingTestResult.status === "passed" ? "outline" : "destructive"}
                    className={bookingTestResult.status === "passed" ? "border-emerald-500 text-emerald-600" : ""}
                    data-testid="booking-test-overall-status"
                  >
                    {bookingTestResult.summary?.passed}/{bookingTestResult.summary?.total} PASS
                  </Badge>
                </div>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Adim</TableHead>
                    <TableHead>Durum</TableHead>
                    <TableHead>Sure</TableHead>
                    <TableHead>Detay</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bookingTestResult.steps?.map((step, i) => (
                    <TableRow key={i} data-testid={`booking-step-${step.name}`}>
                      <TableCell className="font-mono text-xs capitalize">{step.name}</TableCell>
                      <TableCell>
                        {step.status === "passed" ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        ) : step.status === "skipped" ? (
                          <Clock className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{step.duration_ms}ms</TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-xs truncate">
                        {step.error || (step.details ? Object.entries(step.details).filter(([, v]) => v !== null).map(([k, v]) => `${k}: ${v}`).join(", ") : "-")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="text-xs text-muted-foreground flex items-center gap-4">
                <span>trace: <code className="font-mono">{bookingTestResult.trace_id?.slice(0, 12)}...</code></span>
                <span>test params: {bookingTestResult.test_params?.destination} ({bookingTestResult.test_params?.checkin} ~ {bookingTestResult.test_params?.checkout})</span>
              </div>
            </div>
          )}

          {/* Test History */}
          {bookingTestHistory && (
            <div className="border rounded-lg p-4 space-y-3" data-testid="booking-test-history">
              <h3 className="text-sm font-semibold">Test Gecmisi ({bookingTestHistory.total})</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Supplier</TableHead>
                    <TableHead>Mod</TableHead>
                    <TableHead>Sonuc</TableHead>
                    <TableHead>Adimlar</TableHead>
                    <TableHead>Sure</TableHead>
                    <TableHead>Tarih</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bookingTestHistory.tests?.map((test, i) => (
                    <TableRow key={i} data-testid={`test-history-row-${i}`}>
                      <TableCell className="font-medium capitalize">{test.supplier}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">{test.mode}</Badge>
                      </TableCell>
                      <TableCell>
                        {test.status === "passed" ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {test.summary?.passed}/{test.summary?.total}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{test.duration_ms}ms</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {test.timestamp ? new Date(test.timestamp).toLocaleString("tr-TR") : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* KPI Dashboard */}
      {kpiData && (
        <div className="space-y-6" data-testid="kpi-dashboard">
          {/* KPI Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card data-testid="kpi-drift-rate">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">Drift Rate</CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${kpiData.drift_rate > 5 ? "text-red-500" : kpiData.drift_rate > 2 ? "text-amber-500" : "text-emerald-500"}`}>
                  {kpiData.drift_rate}%
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {kpiData.drifted_count} / {kpiData.total_revalidations} revalidation
                </p>
              </CardContent>
            </Card>
            <Card data-testid="kpi-price-consistency">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">Price Consistency</CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${kpiData.price_consistency >= 0.95 ? "text-emerald-500" : kpiData.price_consistency >= 0.9 ? "text-amber-500" : "text-red-500"}`}>
                  {(kpiData.price_consistency * 100).toFixed(1)}%
                </div>
                <p className="text-xs text-muted-foreground mt-1">1 - drift_rate</p>
              </CardContent>
            </Card>
            <Card data-testid="kpi-total-revals">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">Revalidasyonlar</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{kpiData.total_revalidations}</div>
                <p className="text-xs text-muted-foreground mt-1">Toplam kontrol sayisi</p>
              </CardContent>
            </Card>
            <Card data-testid="kpi-drifted-count">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium text-muted-foreground">Sapma Sayisi</CardTitle>
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${kpiData.drifted_count > 0 ? "text-amber-500" : "text-emerald-500"}`}>
                  {kpiData.drifted_count}
                </div>
                <p className="text-xs text-muted-foreground mt-1">drift &gt; 2%</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Drift Severity Breakdown */}
            <Card data-testid="kpi-severity-breakdown">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-5 w-5" /> Drift Severity Dagilimi
                </CardTitle>
              </CardHeader>
              <CardContent>
                {Object.keys(kpiData.severity_breakdown || {}).length > 0 ? (
                  <>
                    <div className="h-48 mb-4">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={Object.entries(kpiData.severity_breakdown).map(([sup, sev]) => ({
                          supplier: sup,
                          normal: sev.normal || 0,
                          warning: sev.warning || 0,
                          high: sev.high || 0,
                          critical: sev.critical || 0,
                        }))}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                          <XAxis dataKey="supplier" tick={{ fontSize: 12 }} />
                          <YAxis tick={{ fontSize: 12 }} />
                          <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} />
                          <Legend wrapperStyle={{ fontSize: "12px" }} />
                          <Bar dataKey="normal" name="Normal (0-2%)" fill="#10b981" stackId="a" />
                          <Bar dataKey="warning" name="Warning (2-5%)" fill="#f59e0b" stackId="a" />
                          <Bar dataKey="high" name="High (5-10%)" fill="#f97316" stackId="a" />
                          <Bar dataKey="critical" name="Critical (10%+)" fill="#ef4444" stackId="a" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Supplier</TableHead>
                          <TableHead>Normal</TableHead>
                          <TableHead>Warning</TableHead>
                          <TableHead>High</TableHead>
                          <TableHead>Critical</TableHead>
                          <TableHead>Drift Rate</TableHead>
                          <TableHead>Consistency</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Object.entries(kpiData.severity_breakdown).map(([sup, sev]) => {
                          const dr = kpiData.supplier_drift_rates?.[sup] || {};
                          return (
                            <TableRow key={sup} data-testid={`severity-row-${sup}`}>
                              <TableCell className="font-medium capitalize">{sup}</TableCell>
                              <TableCell><span className="text-emerald-500 font-mono">{sev.normal || 0}</span></TableCell>
                              <TableCell><span className="text-amber-500 font-mono">{sev.warning || 0}</span></TableCell>
                              <TableCell><span className="text-orange-500 font-mono">{sev.high || 0}</span></TableCell>
                              <TableCell><span className="text-red-500 font-mono">{sev.critical || 0}</span></TableCell>
                              <TableCell className="font-mono">{dr.drift_rate || 0}%</TableCell>
                              <TableCell className="font-mono">{dr.price_consistency ? (dr.price_consistency * 100).toFixed(1) + "%" : "-"}</TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-6">Severity verisi yok — once revalidation calistirin</p>
                )}
              </CardContent>
            </Card>

            {/* Price Drift Timeline */}
            <Card data-testid="kpi-drift-timeline">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <TrendingUp className="h-5 w-5" /> Price Drift Timeline
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(kpiData.price_drift_timeline || []).length > 0 ? (
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={(kpiData.price_drift_timeline || []).map((p, i) => ({
                        idx: i + 1,
                        diff_pct: p.diff_pct,
                        supplier: p.supplier,
                        severity: p.severity,
                        time: p.timestamp ? new Date(p.timestamp).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }) : `${i}`,
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                        <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 11 }} label={{ value: "Diff %", angle: -90, position: "insideLeft", style: { fontSize: 11 } }} />
                        <Tooltip
                          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                          formatter={(value, name) => [`${value}%`, name]}
                          labelFormatter={(label) => `Zaman: ${label}`}
                        />
                        <Legend wrapperStyle={{ fontSize: "12px" }} />
                        {/* Reference lines for severity thresholds */}
                        <Line
                          type="monotone"
                          dataKey="diff_pct"
                          name="Fiyat Farki"
                          stroke="#3b82f6"
                          strokeWidth={2}
                          dot={(props) => {
                            const { cx, cy, payload } = props;
                            const colors = { normal: "#10b981", warning: "#f59e0b", high: "#f97316", critical: "#ef4444" };
                            const color = colors[payload.severity] || "#3b82f6";
                            return <circle cx={cx} cy={cy} r={4} fill={color} stroke={color} />;
                          }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-6">Timeline verisi yok — once revalidation calistirin</p>
                )}
                <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> 0-2% Normal</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500 inline-block" /> 2-5% Warning</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500 inline-block" /> 5-10% High</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> 10%+ Critical</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Supplier Sync Status */}
      <Card data-testid="supplier-sync-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Server className="h-5 w-5" /> Supplier Sync Durumu
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Supplier</TableHead>
                <TableHead>Mod</TableHead>
                <TableHead>Durum</TableHead>
                <TableHead>Sync Araligi</TableHead>
                <TableHead>Otel</TableHead>
                <TableHead>Fiyat</TableHead>
                <TableHead>Index</TableHead>
                <TableHead>Son Sync</TableHead>
                <TableHead>Sure</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(suppliers).map(([sup, data]) => {
                const cfg = supplierConfigs[sup] || {};
                return (
                  <TableRow key={sup} data-testid={`supplier-row-${sup}`}>
                    <TableCell className="font-medium capitalize">{sup}</TableCell>
                    <TableCell>
                      <SandboxModeBadge mode={cfg.mode} configured={cfg.configured} />
                    </TableCell>
                    <TableCell>
                      <SyncStatusBadge status={data.last_sync?.status} />
                    </TableCell>
                    <TableCell>{data.config?.sync_interval_minutes} dk</TableCell>
                    <TableCell>{data.inventory?.hotels || 0}</TableCell>
                    <TableCell>{data.inventory?.prices || 0}</TableCell>
                    <TableCell>{data.inventory?.search_index || 0}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {data.last_sync?.started_at
                        ? new Date(data.last_sync.started_at).toLocaleString("tr-TR")
                        : "-"}
                    </TableCell>
                    <TableCell>{data.last_sync?.duration_ms ? `${data.last_sync.duration_ms}ms` : "-"}</TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => triggerSync(sup)}
                        disabled={syncing[sup] || data.config?.status === "pending"}
                        data-testid={`sync-btn-${sup}`}
                      >
                        {syncing[sup] ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                        <span className="ml-1">Sync</span>
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Cached Search Test */}
      <Card data-testid="search-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Search className="h-5 w-5" /> Cached Search (Supplier API Yok)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              value={searchDest}
              onChange={(e) => setSearchDest(e.target.value)}
              placeholder="Destinasyon (ornek: Antalya, Dubai, Istanbul)"
              className="max-w-sm"
              data-testid="search-input"
            />
            <Button onClick={doSearch} disabled={searching} data-testid="search-btn">
              {searching ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Search className="h-4 w-4 mr-1" />}
              Ara
            </Button>
          </div>

          {searchResults && (
            <div data-testid="search-results">
              <div className="flex items-center gap-4 mb-3 text-sm text-muted-foreground">
                <span>Sonuc: <strong className="text-foreground">{searchResults.total}</strong></span>
                <span>Kaynak: <Badge variant="outline" data-testid="search-source">{searchResults.source}</Badge></span>
                <span>Latency: <strong className="text-foreground">{searchResults.latency_ms}ms</strong></span>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Supplier</TableHead>
                    <TableHead>Otel</TableHead>
                    <TableHead>Sehir</TableHead>
                    <TableHead>Yildiz</TableHead>
                    <TableHead>Fiyat</TableHead>
                    <TableHead>Musait</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {searchResults.results?.map((r, idx) => (
                    <TableRow key={idx} data-testid={`search-result-${idx}`}>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">{r.supplier}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{r.name}</TableCell>
                      <TableCell>{r.city}</TableCell>
                      <TableCell>{"*".repeat(r.stars || 0)}</TableCell>
                      <TableCell className="font-mono">{r.min_price} {r.currency}</TableCell>
                      <TableCell>
                        {r.available
                          ? <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          : <XCircle className="h-4 w-4 text-red-500" />}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* City Breakdown */}
        <Card data-testid="city-breakdown">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-5 w-5" /> Sehir Bazli Envanter
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Sehir</TableHead>
                  <TableHead>Otel</TableHead>
                  <TableHead>Ort. Fiyat</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(cities).map(([city, data]) => (
                  <TableRow key={city}>
                    <TableCell className="font-medium">{city}</TableCell>
                    <TableCell>{data.hotels}</TableCell>
                    <TableCell className="font-mono">{data.avg_price} EUR</TableCell>
                  </TableRow>
                ))}
                {Object.keys(cities).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center text-muted-foreground">
                      Envanter bos - once sync calistirin
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Recent Revalidations */}
        <Card data-testid="revalidations-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ArrowUpDown className="h-5 w-5" /> Son Fiyat Revalidasyonlari
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Supplier</TableHead>
                  <TableHead>Cache</TableHead>
                  <TableHead>Reval</TableHead>
                  <TableHead>Diff</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Kaynak</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentRevals.map((rv, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="capitalize">{rv.supplier}</TableCell>
                    <TableCell className="font-mono">{rv.cached_price} {rv.currency}</TableCell>
                    <TableCell className="font-mono">{rv.revalidated_price} {rv.currency}</TableCell>
                    <TableCell className={`font-mono ${rv.diff_pct > 0 ? "text-red-500" : rv.diff_pct < 0 ? "text-emerald-500" : ""}`}>
                      {rv.diff_pct > 0 ? "+" : ""}{rv.diff_pct}%
                    </TableCell>
                    <TableCell><SeverityBadge severity={rv.drift_severity} /></TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">{rv.source || "simulation"}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
                {recentRevals.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground">
                      Revalidasyon kaydi yok
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* Sync Job History */}
      <Card data-testid="sync-jobs-panel">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Clock className="h-5 w-5" /> Sync Job Gecmisi
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Supplier</TableHead>
                <TableHead>Mod</TableHead>
                <TableHead>Durum</TableHead>
                <TableHead>Basarili</TableHead>
                <TableHead>Basarisiz</TableHead>
                <TableHead>Fiyat</TableHead>
                <TableHead>Sure</TableHead>
                <TableHead>Retry</TableHead>
                <TableHead>Baslangic</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job, idx) => (
                <TableRow key={idx} data-testid={`job-row-${idx}`}>
                  <TableCell className="font-medium capitalize">{job.supplier}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs">{job.sync_mode || "simulation"}</Badge>
                  </TableCell>
                  <TableCell><SyncStatusBadge status={job.status} /></TableCell>
                  <TableCell className="font-mono text-sm">{job.records_succeeded ?? job.records_updated ?? 0}</TableCell>
                  <TableCell className="font-mono text-sm">
                    {(job.records_failed || 0) > 0 ? (
                      <span className="text-red-500">{job.records_failed}</span>
                    ) : "0"}
                  </TableCell>
                  <TableCell className="font-mono text-sm">{job.prices_updated || 0}</TableCell>
                  <TableCell className="font-mono text-sm">{job.duration_ms}ms</TableCell>
                  <TableCell className="font-mono text-xs">{job.retry_count || 0}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {job.started_at ? new Date(job.started_at).toLocaleString("tr-TR") : "-"}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      {["failed", "completed_with_partial_errors", "stuck"].includes(job.status) && job._id && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => retryJob(job._id || job.job_id)}
                          disabled={retryingJob[job._id || job.job_id]}
                          data-testid={`retry-job-${idx}`}
                        >
                          {retryingJob[job._id || job.job_id] ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                        </Button>
                      )}
                      {["failed", "retry_scheduled", "stuck", "pending"].includes(job.status) && job._id && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-500 hover:text-red-700"
                          onClick={() => cancelJob(job._id || job.job_id)}
                          disabled={cancellingJob[job._id || job.job_id]}
                          data-testid={`cancel-job-${idx}`}
                        >
                          <XCircle className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {jobs.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} className="text-center text-muted-foreground">
                    Sync job gecmisi bos
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Architecture Info */}
      <Card data-testid="architecture-info">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertTriangle className="h-5 w-5 text-amber-500" /> Mimari Bilgi
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="font-medium mb-1">Search Flow</p>
              <p className="text-muted-foreground">search &rarr; Redis/Mongo cache</p>
              <p className="text-muted-foreground">Supplier API cagrilmaz</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="font-medium mb-1">Booking Flow</p>
              <p className="text-muted-foreground">cache &rarr; supplier revalidation</p>
              <p className="text-muted-foreground">supplier_response_diff olculur</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="font-medium mb-1">Sync Flow</p>
              <p className="text-muted-foreground">supplier &rarr; MongoDB &rarr; Redis</p>
              <p className="text-muted-foreground">Periyodik guncelleme</p>
            </div>
            <div className="p-3 rounded-lg bg-sky-500/10 border border-sky-500/30">
              <p className="font-medium mb-1 text-sky-600">Sandbox Mode</p>
              <p className="text-muted-foreground">Credential &rarr; real API</p>
              <p className="text-muted-foreground">Config yoksa &rarr; simulation</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
