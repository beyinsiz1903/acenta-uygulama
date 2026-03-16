import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { RefreshCw, Gauge, Layers, AlertTriangle, Activity, FlaskConical, Eye, Zap, Radio, Target, Scale, CheckCircle2, XCircle } from "lucide-react";
import { ScoreGauge } from "./ScoreGauge";
import { useHardeningApi } from "../api";
import { api } from "../../../lib/api";

export function TrafficTestingTab() {
  const { data, loading } = useHardeningApi("/hardening/traffic/status");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  const gate = data.traffic_gate;
  return (
    <div data-testid="traffic-tab" className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(gate.modes).map(([sup, mode]) => (
          <Card key={sup} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize">{sup}</CardTitle></CardHeader>
            <CardContent>
              <Badge data-testid={`traffic-mode-${sup}`} className={mode === "sandbox" ? "bg-blue-600 text-white" : mode === "production" ? "bg-emerald-600 text-white" : "bg-amber-500 text-white"}>{mode.toUpperCase()}</Badge>
              <div className="mt-3 text-xs text-zinc-500">
                <p>Sandbox URL: {data.sandbox_environments[sup]?.url}</p>
                <p>Test scenarios: {data.sandbox_environments[sup]?.scenarios}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {data.recent_sandbox_results?.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader><CardTitle className="text-sm">Recent Sandbox Results</CardTitle></CardHeader>
          <CardContent><div className="text-xs text-zinc-400">
            {data.recent_sandbox_results.map((r, i) => (
              <div key={i} className="flex justify-between py-1 border-b border-zinc-800 last:border-0">
                <span>{r.supplier}</span><span>{r.results?.length || 0} tests</span><span>{r.run_at?.split("T")[0]}</span>
              </div>
            ))}
          </div></CardContent>
        </Card>
      )}
    </div>
  );
}

/* ─── Worker Strategy Sub-panels ─── */
function QueueMonitoringPanel() {
  const { data, loading, refetch } = useHardeningApi("/workers/monitoring");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Badge data-testid="redis-conn-status" className={data.redis_status === "connected" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>Redis: {data.redis_status}</Badge>
        <span className="text-xs text-zinc-400">Ops/sec: {data.redis_ops_per_sec}</span>
        <Button size="sm" variant="ghost" onClick={refetch} className="ml-auto text-xs"><RefreshCw className="w-3 h-3" /></Button>
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Queue Depths</CardTitle></CardHeader>
        <CardContent><div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {Object.entries(data.queue_depths || {}).map(([q, d]) => (
            <div key={q} className="flex justify-between bg-zinc-800/50 rounded p-2"><span className="text-zinc-400 truncate">{q}</span><span data-testid={`qdepth-${q}`} className="font-mono text-zinc-200">{d}</span></div>
          ))}
        </div></CardContent>
      </Card>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">DLQ Depths</CardTitle></CardHeader>
        <CardContent><div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {Object.entries(data.dlq_depths || {}).map(([q, d]) => (
            <div key={q} className="flex justify-between bg-zinc-800/50 rounded p-2"><span className="text-zinc-400 truncate">{q}</span><span data-testid={`dlqdepth-${q}`} className={`font-mono ${d > 0 ? "text-red-400" : "text-zinc-200"}`}>{d}</span></div>
          ))}
        </div></CardContent>
      </Card>
    </div>
  );
}

function WorkerPoolsPanel() {
  const { data: pools, loading } = useHardeningApi("/workers/pools");
  if (loading || !pools) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs text-zinc-400"><Layers className="w-4 h-4" /> {pools.total_pools} pools, {pools.total_queues} queues</div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {Object.entries(pools.pools || {}).map(([name, pool]) => (
          <Card key={name} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize flex items-center gap-2">{name} <Badge data-testid={`pool-priority-${name}`} variant="outline" className="text-[10px]">{pool.priority}</Badge></CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1 text-zinc-400">
              <p>Queues: <span className="text-zinc-300">{pool.queues?.join(", ")}</span></p>
              <p>Concurrency: <span className="text-zinc-300">{pool.concurrency}</span></p>
              <p>Autoscale: <span className="text-zinc-300">{pool.autoscale_min}-{pool.autoscale_max}</span></p>
              <p>Time Limit: <span className="text-zinc-300">{pool.soft_time_limit}s/{pool.time_limit}s</span></p>
              <p className="text-zinc-500 mt-1 text-[10px]">{pool.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function DLQPanel() {
  const { data: dlq, loading } = useHardeningApi("/workers/dlq");
  if (loading || !dlq) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Badge data-testid="dlq-status" className={dlq.status === "healthy" ? "bg-emerald-600 text-white" : "bg-amber-600 text-white"}>{dlq.status}</Badge>
        <span className="text-xs text-zinc-400">Dead Letters: {dlq.total_dead_letters} | Permanent Failures: {dlq.permanent_failures}</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {Object.entries(dlq.queues || {}).map(([q, d]) => (
          <div key={q} className="bg-zinc-800/50 rounded p-2 text-xs"><span className="text-zinc-500 block text-[10px]">{q}</span><span data-testid={`dlq-depth-${q}`} className="text-zinc-200 font-mono">{d.depth}</span></div>
        ))}
      </div>
    </div>
  );
}

function AutoscalingPanel() {
  const { data: autoscaling, loading } = useHardeningApi("/workers/autoscaling");
  if (loading || !autoscaling) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <div className="text-xs text-zinc-400">Pending: {autoscaling.metrics_snapshot?.total_pending} | DLQ: {autoscaling.metrics_snapshot?.total_dlq}</div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {Object.entries(autoscaling.decisions || {}).map(([name, d]) => (
          <Card key={name} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize">{name}</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1 text-zinc-400">
              <p>Action: <Badge data-testid={`autoscale-action-${name}`} className={d.action === "scale_up" ? "bg-amber-600 text-white" : d.action === "scale_down" ? "bg-blue-600 text-white" : ""} variant="outline">{d.action}</Badge></p>
              <p>Queue Depth: {d.current_depth}</p><p>Thresholds: up={d.scale_up_threshold}, down={d.scale_down_threshold}</p><p>Workers: {d.min_workers}-{d.max_workers}</p>
              <p className="text-zinc-500 text-[10px]">{d.reason}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      {autoscaling.rules && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Autoscale Rules</CardTitle></CardHeader>
          <CardContent className="text-xs"><div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {Object.entries(autoscaling.rules).map(([k, v]) => (
              <div key={k} className="bg-zinc-800/50 rounded p-2 text-zinc-400">
                <span className="text-zinc-300 capitalize font-medium">{k}</span>
                <p>Scale up: depth {">="} {v.scale_up.queue_depth_threshold} or latency {">="} {v.scale_up.latency_ms_threshold}ms</p>
                <p>Scale down: depth {"<="} {v.scale_down.queue_depth_threshold}, idle {v.scale_down.idle_minutes}m</p>
                <p>Cooldown: {v.cooldown_seconds}s</p>
              </div>
            ))}
          </div></CardContent>
        </Card>
      )}
    </div>
  );
}

function ObservabilityPanel() {
  const { data: observability, loading } = useHardeningApi("/workers/observability");
  if (loading || !observability) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><p className="text-2xl font-bold text-zinc-200" data-testid="worker-process-count">{observability.total_worker_processes}</p><p className="text-[10px] text-zinc-500">Worker Processes</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><p className="text-2xl font-bold text-zinc-200">{observability.cpu_usage?.total_pct}%</p><p className="text-[10px] text-zinc-500">CPU Usage</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><p className="text-2xl font-bold text-zinc-200">{observability.memory_usage?.total_rss_mb} MB</p><p className="text-[10px] text-zinc-500">Memory RSS</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><p className="text-2xl font-bold text-emerald-400">{observability.job_rates?.success_rate_pct}%</p><p className="text-[10px] text-zinc-500">Success Rate</p></CardContent></Card>
      </div>
      {observability.worker_processes?.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Worker Processes</CardTitle></CardHeader>
          <CardContent className="text-xs"><div className="space-y-1">
            {observability.worker_processes.map((w, i) => (
              <div key={i} className="flex gap-4 bg-zinc-800/50 rounded p-2 text-zinc-400">
                <span className="text-zinc-300 font-mono">PID {w.pid}</span><span>CPU: {w.cpu_pct}%</span><span>MEM: {w.mem_pct}%</span><span>RSS: {Math.round(w.rss_kb / 1024)}MB</span>
              </div>
            ))}
          </div></CardContent>
        </Card>
      )}
    </div>
  );
}

function PerfTestPanel({ runSimulation, simLoading, simResults }) {
  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardHeader className="pb-2"><CardTitle className="text-sm">Queue Performance Test</CardTitle></CardHeader>
      <CardContent className="text-xs space-y-3">
        <p className="text-zinc-500">Inject and drain 1k jobs per minute across all 5 queues to measure Redis throughput.</p>
        <Button data-testid="run-perf-test" size="sm" variant="outline" className="text-xs" disabled={simLoading.perf} onClick={() => runSimulation("perf", "/workers/performance-test?jobs_per_minute=1000")}>
          {simLoading.perf ? "Running..." : "Run 1k Jobs/Min Test"}
        </Button>
        {simResults.perf && (
          <div data-testid="perf-test-result" className={`p-3 rounded ${simResults.perf.verdict === "PASS" ? "bg-emerald-900/30 border border-emerald-800" : "bg-amber-900/30 border border-amber-800"}`}>
            <p className="font-mono font-bold text-sm">{simResults.perf.verdict}</p>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div><span className="text-zinc-500">Injected:</span> <span className="text-zinc-200">{simResults.perf.total_injected}</span></div>
              <div><span className="text-zinc-500">Drained:</span> <span className="text-zinc-200">{simResults.perf.total_drained}</span></div>
              <div><span className="text-zinc-500">Inject Rate:</span> <span className="text-zinc-200">{simResults.perf.throughput?.injection_rate_per_sec} jobs/sec</span></div>
              <div><span className="text-zinc-500">Drain Rate:</span> <span className="text-zinc-200">{simResults.perf.throughput?.drain_rate_per_sec} jobs/sec</span></div>
            </div>
            {simResults.perf.injection_results && (
              <div className="mt-2 space-y-1">
                {Object.entries(simResults.perf.injection_results).map(([q, v]) => (
                  <div key={q} className="flex gap-2 text-zinc-400"><span className="text-zinc-300">{q}:</span> {v.injected} jobs in {v.duration_ms}ms ({v.rate_per_sec} ops/s)</div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function InfraScorePanel() {
  const { data, loading, refetch } = useHardeningApi("/workers/infrastructure-score");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <ScoreGauge score={data.infrastructure_score} max={10} label="Infrastructure" />
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Badge data-testid="infra-meets-target" className={data.meets_target ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{data.meets_target ? "TARGET MET" : "BELOW TARGET"}</Badge>
            <span className="text-xs text-zinc-400">Target: {data.target}/10 | Gap: {data.gap}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            {Object.entries(data.score_components || {}).map(([k, v]) => (
              <div key={k} className="bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-500 capitalize block">{k.replace(/_/g, " ")}</span>
                <span className={`font-mono font-bold ${v.score >= 9 ? "text-emerald-400" : v.score >= 7 ? "text-amber-400" : "text-red-400"}`}>{v.score}/10</span>
                <span className="text-zinc-600 ml-1">({v.weight * 100}%)</span>
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
              <div key={i} className="flex items-center gap-2"><Badge variant="destructive" className="text-[10px]">{r.severity}</Badge><span className="text-zinc-400">{r.risk}: {r.impact}</span></div>
            ))}
          </CardContent>
        </Card>
      )}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Deployment Checklist ({data.checklist_pass_rate}%)</CardTitle></CardHeader>
        <CardContent className="text-xs space-y-1">
          {(data.deployment_checklist || []).map((c, i) => (
            <div key={i} data-testid={`checklist-${i}`} className="flex items-center gap-2 bg-zinc-800/50 rounded p-2">
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

export function WorkerStrategyTab() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [simLoading, setSimLoading] = useState({});
  const [simResults, setSimResults] = useState({});
  const { data: dashboard, loading, refetch } = useHardeningApi("/workers/dashboard");

  const runSimulation = async (type, endpoint) => {
    setSimLoading(p => ({ ...p, [type]: true }));
    try { const res = await api.post(endpoint); setSimResults(p => ({ ...p, [type]: res.data })); }
    catch (e) { setSimResults(p => ({ ...p, [type]: { verdict: "ERROR", error: e.message } })); }
    setSimLoading(p => ({ ...p, [type]: false }));
  };

  if (loading) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  if (!dashboard) return <div className="text-zinc-400 text-sm p-4">Worker dashboard yuklenemedi. API baglantisi kontrol edin.</div>;

  const subTabs = [
    { id: "dashboard", label: "Dashboard", icon: Gauge }, { id: "pools", label: "Worker Pools", icon: Layers },
    { id: "dlq", label: "DLQ", icon: AlertTriangle }, { id: "monitoring", label: "Monitoring", icon: Activity },
    { id: "autoscaling", label: "Autoscaling", icon: Scale }, { id: "failure", label: "Failure Test", icon: FlaskConical },
    { id: "observability", label: "Observability", icon: Eye }, { id: "performance", label: "Perf Test", icon: Zap },
    { id: "incident", label: "Incident", icon: Radio }, { id: "score", label: "Score", icon: Target },
  ];

  return (
    <div data-testid="workers-tab" className="space-y-4">
      <div className="flex items-center gap-4 bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <ScoreGauge score={dashboard.infrastructure_score} max={10} label="Infra Score" size="sm" />
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Workers</span><span data-testid="worker-count" className="text-zinc-200 font-mono">{dashboard.worker_health?.status}</span></div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Pending Jobs</span><span data-testid="pending-jobs" className="text-zinc-200 font-mono">{dashboard.queue_metrics?.total_pending}</span></div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Dead Letters</span><span data-testid="dead-letters" className="text-zinc-200 font-mono">{dashboard.queue_metrics?.total_dlq}</span></div>
          <div className="bg-zinc-800/50 rounded p-2"><span className="text-zinc-500 block">Checklist</span><span data-testid="checklist-rate" className="text-zinc-200 font-mono">{dashboard.checklist_pass_rate}%</span></div>
        </div>
        <Button data-testid="refresh-workers" size="sm" variant="outline" onClick={refetch} className="text-xs"><RefreshCw className="w-3.5 h-3.5" /></Button>
      </div>
      <div className="flex gap-1 overflow-x-auto pb-1">
        {subTabs.map(t => (
          <button key={t.id} data-testid={`worker-tab-${t.id}`} onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap transition-colors ${activeTab === t.id ? "bg-zinc-700 text-white" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"}`}>
            <t.icon className="w-3.5 h-3.5" />{t.label}
          </button>
        ))}
      </div>
      {activeTab === "dashboard" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">Pool Status</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1">
              {Object.entries(dashboard.pools || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between bg-zinc-800/50 rounded p-2"><span className="text-zinc-300 capitalize">{k}</span><Badge data-testid={`pool-${k}`} variant="outline" className="text-[10px]">{v.priority}</Badge></div>
              ))}
            </CardContent>
          </Card>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">Autoscale Decisions</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1">
              {Object.entries(dashboard.autoscaling || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between bg-zinc-800/50 rounded p-2"><span className="text-zinc-300 capitalize">{k}</span><Badge data-testid={`autoscale-${k}`} className={v === "scale_up" ? "bg-amber-600 text-white" : v === "scale_down" ? "bg-blue-600 text-white" : ""} variant="outline">{v}</Badge></div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
      {activeTab === "pools" && <WorkerPoolsPanel />}
      {activeTab === "dlq" && <DLQPanel />}
      {activeTab === "monitoring" && <QueueMonitoringPanel />}
      {activeTab === "autoscaling" && <AutoscalingPanel />}
      {activeTab === "failure" && (
        <div className="space-y-3"><div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {[
            { type: "crash", label: "Worker Crash", desc: "Verify tasks survive worker crash" },
            { type: "dlq_capture", label: "DLQ Capture", desc: "Verify exhausted retries go to DLQ" },
            { type: "retry", label: "Retry Behavior", desc: "Verify retryable tasks are requeued" },
          ].map(sim => (
            <Card key={sim.type} className="bg-zinc-900 border-zinc-800">
              <CardHeader className="pb-2"><CardTitle className="text-sm">{sim.label}</CardTitle></CardHeader>
              <CardContent className="text-xs space-y-2">
                <p className="text-zinc-500">{sim.desc}</p>
                <Button data-testid={`sim-${sim.type}`} size="sm" variant="outline" className="text-xs w-full" disabled={simLoading[sim.type]} onClick={() => runSimulation(sim.type, `/workers/simulate-failure/${sim.type}`)}>
                  {simLoading[sim.type] ? "Running..." : "Run Simulation"}
                </Button>
                {simResults[sim.type] && (
                  <div data-testid={`sim-result-${sim.type}`} className={`p-2 rounded ${simResults[sim.type].verdict === "PASS" ? "bg-emerald-900/30 border border-emerald-800" : "bg-red-900/30 border border-red-800"}`}>
                    <p className="font-mono font-bold">{simResults[sim.type].verdict}</p>
                    {simResults[sim.type].verification && Object.entries(simResults[sim.type].verification).map(([k, v]) => (<p key={k} className="text-zinc-400">{k}: {String(v)}</p>))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div></div>
      )}
      {activeTab === "observability" && <ObservabilityPanel />}
      {activeTab === "performance" && <PerfTestPanel runSimulation={runSimulation} simLoading={simLoading} simResults={simResults} />}
      {activeTab === "incident" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { type: "worker_crash", label: "Worker Crash Recovery", desc: "Verify tasks persist and workers restart" },
            { type: "redis_disconnect", label: "Redis Disconnect Recovery", desc: "Verify reconnection and data persistence" },
          ].map(t => (
            <Card key={t.type} className="bg-zinc-900 border-zinc-800">
              <CardHeader className="pb-2"><CardTitle className="text-sm">{t.label}</CardTitle></CardHeader>
              <CardContent className="text-xs space-y-2">
                <p className="text-zinc-500">{t.desc}</p>
                <Button data-testid={`incident-${t.type}`} size="sm" variant="outline" className="text-xs w-full" disabled={simLoading[`inc_${t.type}`]} onClick={() => runSimulation(`inc_${t.type}`, `/workers/incident-test/${t.type}`)}>
                  {simLoading[`inc_${t.type}`] ? "Testing..." : "Run Test"}
                </Button>
                {simResults[`inc_${t.type}`] && (
                  <div data-testid={`incident-result-${t.type}`} className={`p-2 rounded ${simResults[`inc_${t.type}`].verdict === "PASS" ? "bg-emerald-900/30 border border-emerald-800" : "bg-red-900/30 border border-red-800"}`}>
                    <p className="font-mono font-bold">{simResults[`inc_${t.type}`].verdict}</p>
                    {simResults[`inc_${t.type}`]?.test_steps?.map((s, i) => (<p key={i} className="text-zinc-400">{s.step}: <span className={s.result === "PASS" ? "text-emerald-400" : "text-red-400"}>{s.result}</span></p>))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      {activeTab === "score" && <InfraScorePanel />}
    </div>
  );
}
