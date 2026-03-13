import React, { useState, useEffect, useCallback } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Progress } from "../../components/ui/progress";
import { Shield, Activity, Server, Zap, Lock, AlertTriangle, Scale, Database, RefreshCw, ChevronDown, ChevronUp, CheckCircle2, XCircle, Clock, Eye, Play, Target, TrendingUp, Layers, Gauge, Radio, FlaskConical, Users, FileCheck, Truck, Plug } from "lucide-react";
import SupplierActivationTab from "./SupplierActivationTab";
import StressTestTab from "./StressTestTab";
import PilotLaunchTab from "./PilotLaunchTab";
import SupplierSettingsTab from "./SupplierSettingsTab";
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
  const [activeTab, setActiveTab] = useState("dashboard");
  const [simLoading, setSimLoading] = useState({});
  const [simResults, setSimResults] = useState({});
  const { data: dashboard, loading, refetch } = useApi("/workers/dashboard");

  const runSimulation = async (type, endpoint) => {
    setSimLoading(p => ({ ...p, [type]: true }));
    try {
      const res = await api.post(endpoint);
      setSimResults(p => ({ ...p, [type]: res.data }));
    } catch (e) {
      setSimResults(p => ({ ...p, [type]: { verdict: "ERROR", error: e.message } }));
    }
    setSimLoading(p => ({ ...p, [type]: false }));
  };

  if (loading) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  if (!dashboard) return <div className="text-zinc-400 text-sm p-4">Worker dashboard yüklenemedi. API bağlantısı kontrol edin.</div>;

  const subTabs = [
    { id: "dashboard", label: "Dashboard", icon: Gauge },
    { id: "pools", label: "Worker Pools", icon: Layers },
    { id: "dlq", label: "DLQ", icon: AlertTriangle },
    { id: "monitoring", label: "Monitoring", icon: Activity },
    { id: "autoscaling", label: "Autoscaling", icon: Scale },
    { id: "failure", label: "Failure Test", icon: FlaskConical },
    { id: "observability", label: "Observability", icon: Eye },
    { id: "performance", label: "Perf Test", icon: Zap },
    { id: "incident", label: "Incident", icon: Radio },
    { id: "score", label: "Score", icon: Target },
  ];

  return (
    <div data-testid="workers-tab" className="space-y-4">
      {/* Top Score Bar */}
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

      {/* Sub-tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {subTabs.map(t => (
          <button key={t.id} data-testid={`worker-tab-${t.id}`} onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap transition-colors ${activeTab === t.id ? "bg-zinc-700 text-white" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"}`}>
            <t.icon className="w-3.5 h-3.5" />{t.label}
          </button>
        ))}
      </div>

      {/* Sub-tab content */}
      {activeTab === "dashboard" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">Pool Status</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1">
              {Object.entries(dashboard.pools || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between bg-zinc-800/50 rounded p-2">
                  <span className="text-zinc-300 capitalize">{k}</span>
                  <Badge data-testid={`pool-${k}`} variant="outline" className="text-[10px]">{v.priority}</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2"><CardTitle className="text-sm">Autoscale Decisions</CardTitle></CardHeader>
            <CardContent className="text-xs space-y-1">
              {Object.entries(dashboard.autoscaling || {}).map(([k, v]) => (
                <div key={k} className="flex justify-between bg-zinc-800/50 rounded p-2">
                  <span className="text-zinc-300 capitalize">{k}</span>
                  <Badge data-testid={`autoscale-${k}`} className={v === "scale_up" ? "bg-amber-600 text-white" : v === "scale_down" ? "bg-blue-600 text-white" : ""} variant="outline">{v}</Badge>
                </div>
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
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { type: "crash", label: "Worker Crash", desc: "Verify tasks survive worker crash" },
              { type: "dlq_capture", label: "DLQ Capture", desc: "Verify exhausted retries go to DLQ" },
              { type: "retry", label: "Retry Behavior", desc: "Verify retryable tasks are requeued" },
            ].map(sim => (
              <Card key={sim.type} className="bg-zinc-900 border-zinc-800">
                <CardHeader className="pb-2"><CardTitle className="text-sm">{sim.label}</CardTitle></CardHeader>
                <CardContent className="text-xs space-y-2">
                  <p className="text-zinc-500">{sim.desc}</p>
                  <Button data-testid={`sim-${sim.type}`} size="sm" variant="outline" className="text-xs w-full"
                    disabled={simLoading[sim.type]}
                    onClick={() => runSimulation(sim.type, `/workers/simulate-failure/${sim.type}`)}>
                    {simLoading[sim.type] ? "Running..." : "Run Simulation"}
                  </Button>
                  {simResults[sim.type] && (
                    <div data-testid={`sim-result-${sim.type}`} className={`p-2 rounded ${simResults[sim.type].verdict === "PASS" ? "bg-emerald-900/30 border border-emerald-800" : "bg-red-900/30 border border-red-800"}`}>
                      <p className="font-mono font-bold">{simResults[sim.type].verdict}</p>
                      {simResults[sim.type].verification && Object.entries(simResults[sim.type].verification).map(([k, v]) => (
                        <p key={k} className="text-zinc-400">{k}: {String(v)}</p>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
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
                <Button data-testid={`incident-${t.type}`} size="sm" variant="outline" className="text-xs w-full"
                  disabled={simLoading[`inc_${t.type}`]}
                  onClick={() => runSimulation(`inc_${t.type}`, `/workers/incident-test/${t.type}`)}>
                  {simLoading[`inc_${t.type}`] ? "Testing..." : "Run Test"}
                </Button>
                {simResults[`inc_${t.type}`] && (
                  <div data-testid={`incident-result-${t.type}`} className={`p-2 rounded ${simResults[`inc_${t.type}`].verdict === "PASS" ? "bg-emerald-900/30 border border-emerald-800" : "bg-red-900/30 border border-red-800"}`}>
                    <p className="font-mono font-bold">{simResults[`inc_${t.type}`].verdict}</p>
                    {simResults[`inc_${t.type}`]?.test_steps?.map((s, i) => (
                      <p key={i} className="text-zinc-400">{s.step}: <span className={s.result === "PASS" ? "text-emerald-400" : "text-red-400"}>{s.result}</span></p>
                    ))}
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

function QueueMonitoringPanel() {
  const { data, loading, refetch } = useApi("/workers/monitoring");
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
            <div key={q} className="flex justify-between bg-zinc-800/50 rounded p-2">
              <span className="text-zinc-400 truncate">{q}</span>
              <span data-testid={`qdepth-${q}`} className="font-mono text-zinc-200">{d}</span>
            </div>
          ))}
        </div></CardContent>
      </Card>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">DLQ Depths</CardTitle></CardHeader>
        <CardContent><div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {Object.entries(data.dlq_depths || {}).map(([q, d]) => (
            <div key={q} className="flex justify-between bg-zinc-800/50 rounded p-2">
              <span className="text-zinc-400 truncate">{q}</span>
              <span data-testid={`dlqdepth-${q}`} className={`font-mono ${d > 0 ? "text-red-400" : "text-zinc-200"}`}>{d}</span>
            </div>
          ))}
        </div></CardContent>
      </Card>
    </div>
  );
}

function WorkerPoolsPanel() {
  const { data: pools, loading } = useApi("/workers/pools");
  if (loading || !pools) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs text-zinc-400"><Layers className="w-4 h-4" /> {pools.total_pools} pools, {pools.total_queues} queues</div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {Object.entries(pools.pools || {}).map(([name, pool]) => (
          <Card key={name} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm capitalize flex items-center gap-2">
                {name} <Badge data-testid={`pool-priority-${name}`} variant="outline" className="text-[10px]">{pool.priority}</Badge>
              </CardTitle>
            </CardHeader>
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
  const { data: dlq, loading } = useApi("/workers/dlq");
  if (loading || !dlq) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Badge data-testid="dlq-status" className={dlq.status === "healthy" ? "bg-emerald-600 text-white" : "bg-amber-600 text-white"}>{dlq.status}</Badge>
        <span className="text-xs text-zinc-400">Dead Letters: {dlq.total_dead_letters} | Permanent Failures: {dlq.permanent_failures}</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {Object.entries(dlq.queues || {}).map(([q, d]) => (
          <div key={q} className="bg-zinc-800/50 rounded p-2 text-xs">
            <span className="text-zinc-500 block text-[10px]">{q}</span>
            <span data-testid={`dlq-depth-${q}`} className="text-zinc-200 font-mono">{d.depth}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AutoscalingPanel() {
  const { data: autoscaling, loading } = useApi("/workers/autoscaling");
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
              <p>Queue Depth: {d.current_depth}</p>
              <p>Thresholds: up={d.scale_up_threshold}, down={d.scale_down_threshold}</p>
              <p>Workers: {d.min_workers}-{d.max_workers}</p>
              <p className="text-zinc-500 text-[10px]">{d.reason}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      {autoscaling.rules && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Autoscale Rules</CardTitle></CardHeader>
          <CardContent className="text-xs">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {Object.entries(autoscaling.rules).map(([k, v]) => (
                <div key={k} className="bg-zinc-800/50 rounded p-2 text-zinc-400">
                  <span className="text-zinc-300 capitalize font-medium">{k}</span>
                  <p>Scale up: depth {">="} {v.scale_up.queue_depth_threshold} or latency {">="} {v.scale_up.latency_ms_threshold}ms</p>
                  <p>Scale down: depth {"<="} {v.scale_down.queue_depth_threshold}, idle {v.scale_down.idle_minutes}m</p>
                  <p>Cooldown: {v.cooldown_seconds}s</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ObservabilityPanel() {
  const { data: observability, loading } = useApi("/workers/observability");
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
          <CardContent className="text-xs">
            <div className="space-y-1">
              {observability.worker_processes.map((w, i) => (
                <div key={i} className="flex gap-4 bg-zinc-800/50 rounded p-2 text-zinc-400">
                  <span className="text-zinc-300 font-mono">PID {w.pid}</span>
                  <span>CPU: {w.cpu_pct}%</span>
                  <span>MEM: {w.mem_pct}%</span>
                  <span>RSS: {Math.round(w.rss_kb / 1024)}MB</span>
                </div>
              ))}
            </div>
          </CardContent>
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
        <Button data-testid="run-perf-test" size="sm" variant="outline" className="text-xs"
          disabled={simLoading.perf}
          onClick={() => runSimulation("perf", "/workers/performance-test?jobs_per_minute=1000")}>
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
  const { data, loading, refetch } = useApi("/workers/infrastructure-score");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <ScoreGauge score={data.infrastructure_score} max={10} label="Infrastructure" />
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Badge data-testid="infra-meets-target" className={data.meets_target ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>
              {data.meets_target ? "TARGET MET" : "BELOW TARGET"}
            </Badge>
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

/* ========== LIVE INFRASTRUCTURE TAB ========== */
function LiveInfrastructureTab() {
  const { data, loading, refetch } = useApi("/hardening/activation/infrastructure");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;

  const svc = data.services;
  const statusIcon = (s) => s === "healthy" ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : s === "no_workers" ? <Clock className="w-4 h-4 text-amber-400" /> : <XCircle className="w-4 h-4 text-red-400" />;
  const statusColor = (s) => s === "healthy" ? "border-emerald-600/40 bg-emerald-950/10" : s === "no_workers" ? "border-amber-600/40 bg-amber-950/10" : "border-red-600/40 bg-red-950/10";

  return (
    <div data-testid="live-infra-tab" className="space-y-6">
      {/* Overall Status */}
      <div className={`rounded-lg border p-4 flex items-center gap-4 ${data.overall_status === "healthy" ? "border-emerald-600/40 bg-emerald-950/10" : "border-amber-600/40 bg-amber-950/10"}`}>
        <Radio className={`w-6 h-6 ${data.overall_status === "healthy" ? "text-emerald-400" : "text-amber-400"} animate-pulse`} />
        <div>
          <div data-testid="infra-overall-status" className="text-lg font-bold text-zinc-100 uppercase">{data.overall_status}</div>
          <p className="text-xs text-zinc-500">{data.healthy_services}/{data.total_services} services healthy</p>
        </div>
      </div>

      {/* Service Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Redis */}
        <Card className={`border ${statusColor(svc.redis.status)}`}>
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2">{statusIcon(svc.redis.status)} Redis</CardTitle></CardHeader>
          <CardContent className="text-xs space-y-2 text-zinc-400">
            <div className="flex justify-between"><span>Status</span><Badge data-testid="redis-live-status" className={svc.redis.status === "healthy" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{svc.redis.status}</Badge></div>
            <div className="flex justify-between"><span>Latency</span><span className="font-mono text-zinc-200">{svc.redis.latency_ms}ms</span></div>
            {svc.redis.details && <>
              <div className="flex justify-between"><span>Memory</span><span className="font-mono text-zinc-200">{svc.redis.details.used_memory_human}</span></div>
              <div className="flex justify-between"><span>Clients</span><span className="font-mono text-zinc-200">{svc.redis.details.connected_clients}</span></div>
              <div className="flex justify-between"><span>Version</span><span className="font-mono text-zinc-200">{svc.redis.details.redis_version}</span></div>
              <div className="flex justify-between"><span>Keys</span><span className="font-mono text-zinc-200">{svc.redis.details.total_keys}</span></div>
              <div className="flex justify-between"><span>Queue Depth</span><span className="font-mono text-zinc-200">{svc.redis.details.total_queue_depth}</span></div>
            </>}
          </CardContent>
        </Card>

        {/* Celery */}
        <Card className={`border ${statusColor(svc.celery.status)}`}>
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2">{statusIcon(svc.celery.status)} Celery Workers</CardTitle></CardHeader>
          <CardContent className="text-xs space-y-2 text-zinc-400">
            <div className="flex justify-between"><span>Status</span><Badge data-testid="celery-live-status" className={svc.celery.status === "healthy" ? "bg-emerald-600 text-white" : svc.celery.status === "no_workers" ? "bg-amber-500 text-white" : "bg-red-600 text-white"}>{svc.celery.status}</Badge></div>
            <div className="flex justify-between"><span>Workers</span><span className="font-mono text-zinc-200">{svc.celery.details?.worker_count || 0}</span></div>
            <div className="flex justify-between"><span>Active Tasks</span><span className="font-mono text-zinc-200">{svc.celery.details?.total_active_tasks || 0}</span></div>
            <div className="border-t border-zinc-800 pt-2 mt-2">
              <p className="text-zinc-500 mb-1">Queues:</p>
              <div className="flex flex-wrap gap-1">
                {(svc.celery.details?.queues_configured || []).map(q => <Badge key={q} variant="outline" className="text-[10px]">{q}</Badge>)}
              </div>
            </div>
            <div>
              <p className="text-zinc-500 mb-1">DLQ:</p>
              <div className="flex flex-wrap gap-1">
                {(svc.celery.details?.dlq_configured || []).map(q => <Badge key={q} variant="outline" className="text-[10px] border-red-800 text-red-400">{q}</Badge>)}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* MongoDB */}
        <Card className={`border ${statusColor(svc.mongodb.status)}`}>
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2">{statusIcon(svc.mongodb.status)} MongoDB</CardTitle></CardHeader>
          <CardContent className="text-xs space-y-2 text-zinc-400">
            <div className="flex justify-between"><span>Status</span><Badge data-testid="mongodb-live-status" className={svc.mongodb.status === "healthy" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{svc.mongodb.status}</Badge></div>
            <div className="flex justify-between"><span>Latency</span><span className="font-mono text-zinc-200">{svc.mongodb.latency_ms}ms</span></div>
            {svc.mongodb.details && <>
              <div className="flex justify-between"><span>Collections</span><span className="font-mono text-zinc-200">{svc.mongodb.details.collections}</span></div>
              <div className="flex justify-between"><span>Data Size</span><span className="font-mono text-zinc-200">{svc.mongodb.details.data_size_mb} MB</span></div>
              <div className="flex justify-between"><span>Indexes</span><span className="font-mono text-zinc-200">{svc.mongodb.details.indexes}</span></div>
              <div className="flex justify-between"><span>Objects</span><span className="font-mono text-zinc-200">{svc.mongodb.details.objects?.toLocaleString()}</span></div>
            </>}
          </CardContent>
        </Card>
      </div>

      {/* Queue Depths Detail */}
      {svc.redis.details?.queue_depths && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Celery Queue Depths</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
              {Object.entries(svc.redis.details.queue_depths).map(([q, depth]) => (
                <div key={q} className={`flex flex-col items-center p-3 rounded-lg ${depth > 0 ? "bg-amber-950/20 border border-amber-800/30" : "bg-zinc-800/50"}`}>
                  <span className={`text-lg font-bold font-mono ${depth > 0 ? "text-amber-400" : "text-zinc-400"}`}>{depth}</span>
                  <span className="text-[10px] text-zinc-500 mt-1 text-center">{q}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Button data-testid="refresh-infra" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

/* ========== PERFORMANCE BASELINE TAB ========== */
function PerformanceBaselineTab() {
  const { data, loading, refetch } = useApi("/hardening/activation/performance");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;

  const results = data.results;
  const sla = data.sla_summary;

  return (
    <div data-testid="perf-baseline-tab" className="space-y-6">
      {/* SLA Summary */}
      <div className={`rounded-lg border p-4 ${sla.pass_rate_pct === 100 ? "border-emerald-600/40 bg-emerald-950/10" : "border-amber-600/40 bg-amber-950/10"}`}>
        <div className="flex items-center justify-between">
          <div>
            <div data-testid="sla-pass-rate" className="text-2xl font-bold text-zinc-100">{sla.pass_rate_pct}%</div>
            <p className="text-xs text-zinc-500">SLA Pass Rate ({sla.passing}/{sla.total_tests} tests)</p>
          </div>
          <div className="text-right text-xs text-zinc-500">
            <p>Target: 10k searches/hr</p>
            <p>Target: 1k bookings/hr</p>
          </div>
        </div>
      </div>

      {/* Individual Test Results */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(results).map(([key, result]) => {
          if (result.error) return (
            <Card key={key} className="bg-red-950/20 border-red-900/40">
              <CardHeader className="pb-2"><CardTitle className="text-sm">{key.replace(/_/g, " ")}</CardTitle></CardHeader>
              <CardContent><p className="text-xs text-red-400">{result.error}</p></CardContent>
            </Card>
          );
          return (
            <Card key={key} className={`border ${result.passes_sla ? "border-emerald-600/40 bg-emerald-950/10" : "border-red-600/40 bg-red-950/10"}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  {result.passes_sla ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
                  {key.replace(/_/g, " ")}
                </CardTitle>
              </CardHeader>
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

/* ========== INCIDENT SIMULATION TAB ========== */
function IncidentSimulationTab() {
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(null);

  const runSimulation = async (type) => {
    setRunning(type);
    try {
      const res = await api.post(`/hardening/activation/incident/${type}`);
      setResults(prev => ({ ...prev, [type]: res.data }));
    } catch (e) {
      setResults(prev => ({ ...prev, [type]: { error: "Simulation failed" } }));
    }
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
              <Button data-testid={`simulate-${type}`} size="sm" variant="outline" className="w-full" onClick={() => runSimulation(type)} disabled={running === type}>
                {running === type ? <RefreshCw className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-1" />}
                {running === type ? "Running..." : "Simulate"}
              </Button>
              {results[type] && !results[type].error && (
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-zinc-400">Verdict</span>
                    <Badge className={results[type].verdict === "PASS" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{results[type].verdict}</Badge>
                  </div>
                  {results[type].playbook_executed && (
                    <div className="border-t border-zinc-800 pt-2">
                      <p className="text-zinc-500 mb-1">Playbook Steps:</p>
                      {Object.entries(results[type].playbook_executed).map(([step, action]) => (
                        <div key={step} className="flex items-start gap-1.5 py-0.5">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                          <span className="text-zinc-300">{action}</span>
                        </div>
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

/* ========== TENANT ISOLATION (REAL) TAB ========== */
function TenantIsolationRealTab() {
  const { data, loading, refetch } = useApi("/hardening/activation/tenant-isolation");
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

      {/* Cross-tenant test results */}
      <div className="grid grid-cols-3 gap-4">
        {Object.entries(data.cross_tenant_test).map(([test, result]) => (
          <Card key={test} className={`border ${result === "PASS" ? "border-emerald-600/40 bg-emerald-950/10" : "border-red-600/40 bg-red-950/10"}`}>
            <CardContent className="pt-4 flex items-center justify-between">
              <span className="text-xs text-zinc-300">{test.replace(/_/g, " ")}</span>
              <Badge className={result === "PASS" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{result}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Collection details */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Collection Isolation Details</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="text-zinc-500 border-b border-zinc-800">
                <th className="text-left py-2">Collection</th><th className="text-center">Status</th><th className="text-center">Tenant Field</th><th className="text-right">Docs</th><th className="text-center">Risk</th>
              </tr></thead>
              <tbody>
                {data.results.map((r, i) => (
                  <tr key={i} className="border-b border-zinc-800/50">
                    <td className="py-1.5 text-zinc-300 font-mono">{r.collection}</td>
                    <td className="text-center">
                      <Badge variant={r.status === "isolated" ? "default" : r.status === "empty" ? "outline" : "destructive"} className="text-[10px]">{r.status}</Badge>
                    </td>
                    <td className="text-center text-zinc-400">{r.field_name || "-"}</td>
                    <td className="text-right font-mono text-zinc-400">{r.total_docs ?? "-"}</td>
                    <td className="text-center"><Badge variant={r.risk === "low" ? "outline" : r.risk === "critical" ? "destructive" : "default"} className="text-[10px]">{r.risk}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Button data-testid="refresh-tenant-real" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-run Tests</Button>
    </div>
  );
}

/* ========== DRY RUN TAB ========== */
function DryRunTab() {
  const { data, loading, refetch } = useApi("/hardening/activation/dry-run");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;

  return (
    <div data-testid="dry-run-tab" className="space-y-6">
      {/* Overall Result */}
      <div className={`rounded-lg border p-4 text-center ${data.dry_run_result === "PASS" ? "border-emerald-600/40 bg-emerald-950/10" : "border-red-600/40 bg-red-950/10"}`}>
        <div data-testid="dry-run-result" className={`text-3xl font-bold ${data.dry_run_result === "PASS" ? "text-emerald-400" : "text-red-400"}`}>
          {data.dry_run_result}
        </div>
        <p className="text-xs text-zinc-500 mt-1">{data.summary.passing}/{data.summary.total_steps} steps passed in {data.summary.total_duration_ms}ms</p>
      </div>

      {/* Steps */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Pipeline Steps: Search &rarr; Price &rarr; Book &rarr; Voucher &rarr; Notify</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {data.steps.map((step) => (
            <div key={step.step} data-testid={`dry-run-step-${step.step}`} className={`flex items-center justify-between rounded-lg p-3 border ${step.status === "pass" ? "border-emerald-600/30 bg-emerald-950/10" : "border-red-600/30 bg-red-950/10"}`}>
              <div className="flex items-center gap-3">
                {step.status === "pass" ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <XCircle className="w-5 h-5 text-red-400" />}
                <div>
                  <p className="text-sm font-medium text-zinc-200">Step {step.step}: {step.name}</p>
                  <p className="text-xs text-zinc-500">{step.details || step.error}</p>
                </div>
              </div>
              {step.duration_ms !== undefined && <span className="text-xs font-mono text-zinc-400">{step.duration_ms}ms</span>}
            </div>
          ))}
        </CardContent>
      </Card>

      <Button data-testid="rerun-dry-run" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-run Dry Run</Button>
    </div>
  );
}

/* ========== ONBOARDING TAB ========== */
function OnboardingTab() {
  const { data, loading, refetch } = useApi("/hardening/activation/onboarding");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;

  const s = data.summary;
  return (
    <div data-testid="onboarding-tab" className="space-y-6">
      <div className={`rounded-lg border p-4 ${s.onboarding_ready_pct >= 80 ? "border-emerald-600/40 bg-emerald-950/10" : "border-amber-600/40 bg-amber-950/10"}`}>
        <div className="flex items-center justify-between">
          <div>
            <div data-testid="onboarding-readiness" className="text-2xl font-bold text-zinc-100">{s.onboarding_ready_pct}%</div>
            <p className="text-xs text-zinc-500">Onboarding Readiness ({s.ready}/{s.total_checks} checks pass)</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Checks */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Readiness Checks</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {data.checks.map((c, i) => (
              <div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2.5">
                <div className="flex items-center gap-2">
                  {c.status === "ready" ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : c.status === "test_mode" ? <Clock className="w-4 h-4 text-amber-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
                  <div>
                    <p className="text-xs text-zinc-200">{c.check}</p>
                    <p className="text-[10px] text-zinc-500">{c.details}</p>
                  </div>
                </div>
                <Badge variant={c.status === "ready" ? "default" : c.status === "test_mode" ? "outline" : "destructive"} className="text-[10px]">{c.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Workflow */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Onboarding Workflow</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(data.onboarding_workflow).map(([step, desc]) => (
              <div key={step} className="flex items-center gap-3 bg-zinc-800/50 rounded p-2.5">
                <div className="w-6 h-6 rounded-full bg-zinc-700 flex items-center justify-center text-[10px] font-bold text-zinc-300">{step.split("_")[1]}</div>
                <span className="text-xs text-zinc-300">{desc}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Button data-testid="refresh-onboarding" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}

/* ========== GO-LIVE CERTIFICATION (REAL) TAB ========== */
function GoLiveCertificationTab() {
  const { data, loading, refetch } = useApi("/hardening/activation/certification");
  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;

  const cert = data.certification;
  const scores = data.dimension_scores;
  const weights = data.weights;

  return (
    <div data-testid="golive-cert-tab" className="space-y-6">
      {/* Decision Banner */}
      <div className={`rounded-lg border-2 p-6 text-center ${cert.decision === "GO" ? "border-emerald-500 bg-emerald-950/20" : "border-red-500 bg-red-950/20"}`}>
        <div data-testid="golive-decision" className={`text-4xl font-black tracking-wider ${cert.decision === "GO" ? "text-emerald-400" : "text-red-400"}`}>
          {cert.decision}
        </div>
        <div className="text-lg mt-2 text-zinc-300">Production Readiness: <span className="font-bold">{cert.production_readiness_score}/10</span></div>
        {cert.gap > 0 && <p className="text-sm text-zinc-500 mt-1">Gap to target (8.5): {cert.gap} points</p>}
      </div>

      {/* Dimension Scores */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Dimension Scores (Weighted)</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(scores).map(([dim, score]) => (
              <div key={dim} className="bg-zinc-800/50 rounded-lg p-3 text-center">
                <div className={`text-xl font-bold ${score >= 8 ? "text-emerald-400" : score >= 5 ? "text-amber-400" : "text-red-400"}`}>{score}</div>
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider mt-0.5">{dim}</div>
                <div className="text-[9px] text-zinc-600 mt-0.5">weight: {((weights[dim] || 0) * 100).toFixed(0)}%</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Status Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 text-center">
            <Badge className={data.infrastructure.status === "healthy" ? "bg-emerald-600 text-white" : "bg-amber-500 text-white"}>{data.infrastructure.status}</Badge>
            <p className="text-xs text-zinc-500 mt-1">Infrastructure</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 text-center">
            <div className="text-xl font-bold text-zinc-100">{data.security?.security_score ?? "?"}/10</div>
            <p className="text-xs text-zinc-500 mt-1">Security Score</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 text-center">
            <Badge className={data.reliability.dry_run_result === "PASS" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"}>{data.reliability.dry_run_result}</Badge>
            <p className="text-xs text-zinc-500 mt-1">Dry Run</p>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-4 text-center">
            <div className="text-xl font-bold text-zinc-100">{data.suppliers.active}/{data.suppliers.total}</div>
            <p className="text-xs text-zinc-500 mt-1">Suppliers Active</p>
          </CardContent>
        </Card>
      </div>

      {/* Risks */}
      {data.risks.length > 0 && (
        <Card className="bg-red-950/20 border-red-900/40">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Risk Analysis ({data.risks.length} items)</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {data.risks.map((r, i) => (
              <div key={i} className="flex items-center justify-between bg-zinc-900/50 rounded p-2.5">
                <div className="flex items-center gap-2">
                  <AlertTriangle className={`w-4 h-4 flex-shrink-0 ${r.severity === "critical" ? "text-red-400" : "text-amber-400"}`} />
                  <div>
                    <p className="text-xs text-zinc-200">{r.risk}</p>
                    <p className="text-[10px] text-zinc-500">{r.mitigation}</p>
                  </div>
                </div>
                <Badge variant={r.severity === "critical" ? "destructive" : "default"} className="text-[10px]">{r.severity}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <div className="flex items-center gap-2 text-xs text-zinc-600">
        Risk Level: <Badge variant={data.risk_level === "critical" ? "destructive" : data.risk_level === "high" ? "default" : "outline"} className="text-[10px]">{data.risk_level}</Badge>
        <span className="ml-auto">Onboarding: {data.onboarding_ready}% ready</span>
      </div>

      <Button data-testid="refresh-golive" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-certify</Button>
    </div>
  );
}

/* ========== SECURITY DASHBOARD TAB ========== */
function SecurityDashboardTab() {
  const { data, loading, refetch } = useApi("/hardening/security/readiness");
  const { data: jwt } = useApi("/hardening/security/jwt");
  const { data: tests } = useApi("/hardening/security/tests");

  if (loading || !data) return <div className="animate-pulse h-64 bg-zinc-900 rounded-lg" />;

  const dims = data.dimensions;

  return (
    <div data-testid="security-dashboard-tab" className="space-y-6">
      {/* Score Banner */}
      <div className={`rounded-lg border-2 p-6 text-center ${data.meets_target ? "border-emerald-500 bg-emerald-950/20" : "border-red-500 bg-red-950/20"}`}>
        <div data-testid="security-score" className={`text-4xl font-black tracking-wider ${data.meets_target ? "text-emerald-400" : "text-red-400"}`}>
          {data.security_readiness_score}/10
        </div>
        <p className="text-sm text-zinc-400 mt-1">Security Readiness {data.meets_target ? "(TARGET MET)" : `(Gap: ${data.gap})`}</p>
      </div>

      {/* Dimension Cards */}
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

      {/* JWT Security */}
      {jwt && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Lock className="w-4 h-4" /> JWT Security ({jwt.summary.score_pct}%)</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {jwt.checks.map((c, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-zinc-800/50 rounded p-2">
                <div className="flex items-center gap-2">
                  {c.status === "pass" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}
                  <span className="text-zinc-300">{c.check}</span>
                </div>
                <span className="text-zinc-500 text-[10px] max-w-[40%] text-right">{c.details}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Security Tests */}
      {tests && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Shield className="w-4 h-4" /> Security Tests ({tests.summary.pass_rate_pct}%)</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {tests.tests.map((t, i) => (
              <div key={i} className="flex items-center justify-between text-xs bg-zinc-800/50 rounded p-2">
                <div className="flex items-center gap-2">
                  {t.status === "pass" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-red-400" />}
                  <span className="text-zinc-300">{t.test}</span>
                </div>
                <span className="text-zinc-500 text-[10px] max-w-[40%] text-right">{t.details}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Risks */}
      {data.risks.length > 0 && (
        <Card className="bg-red-950/20 border-red-900/40">
          <CardHeader className="pb-2"><CardTitle className="text-sm text-red-400">Risks ({data.risks.length})</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {data.risks.map((r, i) => (
              <div key={i} className="flex items-center gap-2 text-xs"><AlertTriangle className="w-3.5 h-3.5 text-red-400" /><span className="text-zinc-300">{r.risk}</span><Badge variant="destructive" className="text-[10px] ml-auto">{r.severity}</Badge></div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Top Fixes */}
      {data.top_fixes.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Top Fixes ({data.top_fixes.length})</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {data.top_fixes.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-xs"><span className="text-zinc-300">{f.fix}</span><Badge variant={f.impact === "high" ? "destructive" : "default"} className="text-[10px] ml-auto">{f.impact}</Badge></div>
            ))}
          </CardContent>
        </Card>
      )}

      <Button data-testid="refresh-security" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Re-scan</Button>
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

      <Tabs defaultValue="golive" className="space-y-4">
        <TabsList data-testid="hardening-tabs" className="bg-zinc-900 border border-zinc-800 flex-wrap h-auto gap-1 p-1">
          {/* Production Activation Tabs */}
          <TabsTrigger value="golive" className="text-xs gap-1 data-[state=active]:bg-emerald-700 data-[state=active]:text-white"><FileCheck className="w-3.5 h-3.5" />Go-Live</TabsTrigger>
          <TabsTrigger value="suppliers" className="text-xs gap-1 data-[state=active]:bg-purple-700 data-[state=active]:text-white"><Truck className="w-3.5 h-3.5" />Suppliers</TabsTrigger>
          <TabsTrigger value="security" className="text-xs gap-1 data-[state=active]:bg-red-700 data-[state=active]:text-white"><Shield className="w-3.5 h-3.5" />Security</TabsTrigger>
          <TabsTrigger value="infra" className="text-xs gap-1"><Radio className="w-3.5 h-3.5" />Infrastructure</TabsTrigger>
          <TabsTrigger value="perfbaseline" className="text-xs gap-1"><Gauge className="w-3.5 h-3.5" />Performance</TabsTrigger>
          <TabsTrigger value="incidents" className="text-xs gap-1"><FlaskConical className="w-3.5 h-3.5" />Incidents</TabsTrigger>
          <TabsTrigger value="isolation" className="text-xs gap-1"><Lock className="w-3.5 h-3.5" />Isolation</TabsTrigger>
          <TabsTrigger value="dryrun" className="text-xs gap-1"><Play className="w-3.5 h-3.5" />Dry Run</TabsTrigger>
          <TabsTrigger value="onboarding" className="text-xs gap-1"><Users className="w-3.5 h-3.5" />Onboarding</TabsTrigger>
          <TabsTrigger value="stresstest" className="text-xs gap-1 data-[state=active]:bg-orange-700 data-[state=active]:text-white"><Zap className="w-3.5 h-3.5" />Stress Test</TabsTrigger>
          <TabsTrigger value="pilot" className="text-xs gap-1 data-[state=active]:bg-sky-700 data-[state=active]:text-white"><Play className="w-3.5 h-3.5" />Pilot Launch</TabsTrigger>
          <TabsTrigger value="supplier-settings" className="text-xs gap-1 data-[state=active]:bg-emerald-700 data-[state=active]:text-white"><Plug className="w-3.5 h-3.5" />Supplier Settings</TabsTrigger>
          {/* Design & Execution Tabs */}
          <TabsTrigger value="overview" className="text-xs gap-1"><Shield className="w-3.5 h-3.5" />Overview</TabsTrigger>
          <TabsTrigger value="execution" className="text-xs gap-1"><Target className="w-3.5 h-3.5" />Execution</TabsTrigger>
          <TabsTrigger value="traffic" className="text-xs gap-1"><Zap className="w-3.5 h-3.5" />Traffic</TabsTrigger>
          <TabsTrigger value="workers" className="text-xs gap-1"><Server className="w-3.5 h-3.5" />Workers</TabsTrigger>
          <TabsTrigger value="observability" className="text-xs gap-1"><Activity className="w-3.5 h-3.5" />Observability</TabsTrigger>
          <TabsTrigger value="secrets" className="text-xs gap-1"><Lock className="w-3.5 h-3.5" />Secrets</TabsTrigger>
          <TabsTrigger value="scaling" className="text-xs gap-1"><Scale className="w-3.5 h-3.5" />Scaling</TabsTrigger>
          <TabsTrigger value="dr" className="text-xs gap-1"><Database className="w-3.5 h-3.5" />DR</TabsTrigger>
          <TabsTrigger value="checklist" className="text-xs gap-1"><CheckCircle2 className="w-3.5 h-3.5" />Checklist</TabsTrigger>
        </TabsList>

        {/* Production Activation */}
        <TabsContent value="golive"><GoLiveCertificationTab /></TabsContent>
        <TabsContent value="suppliers"><SupplierActivationTab /></TabsContent>
        <TabsContent value="security"><SecurityDashboardTab /></TabsContent>
        <TabsContent value="infra"><LiveInfrastructureTab /></TabsContent>
        <TabsContent value="perfbaseline"><PerformanceBaselineTab /></TabsContent>
        <TabsContent value="incidents"><IncidentSimulationTab /></TabsContent>
        <TabsContent value="isolation"><TenantIsolationRealTab /></TabsContent>
        <TabsContent value="dryrun"><DryRunTab /></TabsContent>
        <TabsContent value="onboarding"><OnboardingTab /></TabsContent>
        <TabsContent value="stresstest"><StressTestTab /></TabsContent>
        <TabsContent value="pilot"><PilotLaunchTab /></TabsContent>
        <TabsContent value="supplier-settings"><SupplierSettingsTab /></TabsContent>
        {/* Design & Execution */}
        <TabsContent value="overview"><OverviewTab /></TabsContent>
        <TabsContent value="execution"><ExecutionTab /></TabsContent>
        <TabsContent value="traffic"><TrafficTestingTab /></TabsContent>
        <TabsContent value="workers"><WorkerStrategyTab /></TabsContent>
        <TabsContent value="observability"><ObservabilityTab /></TabsContent>
        <TabsContent value="secrets"><SecretsTab /></TabsContent>
        <TabsContent value="scaling"><ScalingTab /></TabsContent>
        <TabsContent value="dr"><DRTab /></TabsContent>
        <TabsContent value="checklist"><ChecklistTab /></TabsContent>
      </Tabs>
    </div>
  );
}
