import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  RefreshCw, CheckCircle, Clock, AlertTriangle, X,
  Activity, Search, ChevronDown, ChevronUp, Play,
  Shield, FileWarning, MessageSquare, RotateCcw,
  Bell, BellOff, ArrowUpRight, Timer, Layers,
  Clipboard, UserCheck, XCircle
} from "lucide-react";
import { cn } from "../lib/utils";
import { toast } from "sonner";

const SEVERITY_MAP = {
  critical: { label: "Kritik", color: "bg-red-100 text-red-800 border-red-200", icon: XCircle },
  high: { label: "Yuksek", color: "bg-orange-100 text-orange-800 border-orange-200", icon: AlertTriangle },
  medium: { label: "Orta", color: "bg-amber-100 text-amber-800 border-amber-200", icon: FileWarning },
  low: { label: "Dusuk", color: "bg-blue-100 text-blue-800 border-blue-200", icon: Shield },
};

const OPS_STATUS_MAP = {
  open: { label: "Acik", color: "bg-red-50 text-red-700 border-red-200" },
  claimed: { label: "Sahiplenildi", color: "bg-blue-50 text-blue-700 border-blue-200" },
  in_progress: { label: "Islemde", color: "bg-amber-50 text-amber-700 border-amber-200" },
  resolved: { label: "Cozuldu", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  escalated: { label: "Eskalasyon", color: "bg-purple-50 text-purple-700 border-purple-200" },
  ignored: { label: "Yoksayildi", color: "bg-slate-50 text-slate-500 border-slate-200" },
};

const ALERT_STATUS_MAP = {
  active: { label: "Aktif", color: "bg-red-50 text-red-700 border-red-200" },
  acknowledged: { label: "Goruldu", color: "bg-amber-50 text-amber-700 border-amber-200" },
  resolved: { label: "Cozuldu", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
};

const MISMATCH_LABELS = {
  missing_invoice: "Eksik Fatura",
  amount_mismatch: "Tutar Uyumsuzlugu",
  tax_mismatch: "Vergi Uyumsuzlugu",
  missing_sync: "Eksik Sync",
  sync_amount_mismatch: "Sync Tutar Fark",
  duplicate_entry: "Cift Kayit",
  customer_mismatch: "Cari Uyumsuzlugu",
  status_mismatch: "Durum Uyumsuzlugu",
};

function SeverityBadge({ severity }) {
  const s = SEVERITY_MAP[severity] || { label: severity, color: "", icon: Shield };
  const Icon = s.icon;
  return (
    <Badge variant="outline" className={cn("gap-1 font-medium text-[10px]", s.color)} data-testid={`severity-${severity}`}>
      <Icon className="h-3 w-3" /> {s.label}
    </Badge>
  );
}

function StatusBadge({ status, map }) {
  const s = map[status] || { label: status, color: "" };
  return <Badge variant="outline" className={cn("font-medium text-[10px]", s.color)}>{s.label}</Badge>;
}

function KpiCard({ label, value, icon: Icon, color, sub, testId }) {
  return (
    <div className={cn("rounded-xl border p-4 flex items-start gap-3", color)} data-testid={testId}>
      <div className="rounded-lg bg-background/80 p-2.5 shadow-sm"><Icon className="h-5 w-5" /></div>
      <div>
        <div className="text-xs font-medium text-muted-foreground">{label}</div>
        <div className="text-2xl font-bold tracking-tight">{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

/* ── Aging Bars ───────────────────────────────────────── */
function AgingBars({ aging }) {
  if (!aging) return null;
  const buckets = [
    { key: "0_1h", label: "0-1 saat", color: "bg-emerald-500" },
    { key: "1_6h", label: "1-6 saat", color: "bg-amber-500" },
    { key: "6_24h", label: "6-24 saat", color: "bg-orange-500" },
    { key: "gt_24h", label: ">24 saat", color: "bg-red-500" },
  ];
  const total = buckets.reduce((s, b) => s + (aging[b.key] || 0), 0);
  return (
    <div className="rounded-xl border p-4" data-testid="aging-bars">
      <div className="text-xs font-medium text-muted-foreground mb-3 flex items-center gap-2">
        <Timer className="h-4 w-4" /> Senkronize Edilmemis Fatura Yaslanmasi
      </div>
      {total === 0 ? (
        <div className="text-sm text-muted-foreground text-center py-2">Tum faturalar senkronize</div>
      ) : (
        <div className="space-y-2">
          {buckets.map(b => {
            const val = aging[b.key] || 0;
            const pct = total > 0 ? (val / total) * 100 : 0;
            return (
              <div key={b.key} className="flex items-center gap-3" data-testid={`aging-${b.key}`}>
                <div className="w-20 text-xs text-muted-foreground">{b.label}</div>
                <div className="flex-1 h-5 bg-muted/40 rounded-full overflow-hidden">
                  <div className={cn("h-full rounded-full transition-all", b.color)} style={{ width: `${pct}%` }} />
                </div>
                <div className="w-8 text-xs font-mono font-bold text-right">{val}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── Reconciliation Tab ───────────────────────────────── */
function ReconciliationTab() {
  const [summary, setSummary] = useState(null);
  const [runs, setRuns] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [selectedRun, setSelectedRun] = useState(null);
  const [mismatchFilter, setMismatchFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [sumRes, runsRes] = await Promise.all([
        api.get("/reconciliation/summary"),
        api.get("/reconciliation/runs", { params: { limit: 10 } }),
      ]);
      setSummary(sumRes.data);
      setRuns(runsRes.data?.items || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const loadItems = useCallback(async (runId) => {
    try {
      const params = { limit: 100, ...(runId ? { run_id: runId } : {}), ...(mismatchFilter ? { mismatch_type: mismatchFilter } : {}), ...(severityFilter ? { severity: severityFilter } : {}) };
      const res = await api.get("/reconciliation/items", { params });
      setItems(res.data?.items || []);
    } catch (e) { console.error(e); }
  }, [mismatchFilter, severityFilter]);

  useEffect(() => { if (selectedRun) loadItems(selectedRun); }, [selectedRun, loadItems]);

  const handleRunNow = async () => {
    setRunning(true);
    try {
      const res = await api.post("/reconciliation/run", { run_type: "manual" });
      toast.success(`Mutabakat tamamlandi: ${res.data?.mismatch_count || 0} uyumsuzluk`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setRunning(false); }
  };

  return (
    <div className="space-y-4" data-testid="reconciliation-tab">
      {/* Summary KPIs */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard label="Acik Uyumsuzluk" value={summary.open_mismatches || 0} icon={AlertTriangle} color="bg-red-50/50" testId="kpi-open-mismatches" />
          <KpiCard label="Kritik" value={summary.critical_mismatches || 0} icon={XCircle} color="bg-red-50/80" testId="kpi-critical" />
          <KpiCard label="Senkronize Edilmemis" value={summary.total_unsynced || 0} icon={Clock} color="bg-amber-50/50" testId="kpi-unsynced" />
          <KpiCard label="Son Calistirma" value={summary.last_run ? new Date(summary.last_run.completed_at).toLocaleString("tr-TR", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" }) : "Yok"} icon={Activity} color="bg-slate-50/50" testId="kpi-last-run"
            sub={summary.last_run?.run_type || ""} />
        </div>
      )}

      {/* Aging */}
      <AgingBars aging={summary?.unsynced_aging} />

      {/* Run History */}
      <div className="rounded-xl border shadow-sm">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h2 className="font-semibold text-sm flex items-center gap-2"><Layers className="h-4 w-4" /> Calistirma Gecmisi</h2>
          <Button size="sm" variant="default" className="h-7 text-xs gap-1" onClick={handleRunNow} disabled={running} data-testid="run-now-btn">
            {running ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />} {running ? "Calisiyor..." : "Simdi Calistir"}
          </Button>
        </div>
        {loading ? <div className="p-5"><div className="animate-pulse h-16 bg-muted rounded-lg" /></div> :
          runs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground" data-testid="no-runs">
              <Layers className="h-8 w-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">Henuz mutabakat calistirmasi yok</p>
            </div>
          ) : (
            <div className="overflow-hidden">
              <table className="w-full text-sm">
                <thead><tr className="bg-muted/40 border-b">
                  <th className="text-left px-5 py-2.5 font-medium text-xs uppercase tracking-wider">Run ID</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Tip</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Durum</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Uyumsuzluk</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Tarih</th>
                  <th className="text-right px-5 py-2.5 font-medium text-xs uppercase tracking-wider">Detay</th>
                </tr></thead>
                <tbody>
                  {runs.map(run => (
                    <tr key={run.run_id} className={cn("border-b last:border-0 hover:bg-muted/20 cursor-pointer", selectedRun === run.run_id && "bg-primary/5")} onClick={() => { setSelectedRun(run.run_id); loadItems(run.run_id); }} data-testid={`run-row-${run.run_id}`}>
                      <td className="px-5 py-3 font-mono text-xs font-medium">{run.run_id}</td>
                      <td className="px-4 py-3"><Badge variant="outline" className="text-[10px]">{run.run_type}</Badge></td>
                      <td className="px-4 py-3"><Badge variant="outline" className={cn("text-[10px]", run.status === "completed" ? "bg-emerald-50 text-emerald-700" : run.status === "failed" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700")}>{run.status}</Badge></td>
                      <td className="px-4 py-3 font-mono text-xs">{run.stats?.total_mismatches || 0}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">{run.completed_at ? new Date(run.completed_at).toLocaleString("tr-TR") : "-"}</td>
                      <td className="px-4 py-3 text-right"><Button size="sm" variant="ghost" className="h-6 text-xs">Detay</Button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>

      {/* Mismatch Items */}
      {selectedRun && (
        <div className="rounded-xl border shadow-sm" data-testid="mismatch-items">
          <div className="flex items-center justify-between px-5 py-3 border-b">
            <h2 className="font-semibold text-sm">Uyumsuzluklar ({items.length})</h2>
            <div className="flex gap-2">
              <select value={mismatchFilter} onChange={e => setMismatchFilter(e.target.value)} className="rounded-lg border px-2 py-1 text-xs bg-background" data-testid="mismatch-type-filter">
                <option value="">Tum Tipler</option>
                {Object.entries(MISMATCH_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)} className="rounded-lg border px-2 py-1 text-xs bg-background" data-testid="severity-filter">
                <option value="">Tum Oncelikler</option>
                <option value="critical">Kritik</option>
                <option value="high">Yuksek</option>
                <option value="medium">Orta</option>
                <option value="low">Dusuk</option>
              </select>
            </div>
          </div>
          {items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground"><p className="text-sm">Bu calistirmada uyumsuzluk yok</p></div>
          ) : (
            <div className="overflow-auto max-h-[400px]">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-card"><tr className="bg-muted/40 border-b">
                  <th className="text-left px-5 py-2.5 font-medium text-xs uppercase tracking-wider">Tip</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Oncelik</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Fatura</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Beklenen</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Gercek</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Kaynak</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Yas</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Detay</th>
                </tr></thead>
                <tbody>
                  {items.map((item, idx) => (
                    <tr key={idx} className="border-b last:border-0 hover:bg-muted/20" data-testid={`mismatch-row-${idx}`}>
                      <td className="px-5 py-2.5"><Badge variant="outline" className="text-[10px]">{MISMATCH_LABELS[item.mismatch_type] || item.mismatch_type}</Badge></td>
                      <td className="px-4 py-2.5"><SeverityBadge severity={item.severity} /></td>
                      <td className="px-4 py-2.5 font-mono text-xs">{item.invoice_id || item.booking_id || "-"}</td>
                      <td className="px-4 py-2.5 font-mono text-xs">{item.amount_expected ? `${item.amount_expected.toFixed(2)} TL` : "-"}</td>
                      <td className="px-4 py-2.5 font-mono text-xs">{item.amount_actual ? `${item.amount_actual.toFixed(2)} TL` : "-"}</td>
                      <td className="px-4 py-2.5"><Badge variant="outline" className="text-[10px]">{item.source_of_truth}</Badge></td>
                      <td className="px-4 py-2.5 text-xs">{item.age_bucket ? item.age_bucket.replace("_", "-").replace("gt", ">") : "-"}</td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground max-w-[200px] truncate" title={item.details}>{item.details || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Finance Ops Queue Tab ────────────────────────────── */
function FinanceOpsTab() {
  const [opsItems, setOpsItems] = useState([]);
  const [opsStats, setOpsStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [noteModal, setNoteModal] = useState(null);
  const [noteText, setNoteText] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [itemsRes, statsRes] = await Promise.all([
        api.get("/reconciliation/ops", { params: { limit: 100, ...(statusFilter ? { status: statusFilter } : {}) } }),
        api.get("/reconciliation/ops/stats"),
      ]);
      setOpsItems(itemsRes.data?.items || []);
      setOpsStats(statsRes.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleAction = async (action, opsId, extra = {}) => {
    try {
      await api.post(`/reconciliation/ops/${action}`, { ops_id: opsId, ...extra });
      toast.success(`${action === "claim" ? "Sahiplenildi" : action === "resolve" ? "Cozuldu" : action === "escalate" ? "Eskalasyon yapildi" : action === "retry" ? "Tekrar istendi" : "Basarili"}`);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  const handleAddNote = async () => {
    if (!noteText.trim()) return;
    try {
      await api.post("/reconciliation/ops/note", { ops_id: noteModal, note_text: noteText });
      toast.success("Not eklendi");
      setNoteModal(null);
      setNoteText("");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="space-y-4" data-testid="finance-ops-tab">
      {/* Stats */}
      {opsStats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <KpiCard label="Aktif" value={opsStats.active || 0} icon={AlertTriangle} color="bg-red-50/50" testId="ops-stat-active" />
          <KpiCard label="Acik" value={opsStats.open || 0} icon={Clock} color="bg-amber-50/50" testId="ops-stat-open" />
          <KpiCard label="Islemde" value={opsStats.in_progress || 0} icon={Activity} color="bg-blue-50/50" testId="ops-stat-progress" />
          <KpiCard label="Eskalasyon" value={opsStats.escalated || 0} icon={ArrowUpRight} color="bg-purple-50/50" testId="ops-stat-escalated" />
          <KpiCard label="Cozulmus" value={opsStats.resolved || 0} icon={CheckCircle} color="bg-emerald-50/50" testId="ops-stat-resolved" />
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2 flex-wrap" data-testid="ops-filters">
        {[
          { value: "", label: "Tumu" },
          { value: "open", label: "Acik" },
          { value: "claimed", label: "Sahiplenilmis" },
          { value: "in_progress", label: "Islemde" },
          { value: "escalated", label: "Eskalasyon" },
          { value: "resolved", label: "Cozulmus" },
        ].map(f => (
          <Button key={f.value} variant={statusFilter === f.value ? "default" : "outline"} size="sm"
            onClick={() => setStatusFilter(f.value)} className="text-xs h-7" data-testid={`ops-filter-${f.value || 'all'}`}>
            {f.label}
          </Button>
        ))}
      </div>

      {/* Items Table */}
      <div className="rounded-xl border shadow-sm">
        {loading ? <div className="p-5"><div className="animate-pulse h-20 bg-muted rounded-lg" /></div> :
          opsItems.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground" data-testid="no-ops">
              <Clipboard className="h-12 w-12 mx-auto mb-3 opacity-20" />
              <p className="text-sm font-medium">Finans operasyonu bulunmuyor</p>
            </div>
          ) : (
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead><tr className="bg-muted/40 border-b">
                  <th className="text-left px-5 py-2.5 font-medium text-xs uppercase tracking-wider">ID</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Oncelik</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Durum</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Tip</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Aciklama</th>
                  <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Atanan</th>
                  <th className="text-right px-5 py-2.5 font-medium text-xs uppercase tracking-wider">Aksiyonlar</th>
                </tr></thead>
                <tbody>
                  {opsItems.map(item => (
                    <tr key={item.ops_id} className="border-b last:border-0 hover:bg-muted/20" data-testid={`ops-row-${item.ops_id}`}>
                      <td className="px-5 py-3 font-mono text-xs font-medium">{item.ops_id}</td>
                      <td className="px-4 py-3"><SeverityBadge severity={item.priority} /></td>
                      <td className="px-4 py-3"><StatusBadge status={item.status} map={OPS_STATUS_MAP} /></td>
                      <td className="px-4 py-3 text-xs">{item.related_type}</td>
                      <td className="px-4 py-3 text-xs text-muted-foreground max-w-[200px] truncate" title={item.description}>{item.description || "-"}</td>
                      <td className="px-4 py-3 text-xs">{item.assigned_to || "-"}</td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex gap-1 justify-end">
                          {item.status === "open" && (
                            <Button size="sm" variant="outline" className="h-6 text-[10px] gap-1" onClick={() => handleAction("claim", item.ops_id)} data-testid={`claim-${item.ops_id}`}>
                              <UserCheck className="h-3 w-3" /> Sahiplen
                            </Button>
                          )}
                          {["open", "claimed", "in_progress"].includes(item.status) && (
                            <>
                              <Button size="sm" variant="outline" className="h-6 text-[10px] gap-1" onClick={() => handleAction("resolve", item.ops_id)} data-testid={`resolve-${item.ops_id}`}>
                                <CheckCircle className="h-3 w-3" /> Coz
                              </Button>
                              <Button size="sm" variant="outline" className="h-6 text-[10px] gap-1" onClick={() => handleAction("escalate", item.ops_id)} data-testid={`escalate-${item.ops_id}`}>
                                <ArrowUpRight className="h-3 w-3" /> Eskale
                              </Button>
                              <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={() => handleAction("retry", item.ops_id)} data-testid={`retry-ops-${item.ops_id}`}>
                                <RotateCcw className="h-3 w-3" />
                              </Button>
                            </>
                          )}
                          <Button size="sm" variant="ghost" className="h-6 text-[10px]" onClick={() => { setNoteModal(item.ops_id); setNoteText(""); }} data-testid={`note-${item.ops_id}`}>
                            <MessageSquare className="h-3 w-3" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>

      {/* Note Modal */}
      {noteModal && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setNoteModal(null)}>
          <div className="bg-card rounded-xl border shadow-xl p-5 w-96" onClick={e => e.stopPropagation()} data-testid="note-modal">
            <h3 className="font-semibold mb-3 flex items-center gap-2"><MessageSquare className="h-4 w-4" /> Not Ekle</h3>
            <textarea value={noteText} onChange={e => setNoteText(e.target.value)}
              className="w-full rounded-lg border px-3 py-2 text-sm bg-background h-24 resize-none" placeholder="Notunuzu yazin..." data-testid="note-textarea" />
            <div className="flex justify-end gap-2 mt-3">
              <Button variant="outline" size="sm" onClick={() => setNoteModal(null)}>Vazgec</Button>
              <Button size="sm" onClick={handleAddNote} data-testid="save-note-btn">Kaydet</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Alerts Tab ───────────────────────────────────────── */
function AlertsTab() {
  const [alerts, setAlerts] = useState([]);
  const [alertStats, setAlertStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("active");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [alertsRes, statsRes] = await Promise.all([
        api.get("/reconciliation/alerts", { params: { limit: 50, ...(statusFilter ? { status: statusFilter } : {}) } }),
        api.get("/reconciliation/alerts/stats"),
      ]);
      setAlerts(alertsRes.data?.items || []);
      setAlertStats(statsRes.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleAcknowledge = async (alertId) => {
    try { await api.post("/reconciliation/alerts/acknowledge", { alert_id: alertId }); toast.success("Alert goruldu olarak isaretlendi"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };
  const handleResolve = async (alertId) => {
    try { await api.post("/reconciliation/alerts/resolve", { alert_id: alertId }); toast.success("Alert cozuldu"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="space-y-4" data-testid="alerts-tab">
      {alertStats && (
        <div className="grid grid-cols-3 gap-3">
          <KpiCard label="Aktif Alert" value={alertStats.active_alerts || 0} icon={Bell} color="bg-red-50/50" testId="alert-stat-active" />
          <KpiCard label="Kritik" value={alertStats.critical_active || 0} icon={XCircle} color="bg-red-50/80" testId="alert-stat-critical" />
          <KpiCard label="Goruldu" value={alertStats.acknowledged_alerts || 0} icon={BellOff} color="bg-amber-50/50" testId="alert-stat-ack" />
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        {[{ value: "active", label: "Aktif" }, { value: "acknowledged", label: "Goruldu" }, { value: "resolved", label: "Cozulmus" }, { value: "", label: "Tumu" }].map(f => (
          <Button key={f.value} variant={statusFilter === f.value ? "default" : "outline"} size="sm"
            onClick={() => setStatusFilter(f.value)} className="text-xs h-7" data-testid={`alert-filter-${f.value || 'all'}`}>
            {f.label}
          </Button>
        ))}
      </div>

      <div className="rounded-xl border shadow-sm">
        {loading ? <div className="p-5"><div className="animate-pulse h-16 bg-muted rounded-lg" /></div> :
          alerts.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground" data-testid="no-alerts">
              <Bell className="h-12 w-12 mx-auto mb-3 opacity-20" />
              <p className="text-sm font-medium">Finansal alert bulunmuyor</p>
            </div>
          ) : (
            <div className="divide-y">
              {alerts.map(alert => (
                <div key={alert.alert_id} className="flex items-center justify-between px-5 py-3" data-testid={`alert-row-${alert.alert_id}`}>
                  <div className="flex items-center gap-3">
                    <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center",
                      alert.severity === "critical" ? "bg-red-100 text-red-700" :
                      alert.severity === "warning" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700")}>
                      {alert.severity === "critical" ? <XCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                    </div>
                    <div>
                      <div className="font-medium text-sm">{alert.message}</div>
                      <div className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                        <SeverityBadge severity={alert.severity} />
                        <StatusBadge status={alert.status} map={ALERT_STATUS_MAP} />
                        <span>{new Date(alert.created_at).toLocaleString("tr-TR")}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    {alert.status === "active" && (
                      <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => handleAcknowledge(alert.alert_id)} data-testid={`ack-alert-${alert.alert_id}`}>
                        <BellOff className="h-3 w-3" /> Goruldu
                      </Button>
                    )}
                    {alert.status !== "resolved" && (
                      <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => handleResolve(alert.alert_id)} data-testid={`resolve-alert-${alert.alert_id}`}>
                        <CheckCircle className="h-3 w-3" /> Coz
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
      </div>
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────── */
export default function AdminFinanceOpsPage() {
  const [activeTab, setActiveTab] = useState("reconciliation");

  const tabs = [
    { id: "reconciliation", label: "Mutabakat", icon: Layers },
    { id: "ops", label: "Finans Operasyonlari", icon: Clipboard },
    { id: "alerts", label: "Alertler", icon: Bell },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="finance-ops-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="finance-ops-title">
            <Shield className="h-6 w-6 text-primary" /> Mutabakat ve Finans Operasyonlari
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Booking, fatura ve muhasebe mutabakati, operasyon kuyrugu ve alertler</p>
        </div>
      </div>

      <div className="flex gap-1 mb-4 border-b" data-testid="finance-ops-tabs">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={cn("flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
                activeTab === tab.id ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
              )} data-testid={`ftab-${tab.id}`}>
              <Icon className="h-4 w-4" /> {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab === "reconciliation" && <ReconciliationTab />}
      {activeTab === "ops" && <FinanceOpsTab />}
      {activeTab === "alerts" && <AlertsTab />}
    </div>
  );
}
