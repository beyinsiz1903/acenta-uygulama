import React, { useState, useEffect, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Progress } from "../../components/ui/progress";
import { Shield, Activity, Server, Zap, Lock, AlertTriangle, Scale, Database, RefreshCw, ChevronDown, ChevronUp, CheckCircle2, XCircle, Clock, Eye, Play, Target, TrendingUp, Layers } from "lucide-react";
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

const severityColor = (s) => ({ critical: "destructive", high: "default", medium: "secondary", low: "outline" }[s] || "outline");
const statusBadge = (s) => {
  if (s === "done" || s === "completed") return <Badge data-testid="status-done" className="bg-emerald-600 text-white">Done</Badge>;
  if (s === "in_progress") return <Badge data-testid="status-progress" className="bg-amber-500 text-white">In Progress</Badge>;
  return <Badge data-testid="status-planned" variant="outline">Planned</Badge>;
};

function ScoreGauge({ score, max, label, size = "lg" }) {
  const pct = (score / max) * 100;
  const color = score >= 8 ? "text-emerald-400" : score >= 5 ? "text-amber-400" : "text-red-400";
  const dim = size === "lg" ? "w-32 h-32" : "w-20 h-20";
  const textSize = size === "lg" ? "text-2xl" : "text-lg";
  const subSize = size === "lg" ? "text-xs" : "text-[10px]";
  return (
    <div data-testid={`gauge-${label?.replace(/\s/g, "-").toLowerCase()}`} className="flex flex-col items-center gap-1.5">
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

/* ========== OVERVIEW TAB (Dual Scores) ========== */
function OverviewTab() {
  const { data, loading, refetch } = useApi("/hardening/status");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="overview-tab" className="space-y-6">
      {/* Dual Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 flex justify-center">
            <ScoreGauge score={data.architecture_maturity} max={10} label="Architecture Maturity" />
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 flex justify-center">
            <ScoreGauge score={data.production_readiness} max={10} label="Production Readiness" />
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-zinc-400">Go-Live Status</CardTitle></CardHeader>
          <CardContent>
            <div data-testid="go-live-status" className={`text-2xl font-bold ${data.go_live_ready ? "text-emerald-400" : "text-red-400"}`}>
              {data.go_live_ready ? "READY" : "NOT READY"}
            </div>
            <p className="text-xs text-zinc-500 mt-1">Target: 8.5/10 readiness</p>
            <p className="text-xs text-zinc-500">Open blockers: {data.blockers?.open || 0}</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-zinc-400">Secrets</CardTitle></CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-zinc-100">{data.components.secrets_configured}/{data.components.secrets_total}</div>
            <Progress value={(data.components.secrets_configured / data.components.secrets_total) * 100} className="mt-2 h-2" />
          </CardContent>
        </Card>
      </div>

      {/* Architecture Breakdown */}
      {data.architecture_breakdown && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">CTO Architecture Assessment</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {Object.entries(data.architecture_breakdown).map(([key, score]) => (
                <div key={key} className="bg-zinc-800/50 rounded-lg p-3 text-center">
                  <div className="text-lg font-bold text-emerald-400">{score}</div>
                  <div className="text-[10px] text-zinc-500 uppercase tracking-wider mt-0.5">{key.replace(/_/g, " ")}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Blockers */}
      {data.blockers?.critical_items?.length > 0 && (
        <Card className="bg-red-950/20 border-red-900/40">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Go-Live Blockers ({data.blockers.open})</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {data.blockers.critical_items.map((b, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                  <span className="text-red-200">{b}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Execution Progress */}
      {data.execution_progress && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Execution Progress</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <Progress value={data.execution_progress.completion_pct} className="flex-1 h-3" />
              <span className="text-sm font-mono text-zinc-300">{data.execution_progress.completion_pct}%</span>
            </div>
            <p className="text-xs text-zinc-500 mt-1">{data.execution_progress.completed_tasks}/{data.execution_progress.total_tasks} tasks completed</p>
          </CardContent>
        </Card>
      )}

      {/* Hardening Components */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Hardening Components</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {data.parts.map((p) => (
              <div key={p.part} data-testid={`part-${p.part}`} className="flex items-center gap-2 p-2 rounded bg-zinc-800/50 text-xs">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                <span className="text-zinc-300 truncate">P{p.part}: {p.name}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Button data-testid="refresh-overview" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

/* ========== EXECUTION TAB (Phase Tracker + Blockers) ========== */
function ExecutionTab() {
  const { data, loading, refetch } = useApi("/hardening/execution/status");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;

  const handleStartPhase = async (phaseId) => {
    try {
      await api.post(`/hardening/execution/phase/${phaseId}/start`);
      refetch();
    } catch {}
  };

  const handleCompleteTask = async (phaseId, taskId) => {
    try {
      await api.post(`/hardening/execution/phase/${phaseId}/task/${taskId}/complete`);
      refetch();
    } catch {}
  };

  const handleResolveBlocker = async (blockerId) => {
    try {
      await api.post(`/hardening/execution/blocker/${blockerId}/resolve`);
      refetch();
    } catch {}
  };

  const r = data.readiness;
  return (
    <div data-testid="execution-tab" className="space-y-6">
      {/* Readiness Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 flex justify-center">
            <ScoreGauge score={r.architecture_maturity_score} max={10} label="Architecture" size="sm" />
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 flex justify-center">
            <ScoreGauge score={r.production_readiness_score} max={10} label="Production" size="sm" />
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 text-center">
            <div className="text-2xl font-bold text-zinc-100">{r.completed_tasks}/{r.total_tasks}</div>
            <p className="text-xs text-zinc-500 mt-1">Tasks Completed</p>
            <Progress value={r.completion_pct} className="mt-2 h-2" />
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 text-center">
            <div className={`text-2xl font-bold ${r.open_blockers === 0 ? "text-emerald-400" : "text-red-400"}`}>{r.open_blockers}</div>
            <p className="text-xs text-zinc-500 mt-1">Open Blockers</p>
            <p className="text-[10px] text-zinc-600 mt-1">Target: 0 for go-live</p>
          </CardContent>
        </Card>
      </div>

      {/* Sprint Progress */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Sprint Progress</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(data.sprints).map(([key, sprint]) => {
              const sprintNum = key.replace("sprint_", "");
              const label = sprintNum === "1" ? "Go-Live Blockers" : sprintNum === "2" ? "Real Integrations" : "Load & Failure Testing";
              return (
                <div key={key} className="bg-zinc-800/50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-zinc-300">Sprint {sprintNum}: {label}</span>
                    <span className="text-xs font-mono text-zinc-400">{sprint.completed_tasks}/{sprint.total_tasks}</span>
                  </div>
                  <Progress value={sprint.progress_pct} className="h-2" />
                  <p className="text-[10px] text-zinc-500 mt-1">{sprint.phases} phases | {sprint.progress_pct}% complete</p>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Go-Live Blockers */}
      <Card className="bg-red-950/20 border-red-900/40">
        <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Go-Live Blockers</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            {data.blockers.map((b) => (
              <div key={b.id} data-testid={`blocker-${b.id}`} className="flex items-center justify-between bg-zinc-900/50 rounded p-3">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  {b.status === "resolved"
                    ? <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    : <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />}
                  <div className="min-w-0">
                    <p className={`text-xs ${b.status === "resolved" ? "text-zinc-500 line-through" : "text-zinc-200"}`}>{b.blocker}</p>
                    <p className="text-[10px] text-zinc-500 mt-0.5">{b.fix_strategy}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                  <Badge variant={severityColor(b.risk)} className="text-[10px]">{b.risk}</Badge>
                  <span className="text-[10px] text-zinc-500">{b.estimated_hours}h</span>
                  {b.status === "open" && (
                    <Button size="sm" variant="outline" className="h-6 text-[10px] px-2" onClick={() => handleResolveBlocker(b.id)}>Resolve</Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Phase Execution */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Execution Phases</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-3">
            {data.phases.map((phase) => (
              <PhaseCard key={phase.id} phase={phase} onStart={handleStartPhase} onCompleteTask={handleCompleteTask} refetch={refetch} />
            ))}
          </div>
        </CardContent>
      </Card>

      <Button data-testid="refresh-execution" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

function PhaseCard({ phase, onStart, onCompleteTask, refetch }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState(null);

  const loadDetail = async () => {
    try {
      const res = await api.get(`/hardening/execution/phase/${phase.id}`);
      setDetail(res.data);
    } catch {}
  };

  const toggleExpand = () => {
    if (!expanded && !detail) loadDetail();
    setExpanded(!expanded);
  };

  const statusColor = phase.status === "completed" ? "border-l-emerald-500" : phase.status === "in_progress" ? "border-l-amber-500" : "border-l-zinc-700";

  return (
    <div data-testid={`phase-${phase.id}`} className={`bg-zinc-800/50 rounded-lg border-l-4 ${statusColor}`}>
      <div className="flex items-center justify-between p-3 cursor-pointer" onClick={toggleExpand}>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-zinc-500 w-5">P{phase.id}</span>
          <span className="text-xs font-medium text-zinc-200">{phase.name}</span>
          <Badge variant="outline" className="text-[10px]">Sprint {phase.sprint}</Badge>
          <Badge variant={phase.priority === "P0" ? "destructive" : "default"} className="text-[10px]">{phase.priority}</Badge>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-zinc-400">{phase.completed_tasks}/{phase.total_tasks}</span>
          <div className="w-16"><Progress value={phase.progress_pct} className="h-1.5" /></div>
          {phase.status === "not_started" && (
            <Button size="sm" variant="outline" className="h-6 text-[10px] px-2" onClick={(e) => { e.stopPropagation(); onStart(phase.id); }}>
              <Play className="w-3 h-3 mr-1" />Start
            </Button>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-zinc-500" /> : <ChevronDown className="w-4 h-4 text-zinc-500" />}
        </div>
      </div>
      {expanded && detail && (
        <div className="px-3 pb-3 space-y-1.5">
          <p className="text-[10px] text-zinc-500 mb-2">{detail.description}</p>
          {detail.tasks.map((task) => (
            <div key={task.id} data-testid={`task-${task.id}`} className="flex items-center justify-between bg-zinc-900/50 rounded p-2">
              <div className="flex items-center gap-2">
                {task.status === "completed"
                  ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  : <div className="w-3.5 h-3.5 rounded-full border border-zinc-600" />}
                <span className={`text-xs ${task.status === "completed" ? "text-zinc-500 line-through" : "text-zinc-300"}`}>{task.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-[10px]">{task.category}</Badge>
                {task.status !== "completed" && (
                  <Button size="sm" variant="ghost" className="h-5 text-[10px] px-1.5" onClick={() => onCompleteTask(phase.id, task.id)}>
                    <CheckCircle2 className="w-3 h-3" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ========== CERTIFICATION TAB ========== */
function CertificationTab() {
  const { data, loading, refetch } = useApi("/hardening/execution/certification");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="certification-tab" className="space-y-6">
      <Card className={`${data.certified ? "bg-emerald-950/20 border-emerald-900/40" : "bg-red-950/20 border-red-900/40"}`}>
        <CardContent className="pt-6 text-center">
          <div className={`text-3xl font-bold ${data.certified ? "text-emerald-400" : "text-red-400"}`}>
            {data.certified ? "CERTIFIED FOR GO-LIVE" : "NOT CERTIFIED"}
          </div>
          <p className="text-sm text-zinc-400 mt-2">{data.recommendation}</p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 flex justify-center">
            <ScoreGauge score={data.architecture_maturity} max={10} label="Architecture" />
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 flex justify-center">
            <ScoreGauge score={data.production_readiness} max={10} label="Production" />
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 text-center">
            <div className="text-2xl font-bold text-zinc-100">{data.gap > 0 ? `${data.gap}` : "0"}</div>
            <p className="text-xs text-zinc-500 mt-1">Gap to Target ({data.target_readiness})</p>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className="bg-zinc-800/50 rounded p-2">
                <span className="text-emerald-400 font-bold">{data.phases_completed}</span>
                <span className="text-zinc-500">/{data.phases_total} phases</span>
              </div>
              <div className="bg-zinc-800/50 rounded p-2">
                <span className="text-emerald-400 font-bold">{data.blockers_resolved}</span>
                <span className="text-zinc-500"> resolved</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {data.architecture_breakdown && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Architecture Breakdown</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {Object.entries(data.architecture_breakdown).map(([key, score]) => (
                <div key={key} className="bg-zinc-800/50 rounded-lg p-3 text-center">
                  <div className="text-lg font-bold text-emerald-400">{score}</div>
                  <div className="text-[10px] text-zinc-500 uppercase tracking-wider mt-0.5">{key.replace(/_/g, " ")}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {data.open_blocker_details?.length > 0 && (
        <Card className="bg-red-950/20 border-red-900/40">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Remaining Blockers ({data.blockers_open})</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {data.open_blocker_details.map((b) => (
                <div key={b.id} className="flex items-center gap-2 text-xs bg-zinc-900/50 rounded p-2">
                  <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />
                  <span className="text-red-200">{b.blocker}</span>
                  <Badge variant="destructive" className="text-[10px] ml-auto">{b.risk}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="text-xs text-zinc-600">Risk Level: <Badge variant={data.risk_level === "critical" ? "destructive" : data.risk_level === "high" ? "default" : "outline"} className="text-[10px]">{data.risk_level}</Badge></div>
      <Button data-testid="refresh-cert" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

/* ========== EXISTING TABS (unchanged logic, compact) ========== */

function TrafficTestingTab() {
  const { data, loading } = useApi("/hardening/traffic/status");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  const gate = data.traffic_gate;
  return (
    <div data-testid="traffic-tab" className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(gate.modes).map(([sup, mode]) => (
          <Card key={sup} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize">{sup}</CardTitle></CardHeader>
            <CardContent>
              <Badge data-testid={`traffic-mode-${sup}`} className={mode === "sandbox" ? "bg-blue-600 text-white" : mode === "production" ? "bg-emerald-600 text-white" : "bg-amber-500 text-white"}>
                {mode.toUpperCase()}
              </Badge>
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
          <CardContent>
            <div className="text-xs text-zinc-400">
              {data.recent_sandbox_results.map((r, i) => (
                <div key={i} className="flex justify-between py-1 border-b border-zinc-800 last:border-0">
                  <span>{r.supplier}</span>
                  <span>{r.results?.length || 0} tests</span>
                  <span>{r.run_at?.split("T")[0]}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function WorkerStrategyTab() {
  const { data, loading } = useApi("/hardening/workers/status");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="workers-tab" className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Badge data-testid="redis-status" className={data.redis_status === "healthy" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>
          Redis: {data.redis_status}
        </Badge>
        <Badge variant="outline">Status: {data.status}</Badge>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(data.worker_pools).map(([name, pool]) => (
          <Card key={name} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize">{name}</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1 text-zinc-400">
              <p>Queues: {pool.queues.join(", ")}</p>
              <p>Concurrency: {pool.concurrency}</p>
              <p>Auto-scale: {pool.autoscale.min} - {pool.autoscale.max}</p>
              <p>Priority: <Badge variant="outline" className="text-[10px]">{pool.priority}</Badge></p>
              <p className="text-zinc-500 mt-1">{pool.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      {Object.keys(data.queue_depths).length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader><CardTitle className="text-sm">Queue Depths</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {Object.entries(data.queue_depths).map(([q, d]) => (
                <div key={q} className="flex justify-between bg-zinc-800/50 rounded p-2">
                  <span className="text-zinc-400">{q}</span>
                  <span className="font-mono text-zinc-200">{d}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ObservabilityTab() {
  const { data, loading } = useApi("/hardening/observability/status");
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
            <p>Service: {data.opentelemetry.service_name}</p>
            <p>Sample rate: {data.opentelemetry.traces.sample_rate}</p>
            <p>Exporter: {data.opentelemetry.traces.exporter}</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Alert Rules</CardTitle></CardHeader>
          <CardContent className="text-xs space-y-1">
            {data.alert_rules.map((r, i) => (
              <div key={i} className="flex items-center gap-2">
                <Badge variant={r.severity === "critical" ? "destructive" : "outline"} className="text-[10px]">{r.severity}</Badge>
                <span className="text-zinc-400">{r.name}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Grafana Dashboards</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {Object.entries(data.grafana_dashboards).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between bg-zinc-800/50 rounded p-3 text-xs">
                <div>
                  <p className="text-zinc-200 font-medium">{v.title}</p>
                  <p className="text-zinc-500">{v.panels} panels</p>
                </div>
                <Eye className="w-4 h-4 text-zinc-500" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PerformanceTab() {
  const { data, loading } = useApi("/hardening/performance/profiles");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="performance-tab" className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(data.profiles).map(([key, p]) => (
          <Card key={key} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">{p.name}</CardTitle></CardHeader>
            <CardContent className="text-xs text-zinc-400 space-y-1">
              <p>Agencies: {p.agencies}</p>
              <p>Searches/hr: {p.searches_per_hour.toLocaleString()}</p>
              <p>Bookings/hr: {p.bookings_per_hour.toLocaleString()}</p>
              <p>Concurrent users: {p.concurrent_users.toLocaleString()}</p>
              <p>Duration: {p.duration_minutes}min (ramp: {p.ramp_up_minutes}min)</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">SLA Targets</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            {Object.entries(data.sla_targets).map(([k, v]) => (
              <div key={k} className="flex justify-between bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-400">{k.replace(/_/g, " ")}</span>
                <span className="font-mono text-zinc-200">{v.target}{v.unit}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Test Scenarios</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-1 text-xs">
            {data.scenarios.map((s, i) => (
              <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                <span className="text-zinc-300">{s.name}</span>
                <div className="flex gap-3 text-zinc-500">
                  <span>Weight: {s.weight}%</span>
                  <span>{s.steps} steps</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function TenantSafetyTab() {
  const { data, loading, refetch } = useApi("/hardening/tenant-safety/audit");
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
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-zinc-500 border-b border-zinc-800">
                <th className="text-left py-2 pr-4">Collection</th><th className="text-left">Status</th><th className="text-right">Docs</th><th className="text-right">Missing</th><th className="text-center">Index</th>
              </tr></thead>
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
          </div>
        </CardContent>
      </Card>
      <Button data-testid="rerun-audit" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-run Audit</Button>
    </div>
  );
}

function SecretsTab() {
  const { data, loading } = useApi("/hardening/secrets/status");
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
        <CardContent>
          <div className="space-y-1 text-xs">
            {data.inventory.map((sec, i) => (
              <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                <div className="flex items-center gap-2">
                  {sec.is_configured ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}
                  <span className="text-zinc-300 font-mono">{sec.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={severityColor(sec.risk_level)} className="text-[10px]">{sec.risk_level}</Badge>
                  <span className="text-zinc-500">{sec.target_source}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Migration Phases</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2 text-xs">
            {data.migration_phases.map((p, i) => (
              <div key={i} className="bg-zinc-800/50 rounded p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-zinc-200 font-medium">Phase {p.phase}: {p.name}</span>
                  <Badge variant="outline" className="text-[10px]">{p.status} - {p.estimated_days}d</Badge>
                </div>
                <p className="text-zinc-500">{p.description}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PlaybooksTab() {
  const { data, loading } = useApi("/hardening/incidents/playbooks");
  const [expanded, setExpanded] = useState(null);
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="playbooks-tab" className="space-y-4">
      {Object.entries(data.playbooks).map(([key, pb]) => (
        <Card key={key} className="bg-zinc-900 border-zinc-800">
          <CardHeader className="cursor-pointer" onClick={() => setExpanded(expanded === key ? null : key)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <CardTitle className="text-sm">{pb.name}</CardTitle>
                <Badge variant="destructive" className="text-[10px]">{pb.severity}</Badge>
              </div>
              {expanded === key ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </div>
          </CardHeader>
          {expanded === key && (
            <CardContent className="text-xs space-y-4">
              <div>
                <p className="text-zinc-400 font-semibold mb-1">Detection Signals:</p>
                <ul className="list-disc list-inside text-zinc-500 space-y-0.5">{pb.detection.signals.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
              <div>
                <p className="text-zinc-400 font-semibold mb-1">Triage ({pb.triage.sla_minutes}min SLA):</p>
                <ul className="list-decimal list-inside text-zinc-500 space-y-0.5">{pb.triage.steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
              <div>
                <p className="text-zinc-400 font-semibold mb-1">Escalation:</p>
                <div className="space-y-1">
                  {pb.escalation.tiers.map((t, i) => (
                    <div key={i} className="flex items-center gap-2 bg-zinc-800 rounded p-2">
                      <Badge variant="outline" className="text-[10px]">{t.tier}</Badge>
                      <span className="text-zinc-300">{t.role}</span>
                      <span className="text-zinc-500 ml-auto">{t.sla_minutes}min</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-zinc-400 font-semibold mb-1">Resolution:</p>
                <ul className="list-disc list-inside text-zinc-500 space-y-0.5">{pb.resolution.actions.map((a, i) => <li key={i}>{a}</li>)}</ul>
              </div>
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  );
}

function ScalingTab() {
  const { data, loading } = useApi("/hardening/scaling/status");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="scaling-tab" className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(data.scaling_configs).map(([key, cfg]) => (
          <Card key={key} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm capitalize">{key.replace(/_/g, " ")}</CardTitle></CardHeader>
            <CardContent className="text-xs text-zinc-400 space-y-1">
              <p>Type: {cfg.type} | Component: {cfg.component}</p>
              <p>Replicas: {cfg.current_replicas} (min: {cfg.min_replicas}, max: {cfg.max_replicas})</p>
              <p>Resources: CPU {cfg.resource_requests.cpu} - {cfg.resource_limits.cpu}, Mem {cfg.resource_requests.memory} - {cfg.resource_limits.memory}</p>
              <div className="mt-2 space-y-0.5">
                {cfg.scaling_metrics.map((m, i) => (
                  <div key={i} className="bg-zinc-800 rounded p-1.5">
                    {m.type === "cpu" ? `CPU target: ${m.target_utilization}%` : m.type === "memory" ? `Memory target: ${m.target_utilization}%` : `${m.metric}: ${m.target}`}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {data.recommendations && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader><CardTitle className="text-sm">Recommendations</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-1 text-xs">
              {data.recommendations.map((r, i) => (
                <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                  <span className="text-zinc-300">{r.action}</span>
                  <Badge variant={r.priority === "P0" ? "destructive" : "outline"} className="text-[10px]">{r.priority}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function DRTab() {
  const { data, loading } = useApi("/hardening/dr/plan");
  const [expanded, setExpanded] = useState(null);
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="dr-tab" className="space-y-4">
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">RTO/RPO Targets</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
            {Object.entries(data.rto_rpo_targets).map(([k, v]) => (
              <div key={k} className="bg-zinc-800/50 rounded p-3">
                <p className="text-zinc-200 font-medium capitalize mb-1">{k.replace(/_/g, " ")}</p>
                <p className="text-zinc-500">{v.description}</p>
                <div className="flex gap-4 mt-2 text-zinc-400">
                  <span>RTO: {v.rto_minutes}min</span>
                  <span>RPO: {v.rpo_minutes}min</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      {Object.entries(data.scenarios).map(([key, sc]) => (
        <Card key={key} className="bg-zinc-900 border-zinc-800">
          <CardHeader className="cursor-pointer" onClick={() => setExpanded(expanded === key ? null : key)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-red-400" />
                <CardTitle className="text-sm">{sc.name}</CardTitle>
                <Badge variant="destructive" className="text-[10px]">{sc.severity}</Badge>
              </div>
              <span className="text-xs text-zinc-500">RTO: {sc.estimated_rto_minutes}min</span>
            </div>
          </CardHeader>
          {expanded === key && (
            <CardContent className="text-xs space-y-3">
              <p className="text-zinc-400">{sc.description}</p>
              {Object.entries(sc.response_plan).map(([phase, steps]) => (
                <div key={phase}>
                  <p className="text-zinc-400 font-semibold capitalize mb-1">{phase}:</p>
                  <ul className="list-disc list-inside text-zinc-500 space-y-0.5">{steps.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </div>
              ))}
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  );
}

function ChecklistTab() {
  const { data, loading } = useApi("/hardening/checklist");
  const [filter, setFilter] = useState("all");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  const m = data.maturity;
  const tasks = filter === "all" ? data.tasks : data.tasks.filter(t => t.priority === filter);
  return (
    <div data-testid="checklist-tab" className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><ScoreGauge score={m.maturity_score} max={10} label={m.maturity_label?.replace(/_/g, " ")} size="sm" /></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-emerald-400">{m.summary.done}</div><p className="text-xs text-zinc-500">Done</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-amber-400">{m.summary.in_progress}</div><p className="text-xs text-zinc-500">In Progress</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-zinc-400">{m.summary.planned}</div><p className="text-xs text-zinc-500">Planned</p></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-center"><div className="text-2xl font-bold text-zinc-100">{m.remaining_effort_days}d</div><p className="text-xs text-zinc-500">Remaining Effort</p></CardContent></Card>
      </div>
      {m.go_live_blockers.length > 0 && (
        <Card className="bg-red-950/30 border-red-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Go-Live Blockers ({m.go_live_blockers.length})</CardTitle></CardHeader>
          <CardContent>
            <ul className="list-disc list-inside text-xs text-red-300 space-y-0.5">{m.go_live_blockers.map((b, i) => <li key={i}>{b}</li>)}</ul>
          </CardContent>
        </Card>
      )}
      <div className="flex gap-2">
        {["all", "P0", "P1", "P2", "P3"].map(f => (
          <Button key={f} size="sm" variant={filter === f ? "default" : "outline"} onClick={() => setFilter(f)} className="text-xs">{f === "all" ? "All" : f}</Button>
        ))}
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="pt-4">
          <div className="space-y-1 text-xs max-h-[500px] overflow-y-auto">
            {tasks.map((t) => (
              <div key={t.id} data-testid={`task-${t.id}`} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  {t.status === "done" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" /> : t.status === "in_progress" ? <Clock className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" /> : <div className="w-3.5 h-3.5 rounded-full border border-zinc-600 flex-shrink-0" />}
                  <span className={`truncate ${t.status === "done" ? "text-zinc-500 line-through" : "text-zinc-300"}`}>{t.task}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0 ml-2">
                  <Badge variant={t.priority === "P0" ? "destructive" : t.priority === "P1" ? "default" : "outline"} className="text-[10px]">{t.priority}</Badge>
                  <Badge variant={severityColor(t.risk)} className="text-[10px]">{t.risk}</Badge>
                  <span className="text-zinc-600 w-8 text-right">{t.effort_days}d</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/* ========== MAIN PAGE ========== */
export default function PlatformHardeningPage() {
  return (
    <div data-testid="platform-hardening-page" className="p-4 md:p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Shield className="w-7 h-7 text-emerald-400" />
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Platform Hardening Dashboard</h1>
          <p className="text-xs text-zinc-500">Enterprise production readiness — Execution Phase</p>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList data-testid="hardening-tabs" className="bg-zinc-900 border border-zinc-800 flex-wrap h-auto gap-1 p-1">
          <TabsTrigger value="overview" className="text-xs gap-1"><Shield className="w-3.5 h-3.5" />Overview</TabsTrigger>
          <TabsTrigger value="execution" className="text-xs gap-1"><Target className="w-3.5 h-3.5" />Execution</TabsTrigger>
          <TabsTrigger value="certification" className="text-xs gap-1"><TrendingUp className="w-3.5 h-3.5" />Certification</TabsTrigger>
          <TabsTrigger value="traffic" className="text-xs gap-1"><Zap className="w-3.5 h-3.5" />Traffic</TabsTrigger>
          <TabsTrigger value="workers" className="text-xs gap-1"><Server className="w-3.5 h-3.5" />Workers</TabsTrigger>
          <TabsTrigger value="observability" className="text-xs gap-1"><Activity className="w-3.5 h-3.5" />Observability</TabsTrigger>
          <TabsTrigger value="performance" className="text-xs gap-1"><Zap className="w-3.5 h-3.5" />Performance</TabsTrigger>
          <TabsTrigger value="tenant" className="text-xs gap-1"><Lock className="w-3.5 h-3.5" />Tenants</TabsTrigger>
          <TabsTrigger value="secrets" className="text-xs gap-1"><Lock className="w-3.5 h-3.5" />Secrets</TabsTrigger>
          <TabsTrigger value="playbooks" className="text-xs gap-1"><AlertTriangle className="w-3.5 h-3.5" />Playbooks</TabsTrigger>
          <TabsTrigger value="scaling" className="text-xs gap-1"><Scale className="w-3.5 h-3.5" />Scaling</TabsTrigger>
          <TabsTrigger value="dr" className="text-xs gap-1"><Database className="w-3.5 h-3.5" />DR</TabsTrigger>
          <TabsTrigger value="checklist" className="text-xs gap-1"><CheckCircle2 className="w-3.5 h-3.5" />Checklist</TabsTrigger>
        </TabsList>

        <TabsContent value="overview"><OverviewTab /></TabsContent>
        <TabsContent value="execution"><ExecutionTab /></TabsContent>
        <TabsContent value="certification"><CertificationTab /></TabsContent>
        <TabsContent value="traffic"><TrafficTestingTab /></TabsContent>
        <TabsContent value="workers"><WorkerStrategyTab /></TabsContent>
        <TabsContent value="observability"><ObservabilityTab /></TabsContent>
        <TabsContent value="performance"><PerformanceTab /></TabsContent>
        <TabsContent value="tenant"><TenantSafetyTab /></TabsContent>
        <TabsContent value="secrets"><SecretsTab /></TabsContent>
        <TabsContent value="playbooks"><PlaybooksTab /></TabsContent>
        <TabsContent value="scaling"><ScalingTab /></TabsContent>
        <TabsContent value="dr"><DRTab /></TabsContent>
        <TabsContent value="checklist"><ChecklistTab /></TabsContent>
      </Tabs>
    </div>
  );
}
