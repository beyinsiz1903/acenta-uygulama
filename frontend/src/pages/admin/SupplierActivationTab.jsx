import React, { useState, useCallback, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Progress } from "../../components/ui/progress";
import {
  RefreshCw, Target, Shield, Zap, Activity, AlertTriangle, Scale,
  CheckCircle2, XCircle, Play, Eye, Radio, Gauge, Layers,
  TrendingUp, ChevronDown, ChevronUp, ArrowRight, FlaskConical
} from "lucide-react";
import { api } from "../../lib/api";

function useApi(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(path);
      setData(res.data);
    } catch {}
    setLoading(false);
  }, [path]);
  useEffect(() => { fetch_(); }, [fetch_]);
  return { data, loading, refetch: fetch_ };
}

function ScoreGauge({ score, max, label, size = "lg" }) {
  const pct = (score / max) * 100;
  const color = score >= 8 ? "text-emerald-400" : score >= 5 ? "text-amber-400" : "text-red-400";
  const dim = size === "lg" ? "w-32 h-32" : "w-20 h-20";
  const textSize = size === "lg" ? "text-2xl" : "text-lg";
  const subSize = size === "lg" ? "text-xs" : "text-[10px]";
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className={`relative ${dim}`}>
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor" className="text-zinc-800" strokeWidth="8" />
          <circle cx="50" cy="50" r="42" fill="none" stroke="currentColor" className={color} strokeWidth="8" strokeDasharray={`${pct * 2.64} 264`} strokeLinecap="round" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${textSize} font-bold ${color}`}>{score}</span>
          <span className={`${subSize} text-zinc-500`}>/{max}</span>
        </div>
      </div>
      {label && <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider text-center leading-tight">{label}</span>}
    </div>
  );
}

const modeBadge = (mode) => {
  const cls = { sandbox: "bg-blue-600", shadow: "bg-purple-600", canary: "bg-amber-600", production: "bg-emerald-600" }[mode] || "bg-zinc-600";
  return <Badge className={`${cls} text-white text-[10px]`}>{mode?.toUpperCase()}</Badge>;
};

const healthBadge = (state) => {
  const cls = { healthy: "bg-emerald-600", degraded: "bg-amber-600", critical: "bg-red-600" }[state] || "bg-zinc-600";
  return <Badge data-testid={`health-${state}`} className={`${cls} text-white text-[10px]`}>{state}</Badge>;
};

/* ========== MAIN SUPPLIER ACTIVATION TAB ========== */
export default function SupplierActivationTab() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [simLoading, setSimLoading] = useState({});
  const [simResults, setSimResults] = useState({});
  const { data: dashboard, loading, refetch } = useApi("/supplier-activation/dashboard");

  const runAction = async (key, method, endpoint) => {
    setSimLoading(p => ({ ...p, [key]: true }));
    try {
      const res = method === "get" ? await api.get(endpoint) : await api.post(endpoint);
      setSimResults(p => ({ ...p, [key]: res.data }));
    } catch (e) {
      setSimResults(p => ({ ...p, [key]: { error: e.message, verdict: "ERROR" } }));
    }
    setSimLoading(p => ({ ...p, [key]: false }));
  };

  if (loading) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  if (!dashboard) return <div className="text-zinc-400 text-sm p-4">Supplier activation dashboard could not be loaded.</div>;

  const subTabs = [
    { id: "dashboard", label: "Dashboard", icon: Gauge },
    { id: "plan", label: "Activation Plan", icon: Layers },
    { id: "shadow", label: "Shadow Traffic", icon: Eye },
    { id: "canary", label: "Canary Deploy", icon: Radio },
    { id: "normalization", label: "Normalization", icon: Shield },
    { id: "failover", label: "Failover", icon: AlertTriangle },
    { id: "ratelimits", label: "Rate Limits", icon: Scale },
    { id: "health", label: "Health", icon: Activity },
    { id: "incidents", label: "Incidents", icon: FlaskConical },
    { id: "traffic", label: "Traffic Analysis", icon: TrendingUp },
    { id: "score", label: "Score", icon: Target },
  ];

  return (
    <div data-testid="supplier-activation-tab" className="space-y-4">
      {/* Top Score Bar */}
      <div className="flex items-center gap-4 bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <ScoreGauge score={dashboard.activation_score} max={10} label="Activation Score" size="sm" />
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Suppliers</span><span data-testid="supplier-count" className="text-zinc-200 font-mono">{dashboard.suppliers?.length || 0}</span></div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Canary Active</span><span data-testid="canary-active" className="text-zinc-200 font-mono">{dashboard.canary_active}</span></div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Health</span><span data-testid="health-summary" className="text-zinc-200 font-mono">{dashboard.health_summary?.healthy || 0} ok</span></div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Checklist</span><span data-testid="checklist-pass" className="text-zinc-200 font-mono">{dashboard.checklist_pass_rate}%</span></div>
        </div>
        <Button data-testid="refresh-activation" size="sm" variant="outline" onClick={refetch} className="text-xs"><RefreshCw className="w-3.5 h-3.5" /></Button>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {subTabs.map(t => (
          <button key={t.id} data-testid={`sa-tab-${t.id}`} onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap transition-colors ${activeTab === t.id ? "bg-zinc-700 text-white" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"}`}>
            <t.icon className="w-3.5 h-3.5" />{t.label}
          </button>
        ))}
      </div>

      {/* Dashboard */}
      {activeTab === "dashboard" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">Supplier Status</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1">
              {(dashboard.suppliers || []).map(s => (
                <div key={s.code} data-testid={`supplier-${s.code}`} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-300 capitalize font-medium">{s.name}</span>
                    <Badge variant="outline" className="text-[10px]">P{s.priority}</Badge>
                  </div>
                  {modeBadge(s.mode)}
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">Health Overview</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-emerald-900/30 border border-emerald-800/50 rounded p-2 text-center">
                  <div className="text-lg font-bold text-emerald-400">{dashboard.health_summary?.healthy || 0}</div>
                  <div className="text-[10px] text-zinc-500">Healthy</div>
                </div>
                <div className="bg-amber-900/30 border border-amber-800/50 rounded p-2 text-center">
                  <div className="text-lg font-bold text-amber-400">{dashboard.health_summary?.degraded || 0}</div>
                  <div className="text-[10px] text-zinc-500">Degraded</div>
                </div>
                <div className="bg-red-900/30 border border-red-800/50 rounded p-2 text-center">
                  <div className="text-lg font-bold text-red-400">{dashboard.health_summary?.critical || 0}</div>
                  <div className="text-[10px] text-zinc-500">Critical</div>
                </div>
              </div>
              <div className="flex items-center gap-2 text-zinc-400">
                <span>Failover Chains: {dashboard.failover_chains}</span>
                <span>|</span>
                <span>Rate Limiters: {dashboard.rate_limiters}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Plan */}
      {activeTab === "plan" && <ActivationPlanPanel />}

      {/* Shadow Traffic */}
      {activeTab === "shadow" && <ShadowTrafficPanel runAction={runAction} simLoading={simLoading} simResults={simResults} />}

      {/* Canary */}
      {activeTab === "canary" && <CanaryPanel runAction={runAction} simLoading={simLoading} simResults={simResults} />}

      {/* Normalization */}
      {activeTab === "normalization" && <NormalizationPanel runAction={runAction} simLoading={simLoading} simResults={simResults} />}

      {/* Failover */}
      {activeTab === "failover" && <FailoverPanel runAction={runAction} simLoading={simLoading} simResults={simResults} />}

      {/* Rate Limits */}
      {activeTab === "ratelimits" && <RateLimitPanel runAction={runAction} simLoading={simLoading} simResults={simResults} />}

      {/* Health */}
      {activeTab === "health" && <HealthPanel />}

      {/* Incidents */}
      {activeTab === "incidents" && <IncidentPanel runAction={runAction} simLoading={simLoading} simResults={simResults} />}

      {/* Traffic Analysis */}
      {activeTab === "traffic" && <TrafficAnalysisPanel />}

      {/* Score */}
      {activeTab === "score" && <ActivationScorePanel />}
    </div>
  );
}

/* ========== PART 1: Activation Plan ========== */
function ActivationPlanPanel() {
  const { data, loading } = useApi("/supplier-activation/plan");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data.suppliers.map(s => (
          <Card key={s.code} data-testid={`plan-${s.code}`} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">{s.name} <Badge variant="outline" className="text-[10px]">P{s.rollout_priority}</Badge></CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-zinc-400 space-y-2">
              <div>
                <span className="text-zinc-500 block">Auth:</span>
                <span className="text-zinc-300">{s.auth.method} | Header: {s.auth.header_name}</span>
              </div>
              <div>
                <span className="text-zinc-500 block">Rate Limits:</span>
                <span className="text-zinc-300">{s.rate_limits.requests_per_second} rps | {s.rate_limits.daily_quota?.toLocaleString()} daily</span>
              </div>
              <div>
                <span className="text-zinc-500 block">Endpoints:</span>
                <div className="text-zinc-300 truncate text-[10px]">Sandbox: {s.endpoints.sandbox}</div>
                <div className="text-zinc-300 truncate text-[10px]">Prod: {s.endpoints.production}</div>
              </div>
              <div>
                <span className="text-zinc-500 block">Timeouts:</span>
                <span className="text-zinc-300">Connect: {s.timeouts.connect_ms}ms | Read: {s.timeouts.read_ms}ms</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-zinc-500">Mode:</span>{modeBadge(s.current_mode)}
                <span className="text-zinc-500 ml-2">Status:</span>
                <Badge variant="outline" className="text-[10px]">{s.activation_status}</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Rollout Phases</CardTitle></CardHeader>
        <CardContent className="text-xs">
          <div className="flex items-center gap-2">
            {data.rollout_phases.map((p, i) => (
              <React.Fragment key={p.phase}>
                <div className="bg-zinc-800/50 rounded p-3 text-center flex-1">
                  <div className="text-zinc-300 font-medium">Phase {p.phase}</div>
                  <div className="text-zinc-500 capitalize">{p.supplier}</div>
                  <div className="text-[10px] text-zinc-600 mt-1">{p.scope}</div>
                  <div className="text-[10px] text-zinc-600">{p.timeline}</div>
                </div>
                {i < data.rollout_phases.length - 1 && <ArrowRight className="w-4 h-4 text-zinc-600 flex-shrink-0" />}
              </React.Fragment>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/* ========== PART 2: Shadow Traffic ========== */
function ShadowTrafficPanel({ runAction, simLoading, simResults }) {
  const suppliers = ["paximum", "aviationstack", "amadeus"];
  return (
    <div className="space-y-3">
      <p className="text-xs text-zinc-500">Shadow traffic sends supplier requests without affecting production. Compares internal pricing vs supplier responses.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {suppliers.map(code => (
          <Card key={code} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize">{code}</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-2">
              <Button data-testid={`shadow-${code}`} size="sm" variant="outline" className="text-xs w-full"
                disabled={simLoading[`shadow_${code}`]}
                onClick={() => runAction(`shadow_${code}`, "post", `/supplier-activation/shadow/${code}`)}>
                {simLoading[`shadow_${code}`] ? "Running..." : "Run Shadow Traffic"}
              </Button>
              {simResults[`shadow_${code}`] && (
                <ShadowResult data={simResults[`shadow_${code}`]} />
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ShadowResult({ data }) {
  if (data.error) return <div className="text-red-400 text-xs">{data.error}</div>;
  return (
    <div data-testid="shadow-result" className={`p-2 rounded text-xs ${data.verdict === "PASS" ? "bg-emerald-900/30 border border-emerald-800" : "bg-amber-900/30 border border-amber-800"}`}>
      <p className="font-mono font-bold">{data.verdict}</p>
      <div className="grid grid-cols-2 gap-1 mt-1 text-zinc-400">
        <span>Success: {data.success_rate_pct}%</span>
        <span>Latency: {data.avg_latency_ms}ms</span>
        <span>Price Diff: {data.avg_price_diff_pct}%</span>
        <span>Schema: {data.schema_valid_pct}%</span>
      </div>
    </div>
  );
}

/* ========== PART 3: Canary Deploy ========== */
function CanaryPanel({ runAction, simLoading, simResults }) {
  const { data, loading, refetch } = useApi("/supplier-activation/canary");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <p className="text-xs text-zinc-500">Canary deployment activates suppliers for a small percentage of traffic with auto-rollback on errors.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {data.canary_configs.map(cfg => (
          <Card key={cfg.supplier_code} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                {cfg.supplier_name}
                {cfg.enabled ? <Badge className="bg-emerald-600 text-white text-[10px]">ACTIVE</Badge> : <Badge variant="outline" className="text-[10px]">INACTIVE</Badge>}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-zinc-500">Traffic:</span>
                <span className="text-zinc-200 font-mono font-bold">{cfg.traffic_pct}%</span>
                <Progress value={cfg.traffic_pct} className="flex-1 h-1.5" />
              </div>
              <div className="text-zinc-500">Max: {cfg.max_pct}% | Step: +{cfg.step_pct}% | Error threshold: {cfg.error_threshold}%</div>
              {healthBadge(cfg.health)}
              <div className="flex gap-1 flex-wrap">
                <Button size="sm" variant="outline" className="text-[10px] h-6 px-2" disabled={cfg.enabled}
                  onClick={async () => { await api.post(`/supplier-activation/canary/${cfg.supplier_code}/enable`); refetch(); }}>Enable</Button>
                <Button size="sm" variant="outline" className="text-[10px] h-6 px-2" disabled={!cfg.enabled}
                  onClick={async () => { await api.post(`/supplier-activation/canary/${cfg.supplier_code}/promote`); refetch(); }}>Promote</Button>
                <Button size="sm" variant="outline" className="text-[10px] h-6 px-2 text-red-400" disabled={!cfg.enabled}
                  onClick={async () => { await api.post(`/supplier-activation/canary/${cfg.supplier_code}/rollback`); refetch(); }}>Rollback</Button>
                <Button size="sm" variant="outline" className="text-[10px] h-6 px-2" disabled={!cfg.enabled || simLoading[`canary_sim_${cfg.supplier_code}`]}
                  onClick={() => runAction(`canary_sim_${cfg.supplier_code}`, "post", `/supplier-activation/canary/${cfg.supplier_code}/simulate`)}>Simulate</Button>
              </div>
              {simResults[`canary_sim_${cfg.supplier_code}`] && (
                <div data-testid={`canary-result-${cfg.supplier_code}`} className={`p-2 rounded ${simResults[`canary_sim_${cfg.supplier_code}`].verdict === "PASS" ? "bg-emerald-900/30 border border-emerald-800" : "bg-red-900/30 border border-red-800"}`}>
                  <p className="font-mono font-bold">{simResults[`canary_sim_${cfg.supplier_code}`].verdict}</p>
                  {simResults[`canary_sim_${cfg.supplier_code}`].metrics && (
                    <div className="text-zinc-400 mt-1">
                      <p>Error: {simResults[`canary_sim_${cfg.supplier_code}`].metrics.error_rate_pct}%</p>
                      <p>Latency: {simResults[`canary_sim_${cfg.supplier_code}`].metrics.avg_latency_ms}ms</p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ========== PART 4: Normalization ========== */
function NormalizationPanel({ runAction, simLoading, simResults }) {
  const suppliers = ["paximum", "aviationstack", "amadeus"];
  return (
    <div className="space-y-3">
      <p className="text-xs text-zinc-500">Validates supplier responses match internal schema. Tests field mapping, type coercion, and default values.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {suppliers.map(code => (
          <Card key={code} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize">{code}</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-2">
              <Button data-testid={`norm-${code}`} size="sm" variant="outline" className="text-xs w-full"
                disabled={simLoading[`norm_${code}`]}
                onClick={() => runAction(`norm_${code}`, "post", `/supplier-activation/normalization/${code}`)}>
                {simLoading[`norm_${code}`] ? "Testing..." : "Run Normalization Test"}
              </Button>
              {simResults[`norm_${code}`] && !simResults[`norm_${code}`].error && (
                <div data-testid={`norm-result-${code}`} className={`p-2 rounded ${simResults[`norm_${code}`].verdict === "PASS" ? "bg-emerald-900/30 border border-emerald-800" : "bg-amber-900/30 border border-amber-800"}`}>
                  <p className="font-mono font-bold">{simResults[`norm_${code}`].verdict}</p>
                  <p className="text-zinc-400">Conformance: {simResults[`norm_${code}`].conformance_pct}%</p>
                  <p className="text-zinc-400">Passed: {simResults[`norm_${code}`].passed}/{simResults[`norm_${code}`].total_samples}</p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ========== PART 5: Failover ========== */
function FailoverPanel({ runAction, simLoading, simResults }) {
  const { data, loading } = useApi("/supplier-activation/failover");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <p className="text-xs text-zinc-500">When a supplier fails: fallback to another supplier or cached inventory. Circuit breaker prevents cascade failures.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {data.failover_chains.map(chain => (
          <Card key={chain.primary} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize">{chain.primary}</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-2 text-zinc-400">
              <div>
                <span className="text-zinc-500">Fallbacks: </span>
                {chain.fallbacks.map((f, i) => (
                  <span key={f}>
                    <Badge variant="outline" className="text-[10px]">{f}</Badge>
                    {i < chain.fallbacks.length - 1 && <ArrowRight className="w-3 h-3 inline mx-1" />}
                  </span>
                ))}
              </div>
              <p>Cache TTL: {chain.cache_ttl_minutes}min | Max retries: {chain.max_retries_before_failover}</p>
              <p>Circuit: {chain.circuit_state} (failures: {chain.circuit_failures})</p>
              <Button data-testid={`failover-sim-${chain.primary}`} size="sm" variant="outline" className="text-xs w-full"
                disabled={simLoading[`fo_${chain.primary}`]}
                onClick={() => runAction(`fo_${chain.primary}`, "post", `/supplier-activation/failover/${chain.primary}/simulate`)}>
                {simLoading[`fo_${chain.primary}`] ? "Simulating..." : "Simulate Failover"}
              </Button>
              {simResults[`fo_${chain.primary}`] && (
                <div data-testid={`failover-result-${chain.primary}`} className={`p-2 rounded ${simResults[`fo_${chain.primary}`].verdict === "PASS" ? "bg-emerald-900/30 border border-emerald-800" : "bg-red-900/30 border border-red-800"}`}>
                  <p className="font-mono font-bold">{simResults[`fo_${chain.primary}`].verdict}</p>
                  <p className="text-zinc-400">Total latency: {simResults[`fo_${chain.primary}`].total_latency_ms}ms</p>
                  {simResults[`fo_${chain.primary}`].steps?.map((s, i) => (
                    <p key={i} className="text-zinc-500">{s.step}. {s.action}: <span className={s.result === "PASS" ? "text-emerald-400" : "text-red-400"}>{s.result}</span></p>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ========== PART 6: Rate Limits ========== */
function RateLimitPanel({ runAction, simLoading, simResults }) {
  const { data, loading } = useApi("/supplier-activation/rate-limits");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <p className="text-xs text-zinc-500">Token bucket + adaptive throttling prevents supplier API bans.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {data.rate_limiters.map(rl => (
          <Card key={rl.supplier_code} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">{rl.supplier_name}</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-2 text-zinc-400">
              <div className="grid grid-cols-2 gap-1">
                <span>RPS: <span className="text-zinc-200">{rl.config.requests_per_second}</span></span>
                <span>RPM: <span className="text-zinc-200">{rl.config.requests_per_minute}</span></span>
                <span>Daily: <span className="text-zinc-200">{rl.config.daily_quota?.toLocaleString()}</span></span>
                <span>Burst: <span className="text-zinc-200">{rl.config.burst_limit}</span></span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-zinc-500">Bucket:</span>
                <Progress value={rl.bucket.utilization_pct} className="flex-1 h-1.5" />
                <span className="text-zinc-300 font-mono">{rl.bucket.utilization_pct}%</span>
              </div>
              <p>Allowed: {rl.bucket.total_allowed} | Throttled: {rl.bucket.total_throttled}</p>
              <p>Adaptive: {rl.adaptive_throttling.current_state} | Backoff: {rl.adaptive_throttling.backoff_factor}x</p>
              <Button data-testid={`rl-sim-${rl.supplier_code}`} size="sm" variant="outline" className="text-xs w-full"
                disabled={simLoading[`rl_${rl.supplier_code}`]}
                onClick={() => runAction(`rl_${rl.supplier_code}`, "post", `/supplier-activation/rate-limits/${rl.supplier_code}/simulate?requests_count=100`)}>
                {simLoading[`rl_${rl.supplier_code}`] ? "Simulating..." : "Simulate 100 Requests"}
              </Button>
              {simResults[`rl_${rl.supplier_code}`] && (
                <div data-testid={`rl-result-${rl.supplier_code}`} className="p-2 rounded bg-zinc-800 border border-zinc-700">
                  <p className="font-mono font-bold">{simResults[`rl_${rl.supplier_code}`].verdict}</p>
                  <p>Allowed: {simResults[`rl_${rl.supplier_code}`].allowed} | Throttled: {simResults[`rl_${rl.supplier_code}`].throttled}</p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ========== PART 7: Health ========== */
function HealthPanel() {
  const { data, loading, refetch } = useApi("/supplier-activation/health");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-zinc-400">Supplier Health Monitoring — Tracks latency, error rate, availability</span>
        <Button size="sm" variant="ghost" onClick={refetch} className="ml-auto text-xs"><RefreshCw className="w-3 h-3" /></Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {data.suppliers.map(s => (
          <Card key={s.supplier_code} data-testid={`health-card-${s.supplier_code}`} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">{s.supplier_name} {healthBadge(s.health_state)}</CardTitle>
            </CardHeader>
            <CardContent className="text-xs space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-zinc-500">Score:</span>
                <span className={`font-bold font-mono ${s.health_score >= 80 ? "text-emerald-400" : s.health_score >= 60 ? "text-amber-400" : "text-red-400"}`}>{s.health_score}</span>
                <Progress value={s.health_score} className="flex-1 h-1.5" />
              </div>
              <div className="grid grid-cols-2 gap-1 text-zinc-400">
                <span>Latency avg: {s.metrics.latency_avg_ms}ms</span>
                <span>Latency p95: {s.metrics.latency_p95_ms}ms</span>
                <span>Error: {s.metrics.error_rate_pct}%</span>
                <span>Timeout: {s.metrics.timeout_rate_pct}%</span>
                <span>Availability: {s.metrics.availability_pct}%</span>
                <span>Calls (15m): {s.metrics.total_calls_15m}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ========== PART 8: Incidents ========== */
function IncidentPanel({ runAction, simLoading, simResults }) {
  const suppliers = ["paximum", "aviationstack", "amadeus"];
  return (
    <div className="space-y-3">
      <p className="text-xs text-zinc-500">Detect supplier outages, auto-degrade, and failover. Simulate incidents for testing.</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {suppliers.map(code => (
          <Card key={code} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize">{code} Incident Test</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-2">
              <Button data-testid={`incident-${code}`} size="sm" variant="outline" className="text-xs w-full"
                disabled={simLoading[`inc_${code}`]}
                onClick={() => runAction(`inc_${code}`, "post", `/supplier-activation/incident/${code}`)}>
                {simLoading[`inc_${code}`] ? "Detecting..." : "Simulate Outage"}
              </Button>
              {simResults[`inc_${code}`] && (
                <div data-testid={`incident-result-${code}`} className={`p-2 rounded ${simResults[`inc_${code}`].verdict === "INCIDENT_HANDLED" ? "bg-amber-900/30 border border-amber-800" : "bg-emerald-900/30 border border-emerald-800"}`}>
                  <p className="font-mono font-bold">{simResults[`inc_${code}`].verdict}</p>
                  <p className="text-zinc-400">Outage: {simResults[`inc_${code}`].outage_detected ? "YES" : "NO"}</p>
                  {simResults[`inc_${code}`].steps?.map((s, i) => (
                    <p key={i} className="text-zinc-500">{s.step}. {s.action}: <span className={s.result === "PASS" || s.result === "ACTIVE" || s.result === "SENT" ? "text-emerald-400" : s.result === "FAIL" || s.result === "CONFIRMED" ? "text-red-400" : "text-amber-400"}>{s.result}</span></p>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ========== PART 9: Traffic Analysis ========== */
function TrafficAnalysisPanel() {
  const { data, loading, refetch } = useApi("/supplier-activation/traffic-analysis");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-zinc-400">Supplier conversion rate, booking success rate, and revenue analysis</span>
        <Button size="sm" variant="ghost" onClick={refetch} className="ml-auto text-xs"><RefreshCw className="w-3 h-3" /></Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {data.suppliers.map(s => (
          <Card key={s.supplier_code} data-testid={`traffic-${s.supplier_code}`} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">{s.supplier_name}</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-2">
              <div className="text-zinc-400 space-y-0.5">
                <div className="flex justify-between"><span>Searches</span><span className="text-zinc-200 font-mono">{s.funnel.searches.toLocaleString()}</span></div>
                <div className="flex justify-between"><span>Detail Views</span><span className="text-zinc-200 font-mono">{s.funnel.detail_views.toLocaleString()}</span></div>
                <div className="flex justify-between"><span>Holds</span><span className="text-zinc-200 font-mono">{s.funnel.holds.toLocaleString()}</span></div>
                <div className="flex justify-between"><span>Bookings</span><span className="text-zinc-200 font-mono">{s.funnel.bookings.toLocaleString()}</span></div>
                <div className="flex justify-between"><span>Cancellations</span><span className="text-zinc-200 font-mono">{s.funnel.cancellations}</span></div>
              </div>
              <div className="border-t border-zinc-800 pt-2 text-zinc-400 space-y-0.5">
                <div className="flex justify-between"><span>Conversion</span><span className="text-emerald-400 font-mono font-bold">{s.rates.overall_conversion_pct}%</span></div>
                <div className="flex justify-between"><span>Booking Success</span><span className="text-emerald-400 font-mono">{s.rates.booking_success_rate_pct}%</span></div>
              </div>
              <div className="border-t border-zinc-800 pt-2 text-zinc-400 space-y-0.5">
                <div className="flex justify-between"><span>GMV</span><span className="text-zinc-200 font-mono">{s.revenue.total_gmv.toLocaleString()} {s.revenue.currency}</span></div>
                <div className="flex justify-between"><span>Commission</span><span className="text-zinc-200 font-mono">{s.revenue.total_commission.toLocaleString()} {s.revenue.currency}</span></div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ========== PART 10: Activation Score ========== */
function ActivationScorePanel() {
  const { data, loading, refetch } = useApi("/supplier-activation/score");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <ScoreGauge score={data.activation_score} max={10} label="Activation" />
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Badge data-testid="activation-meets-target" className={data.meets_target ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>
              {data.meets_target ? "TARGET MET" : "BELOW TARGET"}
            </Badge>
            <span className="text-xs text-zinc-400">Target: {data.target}/10 | Gap: {data.gap}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            {Object.entries(data.score_components || {}).map(([k, v]) => (
              <div key={k} className="bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-500 capitalize block text-[10px]">{k.replace(/_/g, " ")}</span>
                <span className={`font-mono font-bold ${v.score >= 9 ? "text-emerald-400" : v.score >= 7 ? "text-amber-400" : "text-red-400"}`}>{v.score}/10</span>
                <span className="text-zinc-600 ml-1 text-[10px]">({(v.weight * 100).toFixed(0)}%)</span>
                <p className="text-[10px] text-zinc-600 mt-0.5">{v.detail}</p>
              </div>
            ))}
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={refetch}><RefreshCw className="w-3.5 h-3.5" /></Button>
      </div>
      {data.risks?.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Risks</CardTitle></CardHeader>
          <CardContent className="text-xs space-y-1">
            {data.risks.map((r, i) => (
              <div key={i} className="flex items-center gap-2"><Badge variant="destructive" className="text-[10px]">{r.severity}</Badge><span className="text-zinc-400">{r.component}: {r.impact}</span></div>
            ))}
          </CardContent>
        </Card>
      )}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Deployment Checklist ({data.checklist_pass_rate}%)</CardTitle></CardHeader>
        <CardContent className="text-xs space-y-1">
          {(data.deployment_checklist || []).map((c, i) => (
            <div key={i} data-testid={`activation-checklist-${i}`} className="flex items-center gap-2 bg-zinc-800/50 rounded p-2">
              {c.status ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}
              <span className="text-zinc-300 flex-1">{c.item}</span>
              <Badge variant="outline" className="text-[10px]">{c.priority}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
