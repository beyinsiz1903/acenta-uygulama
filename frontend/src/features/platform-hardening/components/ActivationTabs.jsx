import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { RefreshCw, CheckCircle2, XCircle, Clock, Radio, Zap, Server, AlertTriangle, Play, Shield, Lock } from "lucide-react";
import { ScoreGauge } from "./ScoreGauge";
import { useHardeningApi } from "../api";
import { api } from "../../../lib/api";

export function LiveInfrastructureTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/activation/infrastructure");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  const svc = data.services;
  const statusIcon = (s) => s === "healthy" ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : s === "no_workers" ? <Clock className="w-4 h-4 text-amber-400" /> : <XCircle className="w-4 h-4 text-red-400" />;
  const statusColor = (s) => s === "healthy" ? "border-emerald-600/40 bg-emerald-950/10" : s === "no_workers" ? "border-amber-600/40 bg-amber-950/10" : "border-red-600/40 bg-red-950/10";
  return (
    <div data-testid="live-infra-tab" className="space-y-6">
      <div className={`rounded-lg border p-4 flex items-center gap-4 ${data.overall_status === "healthy" ? "border-emerald-600/40 bg-emerald-950/10" : "border-amber-600/40 bg-amber-950/10"}`}>
        <Radio className={`w-6 h-6 ${data.overall_status === "healthy" ? "text-emerald-400" : "text-amber-400"} animate-pulse`} />
        <div><div data-testid="infra-overall-status" className="text-lg font-bold text-zinc-100 uppercase">{data.overall_status}</div><p className="text-xs text-zinc-500">{data.healthy_services}/{data.total_services} services healthy</p></div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className={`border ${statusColor(svc.redis.status)}`}>
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2">{statusIcon(svc.redis.status)} Redis</CardTitle></CardHeader>
          <CardContent className="text-xs space-y-2 text-zinc-400">
            <div className="flex justify-between"><span>Status</span><Badge data-testid="redis-live-status" className={svc.redis.status === "healthy" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{svc.redis.status}</Badge></div>
            <div className="flex justify-between"><span>Latency</span><span className="font-mono text-zinc-200">{svc.redis.latency_ms}ms</span></div>
            {svc.redis.details && <><div className="flex justify-between"><span>Memory</span><span className="font-mono text-zinc-200">{svc.redis.details.used_memory_human}</span></div><div className="flex justify-between"><span>Clients</span><span className="font-mono text-zinc-200">{svc.redis.details.connected_clients}</span></div><div className="flex justify-between"><span>Version</span><span className="font-mono text-zinc-200">{svc.redis.details.redis_version}</span></div><div className="flex justify-between"><span>Keys</span><span className="font-mono text-zinc-200">{svc.redis.details.total_keys}</span></div><div className="flex justify-between"><span>Queue Depth</span><span className="font-mono text-zinc-200">{svc.redis.details.total_queue_depth}</span></div></>}
          </CardContent>
        </Card>
        <Card className={`border ${statusColor(svc.celery.status)}`}>
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2">{statusIcon(svc.celery.status)} Celery Workers</CardTitle></CardHeader>
          <CardContent className="text-xs space-y-2 text-zinc-400">
            <div className="flex justify-between"><span>Status</span><Badge data-testid="celery-live-status" className={svc.celery.status === "healthy" ? "bg-emerald-600 text-white" : svc.celery.status === "no_workers" ? "bg-amber-500 text-white" : "bg-red-600 text-white"}>{svc.celery.status}</Badge></div>
            <div className="flex justify-between"><span>Workers</span><span className="font-mono text-zinc-200">{svc.celery.details?.worker_count || 0}</span></div>
            <div className="flex justify-between"><span>Active Tasks</span><span className="font-mono text-zinc-200">{svc.celery.details?.total_active_tasks || 0}</span></div>
            <div className="border-t border-zinc-800 pt-2 mt-2"><p className="text-zinc-500 mb-1">Queues:</p><div className="flex flex-wrap gap-1">{(svc.celery.details?.queues_configured || []).map(q => <Badge key={q} variant="outline" className="text-[10px]">{q}</Badge>)}</div></div>
            <div><p className="text-zinc-500 mb-1">DLQ:</p><div className="flex flex-wrap gap-1">{(svc.celery.details?.dlq_configured || []).map(q => <Badge key={q} variant="outline" className="text-[10px] border-red-800 text-red-400">{q}</Badge>)}</div></div>
          </CardContent>
        </Card>
        <Card className={`border ${statusColor(svc.mongodb.status)}`}>
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2">{statusIcon(svc.mongodb.status)} MongoDB</CardTitle></CardHeader>
          <CardContent className="text-xs space-y-2 text-zinc-400">
            <div className="flex justify-between"><span>Status</span><Badge data-testid="mongodb-live-status" className={svc.mongodb.status === "healthy" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{svc.mongodb.status}</Badge></div>
            <div className="flex justify-between"><span>Latency</span><span className="font-mono text-zinc-200">{svc.mongodb.latency_ms}ms</span></div>
            {svc.mongodb.details && <><div className="flex justify-between"><span>Collections</span><span className="font-mono text-zinc-200">{svc.mongodb.details.collections}</span></div><div className="flex justify-between"><span>Data Size</span><span className="font-mono text-zinc-200">{svc.mongodb.details.data_size_mb} MB</span></div><div className="flex justify-between"><span>Indexes</span><span className="font-mono text-zinc-200">{svc.mongodb.details.indexes}</span></div><div className="flex justify-between"><span>Objects</span><span className="font-mono text-zinc-200">{svc.mongodb.details.objects?.toLocaleString()}</span></div></>}
          </CardContent>
        </Card>
      </div>
      {svc.redis.details?.queue_depths && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Celery Queue Depths</CardTitle></CardHeader>
          <CardContent><div className="grid grid-cols-3 md:grid-cols-5 gap-2">
            {Object.entries(svc.redis.details.queue_depths).map(([q, depth]) => (
              <div key={q} className={`flex flex-col items-center p-3 rounded-lg ${depth > 0 ? "bg-amber-950/20 border border-amber-800/30" : "bg-zinc-800/50"}`}>
                <span className={`text-lg font-bold font-mono ${depth > 0 ? "text-amber-400" : "text-zinc-400"}`}>{depth}</span>
                <span className="text-[10px] text-zinc-500 mt-1 text-center">{q}</span>
              </div>
            ))}
          </div></CardContent>
        </Card>
      )}
      <Button data-testid="refresh-infra" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

export function PerformanceBaselineTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/activation/performance");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  const results = data.results;
  const sla = data.sla_summary;
  return (
    <div data-testid="perf-baseline-tab" className="space-y-6">
      <div className={`rounded-lg border p-4 ${sla.pass_rate_pct === 100 ? "border-emerald-600/40 bg-emerald-950/10" : "border-amber-600/40 bg-amber-950/10"}`}>
        <div className="flex items-center justify-between">
          <div><div data-testid="sla-pass-rate" className="text-2xl font-bold text-zinc-100">{sla.pass_rate_pct}%</div><p className="text-xs text-zinc-500">SLA Pass Rate ({sla.passing}/{sla.total_tests} tests)</p></div>
          <div className="text-right text-xs text-zinc-500"><p>Target: 10k searches/hr</p><p>Target: 1k bookings/hr</p></div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(results).map(([key, result]) => {
          if (result.error) return (<Card key={key} className="bg-red-950/20 border-red-900/40"><CardHeader className="pb-2"><CardTitle className="text-sm">{key.replace(/_/g, " ")}</CardTitle></CardHeader><CardContent><p className="text-xs text-red-400">{result.error}</p></CardContent></Card>);
          return (
            <Card key={key} className={`border ${result.passes_sla ? "border-emerald-600/40 bg-emerald-950/10" : "border-red-600/40 bg-red-950/10"}`}>
              <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2">{result.passes_sla ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}{key.replace(/_/g, " ")}</CardTitle></CardHeader>
              <CardContent className="text-xs space-y-1.5 text-zinc-400">
                <div className="flex justify-between"><span>Avg</span><span className="font-mono text-zinc-200">{result.avg_ms}ms</span></div>
                {result.p95_ms !== undefined && <div className="flex justify-between"><span>P95</span><span className="font-mono text-zinc-200">{result.p95_ms}ms</span></div>}
                {result.min_ms !== undefined && <div className="flex justify-between"><span>Min/Max</span><span className="font-mono text-zinc-200">{result.min_ms}/{result.max_ms}ms</span></div>}
                <div className="flex justify-between"><span>SLA Target</span><span className="font-mono text-zinc-200">{result.sla_target_ms}ms</span></div>
                <div className="flex justify-between"><span>Samples</span><span className="font-mono text-zinc-200">{result.samples}</span></div>
              </CardContent>
            </Card>
          );
        })}
      </div>
      <Button data-testid="refresh-perf" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-run Baseline</Button>
    </div>
  );
}

