import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { RefreshCw, AlertTriangle, ChevronUp, ChevronDown, Database, CheckCircle2, XCircle, Clock } from "lucide-react";
import { ScoreGauge } from "./ScoreGauge";
import { useHardeningApi } from "../api";
import { severityColor, statusBadge } from "../helpers";

export function PlaybooksTab() {
  const { data, loading } = useHardeningApi("/hardening/incidents/playbooks");
  const [expanded, setExpanded] = useState(null);
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="playbooks-tab" className="space-y-4">
      {Object.entries(data.playbooks).map(([key, pb]) => (
        <Card key={key} className="bg-zinc-900 border-zinc-800">
          <CardHeader className="cursor-pointer" onClick={() => setExpanded(expanded === key ? null : key)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-amber-400" /><CardTitle className="text-sm">{pb.name}</CardTitle><Badge variant="destructive" className="text-[10px]">{pb.severity}</Badge></div>
              {expanded === key ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </div>
          </CardHeader>
          {expanded === key && (
            <CardContent className="text-xs space-y-4">
              <div><p className="text-zinc-400 font-semibold mb-1">Detection Signals:</p><ul className="list-disc list-inside text-zinc-500 space-y-0.5">{pb.detection.signals.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
              <div><p className="text-zinc-400 font-semibold mb-1">Triage ({pb.triage.sla_minutes}min SLA):</p><ul className="list-decimal list-inside text-zinc-500 space-y-0.5">{pb.triage.steps.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
              <div><p className="text-zinc-400 font-semibold mb-1">Escalation:</p><div className="space-y-1">
                {pb.escalation.tiers.map((t, i) => (<div key={i} className="flex items-center gap-2 bg-zinc-800 rounded p-2"><Badge variant="outline" className="text-[10px]">{t.tier}</Badge><span className="text-zinc-300">{t.role}</span><span className="text-zinc-500 ml-auto">{t.sla_minutes}min</span></div>))}
              </div></div>
              <div><p className="text-zinc-400 font-semibold mb-1">Resolution:</p><ul className="list-disc list-inside text-zinc-500 space-y-0.5">{pb.resolution.actions.map((a, i) => <li key={i}>{a}</li>)}</ul></div>
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  );
}

export function ScalingTab() {
  const { data, loading } = useHardeningApi("/hardening/scaling/status");
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
          <CardContent><div className="space-y-1 text-xs">
            {data.recommendations.map((r, i) => (<div key={i} className="flex items-center justify-between bg-zinc-800/50 rounded p-2"><span className="text-zinc-300">{r.action}</span><Badge variant={r.priority === "P0" ? "destructive" : "outline"} className="text-[10px]">{r.priority}</Badge></div>))}
          </div></CardContent>
        </Card>
      )}
    </div>
  );
}

export function DRTab() {
  const { data, loading } = useHardeningApi("/hardening/dr/plan");
  const [expanded, setExpanded] = useState(null);
  if (loading || !data) return <div className="animate-pulse h-48 bg-zinc-900 rounded-lg" />;
  return (
    <div data-testid="dr-tab" className="space-y-4">
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm">RTO/RPO Targets</CardTitle></CardHeader>
        <CardContent><div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
          {Object.entries(data.rto_rpo_targets).map(([k, v]) => (
            <div key={k} className="bg-zinc-800/50 rounded p-3"><p className="text-zinc-200 font-medium capitalize mb-1">{k.replace(/_/g, " ")}</p><p className="text-zinc-500">{v.description}</p><div className="flex gap-4 mt-2 text-zinc-400"><span>RTO: {v.rto_minutes}min</span><span>RPO: {v.rpo_minutes}min</span></div></div>
          ))}
        </div></CardContent>
      </Card>
      {Object.entries(data.scenarios).map(([key, sc]) => (
        <Card key={key} className="bg-zinc-900 border-zinc-800">
          <CardHeader className="cursor-pointer" onClick={() => setExpanded(expanded === key ? null : key)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2"><Database className="w-4 h-4 text-red-400" /><CardTitle className="text-sm">{sc.name}</CardTitle><Badge variant="destructive" className="text-[10px]">{sc.severity}</Badge></div>
              <span className="text-xs text-zinc-500">RTO: {sc.estimated_rto_minutes}min</span>
            </div>
          </CardHeader>
          {expanded === key && (
            <CardContent className="text-xs space-y-3">
              <p className="text-zinc-400">{sc.description}</p>
              {Object.entries(sc.response_plan).map(([phase, steps]) => (
                <div key={phase}><p className="text-zinc-400 font-semibold capitalize mb-1">{phase}:</p><ul className="list-disc list-inside text-zinc-500 space-y-0.5">{steps.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
              ))}
            </CardContent>
          )}
        </Card>
      ))}
    </div>
  );
}

export function ChecklistTab() {
  const { data, loading } = useHardeningApi("/hardening/checklist");
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
          <CardContent><ul className="list-disc list-inside text-xs text-red-300 space-y-0.5">{m.go_live_blockers.map((b, i) => <li key={i}>{b}</li>)}</ul></CardContent>
        </Card>
      )}
      <div className="flex gap-2">
        {["all", "P0", "P1", "P2", "P3"].map(f => (
          <Button key={f} size="sm" variant={filter === f ? "default" : "outline"} onClick={() => setFilter(f)} className="text-xs">{f === "all" ? "All" : f}</Button>
        ))}
      </div>
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="pt-4"><div className="space-y-1 text-xs max-h-[500px] overflow-y-auto">
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
        </div></CardContent>
      </Card>
    </div>
  );
}
