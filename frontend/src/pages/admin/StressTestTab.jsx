import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Progress } from "../../components/ui/progress";
import {
  Activity, AlertTriangle, Database, RefreshCw, CheckCircle2, XCircle,
  Zap, Play, Target, Server, Shield, CreditCard, HardDrive, Users, BarChart3, FileText
} from "lucide-react";
import { api } from "../../lib/api";

/* ========== SCORE GAUGE ========== */
function ScoreGauge({ score, max, label, size = "lg" }) {
  const pct = (score / max) * 100;
  const color = score >= 8 ? "text-emerald-400" : score >= 5 ? "text-amber-400" : "text-red-400";
  const dim = size === "lg" ? "w-32 h-32" : "w-20 h-20";
  const textSize = size === "lg" ? "text-2xl" : "text-lg";
  const subSize = size === "lg" ? "text-xs" : "text-[10px]";
  return (
    <div data-testid={`stress-gauge-${label?.replace(/\s/g, "-").toLowerCase()}`} className="flex flex-col items-center gap-1.5">
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

/* ========== TEST CARD (reusable) ========== */
function TestCard({ testId, icon: Icon, title, desc, endpoint, method = "post", children }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const run = async () => {
    setLoading(true);
    try {
      const res = method === "post" ? await api.post(endpoint) : await api.get(endpoint);
      setResult(res.data);
    } catch (e) {
      setResult({ verdict: "ERROR", error: e.message });
    }
    setLoading(false);
  };

  const verdictColor = result?.verdict === "PASS"
    ? "bg-emerald-900/30 border-emerald-800"
    : result?.verdict === "FAIL"
      ? "bg-red-900/30 border-red-800"
      : "bg-amber-900/30 border-amber-800";

  return (
    <Card data-testid={testId} className="bg-zinc-900 border-zinc-800">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Icon className="w-4 h-4 text-zinc-400" />{title}
        </CardTitle>
      </CardHeader>
      <CardContent className="text-xs space-y-3">
        <p className="text-zinc-500">{desc}</p>
        <Button data-testid={`${testId}-run`} size="sm" variant="outline" className="text-xs w-full" disabled={loading} onClick={run}>
          {loading ? "Running..." : "Run Test"}
        </Button>
        {result && (
          <div data-testid={`${testId}-result`} className={`p-3 rounded border ${verdictColor}`}>
            <div className="flex items-center gap-2 mb-2">
              {result.verdict === "PASS" ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : result.verdict === "FAIL" ? <XCircle className="w-4 h-4 text-red-400" /> : <AlertTriangle className="w-4 h-4 text-amber-400" />}
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

/* ========== SLA Badge Row ========== */
function SLAChecks({ checks }) {
  if (!checks) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {Object.entries(checks).map(([k, v]) => (
        <Badge key={k} data-testid={`sla-${k}`} className={`text-[10px] ${v ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"}`}>
          {v ? "\u2713" : "\u2717"} {k.replace(/_/g, " ")}
        </Badge>
      ))}
    </div>
  );
}

/* ========== MAIN TAB ========== */
export default function StressTestTab() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activePanel, setActivePanel] = useState("overview");

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/stress-test/dashboard");
      setDashboard(res.data);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  const panels = [
    { id: "overview", label: "Overview", icon: Target },
    { id: "load", label: "Load Test", icon: Zap },
    { id: "queue", label: "Queue Stress", icon: Server },
    { id: "supplier", label: "Supplier Outage", icon: AlertTriangle },
    { id: "payment", label: "Payment Failure", icon: CreditCard },
    { id: "cache", label: "Cache Failure", icon: HardDrive },
    { id: "database", label: "DB Stress", icon: Database },
    { id: "incident", label: "Incident Response", icon: Activity },
    { id: "tenant", label: "Tenant Safety", icon: Users },
    { id: "metrics", label: "Metrics", icon: BarChart3 },
    { id: "report", label: "Report", icon: FileText },
  ];

  return (
    <div data-testid="stress-test-tab" className="space-y-4">
      {/* Top Score Bar */}
      <div className="flex items-center gap-4 bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <ScoreGauge score={dashboard?.readiness_score ?? 0} max={10} label="Stress Score" size="sm" />
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="bg-zinc-800/50 rounded p-2">
            <span className="text-zinc-500 block">Tests Run</span>
            <span data-testid="tests-run" className="text-zinc-200 font-mono">{dashboard?.tests_run ?? 0}/{dashboard?.tests_total ?? 8}</span>
          </div>
          <div className="bg-zinc-800/50 rounded p-2">
            <span className="text-zinc-500 block">Tests Passed</span>
            <span data-testid="tests-passed" className="text-zinc-200 font-mono">{dashboard?.tests_passed ?? 0}</span>
          </div>
          <div className="bg-zinc-800/50 rounded p-2">
            <span className="text-zinc-500 block">Bottlenecks</span>
            <span data-testid="bottlenecks" className="text-zinc-200 font-mono">{dashboard?.bottlenecks?.length ?? 0}</span>
          </div>
          <div className="bg-zinc-800/50 rounded p-2">
            <span className="text-zinc-500 block">Status</span>
            <Badge data-testid="stress-status" className={dashboard?.meets_target ? "bg-emerald-600 text-white" : "bg-amber-600 text-white"}>
              {dashboard?.meets_target ? "TARGET MET" : "PENDING"}
            </Badge>
          </div>
        </div>
        <Button data-testid="refresh-stress" size="sm" variant="outline" onClick={fetchDashboard} className="text-xs">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Sub-panel nav */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {panels.map(p => (
          <button key={p.id} data-testid={`stress-panel-${p.id}`} onClick={() => setActivePanel(p.id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap transition-colors ${activePanel === p.id ? "bg-zinc-700 text-white" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"}`}>
            <p.icon className="w-3.5 h-3.5" />{p.label}
          </button>
        ))}
      </div>

      {/* Panel Content */}
      {activePanel === "overview" && <OverviewPanel dashboard={dashboard} loading={loading} />}
      {activePanel === "load" && <LoadTestPanel />}
      {activePanel === "queue" && <QueueStressPanel />}
      {activePanel === "supplier" && <SupplierOutagePanel />}
      {activePanel === "payment" && <PaymentFailurePanel />}
      {activePanel === "cache" && <CacheFailurePanel />}
      {activePanel === "database" && <DatabaseStressPanel />}
      {activePanel === "incident" && <IncidentResponsePanel />}
      {activePanel === "tenant" && <TenantSafetyPanel />}
      {activePanel === "metrics" && <MetricsPanel />}
      {activePanel === "report" && <ReportPanel />}
    </div>
  );
}

/* ========== OVERVIEW PANEL ========== */
function OverviewPanel({ dashboard, loading }) {
  if (loading || !dashboard) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="stress-overview" className="space-y-4">
      {/* Component Status Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Object.entries(dashboard.components || {}).map(([key, comp]) => (
          <Card key={key} className="bg-zinc-900 border-zinc-800">
            <CardContent className="pt-4 text-center">
              <div className={`text-lg font-bold ${comp.status === "pass" ? "text-emerald-400" : comp.status === "fail" ? "text-red-400" : "text-zinc-600"}`}>
                {comp.status === "pass" ? "PASS" : comp.status === "fail" ? "FAIL" : "---"}
              </div>
              <p className="text-[10px] text-zinc-500 mt-1 uppercase">{key.replace(/_/g, " ")}</p>
              <p className="text-[10px] text-zinc-600">weight: {(comp.weight * 100)}%</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* SLA Compliance */}
      {dashboard.sla_compliance && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">SLA Compliance</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
              {Object.entries(dashboard.sla_compliance).map(([k, v]) => (
                <div key={k} className="flex items-center gap-2 bg-zinc-800/50 rounded p-2">
                  {v ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}
                  <span className="text-zinc-300">{k.replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bottlenecks */}
      {dashboard.bottlenecks?.length > 0 && (
        <Card className="bg-red-950/20 border-red-900/40">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Bottlenecks ({dashboard.bottlenecks.length})</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {dashboard.bottlenecks.map((b, i) => (
              <div key={i} className="flex items-center gap-2 text-xs bg-zinc-900/50 rounded p-2">
                <Badge variant={b.severity === "high" ? "destructive" : "default"} className="text-[10px]">{b.severity}</Badge>
                <span className="text-zinc-300">{b.detail}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Recent History */}
      {dashboard.recent_history?.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Recent Test Runs</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-1 text-xs">
              {dashboard.recent_history.map((h, i) => (
                <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                  <span className="text-zinc-300">{h.type.replace(/_/g, " ")}</span>
                  <div className="flex items-center gap-2">
                    <Badge className={h.verdict === "PASS" ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"}>{h.verdict}</Badge>
                    <span className="text-zinc-500">{h.duration_seconds}s</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ========== PART 1 — LOAD TEST ========== */
function LoadTestPanel() {
  return (
    <TestCard testId="load-test" icon={Zap} title="Part 1 — Load Testing" desc="Simulate 10k searches/hr and 1k bookings/hr. Measures API latency, supplier latency, worker throughput." endpoint="/stress-test/load">
      {(r) => (
        <div className="space-y-2 text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Search OK</span><br/><span className="text-zinc-200 font-mono">{r.search_summary?.total_ok}</span></div>
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Booking OK</span><br/><span className="text-zinc-200 font-mono">{r.booking_summary?.total_ok}</span></div>
          </div>
          {r.api_latency && (
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Search P95</span><br/><span className="text-zinc-200 font-mono">{r.api_latency.search_p95_ms}ms</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Booking P95</span><br/><span className="text-zinc-200 font-mono">{r.api_latency.booking_p95_ms}ms</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Search Max</span><br/><span className="text-zinc-200 font-mono">{r.api_latency.search_max_ms}ms</span></div>
            </div>
          )}
          {r.supplier_latency && (
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(r.supplier_latency).map(([k, v]) => (
                <div key={k} className="bg-zinc-800/50 rounded p-2">
                  <span className="text-zinc-500 capitalize">{k}</span><br/>
                  <span className="text-zinc-200 font-mono">{v.avg_ms}ms</span>
                  <span className="text-zinc-600 ml-1">P95:{v.p95_ms}ms</span>
                </div>
              ))}
            </div>
          )}
          <SLAChecks checks={r.sla_check} />
        </div>
      )}
    </TestCard>
  );
}

/* ========== PART 2 — QUEUE STRESS ========== */
function QueueStressPanel() {
  return (
    <TestCard testId="queue-stress" icon={Server} title="Part 2 — Queue Stress Test" desc="Inject 5k jobs across all queues. Verify autoscaling and job completion." endpoint="/stress-test/queue">
      {(r) => (
        <div className="space-y-2 text-xs">
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Total Jobs</span><br/><span className="text-zinc-200 font-mono">{r.total_jobs}</span></div>
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Completed</span><br/><span className="text-emerald-400 font-mono">{r.total_completed}</span></div>
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Failed</span><br/><span className="text-red-400 font-mono">{r.total_failed}</span></div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-zinc-500">Completion:</span>
            <Progress value={r.completion_rate_pct} className="flex-1 h-2" />
            <span className="text-zinc-200 font-mono">{r.completion_rate_pct}%</span>
          </div>
          {r.autoscaling && (
            <div className="bg-zinc-800/50 rounded p-2">
              <p className="text-zinc-400">Workers: {r.autoscaling.initial_workers} → {r.autoscaling.peak_workers} (peak)</p>
              {r.autoscaling.scale_events?.map((e, i) => (
                <p key={i} className="text-zinc-500">{e.time}: {e.action} ({e.from}→{e.to}) — {e.reason}</p>
              ))}
            </div>
          )}
          <SLAChecks checks={r.sla_check} />
        </div>
      )}
    </TestCard>
  );
}

/* ========== PART 3 — SUPPLIER OUTAGE ========== */
function SupplierOutagePanel() {
  const [supplier, setSupplier] = useState("paximum");
  const suppliers = ["paximum", "aviationstack", "amadeus"];
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {suppliers.map(s => (
          <Button key={s} data-testid={`supplier-select-${s}`} size="sm" variant={supplier === s ? "default" : "outline"} className="text-xs capitalize" onClick={() => setSupplier(s)}>{s}</Button>
        ))}
      </div>
      <TestCard testId="supplier-outage" icon={AlertTriangle} title={`Part 3 — Supplier Outage: ${supplier}`} desc="Simulate supplier failure. Verify failover logic and fallback usage." endpoint={`/stress-test/supplier-outage/${supplier}`}>
        {(r) => (
          <div className="space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Failover To</span><br/><span className="text-zinc-200">{r.failover_target}</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Detection</span><br/><span className="text-zinc-200 font-mono">{r.detection_time_ms}ms</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Failover Time</span><br/><span className="text-zinc-200 font-mono">{r.failover_time_ms}ms</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Success Rate</span><br/><span className="text-emerald-400 font-mono">{r.success_rate_pct}%</span></div>
            </div>
            {r.circuit_breaker && (
              <div className="bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-400">Circuit Breaker: </span>
                <Badge className="bg-red-800/60 text-red-300 text-[10px]">{r.circuit_breaker.state}</Badge>
                <span className="text-zinc-500 ml-2">Failures: {r.circuit_breaker.consecutive_failures}</span>
              </div>
            )}
            <SLAChecks checks={r.sla_check} />
          </div>
        )}
      </TestCard>
    </div>
  );
}

/* ========== PART 4 — PAYMENT FAILURE ========== */
function PaymentFailurePanel() {
  return (
    <TestCard testId="payment-failure" icon={CreditCard} title="Part 4 — Payment Failure Test" desc="Simulate payment provider errors. Verify retry logic and incident logging." endpoint="/stress-test/payment-failure">
      {(r) => (
        <div className="space-y-2 text-xs">
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Total Failures</span><br/><span className="text-zinc-200 font-mono">{r.total_failures_simulated}</span></div>
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Retried</span><br/><span className="text-zinc-200 font-mono">{r.total_retried}</span></div>
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Recovered</span><br/><span className="text-emerald-400 font-mono">{r.total_recovered}</span></div>
          </div>
          {r.failure_scenarios?.map((s, i) => (
            <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
              <span className="text-zinc-300">{s.type}</span>
              <div className="flex gap-2">
                <span className="text-zinc-500">x{s.count}</span>
                <span className="text-zinc-400">retried:{s.retried}</span>
                <span className="text-emerald-400">recovered:{s.recovered}</span>
              </div>
            </div>
          ))}
          <SLAChecks checks={r.sla_check} />
        </div>
      )}
    </TestCard>
  );
}

/* ========== PART 5 — CACHE FAILURE ========== */
function CacheFailurePanel() {
  return (
    <TestCard testId="cache-failure" icon={HardDrive} title="Part 5 — Cache Failure Test" desc="Simulate Redis failure. Verify system degradation mode." endpoint="/stress-test/cache-failure">
      {(r) => (
        <div className="space-y-2 text-xs">
          {r.phases?.map((p, i) => (
            <div key={i} className="bg-zinc-800/50 rounded p-2">
              <Badge variant="outline" className="text-[10px] capitalize mb-1">{p.phase}</Badge>
              {p.avg_response_ms && <p className="text-zinc-400">Latency: {p.avg_response_ms}ms</p>}
              {p.throughput_rps && <p className="text-zinc-400">Throughput: {p.throughput_rps} rps</p>}
              {p.cache_hit_rate_pct !== undefined && <p className="text-zinc-400">Cache Hit: {p.cache_hit_rate_pct}%</p>}
              {p.reconnection_time_ms && <p className="text-zinc-400">Recovery: {p.full_recovery_time_ms}ms</p>}
            </div>
          ))}
          {r.impact_summary && (
            <div className="bg-zinc-800/50 rounded p-2">
              <p className="text-zinc-400">Latency increase: {r.impact_summary.latency_increase_factor}x</p>
              <p className="text-zinc-400">Throughput drop: {r.impact_summary.throughput_drop_pct}%</p>
            </div>
          )}
          <SLAChecks checks={r.sla_check} />
        </div>
      )}
    </TestCard>
  );
}

/* ========== PART 6 — DATABASE STRESS ========== */
function DatabaseStressPanel() {
  return (
    <TestCard testId="db-stress" icon={Database} title="Part 6 — Database Stress Test" desc="Simulate high DB load. Measure query latency and index performance." endpoint="/stress-test/database">
      {(r) => (
        <div className="space-y-2 text-xs">
          {r.summary && (
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Avg Query</span><br/><span className="text-zinc-200 font-mono">{r.summary.avg_query_latency_ms}ms</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Index Coverage</span><br/><span className="text-zinc-200 font-mono">{r.summary.index_coverage_pct}%</span></div>
            </div>
          )}
          {r.collections?.map((c, i) => (
            <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
              <span className="text-zinc-300">{c.collection}</span>
              <div className="flex items-center gap-2">
                <Badge className={c.scan_type === "IXSCAN" ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"} variant="outline">{c.scan_type}</Badge>
                <span className="text-zinc-400 font-mono">{c.query_latency_ms}ms</span>
              </div>
            </div>
          ))}
          {r.write_test && (
            <div className="bg-zinc-800/50 rounded p-2">
              <p className="text-zinc-400">Writes: {r.write_test.completed}/{r.write_test.concurrent_writes} | Avg: {r.write_test.avg_write_latency_ms}ms</p>
            </div>
          )}
          <SLAChecks checks={r.sla_check} />
        </div>
      )}
    </TestCard>
  );
}

/* ========== PART 7 — INCIDENT RESPONSE ========== */
function IncidentResponsePanel() {
  const [incidentType, setIncidentType] = useState("supplier_outage");
  const types = ["supplier_outage", "queue_overload", "payment_failure", "database_slowdown"];
  return (
    <div className="space-y-3">
      <div className="flex gap-2 flex-wrap">
        {types.map(t => (
          <Button key={t} data-testid={`incident-select-${t}`} size="sm" variant={incidentType === t ? "default" : "outline"} className="text-xs" onClick={() => setIncidentType(t)}>
            {t.replace(/_/g, " ")}
          </Button>
        ))}
      </div>
      <TestCard testId="incident-response" icon={Activity} title={`Part 7 — Incident: ${incidentType.replace(/_/g, " ")}`} desc="Trigger incident and verify ops response workflow." endpoint={`/stress-test/incident/${incidentType}`}>
        {(r) => (
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <Badge variant={r.severity === "critical" ? "destructive" : "default"}>{r.severity}</Badge>
              <span className="text-zinc-400">Response: {r.total_response_time_ms}ms</span>
              <Badge className={r.within_sla ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"}>
                {r.within_sla ? "Within SLA" : "SLA Breach"}
              </Badge>
            </div>
            {r.steps?.map((s, i) => (
              <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-300">{s.step}</span>
                <div className="flex items-center gap-2">
                  <Badge className={s.result === "PASS" ? "bg-emerald-800/60 text-emerald-300" : "bg-amber-800/60 text-amber-300"}>{s.result}</Badge>
                  <span className="text-zinc-500 font-mono">{s.time_ms}ms</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </TestCard>
    </div>
  );
}

/* ========== PART 8 — TENANT SAFETY ========== */
function TenantSafetyPanel() {
  return (
    <TestCard testId="tenant-safety" icon={Users} title="Part 8 — Tenant Safety Test" desc="Simulate multi-tenant traffic. Verify zero cross-tenant data access." endpoint="/stress-test/tenant-safety">
      {(r) => (
        <div className="space-y-2 text-xs">
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Test Cases</span><br/><span className="text-zinc-200 font-mono">{r.total_test_cases}</span></div>
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Passed</span><br/><span className="text-emerald-400 font-mono">{r.passed}</span></div>
            <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500">Failed</span><br/><span className={`font-mono ${r.failed > 0 ? "text-red-400" : "text-zinc-200"}`}>{r.failed}</span></div>
          </div>
          {r.isolation_mechanisms && (
            <div className="bg-zinc-800/50 rounded p-2">
              <p className="text-zinc-400 mb-1">Isolation Mechanisms:</p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(r.isolation_mechanisms).map(([k, v]) => (
                  <Badge key={k} className={v ? "bg-emerald-800/60 text-emerald-300" : "bg-red-800/60 text-red-300"}>
                    {k.replace(/_/g, " ")}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          <SLAChecks checks={r.sla_check} />
        </div>
      )}
    </TestCard>
  );
}

/* ========== PART 9 — METRICS ========== */
function MetricsPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/stress-test/metrics");
      setData(res.data);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetch_(); }, [fetch_]);

  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  const m = data.metrics;

  return (
    <div data-testid="metrics-panel" className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-zinc-200" data-testid="p95-search">{m.p95_latency.search_ms}ms</p>
            <p className="text-[10px] text-zinc-500">Search P95</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-zinc-200" data-testid="p95-booking">{m.p95_latency.booking_ms}ms</p>
            <p className="text-[10px] text-zinc-500">Booking P95</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 text-center">
            <p className={`text-2xl font-bold ${m.error_rate.within_target ? "text-emerald-400" : "text-red-400"}`} data-testid="error-rate">{m.error_rate.current_pct}%</p>
            <p className="text-[10px] text-zinc-500">Error Rate</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold text-zinc-200" data-testid="queue-total">{m.queue_depth.total}</p>
            <p className="text-[10px] text-zinc-500">Queue Depth</p>
          </CardContent>
        </Card>
      </div>

      {/* Supplier Availability */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Supplier Availability</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-3 text-xs">
            {Object.entries(m.supplier_availability || {}).map(([k, v]) => (
              <div key={k} className="bg-zinc-800/50 rounded p-3 text-center">
                <Badge className={v.available ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{v.available ? "UP" : "DOWN"}</Badge>
                <p className="text-zinc-300 capitalize mt-1">{k}</p>
                <p className="text-zinc-500">{v.uptime_pct}% uptime</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Queue Depth Breakdown */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Queue Depth</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-5 gap-2 text-xs">
            {["booking", "voucher", "notification", "incident", "cleanup"].map(q => (
              <div key={q} className="bg-zinc-800/50 rounded p-2 text-center">
                <span className="text-zinc-200 font-mono">{m.queue_depth[q]}</span>
                <p className="text-zinc-500 capitalize">{q}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Button data-testid="refresh-metrics" size="sm" variant="outline" onClick={fetch_} className="text-xs">
        <RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh Metrics
      </Button>
    </div>
  );
}

/* ========== PART 10 — REPORT ========== */
function ReportPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/stress-test/report");
      setData(res.data);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetch_(); }, [fetch_]);

  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;

  return (
    <div data-testid="report-panel" className="space-y-4">
      {/* Final Score */}
      <Card className={data.meets_target ? "bg-emerald-950/20 border-emerald-900/40" : "bg-red-950/20 border-red-900/40"}>
        <CardContent className="pt-6 flex items-center gap-6">
          <ScoreGauge score={data.readiness_score} max={10} label="Readiness" />
          <div>
            <div className={`text-2xl font-bold ${data.meets_target ? "text-emerald-400" : "text-red-400"}`}>
              {data.recommendation}
            </div>
            <p className="text-sm text-zinc-400 mt-1">Target: {data.target}/10 | Gap: {data.gap}</p>
            <p className="text-xs text-zinc-500">Tests: {data.tests_passed}/{data.tests_total} passed</p>
          </div>
        </CardContent>
      </Card>

      {/* Score Components */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Score Components</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            {Object.entries(data.components || {}).map(([k, v]) => (
              <div key={k} className="bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-500 capitalize block">{k.replace(/_/g, " ")}</span>
                <span className={`font-mono font-bold ${v.score >= 9 ? "text-emerald-400" : v.score >= 7 ? "text-amber-400" : "text-red-400"}`}>{typeof v.score === "number" ? v.score.toFixed(1) : v.score}/10</span>
                <span className="text-zinc-600 ml-1">({(v.weight * 100)}%)</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Capacity Limits */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Capacity Limits</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            {Object.entries(data.capacity_limits || {}).map(([k, v]) => (
              <div key={k} className="flex justify-between bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-400">{k.replace(/_/g, " ")}</span>
                <span className="font-mono text-zinc-200">{typeof v === "boolean" ? (v ? "Yes" : "No") : v.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* SLA */}
      {data.sla_compliance && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">SLA Compliance</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
              {Object.entries(data.sla_compliance).map(([k, v]) => (
                <div key={k} className="flex items-center gap-2 bg-zinc-800/50 rounded p-2">
                  {v ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}
                  <span className="text-zinc-300">{k.replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Button data-testid="refresh-report" size="sm" variant="outline" onClick={fetch_} className="text-xs">
        <RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh Report
      </Button>
    </div>
  );
}
