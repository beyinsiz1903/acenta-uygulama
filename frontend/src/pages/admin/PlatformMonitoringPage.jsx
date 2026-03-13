import React, { useState, useEffect, useCallback } from "react";
import {
  Activity, Database, Server, Clock, RefreshCw, Loader2,
  Wifi, WifiOff, Play, BarChart3, Gauge, HardDrive,
  TrendingUp, AlertTriangle, CheckCircle, XCircle, Zap,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../../components/ui/table";
import { toast } from "sonner";
import { scalabilityApi } from "../../api/scalability";

function StatusBadge({ status }) {
  if (status === "healthy" || status === "ok" || status === true)
    return <Badge data-testid="status-healthy" className="bg-emerald-100 text-emerald-800 border-emerald-300">Aktif</Badge>;
  if (status === "error" || status === false)
    return <Badge data-testid="status-error" className="bg-red-100 text-red-800 border-red-300">Hata</Badge>;
  return <Badge data-testid="status-unknown" className="bg-gray-100 text-gray-700">Bilinmiyor</Badge>;
}

function MetricCard({ title, value, subtitle, icon: Icon, trend, testId }) {
  return (
    <Card data-testid={testId}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{title}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
          </div>
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
        {trend !== undefined && (
          <div className="flex items-center gap-1 mt-2">
            {trend > 0 ? <TrendingUp className="h-3 w-3 text-emerald-600" /> : <AlertTriangle className="h-3 w-3 text-amber-600" />}
            <span className={`text-xs font-medium ${trend > 0 ? "text-emerald-600" : "text-amber-600"}`}>
              %{Math.abs(trend).toFixed(1)}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ========================= OVERVIEW TAB =========================
function OverviewTab({ data }) {
  if (!data) return null;
  const { cache, last_24h, redis, scheduler } = data;
  return (
    <div className="space-y-6" data-testid="overview-tab">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard title="Arama (24s)" value={last_24h?.searches || 0} icon={BarChart3} testId="metric-searches" />
        <MetricCard title="Rezervasyon (24s)" value={last_24h?.bookings || 0} icon={Zap} testId="metric-bookings" />
        <MetricCard title="Komisyon (24s)" value={last_24h?.commissions || 0} icon={TrendingUp} testId="metric-commissions" />
        <MetricCard title="Uyumsuzluk" value={last_24h?.recon_mismatches || 0} icon={AlertTriangle} testId="metric-mismatches" />
        <MetricCard title="Cache Hit" value={`%${cache?.hit_rate_pct || 0}`} subtitle={`${cache?.hits || 0}/${cache?.total || 0}`} icon={Database} testId="metric-cache-hit" />
        <MetricCard title="Redis" value={redis?.status === "healthy" ? "Aktif" : "Kapalı"} subtitle={redis?.used_memory_human} icon={redis?.status === "healthy" ? Wifi : WifiOff} testId="metric-redis" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card data-testid="scheduler-summary-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4" /> Zamanlanmis Gorevler
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 mb-3">
              <StatusBadge status={scheduler?.running} />
              <span className="text-sm text-muted-foreground">{scheduler?.total_jobs || 0} gorev aktif</span>
            </div>
            <div className="space-y-2">
              {(scheduler?.jobs || []).map(j => (
                <div key={j.id} className="flex items-center justify-between text-xs border-b pb-1">
                  <span className="font-medium">{j.name}</span>
                  <span className="text-muted-foreground">{j.next_run ? new Date(j.next_run).toLocaleString("tr-TR") : "-"}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card data-testid="infrastructure-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Server className="h-4 w-4" /> Altyapi Durumu
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Redis</span>
                <StatusBadge status={redis?.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Job Scheduler</span>
                <StatusBadge status={scheduler?.running} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Baglanti Sayisi</span>
                <span className="text-sm font-medium">{redis?.connected_clients || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Bellek Kullanimi</span>
                <span className="text-sm font-medium">{redis?.used_memory_human || "-"}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ========================= CACHE TAB =========================
function CacheTab({ data }) {
  if (!data) return null;
  const { cache, search_metrics } = data;
  const searchEntries = Object.entries(search_metrics || {});
  return (
    <div className="space-y-6" data-testid="cache-tab">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard title="Cache Hit" value={cache?.hits || 0} icon={CheckCircle} testId="cache-hits" />
        <MetricCard title="Cache Miss" value={cache?.misses || 0} icon={XCircle} testId="cache-misses" />
        <MetricCard title="Toplam" value={cache?.total || 0} icon={Database} testId="cache-total" />
        <MetricCard title="Hit Orani" value={`%${cache?.hit_rate_pct || 0}`} icon={Gauge} testId="cache-hit-rate" />
      </div>
      {searchEntries.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Urun Tipi Bazinda Cache</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Urun Tipi</TableHead>
                  <TableHead className="text-right">Hit</TableHead>
                  <TableHead className="text-right">Miss</TableHead>
                  <TableHead className="text-right">Hit %</TableHead>
                  <TableHead className="text-right">Ort. Latency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {searchEntries.map(([pt, m]) => {
                  const total = (m.cache_hit || 0) + (m.cache_miss || 0);
                  const hitRate = total > 0 ? ((m.cache_hit || 0) / total * 100).toFixed(1) : "0.0";
                  const avgLat = (m.cache_miss || 0) > 0 ? ((m.total_latency_ms || 0) / m.cache_miss).toFixed(0) : "0";
                  return (
                    <TableRow key={pt}>
                      <TableCell className="font-medium capitalize">{pt}</TableCell>
                      <TableCell className="text-right">{m.cache_hit || 0}</TableCell>
                      <TableCell className="text-right">{m.cache_miss || 0}</TableCell>
                      <TableCell className="text-right">%{hitRate}</TableCell>
                      <TableCell className="text-right">{avgLat}ms</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ========================= SUPPLIER METRICS TAB =========================
function SupplierMetricsTab({ data }) {
  const entries = Object.entries(data?.supplier_metrics || {});
  if (entries.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground" data-testid="supplier-metrics-empty">
        Henuz supplier metrigi yok. Arama ve rezervasyon yapildikca veriler burada gorunecek.
      </div>
    );
  }
  return (
    <div className="space-y-4" data-testid="supplier-metrics-tab">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Supplier</TableHead>
            <TableHead className="text-right">Arama</TableHead>
            <TableHead className="text-right">Ort. Latency</TableHead>
            <TableHead className="text-right">Rez. Toplam</TableHead>
            <TableHead className="text-right">Basari</TableHead>
            <TableHead className="text-right">Basarisiz</TableHead>
            <TableHead className="text-right">Basari %</TableHead>
            <TableHead className="text-right">Gelir</TableHead>
            <TableHead className="text-right">Markup</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map(([sc, m]) => {
            const successRate = m.booking_count > 0 ? (m.booking_success / m.booking_count * 100).toFixed(1) : "0.0";
            const avgLatency = m.search_count > 0 ? (m.search_latency_sum / m.search_count).toFixed(0) : "0";
            return (
              <TableRow key={sc}>
                <TableCell className="font-medium capitalize">{sc.replace("real_", "").replace(/_/g, " ")}</TableCell>
                <TableCell className="text-right">{m.search_count}</TableCell>
                <TableCell className="text-right">{avgLatency}ms</TableCell>
                <TableCell className="text-right">{m.booking_count}</TableCell>
                <TableCell className="text-right text-emerald-600">{m.booking_success}</TableCell>
                <TableCell className="text-right text-red-600">{m.booking_fail}</TableCell>
                <TableCell className="text-right">
                  <Badge className={parseFloat(successRate) >= 80 ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}>
                    %{successRate}
                  </Badge>
                </TableCell>
                <TableCell className="text-right font-medium">{m.revenue?.toLocaleString("tr-TR")} TRY</TableCell>
                <TableCell className="text-right">{m.markup?.toLocaleString("tr-TR")} TRY</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

// ========================= SCHEDULER TAB =========================
function SchedulerTab({ data, onTrigger }) {
  const { scheduler } = data || {};
  const jobs = scheduler?.jobs || [];
  const history = scheduler?.history || {};

  return (
    <div className="space-y-6" data-testid="scheduler-tab">
      <div className="flex items-center gap-3 mb-2">
        <StatusBadge status={scheduler?.running} />
        <span className="text-sm text-muted-foreground">{scheduler?.total_jobs || 0} zamanlanmis gorev</span>
      </div>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Aktif Gorevler</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Gorev</TableHead>
                <TableHead>Sonraki Calisma</TableHead>
                <TableHead>Son Calisma</TableHead>
                <TableHead>Durum</TableHead>
                <TableHead className="text-right">Islem</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map(j => {
                const h = history[j.id];
                const lastRun = h?.last_run;
                return (
                  <TableRow key={j.id}>
                    <TableCell className="font-medium">{j.name}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {j.next_run ? new Date(j.next_run).toLocaleString("tr-TR") : "-"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {lastRun?.timestamp ? new Date(lastRun.timestamp).toLocaleString("tr-TR") : "Henuz calismadi"}
                    </TableCell>
                    <TableCell>
                      {lastRun?.status === "success" && <Badge className="bg-emerald-100 text-emerald-800">Basarili</Badge>}
                      {lastRun?.status === "error" && <Badge className="bg-red-100 text-red-800">Hata</Badge>}
                      {!lastRun && <Badge className="bg-gray-100 text-gray-600">Bekliyor</Badge>}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm" variant="outline"
                        data-testid={`trigger-${j.id}`}
                        onClick={() => onTrigger(j.id)}
                      >
                        <Play className="h-3 w-3 mr-1" /> Calistir
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      {Object.keys(history).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Son Calisma Gecmisi</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(history).map(([name, h]) => (
                <div key={name} className="border-b pb-2">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium capitalize">{name.replace(/_/g, " ")}</span>
                    <span className="text-xs text-muted-foreground">{h.total_runs} calisma</span>
                  </div>
                  {(h.recent_runs || []).slice(-3).reverse().map((r, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground ml-4">
                      {r.status === "success" ? <CheckCircle className="h-3 w-3 text-emerald-500" /> : <XCircle className="h-3 w-3 text-red-500" />}
                      <span>{new Date(r.timestamp).toLocaleString("tr-TR")}</span>
                      <span className="truncate max-w-[300px]">{r.details}</span>
                      <span>{r.duration_ms}ms</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ========================= MAIN PAGE =========================
export default function PlatformMonitoringPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("overview");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const d = await scalabilityApi.getMonitoringDashboard();
      setData(d);
    } catch (e) {
      toast.error("Monitoring verileri yuklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleTriggerJob = async (jobId) => {
    try {
      await scalabilityApi.triggerJob(jobId);
      toast.success(`${jobId.replace(/_/g, " ")} baslatildi`);
      setTimeout(loadData, 2000);
    } catch {
      toast.error("Gorev baslatilamadi");
    }
  };

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="platform-monitoring-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Platform Izleme & Operasyon</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Cache, scheduler, supplier metrikleri ve altyapi durumu
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadData} disabled={loading} data-testid="refresh-btn">
          {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <RefreshCw className="h-4 w-4 mr-1" />}
          Yenile
        </Button>
      </div>

      {loading && !data ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList data-testid="monitoring-tabs">
            <TabsTrigger value="overview" data-testid="tab-overview">
              <Activity className="h-3.5 w-3.5 mr-1" /> Genel Bakis
            </TabsTrigger>
            <TabsTrigger value="cache" data-testid="tab-cache">
              <Database className="h-3.5 w-3.5 mr-1" /> Cache
            </TabsTrigger>
            <TabsTrigger value="suppliers" data-testid="tab-suppliers">
              <BarChart3 className="h-3.5 w-3.5 mr-1" /> Supplier Metrikleri
            </TabsTrigger>
            <TabsTrigger value="scheduler" data-testid="tab-scheduler">
              <Clock className="h-3.5 w-3.5 mr-1" /> Zamanlanmis Gorevler
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewTab data={data} />
          </TabsContent>
          <TabsContent value="cache">
            <CacheTab data={data} />
          </TabsContent>
          <TabsContent value="suppliers">
            <SupplierMetricsTab data={data} />
          </TabsContent>
          <TabsContent value="scheduler">
            <SchedulerTab data={data} onTrigger={handleTriggerJob} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
