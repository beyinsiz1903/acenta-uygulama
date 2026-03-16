import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { RefreshCw, Eye, CheckCircle2, XCircle, Clock } from "lucide-react";
import { useHardeningApi } from "../api";
import { severityColor } from "../helpers";

export function ObservabilityTab() {
  const { data, loading } = useHardeningApi("/hardening/observability/status");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="observability-tab" className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Prometheus</CardTitle></CardHeader>
          <CardContent className="text-xs text-zinc-400 space-y-1">
            <p>Metrics defined: {data.prometheus.metrics_defined}</p>
            <p>Counters: {data.prometheus.counters} | Histograms: {data.prometheus.histograms} | Gauges: {data.prometheus.gauges}</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">OpenTelemetry</CardTitle></CardHeader>
          <CardContent className="text-xs text-zinc-400 space-y-1">
            <p>Service: {data.opentelemetry.service_name}</p><p>Sample rate: {data.opentelemetry.traces.sample_rate}</p><p>Exporter: {data.opentelemetry.traces.exporter}</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Alert Rules</CardTitle></CardHeader>
          <CardContent className="text-xs space-y-1">
            {data.alert_rules.map((r, i) => (
              <div key={i} className="flex items-center gap-2"><Badge variant={r.severity === "critical" ? "destructive" : "outline"} className="text-[10px]">{r.severity}</Badge><span className="text-zinc-400">{r.name}</span></div>
            ))}
          </CardContent>
        </Card>
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Grafana Dashboards</CardTitle></CardHeader>
        <CardContent><div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(data.grafana_dashboards).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between bg-zinc-800/50 rounded p-3 text-xs"><div><p className="text-zinc-200 font-medium">{v.title}</p><p className="text-zinc-500">{v.panels} panels</p></div><Eye className="w-4 h-4 text-zinc-500" /></div>
          ))}
        </div></CardContent>
      </Card>
    </div>
  );
}

export function PerformanceTab() {
  const { data, loading } = useHardeningApi("/hardening/performance/profiles");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="performance-tab" className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(data.profiles).map(([key, p]) => (
          <Card key={key} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">{p.name}</CardTitle></CardHeader>
            <CardContent className="text-xs text-zinc-400 space-y-1">
              <p>Agencies: {p.agencies}</p><p>Searches/hr: {p.searches_per_hour.toLocaleString()}</p><p>Bookings/hr: {p.bookings_per_hour.toLocaleString()}</p>
              <p>Concurrent users: {p.concurrent_users.toLocaleString()}</p><p>Duration: {p.duration_minutes}min (ramp: {p.ramp_up_minutes}min)</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">SLA Targets</CardTitle></CardHeader>
        <CardContent><div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
          {Object.entries(data.sla_targets).map(([k, v]) => (
            <div key={k} className="flex justify-between bg-zinc-800/50 rounded p-2"><span className="text-zinc-400">{k.replace(/_/g, " ")}</span><span className="font-mono text-zinc-200">{v.target}{v.unit}</span></div>
          ))}
        </div></CardContent>
      </Card>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Test Scenarios</CardTitle></CardHeader>
        <CardContent><div className="space-y-1 text-xs">
          {data.scenarios.map((s, i) => (
            <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2"><span className="text-zinc-300">{s.name}</span><div className="flex gap-3 text-zinc-500"><span>Weight: {s.weight}%</span><span>{s.steps} steps</span></div></div>
          ))}
        </div></CardContent>
      </Card>
    </div>
  );
}

export function TenantSafetyTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/tenant-safety/audit");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="tenant-tab" className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-zinc-100">{data.score}%</div><p className="text-xs text-zinc-500">Isolation Score</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-emerald-400">{data.passed}</div><p className="text-xs text-zinc-500">Passed</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-red-400">{data.failed}</div><p className="text-xs text-zinc-500">Failed</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-amber-400">{data.warnings}</div><p className="text-xs text-zinc-500">Warnings</p></CardContent></Card>
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Collection Audit</CardTitle></CardHeader>
        <CardContent><div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead><tr className="text-zinc-500 border-b border-zinc-800"><th className="text-left py-2 pr-4">Collection</th><th className="text-left">Status</th><th className="text-right">Docs</th><th className="text-right">Missing</th><th className="text-center">Index</th></tr></thead>
            <tbody>
              {data.collection_results.map((c, i) => (
                <tr key={i} className="border-b border-zinc-800/50">
                  <td className="py-1.5 text-zinc-300 pr-4">{c.collection}</td>
                  <td>{c.status === "pass" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : c.status === "fail" ? <XCircle className="w-3.5 h-3.5 text-red-400" /> : <Clock className="w-3.5 h-3.5 text-zinc-500" />}</td>
                  <td className="text-right text-zinc-400 font-mono">{c.doc_count}</td>
                  <td className="text-right font-mono">{c.missing_tenant_field > 0 ? <span className="text-red-400">{c.missing_tenant_field}</span> : <span className="text-zinc-500">0</span>}</td>
                  <td className="text-center">{c.has_tenant_index ? <CheckCircle2 className="w-3 h-3 text-emerald-400 inline" /> : c.doc_count > 0 ? <XCircle className="w-3 h-3 text-amber-400 inline" /> : <span className="text-zinc-600">-</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div></CardContent>
      </Card>
      <Button data-testid="rerun-audit" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-run Audit</Button>
    </div>
  );
}

export function SecretsTab() {
  const { data, loading } = useHardeningApi("/hardening/secrets/status");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  const s = data.summary;
  return (
    <div data-testid="secrets-tab" className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-zinc-100">{s.total_secrets}</div><p className="text-xs text-zinc-500">Total Secrets</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-emerald-400">{s.configured}</div><p className="text-xs text-zinc-500">Configured</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-red-400">{s.missing}</div><p className="text-xs text-zinc-500">Missing</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-zinc-100">{s.migration_progress_pct}%</div><p className="text-xs text-zinc-500">Vault Migration</p></CardContent></Card>
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Secret Inventory</CardTitle></CardHeader>
        <CardContent><div className="space-y-1 text-xs">
          {data.inventory.map((sec, i) => (
            <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
              <div className="flex items-center gap-2">{sec.is_configured ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}<span className="text-zinc-300 font-mono">{sec.name}</span></div>
              <div className="flex items-center gap-2"><Badge variant={severityColor(sec.risk_level)} className="text-[10px]">{sec.risk_level}</Badge><span className="text-zinc-500">{sec.target_source}</span></div>
            </div>
          ))}
        </div></CardContent>
      </Card>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Migration Phases</CardTitle></CardHeader>
        <CardContent><div className="space-y-2 text-xs">
          {data.migration_phases.map((p, i) => (
            <div key={i} className="bg-zinc-800/50 rounded p-3">
              <div className="flex items-center justify-between mb-1"><span className="text-zinc-200 font-medium">Phase {p.phase}: {p.name}</span><Badge variant="outline" className="text-[10px]">{p.status} - {p.estimated_days}d</Badge></div>
              <p className="text-zinc-500">{p.description}</p>
            </div>
          ))}
        </div></CardContent>
      </Card>
    </div>
  );
}
