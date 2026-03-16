import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { RefreshCw, ChevronDown, ChevronUp, XCircle, Loader2, CheckCircle2 } from "lucide-react";
import { ScoreGauge } from "./ScoreGauge";
import { useHardeningApi, hardeningApi } from "../api";
import { severityColor, statusBadge } from "../helpers";

export function OverviewTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/overview");
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="overview-tab" className="space-y-6">
      <div className="flex items-center gap-6 bg-zinc-900 border border-zinc-800 rounded-lg p-6">
        <ScoreGauge score={data.overall_score} max={10} label="Overall Score" />
        <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div className="bg-zinc-800/50 rounded-lg p-3"><span className="text-zinc-500 block">Phases</span><span data-testid="phase-progress" className="text-lg font-bold text-zinc-200">{data.completed_phases}/{data.total_phases}</span></div>
          <div className="bg-zinc-800/50 rounded-lg p-3"><span className="text-zinc-500 block">Tasks</span><span data-testid="task-progress" className="text-lg font-bold text-zinc-200">{data.completed_tasks}/{data.total_tasks}</span></div>
          <div className="bg-zinc-800/50 rounded-lg p-3"><span className="text-zinc-500 block">Blockers</span><span data-testid="blocker-count" className="text-lg font-bold text-red-400">{data.open_blockers}</span></div>
          <div className="bg-zinc-800/50 rounded-lg p-3"><span className="text-zinc-500 block">Risk Level</span><Badge data-testid="risk-level" variant={severityColor(data.risk_level)}>{data.risk_level}</Badge></div>
        </div>
        <Button data-testid="refresh-overview" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-4 h-4" /></Button>
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">Phase Summary</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {data.phases?.map((p) => (
              <div key={p.id} className="flex items-center gap-3 bg-zinc-800/50 rounded-lg p-3">
                {statusBadge(p.status)}
                <div className="flex-1 min-w-0"><div className="text-sm font-medium text-zinc-200 truncate">{p.name}</div><div className="text-xs text-zinc-500">{p.completed}/{p.total} tasks</div></div>
                <span className="text-xs font-mono text-zinc-400">{p.score}/10</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function ExecutionTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/execution/status");
  const [busyPhase, setBusyPhase] = useState(null);
  const [busyTask, setBusyTask] = useState(null);
  const [busyBlocker, setBusyBlocker] = useState(null);

  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;

  const startPhase = async (id) => { setBusyPhase(id); try { await hardeningApi.startPhase(id); await refetch(); } finally { setBusyPhase(null); } };
  const completeTask = async (phaseId, taskId) => { setBusyTask(taskId); try { await hardeningApi.completeTask(phaseId, taskId); await refetch(); } finally { setBusyTask(null); } };
  const resolveBlocker = async (id) => { setBusyBlocker(id); try { await hardeningApi.resolveBlocker(id); await refetch(); } finally { setBusyBlocker(null); } };

  return (
    <div data-testid="execution-tab" className="space-y-6">
      <div className="flex items-center gap-2">
        <ScoreGauge score={data.overall_progress_pct} max={100} label="Progress" size="sm" />
        <div className="text-xs text-zinc-400 space-y-0.5">
          <p>Total tasks: {data.total_tasks} | Done: {data.completed_tasks}</p>
          <p>Open blockers: {data.open_blockers}</p>
        </div>
        <Button data-testid="refresh-execution" variant="outline" size="sm" className="ml-auto" onClick={refetch}><RefreshCw className="w-3.5 h-3.5" /></Button>
      </div>
      <div className="space-y-4">
        {data.phases?.map((phase) => (
          <Card key={phase.phase_id} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {statusBadge(phase.status)}
                  <CardTitle className="text-sm">{phase.name}</CardTitle>
                  <span className="text-xs text-zinc-500">({phase.completed}/{phase.total} tasks)</span>
                </div>
                {phase.status === "planned" && (
                  <Button data-testid={`start-phase-${phase.phase_id}`} variant="outline" size="sm" disabled={busyPhase === phase.phase_id} onClick={() => startPhase(phase.phase_id)}>
                    {busyPhase === phase.phase_id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Start"}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-1.5 text-xs">
              {phase.tasks?.map((t) => (
                <div key={t.task_id} className="flex items-center justify-between bg-zinc-800/50 rounded p-2">
                  <div className="flex items-center gap-2">
                    {t.status === "done" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <div className="w-3.5 h-3.5 rounded-full border border-zinc-600" />}
                    <span className={t.status === "done" ? "text-zinc-500 line-through" : "text-zinc-300"}>{t.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={severityColor(t.risk)} className="text-[10px]">{t.risk}</Badge>
                    {t.status !== "done" && phase.status === "in_progress" && (
                      <Button size="xs" variant="outline" disabled={busyTask === t.task_id} onClick={() => completeTask(phase.phase_id, t.task_id)}>
                        {busyTask === t.task_id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Done"}
                      </Button>
                    )}
                  </div>
                </div>
              ))}
              {phase.blockers?.filter((b) => !b.resolved).length > 0 && (
                <div className="mt-2 space-y-1">
                  <p className="text-red-400 font-semibold text-xs">Blockers:</p>
                  {phase.blockers.filter((b) => !b.resolved).map((b) => (
                    <div key={b.id} className="flex items-center justify-between bg-red-950/30 rounded p-2">
                      <div className="flex items-center gap-2"><XCircle className="w-3.5 h-3.5 text-red-400" /><span className="text-red-200">{b.blocker}</span></div>
                      <Button size="xs" variant="outline" disabled={busyBlocker === b.id} onClick={() => resolveBlocker(b.id)}>
                        {busyBlocker === b.id ? <Loader2 className="w-3 h-3 animate-spin" /> : "Resolve"}
                      </Button>
                    </div>
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

export function CertificationTab() {
  const { data, loading, refetch } = useHardeningApi("/hardening/execution/certification");
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
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 flex justify-center"><ScoreGauge score={data.architecture_maturity} max={10} label="Architecture" /></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 flex justify-center"><ScoreGauge score={data.production_readiness} max={10} label="Production" /></CardContent></Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 text-center">
            <div className="text-2xl font-bold text-zinc-100">{data.gap > 0 ? `${data.gap}` : "0"}</div>
            <p className="text-xs text-zinc-500 mt-1">Gap to Target ({data.target_readiness})</p>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-emerald-400 font-bold">{data.phases_completed}</span><span className="text-zinc-500">/{data.phases_total} phases</span></div>
              <div className="bg-zinc-800/50 rounded p-2"><span className="text-emerald-400 font-bold">{data.blockers_resolved}</span><span className="text-zinc-500"> resolved</span></div>
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
          <CardContent><div className="space-y-1.5">
            {data.open_blocker_details.map((b) => (
              <div key={b.id} className="flex items-center gap-2 text-xs bg-zinc-900/50 rounded p-2">
                <XCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" /><span className="text-red-200">{b.blocker}</span>
                <Badge variant="destructive" className="text-[10px] ml-auto">{b.risk}</Badge>
              </div>
            ))}
          </div></CardContent>
        </Card>
      )}
      <div className="text-xs text-zinc-600">Risk Level: <Badge variant={data.risk_level === "critical" ? "destructive" : data.risk_level === "high" ? "default" : "outline"} className="text-[10px]">{data.risk_level}</Badge></div>
      <Button data-testid="refresh-cert" variant="outline" size="sm" onClick={refetch}><RefreshCw className="w-3.5 h-3.5 mr-1" />Refresh</Button>
    </div>
  );
}
