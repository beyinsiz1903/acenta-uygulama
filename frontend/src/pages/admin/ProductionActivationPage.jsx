import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import {
  Activity, AlertTriangle, CheckCircle, Shield, Server,
  FileText, Bell, Database, RefreshCw, XCircle, Clock,
  Zap, Globe, Lock, BarChart3, TrendingUp
} from "lucide-react";
import { api } from "../../lib/api";

function useApiData(endpoint, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(endpoint);
      setData(res.data);
      setError(null);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => { fetchData(); }, [fetchData, ...deps]);

  return { data, loading, error, refetch: fetchData };
}

function StatusBadge({ status }) {
  const map = {
    pass: { color: "bg-emerald-500/15 text-emerald-700 border-emerald-500/30", icon: CheckCircle },
    fail: { color: "bg-red-500/15 text-red-700 border-red-500/30", icon: XCircle },
    warn: { color: "bg-amber-500/15 text-amber-700 border-amber-500/30", icon: AlertTriangle },
    healthy: { color: "bg-emerald-500/15 text-emerald-700 border-emerald-500/30", icon: CheckCircle },
    unhealthy: { color: "bg-red-500/15 text-red-700 border-red-500/30", icon: XCircle },
    done: { color: "bg-emerald-500/15 text-emerald-700 border-emerald-500/30", icon: CheckCircle },
    pending: { color: "bg-slate-500/15 text-slate-600 border-slate-500/30", icon: Clock },
    skeleton_ready: { color: "bg-blue-500/15 text-blue-700 border-blue-500/30", icon: Zap },
    migration_path_ready: { color: "bg-violet-500/15 text-violet-700 border-violet-500/30", icon: Lock },
  };
  const cfg = map[status] || map.pending;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.color}`}>
      <Icon className="h-3 w-3" />{status}
    </span>
  );
}

function MetricCard({ title, value, icon: Icon, subtitle, color = "text-foreground" }) {
  return (
    <Card className="border border-border/50">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{title}</p>
            <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          {Icon && <Icon className="h-5 w-5 text-muted-foreground" />}
        </div>
      </CardContent>
    </Card>
  );
}

function ReadinessTab() {
  const { data, loading, refetch } = useApiData("/production/readiness");
  if (loading) return <div className="animate-pulse p-8 text-center text-muted-foreground">Loading...</div>;
  if (!data) return null;
  const { summary, maturity, checks, go_live_blockers, warnings } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard title="Readiness Score" value={`${summary.readiness_score}%`} icon={BarChart3} color={summary.readiness_score >= 80 ? "text-emerald-600" : "text-amber-600"} />
        <MetricCard title="Maturity Score" value={maturity.overall_score} icon={TrendingUp} subtitle={maturity.rating} color={maturity.overall_score >= 8 ? "text-emerald-600" : "text-amber-600"} />
        <MetricCard title="Checks Passed" value={`${summary.passed}/${summary.total_checks}`} icon={CheckCircle} color="text-emerald-600" />
        <MetricCard title="Go-Live Ready" value={summary.go_live_ready ? "YES" : "NO"} icon={summary.go_live_ready ? CheckCircle : AlertTriangle} color={summary.go_live_ready ? "text-emerald-600" : "text-red-600"} />
      </div>
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Maturity Dimensions</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(maturity.dimensions).map(([key, val]) => (
              <div key={key} className="p-3 rounded-lg bg-muted/40">
                <p className="text-xs text-muted-foreground capitalize">{key}</p>
                <p className={`text-lg font-bold ${val >= 8 ? 'text-emerald-600' : val >= 7 ? 'text-amber-600' : 'text-red-600'}`}>{val}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">All Checks</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            {checks.map((c, i) => (
              <div key={i} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-muted/40 transition-colors">
                <div className="flex items-center gap-3">
                  <StatusBadge status={c.status} />
                  <span className="text-sm font-medium">{c.check}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">{c.category}</Badge>
                  <Badge variant={c.severity === 'critical' ? 'destructive' : 'secondary'} className="text-xs">{c.severity}</Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function PipelineTab() {
  const { data, loading } = useApiData("/production/pipeline/status");
  if (loading) return <div className="animate-pulse p-8 text-center text-muted-foreground">Loading...</div>;
  if (!data) return null;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard title="Redis" value={data.redis} icon={Database} color={data.redis === 'healthy' ? 'text-emerald-600' : 'text-red-600'} />
        <MetricCard title="RBAC Middleware" value={data.rbac_middleware} icon={Shield} color="text-emerald-600" />
        <MetricCard title="Reliability Pipeline" value={data.reliability_pipeline} icon={Activity} color="text-emerald-600" />
        <MetricCard title="Open Incidents" value={data.open_incidents} icon={AlertTriangle} color={data.open_incidents > 0 ? 'text-amber-600' : 'text-emerald-600'} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base flex items-center gap-2"><Globe className="h-4 w-4" />Suppliers</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between"><span className="text-sm text-muted-foreground">Total Registered</span><span className="font-medium">{data.suppliers?.total || 0}</span></div>
              <div className="flex justify-between"><span className="text-sm text-muted-foreground">Disabled</span><span className="font-medium text-red-600">{data.suppliers?.disabled || 0}</span></div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base flex items-center gap-2"><FileText className="h-4 w-4" />Operations</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between"><span className="text-sm text-muted-foreground">Vouchers Generated</span><span className="font-medium">{data.vouchers_generated}</span></div>
              <div className="flex justify-between"><span className="text-sm text-muted-foreground">Notifications Sent</span><span className="font-medium">{Object.values(data.notifications || {}).reduce((a, b) => a + b, 0)}</span></div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function TasksTab() {
  const { data, loading } = useApiData("/production/readiness/tasks");
  if (loading) return <div className="animate-pulse p-8 text-center text-muted-foreground">Loading...</div>;
  if (!data) return null;
  const { tasks, risk_matrix } = data;
  const done = tasks.filter(t => t.status === 'done').length;
  const total = tasks.length;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <MetricCard title="Completed" value={`${done}/${total}`} icon={CheckCircle} color="text-emerald-600" />
        <MetricCard title="In Progress" value={tasks.filter(t => !['done','pending'].includes(t.status)).length} icon={RefreshCw} color="text-blue-600" />
        <MetricCard title="Risks Identified" value={risk_matrix.length} icon={AlertTriangle} color="text-amber-600" />
      </div>
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Top 30 Production Tasks</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-1 max-h-[500px] overflow-y-auto">
            {tasks.map(t => (
              <div key={t.id} className="flex items-center justify-between py-2 px-3 rounded hover:bg-muted/40 transition-colors">
                <div className="flex items-center gap-3">
                  <Badge variant={t.priority === 'P0' ? 'destructive' : t.priority === 'P1' ? 'default' : 'secondary'} className="text-xs w-8 justify-center">{t.priority}</Badge>
                  <span className="text-sm">{t.task}</span>
                </div>
                <StatusBadge status={t.status} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Go-Live Risk Matrix</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            {risk_matrix.map((r, i) => (
              <div key={i} className="flex items-start gap-3 py-2 px-3 rounded-lg bg-muted/30">
                <AlertTriangle className={`h-4 w-4 mt-0.5 flex-shrink-0 ${r.impact === 'critical' ? 'text-red-500' : r.impact === 'high' ? 'text-amber-500' : 'text-slate-400'}`} />
                <div className="flex-1">
                  <p className="text-sm font-medium">{r.risk}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Mitigation: {r.mitigation}</p>
                </div>
                <div className="flex gap-1">
                  <Badge variant="outline" className="text-xs">{r.probability}</Badge>
                  <Badge variant={r.impact === 'critical' ? 'destructive' : 'secondary'} className="text-xs">{r.impact}</Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SuppliersTab() {
  const { data, loading } = useApiData("/production/suppliers/integrations");
  if (loading) return <div className="animate-pulse p-8 text-center text-muted-foreground">Loading...</div>;
  if (!data) return null;
  const { suppliers, risk_matrix, rollout_order } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {Object.entries(suppliers).map(([code, s]) => (
          <Card key={code} className="border border-border/50">
            <CardContent className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-semibold text-sm">{s.name}</p>
                  <p className="text-xs text-muted-foreground">{s.code}</p>
                </div>
                <StatusBadge status={s.is_configured ? 'pass' : 'warn'} />
              </div>
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="flex justify-between"><span>Auth</span><span className="font-medium text-foreground">{s.auth_method}</span></div>
                <div className="flex justify-between"><span>Rate Limit</span><span className="font-medium text-foreground">{s.rate_limit_rps} rps</span></div>
                <div className="flex justify-between"><span>Timeout</span><span className="font-medium text-foreground">{s.timeout_ms}ms</span></div>
                <div className="flex justify-between"><span>Mode</span><span className="font-medium text-foreground">{s.sandbox_mode ? 'Sandbox' : 'Production'}</span></div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Rollout Plan</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-3">
            {rollout_order.map((r, i) => (
              <div key={i} className="flex items-center gap-4 p-3 rounded-lg bg-muted/30">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-bold text-sm">{r.phase}</div>
                <div className="flex-1">
                  <p className="text-sm font-medium capitalize">{r.supplier}</p>
                  <p className="text-xs text-muted-foreground">{r.scope}</p>
                </div>
                <Badge variant="outline" className="text-xs">{r.timeline}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SecretsTab() {
  const { data, loading } = useApiData("/production/readiness/secrets");
  if (loading) return <div className="animate-pulse p-8 text-center text-muted-foreground">Loading...</div>;
  if (!data) return null;
  const { inventory, migration } = data;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard title="Readiness" value={`${migration.readiness_score}%`} icon={Lock} color={migration.readiness_score > 50 ? 'text-emerald-600' : 'text-amber-600'} />
        <MetricCard title="Configured" value={`${migration.configured}/${migration.total_secrets}`} icon={CheckCircle} />
        <MetricCard title="Critical" value={`${migration.critical_configured}/${migration.critical_secrets}`} icon={Shield} color="text-red-600" />
        <MetricCard title="Phase" value={migration.migration_phase} icon={Database} subtitle={`Target: ${migration.target_phase}`} />
      </div>
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Secret Inventory</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            {inventory.map((s, i) => (
              <div key={i} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-muted/40">
                <div className="flex items-center gap-3">
                  <Lock className={`h-4 w-4 ${s.is_configured ? 'text-emerald-500' : 'text-red-400'}`} />
                  <div>
                    <p className="text-sm font-mono font-medium">{s.key}</p>
                    <p className="text-xs text-muted-foreground">{s.type} | Rotation: {s.rotation_policy}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={s.risk_level === 'critical' ? 'destructive' : s.risk_level === 'high' ? 'default' : 'secondary'} className="text-xs">{s.risk_level}</Badge>
                  <StatusBadge status={s.is_configured ? 'pass' : 'fail'} />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-3"><CardTitle className="text-base">Migration Steps</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            {migration.migration_steps.map((s, i) => (
              <div key={i} className="flex items-center gap-3 py-2 px-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${s.status === 'done' ? 'bg-emerald-500 text-white' : 'bg-muted text-muted-foreground'}`}>{s.step}</div>
                <span className={`text-sm ${s.status === 'done' ? 'text-emerald-600 font-medium' : 'text-muted-foreground'}`}>{s.action}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function ProductionActivationPage() {
  const [activeTab, setActiveTab] = useState("readiness");
  return (
    <div data-testid="production-activation-dashboard" className="space-y-6 p-1">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Production Activation</h1>
          <p className="text-sm text-muted-foreground mt-1">Platform readiness, reliability pipeline, and go-live certification</p>
        </div>
        <Badge variant="outline" className="text-xs px-3 py-1">
          <Server className="h-3 w-3 mr-1" />Production Layer
        </Badge>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-muted/50">
          <TabsTrigger value="readiness" data-testid="tab-readiness" className="text-xs gap-1"><CheckCircle className="h-3.5 w-3.5" />Readiness</TabsTrigger>
          <TabsTrigger value="pipeline" data-testid="tab-pipeline" className="text-xs gap-1"><Activity className="h-3.5 w-3.5" />Pipeline</TabsTrigger>
          <TabsTrigger value="tasks" data-testid="tab-tasks" className="text-xs gap-1"><BarChart3 className="h-3.5 w-3.5" />Tasks</TabsTrigger>
          <TabsTrigger value="suppliers" data-testid="tab-suppliers" className="text-xs gap-1"><Globe className="h-3.5 w-3.5" />Suppliers</TabsTrigger>
          <TabsTrigger value="secrets" data-testid="tab-secrets" className="text-xs gap-1"><Lock className="h-3.5 w-3.5" />Secrets</TabsTrigger>
        </TabsList>
        <TabsContent value="readiness"><ReadinessTab /></TabsContent>
        <TabsContent value="pipeline"><PipelineTab /></TabsContent>
        <TabsContent value="tasks"><TasksTab /></TabsContent>
        <TabsContent value="suppliers"><SuppliersTab /></TabsContent>
        <TabsContent value="secrets"><SecretsTab /></TabsContent>
      </Tabs>
    </div>
  );
}
