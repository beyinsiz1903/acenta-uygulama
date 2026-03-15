import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import {
  Activity, AlertTriangle, CheckCircle2, Clock, Loader2, Search, ShoppingCart,
  FileText, RefreshCw, Users, TrendingUp, Zap, XCircle, BarChart3, Play, Timer,
  ArrowUpDown, TrendingDown, ArrowUp, ArrowDown,
} from "lucide-react";
import { api } from "../lib/api";
import { useNavigate } from "react-router-dom";

function MetricCard({ title, value, subtitle, icon: Icon, variant = "default", testId }) {
  const colorMap = {
    default: "text-foreground",
    success: "text-emerald-600",
    warning: "text-amber-600",
    danger: "text-red-600",
  };
  return (
    <Card data-testid={testId}>
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${colorMap[variant]}`}>{value}</div>
        {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

function IncidentsPanel({ incidents }) {
  if (!incidents || incidents.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground text-sm" data-testid="no-incidents">
        Olay kaydi bulunamadi
      </div>
    );
  }
  return (
    <Table data-testid="incidents-table">
      <TableHeader>
        <TableRow>
          <TableHead>Zaman</TableHead>
          <TableHead>Acenta</TableHead>
          <TableHead>Adim</TableHead>
          <TableHead>Flow Stage</TableHead>
          <TableHead>Supplier</TableHead>
          <TableHead>Severity</TableHead>
          <TableHead>Retry</TableHead>
          <TableHead>Durum</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {incidents.map((inc, idx) => (
          <TableRow key={idx}>
            <TableCell className="text-xs">{new Date(inc.timestamp).toLocaleString("tr-TR")}</TableCell>
            <TableCell className="font-medium text-sm">{inc.agency_name}</TableCell>
            <TableCell className="text-sm">{inc.step}</TableCell>
            <TableCell className="text-sm">{inc.flow_stage || "-"}</TableCell>
            <TableCell className="text-sm">{inc.supplier || "-"}</TableCell>
            <TableCell>
              <Badge variant={inc.severity === "critical" ? "destructive" : "secondary"} className="text-xs">
                {inc.severity}
              </Badge>
            </TableCell>
            <TableCell className="text-sm">{inc.retry_count ?? 0}</TableCell>
            <TableCell>
              <Badge variant="outline" className="text-xs">{inc.status}</Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function SimulationResultsTable({ results }) {
  if (!results) return null;
  const diffSummary = results.supplier_response_diff_summary || {};
  return (
    <Card data-testid="simulation-results-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Play className="h-4 w-4" />
          Simulation Sonuclari ({results.passed}/{results.total_flows} PASS)
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 grid-cols-2 md:grid-cols-5 text-sm">
          <div className="bg-emerald-500/10 rounded-md p-3 text-center">
            <div className="text-2xl font-bold text-emerald-600">{results.passed}</div>
            <div className="text-xs text-muted-foreground">PASS</div>
          </div>
          <div className="bg-red-500/10 rounded-md p-3 text-center">
            <div className="text-2xl font-bold text-red-600">{results.failed}</div>
            <div className="text-xs text-muted-foreground">FAIL</div>
          </div>
          <div className="bg-primary/10 rounded-md p-3 text-center">
            <div className="text-2xl font-bold text-primary">{results.success_rate}%</div>
            <div className="text-xs text-muted-foreground">Basari Orani</div>
          </div>
          <div className="bg-muted rounded-md p-3 text-center">
            <div className="text-2xl font-bold">{results.avg_flow_duration_ms} ms</div>
            <div className="text-xs text-muted-foreground">Ort. Akis Suresi</div>
          </div>
          <div className={`rounded-md p-3 text-center ${(diffSummary.alert_count ?? 0) > 0 ? "bg-red-500/10" : "bg-emerald-500/10"}`} data-testid="sim-diff-summary">
            <div className={`text-2xl font-bold ${(diffSummary.alert_count ?? 0) > 0 ? "text-red-600" : "text-emerald-600"}`}>
              {diffSummary.avg_diff_pct ?? 0}%
            </div>
            <div className="text-xs text-muted-foreground">Ort. Fiyat Farki</div>
          </div>
        </div>

        <Table data-testid="simulation-flows-table">
          <TableHeader>
            <TableRow>
              <TableHead>Flow</TableHead>
              <TableHead>Acenta</TableHead>
              <TableHead>Sonuc</TableHead>
              <TableHead>Sure (ms)</TableHead>
              <TableHead>Supplier</TableHead>
              <TableHead>Fiyat Diff (%)</TableHead>
              <TableHead>Zaman</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.flows.map((f) => {
              const fd = f.supplier_response_diff || {};
              return (
                <TableRow key={f.flow_num}>
                  <TableCell className="font-mono font-bold">{f.flow_num}</TableCell>
                  <TableCell className="text-sm">{f.agency_name}</TableCell>
                  <TableCell>
                    <Badge variant={f.result === "PASS" ? "default" : "destructive"} className="text-xs" data-testid={`flow-${f.flow_num}-result`}>
                      {f.result === "PASS" ? <CheckCircle2 className="h-3 w-3 mr-1 inline" /> : <XCircle className="h-3 w-3 mr-1 inline" />}
                      {f.result}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{f.duration_ms}</TableCell>
                  <TableCell className="text-sm">{f.supplier}</TableCell>
                  <TableCell>
                    <span className={`font-mono text-sm ${Math.abs(fd.diff_pct ?? 0) > 5 ? "text-red-600 font-bold" : fd.diff_pct > 0 ? "text-amber-600" : "text-emerald-600"}`}>
                      {(fd.diff_pct ?? 0) > 0 ? "+" : ""}{(fd.diff_pct ?? 0).toFixed(2)}%
                    </span>
                  </TableCell>
                  <TableCell className="text-xs">{new Date(f.timestamp).toLocaleTimeString("tr-TR")}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export default function PilotOnboardingDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [metrics, setMetrics] = useState(null);
  const [agencies, setAgencies] = useState(null);
  const [simRunning, setSimRunning] = useState(false);
  const [simResults, setSimResults] = useState(null);
  const navigate = useNavigate();

  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      const [metricsRes, agenciesRes] = await Promise.all([
        api.get("/pilot/onboarding/metrics"),
        api.get("/pilot/onboarding/agencies"),
      ]);
      setMetrics(metricsRes.data);
      setAgencies(agenciesRes.data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Veri yuklenemedi");
    } finally {
      setLoading(false);
    }
  };

  const runSimulation = async () => {
    setSimRunning(true);
    setSimResults(null);
    try {
      const resp = await api.post("/pilot/onboarding/run-simulation", {
        count: 10,
        supplier_type: "ratehawk",
        accounting_provider: "luca",
      });
      setSimResults(resp.data);
      // Refresh metrics after simulation
      fetchData();
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Simulasyon basarisiz");
    } finally {
      setSimRunning(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="loading-state">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !metrics) {
    return (
      <div className="text-center py-16 space-y-3" data-testid="error-state">
        <AlertTriangle className="h-10 w-10 text-muted-foreground mx-auto" />
        <p className="text-sm font-medium">{error}</p>
        <Button variant="outline" onClick={fetchData}>Tekrar Dene</Button>
      </div>
    );
  }

  const fh = metrics?.flow_health || {};
  const sm = metrics?.supplier_metrics || {};
  const fm = metrics?.finance_metrics || {};
  const ph = metrics?.platform_health || {};
  const ff = metrics?.financial_flow || {};
  const pu = metrics?.pilot_usage || {};
  const im = metrics?.incident_monitoring || {};
  const srd = metrics?.supplier_response_diff || {};
  const simDiffSummary = simResults?.supplier_response_diff_summary || {};

  return (
    <div className="space-y-6" data-testid="pilot-onboarding-dashboard">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground" data-testid="dashboard-title">Pilot Onboarding Dashboard</h1>
            <Badge variant="outline" className="text-xs">MEGA PROMPT #35</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Pilot acenta akis dogrulamasi ve operasyon gorunurlugu
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchData} data-testid="refresh-btn">
            <RefreshCw className="h-4 w-4 mr-1" /> Yenile
          </Button>
          <Button size="sm" variant="default" onClick={runSimulation} disabled={simRunning} data-testid="run-simulation-btn">
            {simRunning ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Play className="h-4 w-4 mr-1" />}
            {simRunning ? "Simulasyon calisiyor..." : "10 Akis Calistir"}
          </Button>
          <Button size="sm" variant="outline" onClick={() => navigate("/app/admin/pilot-wizard")} data-testid="new-agency-btn">
            <Users className="h-4 w-4 mr-1" /> Yeni Pilot Acenta
          </Button>
        </div>
      </div>

      {/* Simulation Results */}
      {simResults && <SimulationResultsTable results={simResults} />}

      {/* Flow Health - CTO'nun istegi */}
      <div>
        <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <Activity className="h-4 w-4" /> Flow Health
        </h2>
        <div className="grid gap-4 grid-cols-1 md:grid-cols-3" data-testid="flow-health-section">
          <MetricCard
            title="Flow Basari Orani"
            value={`${fh.flow_success_rate ?? 0}%`}
            subtitle={`Toplam: ${fh.total_flows ?? 0} akis`}
            icon={CheckCircle2}
            variant={fh.flow_success_rate >= 95 ? "success" : fh.flow_success_rate >= 80 ? "warning" : "danger"}
            testId="flow-success-rate-card"
          />
          <MetricCard
            title="Ort. Akis Suresi"
            value={`${fh.avg_flow_duration_ms ?? 0} ms`}
            icon={Timer}
            variant={fh.avg_flow_duration_ms <= 5000 ? "success" : "warning"}
            testId="avg-flow-duration-card"
          />
          <MetricCard
            title="Basarisiz Akislar"
            value={fh.failed_flows ?? 0}
            icon={XCircle}
            variant={fh.failed_flows > 0 ? "danger" : "success"}
            testId="failed-flows-card"
          />
        </div>
      </div>

      {/* Supplier Metrics - CTO'nun istegi */}
      <div>
        <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <Zap className="h-4 w-4" /> Supplier Metrics
        </h2>
        <div className="grid gap-4 grid-cols-1 md:grid-cols-3" data-testid="supplier-metrics-section">
          <MetricCard
            title="Supplier Latency"
            value={`${sm.supplier_latency_ms ?? 0} ms`}
            icon={Clock}
            variant={sm.supplier_latency_ms <= 500 ? "success" : "warning"}
            testId="supplier-latency-card"
          />
          <MetricCard
            title="Supplier Hata Orani"
            value={`${sm.supplier_error_rate ?? 0}%`}
            icon={AlertTriangle}
            variant={sm.supplier_error_rate <= 5 ? "success" : "danger"}
            testId="supplier-error-rate-card"
          />
          <MetricCard
            title="Supplier Basari Orani"
            value={`${sm.supplier_success_rate ?? 0}%`}
            icon={CheckCircle2}
            variant={sm.supplier_success_rate >= 95 ? "success" : "warning"}
            testId="supplier-success-rate-card"
          />
        </div>
      </div>

      {/* Supplier Response Diff - CTO kritik uyarisi: supplier dependency metrik */}
      <div>
        <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <ArrowUpDown className="h-4 w-4" /> Supplier Response Diff
          {srd.alert_count > 0 && (
            <Badge variant="destructive" className="text-xs ml-2" data-testid="diff-alert-badge">
              {srd.alert_count} Alert
            </Badge>
          )}
        </h2>
        <div className="grid gap-4 grid-cols-1 md:grid-cols-4" data-testid="supplier-response-diff-section">
          <MetricCard
            title="Ort. Fiyat Farki"
            value={`${srd.avg_diff_pct ?? 0}%`}
            subtitle={`${srd.avg_diff_amount ?? 0} TRY ort. fark`}
            icon={ArrowUpDown}
            variant={Math.abs(srd.avg_diff_pct ?? 0) <= 2 ? "success" : Math.abs(srd.avg_diff_pct ?? 0) <= 5 ? "warning" : "danger"}
            testId="avg-diff-pct-card"
          />
          <MetricCard
            title="Maks. Fiyat Farki"
            value={`${srd.max_diff_pct ?? 0}%`}
            subtitle={`${srd.max_diff_amount ?? 0} TRY maks. fark`}
            icon={ArrowUp}
            variant={(srd.max_diff_pct ?? 0) <= 3 ? "success" : (srd.max_diff_pct ?? 0) <= 5 ? "warning" : "danger"}
            testId="max-diff-pct-card"
          />
          <MetricCard
            title="Drift Dagilimi"
            value={`${srd.drift_up_count ?? 0} / ${srd.drift_down_count ?? 0} / ${srd.drift_stable_count ?? 0}`}
            subtitle="Yukari / Asagi / Sabit"
            icon={TrendingDown}
            testId="drift-distribution-card"
          />
          <MetricCard
            title="Diff Alarmlar"
            value={srd.alert_count ?? 0}
            subtitle={`Esik: >${srd.alert_threshold_pct ?? 5}% | ${srd.total_checks ?? 0} kontrol`}
            icon={AlertTriangle}
            variant={(srd.alert_count ?? 0) === 0 ? "success" : "danger"}
            testId="diff-alert-count-card"
          />
        </div>
        {srd.recent_diffs && srd.recent_diffs.length > 0 && (
          <Card className="mt-4" data-testid="recent-diffs-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Son Fiyat Farklari</CardTitle>
            </CardHeader>
            <CardContent>
              <Table data-testid="recent-diffs-table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Supplier</TableHead>
                    <TableHead>Ilk Fiyat</TableHead>
                    <TableHead>Revalidation Fiyat</TableHead>
                    <TableHead>Fark (TRY)</TableHead>
                    <TableHead>Fark (%)</TableHead>
                    <TableHead>Yon</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {srd.recent_diffs.map((d, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="text-sm font-medium">{d.supplier}</TableCell>
                      <TableCell className="font-mono text-sm">{d.initial_price?.toFixed(2)} TRY</TableCell>
                      <TableCell className="font-mono text-sm">{d.revalidation_price?.toFixed(2)} TRY</TableCell>
                      <TableCell className={`font-mono text-sm ${d.diff_amount > 0 ? "text-red-600" : d.diff_amount < 0 ? "text-emerald-600" : ""}`}>
                        {d.diff_amount > 0 ? "+" : ""}{d.diff_amount?.toFixed(2)}
                      </TableCell>
                      <TableCell className={`font-mono text-sm ${Math.abs(d.diff_pct) > 5 ? "text-red-600 font-bold" : ""}`}>
                        {d.diff_pct > 0 ? "+" : ""}{d.diff_pct?.toFixed(2)}%
                      </TableCell>
                      <TableCell>
                        <Badge variant={d.drift_direction === "up" ? "destructive" : d.drift_direction === "down" ? "default" : "secondary"} className="text-xs">
                          {d.drift_direction === "up" && <ArrowUp className="h-3 w-3 mr-1 inline" />}
                          {d.drift_direction === "down" && <ArrowDown className="h-3 w-3 mr-1 inline" />}
                          {d.drift_direction}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Finance Metrics - CTO'nun istegi */}
      <div>
        <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4" /> Finance Metrics
        </h2>
        <div className="grid gap-4 grid-cols-1 md:grid-cols-3" data-testid="finance-metrics-section">
          <MetricCard
            title="Fatura Olusturma Suresi"
            value={`${fm.invoice_generation_time_ms ?? 0} ms`}
            icon={FileText}
            variant={fm.invoice_generation_time_ms <= 1000 ? "success" : "warning"}
            testId="invoice-gen-time-card"
          />
          <MetricCard
            title="Muhasebe Sync Latency"
            value={`${fm.accounting_sync_latency_ms ?? 0} ms`}
            icon={RefreshCw}
            variant={fm.accounting_sync_latency_ms <= 1000 ? "success" : "warning"}
            testId="accounting-sync-latency-card"
          />
          <MetricCard
            title="Mutabakat Uyumsuzluk"
            value={`${fm.reconciliation_mismatch_rate ?? 0}%`}
            icon={XCircle}
            variant={fm.reconciliation_mismatch_rate <= 2 ? "success" : "danger"}
            testId="recon-mismatch-card"
          />
        </div>
      </div>

      <Separator />

      {/* Platform Health */}
      <div>
        <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <Activity className="h-4 w-4" /> Platform Health
        </h2>
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4" data-testid="platform-health-section">
          <MetricCard
            title="Search Basari Orani"
            value={`${ph.search_success_rate ?? 0}%`}
            icon={Search}
            variant={ph.search_success_rate >= 95 ? "success" : ph.search_success_rate >= 80 ? "warning" : "danger"}
          />
          <MetricCard
            title="Booking Basari Orani"
            value={`${ph.booking_success_rate ?? 0}%`}
            icon={ShoppingCart}
            variant={ph.booking_success_rate >= 95 ? "success" : ph.booking_success_rate >= 80 ? "warning" : "danger"}
          />
          <MetricCard
            title="Tedarikci Latency"
            value={`${ph.supplier_latency_ms ?? 0} ms`}
            icon={Zap}
            variant={ph.supplier_latency_ms <= 500 ? "success" : "warning"}
          />
          <MetricCard
            title="Tedarikci Hata Orani"
            value={`${ph.supplier_error_rate ?? 0}%`}
            icon={AlertTriangle}
            variant={ph.supplier_error_rate <= 5 ? "success" : "danger"}
          />
        </div>
      </div>

      {/* Pilot Usage */}
      <div>
        <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <TrendingUp className="h-4 w-4" /> Pilot Usage
        </h2>
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4" data-testid="pilot-usage-section">
          <MetricCard title="Aktif Acentalar" value={pu.active_agencies ?? 0} subtitle={`Toplam: ${pu.total_agencies ?? 0}`} icon={Users} />
          <MetricCard title="Gunluk Arama" value={pu.daily_searches ?? 0} icon={Search} />
          <MetricCard title="Gunluk Rezervasyon" value={pu.daily_bookings ?? 0} icon={ShoppingCart} />
          <MetricCard title="Uretilen Gelir" value={`${(pu.revenue_generated ?? 0).toLocaleString("tr-TR")} TRY`} icon={TrendingUp} />
        </div>
      </div>

      {/* Incident Monitoring */}
      <div>
        <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" /> Incident Monitoring
        </h2>
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4 mb-4" data-testid="incident-monitoring-section">
          <MetricCard
            title="Basarisiz Booking"
            value={im.failed_bookings ?? 0}
            icon={XCircle}
            variant={im.failed_bookings > 0 ? "danger" : "success"}
          />
          <MetricCard
            title="Basarisiz Fatura"
            value={im.failed_invoices ?? 0}
            icon={FileText}
            variant={im.failed_invoices > 0 ? "warning" : "success"}
          />
          <MetricCard
            title="Basarisiz Muhasebe Sync"
            value={im.failed_accounting_sync ?? 0}
            icon={RefreshCw}
            variant={im.failed_accounting_sync > 0 ? "danger" : "success"}
          />
          <MetricCard
            title="Kritik Uyarilar"
            value={im.critical_alerts ?? 0}
            icon={AlertTriangle}
            variant={im.critical_alerts > 0 ? "danger" : "success"}
          />
        </div>
      </div>

      <Separator />

      {/* Pilot Agencies Table */}
      <Card data-testid="agencies-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            Pilot Acentalar ({agencies?.total ?? 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {agencies?.agencies?.length > 0 ? (
            <div className="overflow-auto max-h-96">
              <Table data-testid="agencies-table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Acenta</TableHead>
                    <TableHead>Mod</TableHead>
                    <TableHead>Tedarikci</TableHead>
                    <TableHead>Muhasebe</TableHead>
                    <TableHead>Adim</TableHead>
                    <TableHead>Durum</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {agencies.agencies.map((a, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">{a.name}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">{a.mode}</Badge>
                      </TableCell>
                      <TableCell className="text-sm">{a.supplier_config?.supplier_type || "-"}</TableCell>
                      <TableCell className="text-sm">{a.accounting_config?.provider_type || "-"}</TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="text-xs">{a.wizard_step}/9</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={a.status === "active" ? "default" : "secondary"} className="text-xs">
                          {a.status === "active" ? <CheckCircle2 className="h-3 w-3 mr-1 inline" /> : null}
                          {a.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground text-sm" data-testid="no-agencies">
              Henuz pilot acenta eklenmemis
            </div>
          )}
        </CardContent>
      </Card>

      {/* Incidents */}
      <Card data-testid="incidents-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            Son Olaylar (severity / flow_stage / supplier / retry_count)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <IncidentsPanel incidents={metrics?.recent_incidents} />
        </CardContent>
      </Card>
    </div>
  );
}
