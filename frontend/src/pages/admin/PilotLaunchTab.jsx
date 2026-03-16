import React, { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Progress } from "../../components/ui/progress";
import {
  Activity, AlertTriangle, CheckCircle2, XCircle, RefreshCw, Zap, Play,
  Target, Server, Shield, CreditCard, Users, BarChart3, FileText, Rocket,
  Radio, MonitorCheck, Plane, Building2
} from "lucide-react";
import { api } from "../../lib/api";

function ScoreGauge({ score, max, label, size = "lg" }) {
  const pct = (score / max) * 100;
  const color = score >= 8 ? "text-emerald-400" : score >= 5 ? "text-amber-400" : "text-red-400";
  const dim = size === "lg" ? "w-32 h-32" : "w-20 h-20";
  const textSize = size === "lg" ? "text-2xl" : "text-lg";
  return (
    <div data-testid={`pilot-gauge-${label?.replace(/\s/g, "-").toLowerCase()}`} className="flex flex-col items-center gap-1.5">
      <div className={`relative ${dim}`}>
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor" className="text-zinc-800" strokeWidth="8" />
          <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor" className={color} strokeWidth="8" strokeDasharray={`${pct * 2.64} 264`} strokeLinecap="round" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${textSize} font-bold ${color}`}>{score}</span>
          <span className="text-[10px] text-zinc-500">/{max}</span>
        </div>
      </div>
      {label && <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider text-center leading-tight">{label}</span>}
    </div>
  );
}

function ActionCard({ testId, icon: Icon, title, desc, endpoint, method = "post", children }) {
      const run = async () => {
    setLoading(true);
    try {
      const res = method === "post" ? await api.post(endpoint) : await api.get(endpoint);
      setResult(res.data);
    } catch (e) { setResult({ verdict: "ERROR", error: e.message }); }
    setLoading(false);
  };
  const vc = result?.verdict === "PASS" ? "bg-emerald-900/30 border-emerald-800" : result?.verdict === "FAIL" ? "bg-red-900/30 border-red-800" : "bg-amber-900/30 border-amber-800";
  return (
    <Card data-testid={testId} className="bg-zinc-900 border-zinc-800">
      <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Icon className="w-4 h-4 text-zinc-400" />{title}</CardTitle></CardHeader>
      <CardContent className="text-xs space-y-3">
        <p className="text-zinc-500">{desc}</p>
        <Button data-testid={`${testId}-run`} size="sm" variant="outline" className="text-xs w-full" disabled={loading} onClick={run}>
          {loading ? "Running..." : "Execute"}
        </Button>
        {result && (
          <div data-testid={`${testId}-result`} className={`p-3 rounded border ${vc}`}>
            <div className="flex items-center gap-2 mb-2">
              {result.verdict === "PASS" ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
              <span className="font-mono font-bold text-sm">{result.verdict}</span>
              {result.duration_seconds && <span className="text-zinc-500 ml-auto">{result.duration_seconds}s</span>}
            </div>
            {children && children(result)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SLARow({ checks }) {
  if (!checks) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {Object.entries(checks).map(([k, v]) => (
        <Badge key={k} className={`text-[10px] ${v ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"}`}>
          {v ? "\u2713" : "\u2717"} {k.replace(/_/g, " ")}
        </Badge>
      ))}
    </div>
  );
}

export default function PilotLaunchTab() {
  const { data: dashboard, isLoading: loading, refetch } = useQuery({
    queryKey: ["pilot", "dashboard"],
    queryFn: async () => {
      const resp = await api.get("/pilot/dashboard");
      return resp.data || null;
    },
    staleTime: 30_000,
  });

  const [panel, setPanel] = useState("overview");

  const panels = [
    { id: "overview", label: "Overview", icon: Target },
    { id: "environment", label: "Environment", icon: Server },
    { id: "suppliers", label: "Suppliers", icon: Plane },
    { id: "monitoring", label: "Monitoring", icon: MonitorCheck },
    { id: "incidents", label: "Incidents", icon: AlertTriangle },
    { id: "agencies", label: "Agencies", icon: Building2 },
    { id: "booking", label: "Booking Flow", icon: CreditCard },
    { id: "inctest", label: "Incident Test", icon: Shield },
    { id: "performance", label: "Performance", icon: BarChart3 },
    { id: "report", label: "Report", icon: FileText },
    { id: "golive", label: "Go-Live", icon: Rocket },
  ];

  const decColor = { GO: "bg-emerald-600", CONDITIONAL_GO: "bg-amber-600", NO_GO: "bg-red-600" };

  return (
    <div data-testid="pilot-launch-tab" className="space-y-4">
      {/* Top Bar */}
      <div className="flex items-center gap-4 bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <ScoreGauge score={dashboard?.readiness_score ?? 0} max={10} label="Pilot Score" size="sm" />
        <div className="flex-1 grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Decision</span>
            <Badge data-testid="pilot-decision" className={`${decColor[dashboard?.decision] || "bg-zinc-600"} text-white`}>{dashboard?.decision || "---"}</Badge>
          </div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Agencies</span>
            <span data-testid="pilot-agencies" className="text-zinc-200 font-mono">{dashboard?.active_agencies ?? 0}/{dashboard?.total_agencies ?? 0}</span>
          </div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Checklist</span>
            <span data-testid="pilot-checklist" className="text-zinc-200 font-mono">{dashboard?.checklist_pass_rate ?? 0}%</span>
          </div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Incidents</span>
            <span data-testid="pilot-incidents-count" className="text-zinc-200 font-mono">{dashboard?.incident_log?.total_incidents ?? 0}</span>
          </div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Risk</span>
            <Badge data-testid="pilot-risk" className={dashboard?.risk_level === "low" ? "bg-emerald-700 text-white" : dashboard?.risk_level === "medium" ? "bg-amber-700 text-white" : "bg-red-700 text-white"}>{dashboard?.risk_level || "---"}</Badge>
          </div>
        </div>
        <Button data-testid="refresh-pilot" size="sm" variant="outline" onClick={() => refetch()}><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /></Button>
      </div>

      {/* Nav */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {panels.map(p => (
          <button key={p.id} data-testid={`pilot-panel-${p.id}`} onClick={() => setPanel(p.id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap transition-colors ${panel === p.id ? "bg-zinc-700 text-white" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"}`}>
            <p.icon className="w-3.5 h-3.5" />{p.label}
          </button>
        ))}
      </div>

      {panel === "overview" && <OverviewPanel dashboard={dashboard} loading={loading} />}
      {panel === "environment" && <EnvironmentPanel />}
      {panel === "suppliers" && <SupplierPanel />}
      {panel === "monitoring" && <MonitoringPanel />}
      {panel === "incidents" && <IncidentPanel />}
      {panel === "agencies" && <AgencyPanel />}
      {panel === "booking" && <BookingFlowPanel />}
      {panel === "inctest" && <IncidentTestPanel />}
      {panel === "performance" && <PerformancePanel />}
      {panel === "report" && <ReportPanel />}
      {panel === "golive" && <GoLivePanel />}
    </div>
  );
}

/* ───── OVERVIEW ───── */
function OverviewPanel({ dashboard: d, loading }) {
  if (loading || !d) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="pilot-overview" className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {Object.entries(d.components || {}).map(([k, c]) => (
          <Card key={k} className="bg-zinc-900 border-zinc-800">
            <CardContent className="pt-4 text-center">
              <div className={`text-lg font-bold ${c.status === "pass" ? "text-emerald-400" : "text-red-400"}`}>{typeof c.score === "number" ? c.score.toFixed(1) : c.score}/10</div>
              <p className="text-[10px] text-zinc-500 mt-1 uppercase">{k.replace(/_/g, " ")}</p>
              <p className="text-[10px] text-zinc-600">{(c.weight * 100)}%</p>
            </CardContent>
          </Card>
        ))}
      </div>
      {d.go_live_checklist?.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Go-Live Checklist ({d.checklist_pass_rate}%)</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {d.go_live_checklist.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-xs bg-zinc-800/50 rounded p-2">
                {c.passed ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}
                <span className="text-zinc-300 flex-1">{c.item}</span>
                <span className="text-zinc-500">{c.evidence}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      {d.recent_events?.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Recent Events</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {d.recent_events.map((e, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-300">{e.event}: {e.action}</span>
                <Badge className={e.verdict === "PASS" ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"}>{e.verdict}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ───── PART 1: ENVIRONMENT ───── */
function EnvironmentPanel() {
  const [env, setEnv] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => { setLoading(true); try { const r = await api.get("/pilot/environment"); setEnv(r.data); } catch {} setLoading(false); }, []);

  if (loading || !env) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  const e = env.pilot_environment;
  return (
    <div data-testid="env-panel" className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><Badge className={e.status === "active" ? "bg-emerald-600 text-white" : "bg-amber-600 text-white"}>{e.status?.toUpperCase()}</Badge><p className="text-[10px] text-zinc-500 mt-2">Environment Status</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-xl font-bold text-zinc-200">{e.active_agencies}/{e.max_agencies}</span><p className="text-[10px] text-zinc-500 mt-1">Agencies</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-xl font-bold text-zinc-200">{e.current_traffic_pct}%/{e.max_traffic_pct}%</span><p className="text-[10px] text-zinc-500 mt-1">Traffic Limit</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-xl font-bold text-emerald-400">{e.monitoring_enabled ? "ON" : "OFF"}</span><p className="text-[10px] text-zinc-500 mt-1">Monitoring</p></CardContent></Card>
      </div>
      {e.feature_flags && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Feature Flags</CardTitle></CardHeader>
          <CardContent><div className="flex flex-wrap gap-2">
            {Object.entries(e.feature_flags).map(([k, v]) => (
              <Badge key={k} className={v ? "bg-emerald-800/60 text-emerald-300" : "bg-zinc-700 text-zinc-400"}>{k.replace(/_/g, " ")}: {v ? "ON" : "OFF"}</Badge>
            ))}
          </div></CardContent>
        </Card>
      )}
      <ActionCard testId="activate-env" icon={Play} title="Activate Pilot Environment" desc="Run preflight checks and activate the controlled pilot environment." endpoint="/pilot/environment/activate">
        {(r) => (
          <div className="space-y-1 text-xs">
            {r.preflight_checks?.map((c, i) => (
              <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-1.5">
                <span className="text-zinc-300">{c.check}</span>
                <Badge className={c.passed ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"}>{c.passed ? "PASS" : "FAIL"}</Badge>
              </div>
            ))}
            <p className="text-zinc-400 mt-1">Passed: {r.passed}/{r.total}</p>
          </div>
        )}
      </ActionCard>
    </div>
  );
}

/* ───── PART 2: SUPPLIERS ───── */
function SupplierPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => { setLoading(true); try { const r = await api.get("/pilot/supplier-traffic"); setData(r.data); } catch {} setLoading(false); }, []);

  const [activating, setActivating] = useState({});
  const activate = async (code, mode) => {
    setActivating(p => ({ ...p, [`${code}_${mode}`]: true }));
    try { await api.post(`/pilot/supplier-traffic/${code}/${mode}`); fetch_(); } catch {}
    setActivating(p => ({ ...p, [`${code}_${mode}`]: false }));
  };

  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="supplier-panel" className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(data.suppliers || {}).map(([code, s]) => (
          <Card key={code} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize flex items-center gap-2">{code}<Badge variant="outline">{s.phase}</Badge></CardTitle></CardHeader>
            <CardContent className="text-xs space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Shadow Requests</span><br/><span className="text-zinc-200 font-mono">{s.shadow_requests_sent}</span></div>
                <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Match Rate</span><br/><span className="text-emerald-400 font-mono">{s.shadow_match_rate_pct}%</span></div>
              </div>
              <div className="bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-500">Auth: </span><Badge className={s.auth?.status === "valid" ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"}>{s.auth?.status}</Badge>
                <span className="text-zinc-500 ml-2">Expires: {s.auth?.expires_in_hours}h</span>
              </div>
              <div className="flex gap-1.5">
                {["shadow", "limited", "full"].map(m => (
                  <Button key={m} data-testid={`activate-${code}-${m}`} size="sm" variant={s.status === m ? "default" : "outline"} className="text-xs flex-1 capitalize" disabled={activating[`${code}_${m}`]} onClick={() => activate(code, m)}>{m}</Button>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ───── PART 3: MONITORING ───── */
function MonitoringPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => { setLoading(true); try { const r = await api.get("/pilot/monitoring"); setData(r.data); } catch {} setLoading(false); }, []);
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  const m = data.tracked_metrics;
  return (
    <div data-testid="monitoring-panel" className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><Badge className="bg-emerald-600 text-white">{data.prometheus?.status}</Badge><p className="text-[10px] text-zinc-500 mt-2">Prometheus</p><p className="text-[10px] text-zinc-600">{data.prometheus?.targets} targets | {data.prometheus?.metrics_collected} metrics</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><Badge className="bg-emerald-600 text-white">{data.grafana?.status}</Badge><p className="text-[10px] text-zinc-500 mt-2">Grafana</p><p className="text-[10px] text-zinc-600">{data.grafana?.dashboards?.length} dashboards</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-xl font-bold text-zinc-200">{data.prometheus?.active_alerts}</span><p className="text-[10px] text-zinc-500 mt-1">Active Alerts</p></CardContent></Card>
      </div>
      {m && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Live Metrics</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">API P95</span><br/><span className="text-zinc-200 font-mono">{m.api_latency?.p95_ms}ms</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Paximum P95</span><br/><span className="text-zinc-200 font-mono">{m.supplier_latency?.paximum?.p95_ms}ms</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Queue Depth</span><br/><span className="text-zinc-200 font-mono">{(m.queue_depth?.booking || 0) + (m.queue_depth?.voucher || 0) + (m.queue_depth?.notification || 0)}</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Booking Rate</span><br/><span className="text-emerald-400 font-mono">{m.booking_success_rate_pct}%</span></div>
            </div>
          </CardContent>
        </Card>
      )}
      {data.grafana?.dashboards && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Grafana Dashboards</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {data.grafana.dashboards.map((d, i) => (
              <div key={i} className="flex justify-between text-xs bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-300">{d.name}</span>
                <span className="text-zinc-500">{d.panels} panels | {d.refresh_s}s refresh</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      <Button data-testid="refresh-monitoring" size="sm" variant="outline" onClick={fetch_} className="text-xs"><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

/* ───── PART 4: INCIDENTS ───── */
function IncidentPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => { setLoading(true); try { const r = await api.get("/pilot/incidents"); setData(r.data); } catch {} setLoading(false); }, []);

  const [simType, setSimType] = useState("supplier_outage");
  const types = ["supplier_outage", "queue_backlog", "payment_failure"];

  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="incident-panel" className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-zinc-400">
        <Radio className="w-4 h-4" />{data.active_rules}/{data.total_rules} rules active | Channels: {data.alert_channels?.join(", ")}
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Detection Rules</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          {data.detection_rules?.map((r, i) => (
            <div key={i} className="flex items-center justify-between text-xs bg-zinc-800/50 rounded p-2">
              <span className="text-zinc-300">{r.name}</span>
              <div className="flex items-center gap-2">
                <Badge variant={r.severity === "critical" ? "destructive" : r.severity === "high" ? "default" : "secondary"}>{r.severity}</Badge>
                <span className="text-zinc-500">{r.condition}</span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
      <div className="flex gap-2">
        {types.map(t => (
          <Button key={t} size="sm" variant={simType === t ? "default" : "outline"} className="text-xs" onClick={() => setSimType(t)}>{t.replace(/_/g, " ")}</Button>
        ))}
      </div>
      <ActionCard testId="simulate-incident" icon={AlertTriangle} title={`Simulate: ${simType.replace(/_/g, " ")}`} desc="Trigger incident detection and verify alert workflow." endpoint={`/pilot/incidents/simulate/${simType}`}>
        {(r) => (
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-2"><Badge variant="destructive">{r.severity}</Badge><span className="text-zinc-400">Response: {r.total_response_ms}ms</span><Badge className={r.within_sla ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"}>{r.within_sla ? "Within SLA" : "SLA Breach"}</Badge></div>
            {r.steps?.map((s, i) => (
              <div key={i} className="flex justify-between bg-zinc-800/50 rounded p-1.5"><span className="text-zinc-300">{s.step}</span><span className="text-zinc-500 font-mono">{s.time_ms}ms</span></div>
            ))}
          </div>
        )}
      </ActionCard>
    </div>
  );
}

/* ───── PART 5: AGENCIES ───── */
function AgencyPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => { setLoading(true); try { const r = await api.get("/pilot/agencies"); setData(r.data); } catch {} setLoading(false); }, []);
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="agency-panel" className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-xl font-bold text-zinc-200">{data.total}</span><p className="text-[10px] text-zinc-500">Total Agencies</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-xl font-bold text-emerald-400">{data.active}</span><p className="text-[10px] text-zinc-500">Active</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-xl font-bold text-amber-400">{data.onboarding}</span><p className="text-[10px] text-zinc-500">Onboarding</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-xl font-bold text-zinc-200">{data.total_bookings}</span><p className="text-[10px] text-zinc-500">Total Bookings</p></CardContent></Card>
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Pilot Agencies</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {data.agencies?.map((a, i) => (
            <div key={i} className="flex items-center justify-between text-xs bg-zinc-800/50 rounded p-3">
              <div><span className="text-zinc-200 font-medium">{a.name}</span><p className="text-zinc-500">{a.users} users | {a.config?.suppliers?.join(", ")} | {a.config?.currency}</p></div>
              <div className="flex items-center gap-2">
                <Badge className={a.status === "active" ? "bg-emerald-600 text-white" : "bg-amber-600 text-white"}>{a.status}</Badge>
                <span className="text-zinc-400 font-mono">{a.bookings} bookings</span>
                {a.training_completed && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
      {data.training_materials && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Training Materials</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {data.training_materials.map((m, i) => (
              <div key={i} className="flex justify-between text-xs bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-300">{m.title}</span>
                <span className="text-zinc-500">{m.format} {m.pages ? `(${m.pages}p)` : m.duration_min ? `(${m.duration_min}min)` : m.endpoints ? `(${m.endpoints} endpoints)` : ""}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ───── PART 6: BOOKING FLOW ───── */
function BookingFlowPanel() {
  const [flowType, setFlowType] = useState("hotel");
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {["hotel", "flight"].map(t => (
          <Button key={t} size="sm" variant={flowType === t ? "default" : "outline"} className="text-xs capitalize" onClick={() => setFlowType(t)}>{t}</Button>
        ))}
      </div>
      <ActionCard testId="booking-flow" icon={CreditCard} title={`Real Booking Flow: ${flowType}`} desc="Execute: search → pricing → booking → voucher → notifications." endpoint={`/pilot/booking-flow/${flowType}`}>
        {(r) => (
          <div className="space-y-2 text-xs">
            {r.steps?.map((s, i) => (
              <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                <div className="flex items-center gap-2">
                  {s.result === "PASS" ? <CheckCircle2 className="w-3 h-3 text-emerald-400" /> : <XCircle className="w-3 h-3 text-red-400" />}
                  <span className="text-zinc-300">{s.step}</span>
                </div>
                <span className="text-zinc-500 font-mono">{s.latency_ms}ms</span>
              </div>
            ))}
            {r.booking && (
              <div className="bg-zinc-800/50 rounded p-2 mt-1">
                <span className="text-zinc-400">Booking: </span>
                <span className="text-zinc-200 font-mono">{r.booking.booking_id}</span>
                <Badge className={r.booking.status === "confirmed" ? "bg-emerald-800/60 text-emerald-300 ml-2" : "bg-red-800/60 text-red-300 ml-2"}>{r.booking.status}</Badge>
                <span className="text-zinc-500 ml-2">{r.booking.total_amount} {r.booking.currency}</span>
              </div>
            )}
            <SLARow checks={r.sla_check} />
          </div>
        )}
      </ActionCard>
    </div>
  );
}

/* ───── PART 7: INCIDENT TEST ───── */
function IncidentTestPanel() {
  const [scenario, setScenario] = useState("supplier_outage");
  const scenarios = ["supplier_outage", "payment_error", "database_slowdown"];
  return (
    <div className="space-y-3">
      <div className="flex gap-2 flex-wrap">
        {scenarios.map(s => (
          <Button key={s} size="sm" variant={scenario === s ? "default" : "outline"} className="text-xs" onClick={() => setScenario(s)}>{s.replace(/_/g, " ")}</Button>
        ))}
      </div>
      <ActionCard testId="incident-test" icon={Shield} title={`Production Incident: ${scenario.replace(/_/g, " ")}`} desc="Simulate production incident and verify auto-recovery." endpoint={`/pilot/incident-test/${scenario}`}>
        {(r) => (
          <div className="space-y-2 text-xs">
            <p className="text-zinc-400">{r.description}</p>
            {r.phases?.map((p, i) => (
              <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-300">{p.phase}</span>
                <div className="flex items-center gap-2">
                  <Badge className="bg-emerald-800/60 text-emerald-300">{p.status}</Badge>
                  <span className="text-zinc-500 font-mono">{p.time_ms}ms</span>
                </div>
              </div>
            ))}
            <div className="bg-zinc-800/50 rounded p-2">
              <span className="text-zinc-400">Recovery: {r.total_recovery_seconds}s | Data Loss: {r.data_loss ? "YES" : "NONE"} | Auto: {r.auto_recovery_worked ? "YES" : "NO"}</span>
            </div>
            <SLARow checks={r.sla_check} />
          </div>
        )}
      </ActionCard>
    </div>
  );
}

/* ───── PART 8: PERFORMANCE ───── */
function PerformancePanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => { setLoading(true); try { const r = await api.get("/pilot/performance"); setData(r.data); } catch {} setLoading(false); }, []);
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  const p = data.performance;
  return (
    <div data-testid="perf-panel" className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-2xl font-bold text-zinc-200" data-testid="api-p95">{p.p95_latency?.api_ms}ms</span><p className="text-[10px] text-zinc-500">API P95</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-2xl font-bold text-zinc-200">{p.p95_latency?.supplier_ms}ms</span><p className="text-[10px] text-zinc-500">Supplier P95</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-2xl font-bold text-emerald-400">{p.booking_success_rate?.rate_pct}%</span><p className="text-[10px] text-zinc-500">Booking Success</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><span className="text-2xl font-bold text-zinc-200">{p.throughput?.bookings_per_hour}</span><p className="text-[10px] text-zinc-500">Bookings/hr</p></CardContent></Card>
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Supplier Reliability</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 text-xs">
            {Object.entries(p.supplier_reliability || {}).map(([k, v]) => (
              <div key={k} className="bg-zinc-800/50 rounded p-3">
                <span className="text-zinc-300 capitalize font-medium">{k}</span>
                <div className="grid grid-cols-3 gap-2 mt-1">
                  <div><span className="text-zinc-500">Uptime</span><br/><span className="text-emerald-400 font-mono">{v.uptime_pct}%</span></div>
                  <div><span className="text-zinc-500">Latency</span><br/><span className="text-zinc-200 font-mono">{v.avg_latency_ms}ms</span></div>
                  <div><span className="text-zinc-500">Errors</span><br/><span className="text-red-400 font-mono">{v.error_rate_pct}%</span></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      {data.pilot_traffic_summary && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Pilot Traffic Summary</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
              {Object.entries(data.pilot_traffic_summary).map(([k, v]) => (
                <div key={k} className="bg-zinc-800/50 rounded p-2 text-center"><span className="text-zinc-200 font-mono">{typeof v === "number" ? v.toLocaleString() : v}</span><p className="text-zinc-500">{k.replace(/_/g, " ")}</p></div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
      <Button data-testid="refresh-perf" size="sm" variant="outline" onClick={fetch_} className="text-xs"><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

/* ───── PART 9: REPORT ───── */
function ReportPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => { setLoading(true); try { const r = await api.get("/pilot/report"); setData(r.data); } catch {} setLoading(false); }, []);
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="report-panel" className="space-y-4">
      <Card className={data.meets_target ? "bg-emerald-950/20 border-emerald-900/40" : "bg-red-950/20 border-red-900/40"}>
        <CardContent className="pt-6 flex items-center gap-6">
          <ScoreGauge score={data.readiness_score} max={10} label="Pilot Score" />
          <div>
            <div className={`text-2xl font-bold ${data.meets_target ? "text-emerald-400" : "text-red-400"}`}>{data.recommendation}</div>
            <p className="text-sm text-zinc-400 mt-1">Target: {data.target}/10 | Gap: {data.gap}</p>
          </div>
        </CardContent>
      </Card>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {Object.entries(data.components || {}).map(([k, c]) => (
          <div key={k} className="bg-zinc-800/50 rounded p-2 text-xs"><span className="text-zinc-500 capitalize block">{k.replace(/_/g, " ")}</span><span className={`font-mono font-bold ${c.score >= 9 ? "text-emerald-400" : "text-amber-400"}`}>{typeof c.score === "number" ? c.score.toFixed(1) : c.score}/10</span><span className="text-zinc-600 ml-1">({(c.weight * 100)}%)</span></div>
        ))}
      </div>
      {data.supplier_reliability && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Supplier Reliability</CardTitle></CardHeader>
          <CardContent><div className="flex gap-4 text-xs">
            {Object.entries(data.supplier_reliability).map(([k, v]) => (
              <div key={k} className="bg-zinc-800/50 rounded p-2 text-center flex-1"><span className="text-zinc-200 font-mono">{v}%</span><p className="text-zinc-500 capitalize">{k}</p></div>
            ))}
          </div></CardContent>
        </Card>
      )}
      {data.incident_log && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Incident Log</CardTitle></CardHeader>
          <CardContent><div className="flex gap-4 text-xs">
            <div className="bg-zinc-800/50 rounded p-2 flex-1 text-center"><span className="text-zinc-200 font-mono">{data.incident_log.total_incidents}</span><p className="text-zinc-500">Total</p></div>
            <div className="bg-zinc-800/50 rounded p-2 flex-1 text-center"><span className="text-emerald-400 font-mono">{data.incident_log.resolved}</span><p className="text-zinc-500">Resolved</p></div>
            <div className="bg-zinc-800/50 rounded p-2 flex-1 text-center"><span className="text-zinc-200 font-mono">{data.incident_log.mttr_minutes}m</span><p className="text-zinc-500">MTTR</p></div>
          </div></CardContent>
        </Card>
      )}
      <Button data-testid="refresh-report" size="sm" variant="outline" onClick={fetch_} className="text-xs"><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

/* ───── PART 10: GO-LIVE ───── */
function GoLivePanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => { setLoading(true); try { const r = await api.get("/pilot/go-live"); setData(r.data); } catch {} setLoading(false); }, []);
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  const dc = { GO: "bg-emerald-950/20 border-emerald-900/40", CONDITIONAL_GO: "bg-amber-950/20 border-amber-900/40", NO_GO: "bg-red-950/20 border-red-900/40" };
  const dtc = { GO: "text-emerald-400", CONDITIONAL_GO: "text-amber-400", NO_GO: "text-red-400" };
  return (
    <div data-testid="golive-panel" className="space-y-4">
      <Card className={dc[data.decision] || "bg-zinc-900 border-zinc-800"}>
        <CardContent className="pt-6 flex items-center gap-6">
          <ScoreGauge score={data.readiness_score} max={10} label="Readiness" />
          <div>
            <div className={`text-3xl font-bold ${dtc[data.decision]}`}>{data.decision?.replace(/_/g, " ")}</div>
            <p className="text-sm text-zinc-400 mt-1">{data.recommendation}</p>
            <div className="flex gap-2 mt-2">
              <Badge className={data.risk_level === "low" ? "bg-emerald-700 text-white" : data.risk_level === "medium" ? "bg-amber-700 text-white" : "bg-red-700 text-white"}>Risk: {data.risk_level}</Badge>
              <Badge variant="outline">{data.checklist_pass_rate}% checklist</Badge>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Go-Live Checklist</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          {data.go_live_checklist?.map((c, i) => (
            <div key={i} className="flex items-center gap-2 text-xs bg-zinc-800/50 rounded p-2">
              {c.passed ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" /> : <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />}
              <span className="text-zinc-300 flex-1">{c.item}</span>
              <span className="text-zinc-500 text-[10px]">{c.evidence}</span>
            </div>
          ))}
        </CardContent>
      </Card>
      {data.pilot_summary && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Pilot Summary</CardTitle></CardHeader>
          <CardContent><div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
            {Object.entries(data.pilot_summary).map(([k, v]) => (
              <div key={k} className="bg-zinc-800/50 rounded p-2 text-center"><span className="text-zinc-200 font-mono">{typeof v === "number" ? v.toLocaleString() : v}</span><p className="text-zinc-500">{k.replace(/_/g, " ")}</p></div>
            ))}
          </div></CardContent>
        </Card>
      )}
      {data.next_steps?.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Next Steps</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {data.next_steps.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-xs bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-500 font-mono w-5">{i + 1}.</span>
                <span className="text-zinc-300">{s}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      <Button data-testid="refresh-golive" size="sm" variant="outline" onClick={fetch_} className="text-xs"><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}