export function IncidentSimulationTab() {
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(null);
  const runSim = async (type) => {
    setRunning(type);
    try { const res = await api.post(`/hardening/activation/incident/${type}`); setResults(prev => ({ ...prev, [type]: res.data })); }
    catch { setResults(prev => ({ ...prev, [type]: { error: "Simulation failed" } })); }
    setRunning(null);
  };
  const incidents = [
    { type: "supplier_outage", label: "Supplier Outage", icon: <Zap className="w-4 h-4" />, desc: "Simulate Paximum API timeout" },
    { type: "queue_backlog", label: "Queue Backlog", icon: <Server className="w-4 h-4" />, desc: "Measure queue depths & backlog handling" },
    { type: "payment_failure", label: "Payment Failure", icon: <AlertTriangle className="w-4 h-4" />, desc: "Simulate Stripe webhook failure" },
  ];
  return (
    <div data-testid="incident-sim-tab" className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {incidents.map(({ type, label, icon, desc }) => (
          <Card key={type} className={`border ${results[type]?.verdict === "PASS" ? "border-emerald-600/40 bg-emerald-950/10" : "bg-zinc-900 border-zinc-800"}`}>
            <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2">{icon} {label}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-zinc-500">{desc}</p>
              <Button data-testid={`simulate-${type}`} size="sm" variant="outline" className="w-full" onClick={() => runSim(type)} disabled={running === type}>
                {running === type ? <RefreshCw className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-1" />}{running === type ? "Running..." : "Simulate"}
              </Button>
              {results[type] && !results[type].error && (
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between items-center"><span className="text-zinc-400">Verdict</span><Badge className={results[type].verdict === "PASS" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{results[type].verdict}</Badge></div>
                  {results[type].playbook_executed && (
                    <div className="border-t border-zinc-800 pt-2"><p className="text-zinc-500 mb-1">Playbook Steps:</p>
                      {Object.entries(results[type].playbook_executed).map(([step, action]) => (
                        <div key={step} className="flex items-start gap-1.5 py-0.5"><CheckCircle2 className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" /><span className="text-zinc-300">{action}</span></div>
                      ))}
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

export function TenantIsolationRealTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/activation/tenant-isolation");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  const s = data.summary;
  return (
    <div data-testid="tenant-real-tab" className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-zinc-100">{s.collections_checked}</div><p className="text-xs text-zinc-500">Checked</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-emerald-400">{s.isolated}</div><p className="text-xs text-zinc-500">Isolated</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-amber-400">{s.partial}</div><p className="text-xs text-zinc-500">Partial</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-red-400">{s.not_isolated}</div><p className="text-xs text-zinc-500">Not Isolated</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div data-testid="isolation-score" className="text-2xl font-bold text-zinc-100">{s.isolation_score_pct}%</div><p className="text-xs text-zinc-500">Score</p></CardContent></Card>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(data.cross_tenant_test).map(([test, result]) => (
          <Card key={test} className={`border ${result === "PASS" ? "border-emerald-600/40 bg-emerald-950/10" : "border-red-600/40 bg-red-950/10"}`}><CardContent className="pt-4 flex items-center justify-between"><span className="text-xs text-zinc-300">{test.replace(/_/g, " ")}</span><Badge className={result === "PASS" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{result}</Badge></CardContent></Card>
        ))}
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Collection Isolation Details</CardTitle></CardHeader>
        <CardContent><div className="overflow-x-auto"><table className="w-full text-xs">
          <thead><tr className="text-zinc-500 border-b border-zinc-800"><th className="text-left py-2">Collection</th><th className="text-center">Status</th><th className="text-center">Tenant Field</th><th className="text-right">Docs</th><th className="text-center">Risk</th></tr></thead>
          <tbody>{data.results.map((r, i) => (
            <tr key={i} className="border-b border-zinc-800/50">
              <td className="py-1.5 text-zinc-300 font-mono">{r.collection}</td>
              <td className="text-center"><Badge variant={r.status === "isolated" ? "default" : r.status === "empty" ? "outline" : "destructive"} className="text-[10px]">{r.status}</Badge></td>
              <td className="text-center text-zinc-400">{r.field_name || "-"}</td>
              <td className="text-right font-mono text-zinc-400">{r.total_docs ?? "-"}</td>
              <td className="text-center"><Badge variant={r.risk === "low" ? "outline" : r.risk === "critical" ? "destructive" : "default"} className="text-[10px]">{r.risk}</Badge></td>
            </tr>
          ))}</tbody>
        </table></div></CardContent>
      </Card>
      <Button data-testid="refresh-tenant-real" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-run Tests</Button>
    </div>
  );
}

export function DryRunTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/activation/dry-run");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="dry-run-tab" className="space-y-6">
      <div className={`rounded-lg border p-4 text-center ${data.dry_run_result === "PASS" ? "border-emerald-600/40 bg-emerald-950/10" : "border-red-600/40 bg-red-950/10"}`}>
        <div data-testid="dry-run-result" className={`text-3xl font-bold ${data.dry_run_result === "PASS" ? "text-emerald-400" : "text-red-400"}`}>{data.dry_run_result}</div>
        <p className="text-xs text-zinc-500 mt-1">{data.summary.passing}/{data.summary.total_steps} steps passed in {data.summary.total_duration_ms}ms</p>
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Pipeline Steps: Search &rarr; Price &rarr; Book &rarr; Voucher &rarr; Notify</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {data.steps.map((step) => (
            <div key={step.step} data-testid={`dry-run-step-${step.step}`} className={`flex items-center justify-between rounded-lg p-3 border ${step.status === "pass" ? "border-emerald-600/30 bg-emerald-950/10" : "border-red-600/30 bg-red-950/10"}`}>
              <div className="flex items-center gap-3">{step.status === "pass" ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <XCircle className="w-5 h-5 text-red-400" />}<div><p className="text-sm font-medium text-zinc-200">Step {step.step}: {step.name}</p><p className="text-xs text-zinc-500">{step.details || step.error}</p></div></div>
              {step.duration_ms !== undefined && <span className="text-xs font-mono text-zinc-400">{step.duration_ms}ms</span>}
            </div>
          ))}
        </CardContent>
      </Card>
      <Button data-testid="rerun-dry-run" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-run Dry Run</Button>
    </div>
  );
}

export function OnboardingTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/activation/onboarding");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  const s = data.summary;
  return (
    <div data-testid="onboarding-tab" className="space-y-6">
      <div className={`rounded-lg border p-4 ${s.onboarding_ready_pct >= 80 ? "border-emerald-600/40 bg-emerald-950/10" : "border-amber-600/40 bg-amber-950/10"}`}>
        <div className="flex items-center justify-between"><div><div data-testid="onboarding-readiness" className="text-2xl font-bold text-zinc-100">{s.onboarding_ready_pct}%</div><p className="text-xs text-zinc-500">Onboarding Readiness ({s.ready}/{s.total_checks} checks pass)</p></div></div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Readiness Checks</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {data.checks.map((c, i) => (
              <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2.5">
                <div className="flex items-center gap-2">{c.status === "ready" ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : c.status === "test_mode" ? <Clock className="w-4 h-4 text-amber-400" /> : <XCircle className="w-4 h-4 text-red-400" />}<div><p className="text-xs text-zinc-200">{c.check}</p><p className="text-[10px] text-zinc-500">{c.details}</p></div></div>
                <Badge variant={c.status === "ready" ? "default" : c.status === "test_mode" ? "outline" : "destructive"} className="text-[10px]">{c.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Onboarding Workflow</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(data.onboarding_workflow).map(([step, desc]) => (
              <div key={step} className="flex items-center gap-3 bg-zinc-800/50 rounded p-2.5"><div className="w-6 h-6 rounded-full bg-zinc-700 flex items-center justify-center text-[10px] font-bold text-zinc-300">{step.split("_")[1]}</div><span className="text-xs text-zinc-300">{desc}</span></div>
            ))}
          </CardContent>
        </Card>
      </div>
      <Button data-testid="refresh-onboarding" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

export function GoLiveCertificationTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/activation/certification");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  const cert = data.certification;
  const scores = data.dimension_scores;
  const weights = data.weights;
  return (
    <div data-testid="golive-cert-tab" className="space-y-6">
      <div className={`rounded-lg border-2 p-6 text-center ${cert.decision === "GO" ? "border-emerald-500 bg-emerald-950/20" : "border-red-500 bg-red-950/20"}`}>
        <div data-testid="golive-decision" className={`text-4xl font-black tracking-wider ${cert.decision === "GO" ? "text-emerald-400" : "text-red-400"}`}>{cert.decision}</div>
        <div className="text-lg mt-2 text-zinc-300">Production Readiness: <span className="font-bold">{cert.production_readiness_score}/10</span></div>
        {cert.gap > 0 && <p className="text-sm text-zinc-500 mt-1">Gap to target (8.5): {cert.gap} points</p>}
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Dimension Scores (Weighted)</CardTitle></CardHeader>
        <CardContent><div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {Object.entries(scores).map(([dim, score]) => (
            <div key={dim} className="bg-zinc-800/50 rounded-lg p-3 text-center">
              <div className={`text-xl font-bold ${score >= 8 ? "text-emerald-400" : score >= 5 ? "text-amber-400" : "text-red-400"}`}>{score}</div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider mt-0.5">{dim}</div>
              <div className="text-[9px] text-zinc-600 mt-0.5">weight: {((weights[dim] || 0) * 100).toFixed(0)}%</div>
            </div>
          ))}
        </div></CardContent>
      </Card>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><Badge className={data.infrastructure.status === "healthy" ? "bg-emerald-600 text-white" : "bg-amber-500 text-white"}>{data.infrastructure.status}</Badge><p className="text-xs text-zinc-500 mt-1">Infrastructure</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><div className="text-xl font-bold text-zinc-100">{data.security?.security_score ?? "?"}/10</div><p className="text-xs text-zinc-500 mt-1">Security Score</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><Badge className={data.reliability.dry_run_result === "PASS" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{data.reliability.dry_run_result}</Badge><p className="text-xs text-zinc-500 mt-1">Dry Run</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-4 text-center"><div className="text-xl font-bold text-zinc-100">{data.suppliers.active}/{data.suppliers.total}</div><p className="text-xs text-zinc-500 mt-1">Suppliers Active</p></CardContent></Card>
      </div>
      {data.risks.length > 0 && (
        <Card className="bg-red-950/20 border-red-900/40">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Risk Analysis ({data.risks.length} items)</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {data.risks.map((r, i) => (<div key={i} className="flex items-center justify-between bg-zinc-900/50 rounded p-2.5"><div className="flex items-center gap-2"><AlertTriangle className={`w-4 h-4 flex-shrink-0 ${r.severity === "critical" ? "text-red-400" : "text-amber-400"}`} /><div><p className="text-xs text-zinc-200">{r.risk}</p><p className="text-[10px] text-zinc-500">{r.mitigation}</p></div></div><Badge variant={r.severity === "critical" ? "destructive" : "default"} className="text-[10px]">{r.severity}</Badge></div>))}
          </CardContent>
        </Card>
      )}
      <div className="flex items-center gap-2 text-xs text-zinc-600">Risk Level: <Badge variant={data.risk_level === "critical" ? "destructive" : data.risk_level === "high" ? "default" : "outline"} className="text-[10px]">{data.risk_level}</Badge><span className="ml-auto">Onboarding: {data.onboarding_ready}% ready</span></div>
      <Button data-testid="refresh-golive" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-certify</Button>
    </div>
  );
}

export function SecurityDashboardTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/security/readiness");
  const { data: jwt } = useHardeningApi("/hardening/security/jwt");
  const { data: tests } = useHardeningApi("/hardening/security/tests");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  const dims = data.dimensions;
  return (
    <div data-testid="security-dashboard-tab" className="space-y-6">
      <div className={`rounded-lg border-2 p-6 text-center ${data.meets_target ? "border-emerald-500 bg-emerald-950/20" : "border-red-500 bg-red-950/20"}`}>
        <div data-testid="security-score" className={`text-4xl font-black tracking-wider ${data.meets_target ? "text-emerald-400" : "text-red-400"}`}>{data.security_readiness_score}/10</div>
        <p className="text-sm text-zinc-400 mt-1">Security Readiness {data.meets_target ? "(TARGET MET)" : `(Gap: ${data.gap})`}</p>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {Object.entries(dims).map(([dim, info]) => (
          <Card key={dim} className={`border ${info.score >= 8 ? "border-emerald-600/40 bg-emerald-950/10" : info.score >= 5 ? "border-amber-600/40 bg-amber-950/10" : "border-red-600/40 bg-red-950/10"}`}>
            <CardContent className="pt-4 text-center">
              <div className={`text-2xl font-bold ${info.score >= 8 ? "text-emerald-400" : info.score >= 5 ? "text-amber-400" : "text-red-400"}`}>{info.score}</div>
              <div className="text-[10px] text-zinc-500 uppercase tracking-wider mt-0.5">{dim.replace(/_/g, " ")}</div>
              <p className="text-[9px] text-zinc-600 mt-1">{info.details}</p>
              <div className="text-[9px] text-zinc-600">weight: {(info.weight * 100).toFixed(0)}%</div>
            </CardContent>
          </Card>
        ))}
      </div>
      {jwt && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Lock className="w-4 h-4" /> JWT Security ({jwt.summary.score_pct}%)</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {jwt.checks.map((c, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-zinc-800/50 rounded p-2"><div className="flex items-center gap-2">{c.status === "pass" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}<span className="text-zinc-300">{c.check}</span></div><span className="text-zinc-500 text-[10px] max-w-[40%] text-right">{c.details}</span></div>
            ))}
          </CardContent>
        </Card>
      )}
      {tests && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Shield className="w-4 h-4" /> Security Tests ({tests.summary.pass_rate_pct}%)</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {tests.tests.map((t, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-zinc-800/50 rounded p-2"><div className="flex items-center gap-2">{t.status === "pass" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}<span className="text-zinc-300">{t.test}</span></div><span className="text-zinc-500 text-[10px] max-w-[40%] text-right">{t.details}</span></div>
            ))}
          </CardContent>
        </Card>
      )}
      {data.risks.length > 0 && (
        <Card className="bg-red-950/20 border-red-900/40">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Risks ({data.risks.length})</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {data.risks.map((r, i) => (<div key={i} className="flex items-center gap-2 text-xs"><AlertTriangle className="w-3.5 h-3.5 text-red-400" /><span className="text-zinc-300">{r.risk}</span><Badge variant="destructive" className="text-[10px] ml-auto">{r.severity}</Badge></div>))}
          </CardContent>
        </Card>
      )}
      {data.top_fixes.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Top Fixes ({data.top_fixes.length})</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {data.top_fixes.map((f, i) => (<div key={i} className="flex items-center gap-2 text-xs"><span className="text-zinc-300">{f.fix}</span><Badge variant={f.impact === "high" ? "destructive" : "default"} className="text-[10px] ml-auto">{f.impact}</Badge></div>))}
          </CardContent>
        </Card>
      )}
      <Button data-testid="refresh-security" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-scan</Button>
    </div>
  );
}
