import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import {
  Activity, AlertTriangle, CheckCircle2, Clock, Loader2, Search, ShoppingCart,
  FileText, RefreshCw, Users, TrendingUp, Zap, XCircle, BarChart3,
} from "lucide-react";
import { api } from "../lib/api";
import { useNavigate } from "react-router-dom";

function MetricCard({ title, value, subtitle, icon: Icon, variant = "default" }) {
  const colorMap = {
    default: "text-foreground",
    success: "text-emerald-600",
    warning: "text-amber-600",
    danger: "text-red-600",
  };
  return (
    <Card>
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
          <TableHead>Onem</TableHead>
          <TableHead>Durum</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {incidents.map((inc, idx) => (
          <TableRow key={idx}>
            <TableCell className="text-xs">{new Date(inc.timestamp).toLocaleString("tr-TR")}</TableCell>
            <TableCell className="font-medium text-sm">{inc.agency_name}</TableCell>
            <TableCell className="text-sm">{inc.step}</TableCell>
            <TableCell>
              <Badge variant={inc.severity === "critical" ? "destructive" : "secondary"} className="text-xs">
                {inc.severity}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge variant="outline" className="text-xs">{inc.status}</Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default function PilotOnboardingDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [metrics, setMetrics] = useState(null);
  const [agencies, setAgencies] = useState(null);
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

  useEffect(() => { fetchData(); }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96" data-testid="loading-state">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 space-y-3" data-testid="error-state">
        <AlertTriangle className="h-10 w-10 text-muted-foreground mx-auto" />
        <p className="text-sm font-medium">{error}</p>
        <Button variant="outline" onClick={fetchData}>Tekrar Dene</Button>
      </div>
    );
  }

  const ph = metrics?.platform_health || {};
  const ff = metrics?.financial_flow || {};
  const pu = metrics?.pilot_usage || {};
  const im = metrics?.incident_monitoring || {};

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
          <Button size="sm" onClick={() => navigate("/app/admin/pilot-wizard")} data-testid="new-agency-btn">
            <Users className="h-4 w-4 mr-1" /> Yeni Pilot Acenta
          </Button>
        </div>
      </div>

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

      {/* Financial Flow */}
      <div>
        <h2 className="text-base font-semibold text-foreground mb-3 flex items-center gap-2">
          <BarChart3 className="h-4 w-4" /> Financial Flow
        </h2>
        <div className="grid gap-4 grid-cols-1 md:grid-cols-3" data-testid="financial-flow-section">
          <MetricCard
            title="Booking → Invoice Donusum"
            value={`${ff.booking_invoice_conversion ?? 0}%`}
            icon={FileText}
            variant={ff.booking_invoice_conversion >= 95 ? "success" : "warning"}
          />
          <MetricCard
            title="Invoice → Muhasebe Sync Latency"
            value={`${ff.invoice_accounting_sync_latency_ms ?? 0} ms`}
            icon={Clock}
            variant={ff.invoice_accounting_sync_latency_ms <= 1000 ? "success" : "warning"}
          />
          <MetricCard
            title="Mutabakat Uyumsuzluk Orani"
            value={`${ff.reconciliation_mismatch_rate ?? 0}%`}
            icon={XCircle}
            variant={ff.reconciliation_mismatch_rate <= 2 ? "success" : "danger"}
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
            Son Olaylar
          </CardTitle>
        </CardHeader>
        <CardContent>
          <IncidentsPanel incidents={metrics?.recent_incidents} />
        </CardContent>
      </Card>
    </div>
  );
}
