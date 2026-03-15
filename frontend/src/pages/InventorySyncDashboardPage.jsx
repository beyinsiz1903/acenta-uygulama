import React, { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Database, RefreshCw, Search, Loader2, CheckCircle2, XCircle, Clock,
  HardDrive, Layers, ArrowUpDown, Zap, Server, Activity, AlertTriangle,
} from "lucide-react";
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
  if (status === "running") return <Badge variant="outline" className="border-sky-500 text-sky-600" data-testid="sync-running">Running</Badge>;
  if (status === "failed") return <Badge variant="destructive" data-testid="sync-failed">Failed</Badge>;
  return <Badge variant="secondary" data-testid="sync-never">Never</Badge>;
}

export default function InventorySyncDashboardPage() {
  const [syncStatus, setSyncStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [searchResults, setSearchResults] = useState(null);
  const [syncJobs, setSyncJobs] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState({});
  const [searchDest, setSearchDest] = useState("Antalya");
  const [searching, setSearching] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [statusRes, statsRes, jobsRes] = await Promise.all([
        api.get("/inventory/sync/status"),
        api.get("/inventory/stats"),
        api.get("/inventory/sync/jobs?limit=10"),
      ]);
      setSyncStatus(statusRes.data);
      setStats(statsRes.data);
      setSyncJobs(jobsRes.data);
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
              {Object.entries(suppliers).map(([sup, data]) => (
                <TableRow key={sup} data-testid={`supplier-row-${sup}`}>
                  <TableCell className="font-medium capitalize">{sup}</TableCell>
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
              ))}
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
                  </TableRow>
                ))}
                {recentRevals.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
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
                <TableHead>Durum</TableHead>
                <TableHead>Otel</TableHead>
                <TableHead>Fiyat</TableHead>
                <TableHead>Musaitlik</TableHead>
                <TableHead>Sure</TableHead>
                <TableHead>Baslangiц</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job, idx) => (
                <TableRow key={idx} data-testid={`job-row-${idx}`}>
                  <TableCell className="font-medium capitalize">{job.supplier}</TableCell>
                  <TableCell><SyncStatusBadge status={job.status} /></TableCell>
                  <TableCell>{job.records_updated}</TableCell>
                  <TableCell>{job.prices_updated}</TableCell>
                  <TableCell>{job.availability_updated}</TableCell>
                  <TableCell className="font-mono">{job.duration_ms}ms</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {job.started_at ? new Date(job.started_at).toLocaleString("tr-TR") : "-"}
                  </TableCell>
                </TableRow>
              ))}
              {jobs.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground">
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
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
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
