import React, { useState, useCallback, useMemo } from "react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  RefreshCw, CheckCircle, Clock, AlertTriangle, X,
  Settings, Shield, Wifi, WifiOff, Key, Trash2,
  RotateCcw, Database, Activity,
  ChevronDown, ChevronUp, Users, Zap, Search,
  Plus, Power, PowerOff
} from "lucide-react";
import { cn } from "../lib/utils";
import { toast } from "sonner";
import { api } from "../lib/api";
import { PageShell, DataTable, StatusBadge } from "../design-system";
import { useAccountingDashboard, useSyncJobs, useRetryJob, useAccountingRules, useAccountingCustomers } from "../features/accounting/hooks";

const MAX_ATTEMPTS = 5;

const JOB_STATUS_MAP = {
  pending: { label: "Bekliyor", color: "warning" },
  processing: { label: "Isleniyor", color: "info" },
  synced: { label: "Senkronize", color: "success" },
  failed: { label: "Basarisiz", color: "danger" },
  retrying: { label: "Yeniden Deniyor", color: "warning" },
};

function DashboardCard({ label, value, icon: Icon, color, sub, testId }) {
  return (
    <div className={cn("rounded-xl border p-4 flex items-start gap-3 transition-all", color)} data-testid={testId}>
      <div className="rounded-lg bg-background/80 p-2.5 shadow-sm">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <div className="text-xs font-medium text-muted-foreground">{label}</div>
        <div className="text-2xl font-bold tracking-tight">{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

/* ── Credential Settings Panel ───────────────────────────── */
function CredentialSettings({ onClose, onSaved }) {
  const [providers, setProviders] = useState([]);
  const [configs, setConfigs] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [credentials, setCredentials] = useState({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [provRes, confRes] = await Promise.all([
        api.get("/accounting/providers"),
        api.get("/accounting/credentials"),
      ]);
      setProviders(provRes.data?.providers || []);
      setConfigs(confRes.data?.integrators || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useState(() => { loadData(); });

  const handleSave = async () => {
    if (!selectedProvider) return;
    const missing = selectedProvider.credential_fields.filter(f => f.required && !credentials[f.key]);
    if (missing.length) { toast.error(`Zorunlu alanlar: ${missing.map(f => f.label).join(", ")}`); return; }
    setSaving(true);
    try {
      await api.post("/accounting/credentials", { provider: selectedProvider.code, credentials });
      toast.success("Kimlik bilgileri kaydedildi");
      setSelectedProvider(null); setCredentials({}); loadData(); onSaved?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setSaving(false); }
  };

  const handleTest = async (provider) => {
    setTesting(true);
    try {
      const res = await api.post("/accounting/test-connection", { provider });
      res.data.success ? toast.success(res.data.message || "Baglanti basarili") : toast.error(res.data.message || "Baglanti basarisiz");
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setTesting(false); }
  };

  const handleDelete = async (provider) => {
    if (!window.confirm("Bu muhasebe yapilandirmasini silmek istediginize emin misiniz?")) return;
    try {
      await api.delete(`/accounting/credentials/${provider}`);
      toast.success("Yapilandirma silindi"); loadData(); onSaved?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="rounded-xl border bg-card shadow-sm p-5 mb-6" data-testid="accounting-settings">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold flex items-center gap-2"><Settings className="h-4 w-4" /> Muhasebe Entegrator Ayarlari</h3>
        <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
      </div>
      {loading ? <div className="animate-pulse h-20 bg-muted rounded-lg" /> : (
        <div className="space-y-4">
          {configs.length > 0 && (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">Yapilandirilmis Sistemler</div>
              {configs.map(cfg => (
                <div key={cfg.provider} className="rounded-lg border p-3 flex items-center justify-between mb-2" data-testid={`acct-config-${cfg.provider}`}>
                  <div className="flex items-center gap-3">
                    <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center", cfg.status === "active" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700")}>
                      {cfg.status === "active" ? <Wifi className="h-4 w-4" /> : <Key className="h-4 w-4" />}
                    </div>
                    <div>
                      <div className="font-medium text-sm">{cfg.provider?.toUpperCase()}</div>
                      <div className="text-xs text-muted-foreground">
                        {cfg.masked_credentials?.username && `Kullanici: ${cfg.masked_credentials.username}`}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => handleTest(cfg.provider)} disabled={testing} data-testid={`acct-test-btn-${cfg.provider}`}>
                      <Wifi className="h-3 w-3" /> Test
                    </Button>
                    <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive" onClick={() => handleDelete(cfg.provider)} data-testid={`acct-delete-btn-${cfg.provider}`}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {!selectedProvider ? (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">Muhasebe Sistemi Ekle</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {providers.filter(p => !configs.some(c => c.provider === p.code)).map(p => (
                  <button key={p.code} onClick={() => { setSelectedProvider(p); setCredentials({}); }}
                    className="rounded-lg border-2 border-dashed p-3 text-left hover:border-primary hover:bg-primary/5 transition-all" data-testid={`add-acct-provider-${p.code}`}>
                    <Shield className="h-5 w-5 mb-1 text-primary" />
                    <div className="font-medium text-sm">{p.name}</div>
                    <div className="text-xs text-muted-foreground">{p.description}</div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div data-testid="acct-credential-form">
              <div className="text-xs font-medium text-muted-foreground mb-2">{selectedProvider.name} - Kimlik Bilgileri</div>
              <div className="space-y-2">
                {selectedProvider.credential_fields.map(field => (
                  <div key={field.key}>
                    <label className="text-xs font-medium block mb-1">{field.label} {field.required && <span className="text-destructive">*</span>}</label>
                    <input type={field.type === "password" ? "password" : "text"} value={credentials[field.key] || ""}
                      onChange={e => setCredentials(c => ({ ...c, [field.key]: e.target.value }))}
                      className="w-full rounded-lg border px-3 py-2 text-sm bg-background" placeholder={field.placeholder || ""} data-testid={`acct-field-${field.key}`} />
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-2 mt-3">
                <Button variant="outline" size="sm" onClick={() => setSelectedProvider(null)}>Vazgec</Button>
                <Button size="sm" onClick={handleSave} disabled={saving} data-testid="save-acct-credentials-btn">{saving ? "Kaydediliyor..." : "Kaydet"}</Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Auto Sync Rules Panel ───────────────────────────────── */
function AutoSyncRulesPanel() {
  const { data: rules = [], isLoading: loading, refetch: load } = useAccountingRules();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ rule_name: "", trigger_event: "invoice_issued", provider: "luca", requires_approval: false, enabled: true });

  const handleCreate = async () => {
    if (!form.rule_name.trim()) { toast.error("Kural adi gerekli"); return; }
    try {
      await api.post("/accounting/rules", form);
      toast.success("Kural olusturuldu");
      setShowCreate(false);
      setForm({ rule_name: "", trigger_event: "invoice_issued", provider: "luca", requires_approval: false, enabled: true });
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  const toggleRule = async (rule) => {
    try {
      await api.put(`/accounting/rules/${rule.rule_id}`, { enabled: !rule.enabled });
      toast.success(rule.enabled ? "Kural devre disi" : "Kural aktif");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  const deleteRule = async (ruleId) => {
    if (!window.confirm("Bu kurali silmek istediginize emin misiniz?")) return;
    try {
      await api.delete(`/accounting/rules/${ruleId}`);
      toast.success("Kural silindi");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  const TRIGGER_LABELS = { invoice_issued: "Fatura Kesildiginde", invoice_approved: "Onay Sonrasi", booking_confirmed: "Booking Onayinda", manual_trigger: "Manuel" };

  return (
    <div className="rounded-xl border shadow-sm" data-testid="auto-sync-rules-panel">
      <div className="flex items-center justify-between px-5 py-3 border-b">
        <h2 className="font-semibold text-sm flex items-center gap-2"><Zap className="h-4 w-4 text-amber-500" /> Otomasyon Kurallari</h2>
        <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => setShowCreate(!showCreate)} data-testid="add-rule-btn">
          <Plus className="h-3 w-3" /> Kural Ekle
        </Button>
      </div>
      {showCreate && (
        <div className="px-5 py-3 border-b bg-muted/20 space-y-3" data-testid="create-rule-form">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium block mb-1">Kural Adi</label>
              <input value={form.rule_name} onChange={e => setForm(f => ({ ...f, rule_name: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm bg-background" placeholder="Ornek: Otomatik Sync" data-testid="rule-name-input" />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Tetikleyici</label>
              <select value={form.trigger_event} onChange={e => setForm(f => ({ ...f, trigger_event: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm bg-background" data-testid="rule-trigger-select">
                <option value="invoice_issued">Fatura Kesildiginde</option>
                <option value="invoice_approved">Onay Sonrasi</option>
                <option value="booking_confirmed">Booking Onayinda</option>
                <option value="manual_trigger">Manuel</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs">
              <input type="checkbox" checked={form.requires_approval} onChange={e => setForm(f => ({ ...f, requires_approval: e.target.checked }))} data-testid="rule-approval-check" />
              Onay Gerektirir
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowCreate(false)}>Vazgec</Button>
            <Button size="sm" onClick={handleCreate} data-testid="save-rule-btn">Kaydet</Button>
          </div>
        </div>
      )}
      <div className="divide-y">
        {loading ? <div className="p-5"><div className="animate-pulse h-10 bg-muted rounded-lg" /></div> :
          rules.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground" data-testid="no-rules">
              <Zap className="h-8 w-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">Henuz otomasyon kurali yok</p>
            </div>
          ) : rules.map(rule => (
            <div key={rule.rule_id} className="flex items-center justify-between px-5 py-3" data-testid={`rule-row-${rule.rule_id}`}>
              <div className="flex items-center gap-3">
                <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center", rule.enabled ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-400")}>
                  {rule.enabled ? <Power className="h-4 w-4" /> : <PowerOff className="h-4 w-4" />}
                </div>
                <div>
                  <div className="font-medium text-sm">{rule.rule_name}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px]">{TRIGGER_LABELS[rule.trigger_event] || rule.trigger_event}</Badge>
                    <span>{rule.provider?.toUpperCase()}</span>
                    {rule.requires_approval && <Badge variant="outline" className="text-[10px] bg-amber-50 text-amber-700">Onay Gerekli</Badge>}
                  </div>
                </div>
              </div>
              <div className="flex gap-1">
                <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => toggleRule(rule)} data-testid={`toggle-rule-${rule.rule_id}`}>
                  {rule.enabled ? <PowerOff className="h-3 w-3" /> : <Power className="h-3 w-3" />}
                </Button>
                <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive" onClick={() => deleteRule(rule.rule_id)} data-testid={`delete-rule-${rule.rule_id}`}>
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          ))
        }
      </div>
    </div>
  );
}

/* ── Customer List Panel ─────────────────────────────────── */
function CustomerPanel() {
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState(true);
  const { data: customerData, isLoading: loading } = useAccountingCustomers(search ? { search } : {});
  const customers = customerData?.items || [];
  const total = customerData?.total || 0;

  return (
    <div className="rounded-xl border shadow-sm" data-testid="customer-panel">
      <button className="w-full flex items-center justify-between px-5 py-3 hover:bg-muted/30 transition-colors" onClick={() => setExpanded(!expanded)} data-testid="toggle-customers">
        <h2 className="font-semibold text-sm flex items-center gap-2">
          <Users className="h-4 w-4 text-blue-500" /> Cari Hesaplar
          <Badge variant="outline" className="text-xs">{total}</Badge>
        </h2>
        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {expanded && (
        <>
          <div className="px-5 pb-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <input placeholder="VKN, isim veya email ile ara..." value={search} onChange={e => setSearch(e.target.value)}
                className="w-full rounded-lg border pl-9 pr-3 py-2 text-sm bg-background" data-testid="customer-search" />
            </div>
          </div>
          {loading ? <div className="p-5"><div className="animate-pulse h-20 bg-muted rounded-lg" /></div> :
            customers.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground" data-testid="no-customers">
                <Users className="h-8 w-8 mx-auto mb-2 opacity-20" />
                <p className="text-sm">Henuz cari hesap yok</p>
                <p className="text-xs mt-1">Fatura senkronizasyonu yapildiginda cariler otomatik olusturulur.</p>
              </div>
            ) : (
              <div className="overflow-hidden">
                <table className="w-full text-sm">
                  <thead><tr className="bg-muted/40 border-t border-b">
                    <th className="text-left px-5 py-2.5 font-medium text-xs uppercase tracking-wider">Musteri</th>
                    <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">VKN/TCKN</th>
                    <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Email</th>
                    <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Esleme</th>
                    <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Ext. ID</th>
                  </tr></thead>
                  <tbody>
                    {customers.map(c => (
                      <tr key={c.customer_id} className="border-b last:border-0 hover:bg-muted/20" data-testid={`customer-row-${c.customer_id}`}>
                        <td className="px-5 py-3 font-medium text-sm">{c.name || "-"}</td>
                        <td className="px-4 py-3 font-mono text-xs">{c.vkn || c.tckn || "-"}</td>
                        <td className="px-4 py-3 text-xs text-muted-foreground">{c.email || "-"}</td>
                        <td className="px-4 py-3"><Badge variant="outline" className="text-[10px]">{c.match_method}</Badge></td>
                        <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{c.external_customer_id || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
        </>
      )}
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────── */
export default function AdminAccountingPage() {
  const [showSettings, setShowSettings] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [activeTab, setActiveTab] = useState("overview");

  const { data: dashboard, refetch: refetchDashboard } = useAccountingDashboard();
  const { data: syncJobs = [], isLoading, isError, refetch: refetchJobs } = useSyncJobs(statusFilter ? { status: statusFilter } : {});
  const retryMutation = useRetryJob();

  const refetch = useCallback(() => {
    refetchDashboard();
    refetchJobs();
  }, [refetchDashboard, refetchJobs]);

  const handleRetry = async (jobId) => {
    try {
      await retryMutation.mutateAsync(jobId);
      toast.success("Yeniden deneme basarili");
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    }
  };

  const lucaStatus = dashboard?.providers?.find(p => p.provider === "luca");

  const syncColumns = useMemo(() => [
    {
      accessorKey: "job_id",
      header: "Job ID",
      cell: ({ row }) => <span className="font-mono text-xs font-medium">{row.original.job_id}</span>,
      size: 120,
    },
    {
      accessorKey: "invoice_id",
      header: "Fatura",
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.invoice_id}</span>,
      size: 120,
    },
    {
      accessorKey: "status",
      header: "Durum",
      cell: ({ row }) => {
        const s = JOB_STATUS_MAP[row.original.status];
        return s ? <StatusBadge status={row.original.status} color={s.color} label={s.label} /> : <Badge variant="outline">{row.original.status}</Badge>;
      },
      size: 120,
    },
    {
      accessorKey: "external_ref",
      header: "Ref",
      cell: ({ row }) => <span className="font-mono text-xs text-muted-foreground">{row.original.external_ref || "-"}</span>,
    },
    {
      accessorKey: "attempt_count",
      header: "Deneme",
      cell: ({ row }) => <span className="text-xs text-center">{row.original.attempt_count || 0}/{MAX_ATTEMPTS}</span>,
      size: 80,
    },
    {
      accessorKey: "error_message",
      header: "Hata",
      cell: ({ row }) => (
        <span className="text-xs text-muted-foreground max-w-[180px] truncate block" title={row.original.error_message || ""}>
          {row.original.error_message ? <span className="text-red-600">{row.original.error_message}</span> : "-"}
        </span>
      ),
    },
    {
      id: "actions",
      header: () => <span className="sr-only">Aksiyon</span>,
      cell: ({ row }) => {
        const job = row.original;
        if (job.status === "synced") {
          return <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200"><CheckCircle className="h-3 w-3 mr-1" /> Tamam</Badge>;
        }
        if (job.status === "failed" || job.status === "retrying") {
          return (
            <Button size="sm" variant="outline" className="h-7 text-xs gap-1"
              onClick={(e) => { e.stopPropagation(); handleRetry(job.job_id); }}
              disabled={retryMutation.isPending}
              data-testid={`retry-btn-${job.job_id}`}>
              <RotateCcw className="h-3 w-3" /> Tekrarla
            </Button>
          );
        }
        return null;
      },
      enableSorting: false,
      size: 100,
    },
  ], [retryMutation.isPending, handleRetry]);

  const tabs = [
    { value: "overview", label: "Genel Bakis", icon: <Activity className="h-4 w-4" /> },
    { value: "rules", label: "Otomasyon", icon: <Zap className="h-4 w-4" /> },
    { value: "customers", label: "Cariler", icon: <Users className="h-4 w-4" /> },
  ];

  return (
    <PageShell
      title="Muhasebe Operasyonlari"
      description="Senkronizasyon, cari eslestirme ve otomasyon yonetimi"
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      actions={
        <>
          <Button variant="outline" size="sm" onClick={() => setShowSettings(!showSettings)} data-testid="acct-settings-btn">
            <Settings className="h-4 w-4 mr-1" /> Ayarlar
          </Button>
          <Button variant="outline" size="sm" onClick={refetch} data-testid="acct-refresh-btn">
            <RefreshCw className="h-4 w-4 mr-1" /> Yenile
          </Button>
        </>
      }
    >
      <div data-testid="accounting-page">
        {showSettings && <CredentialSettings onClose={() => setShowSettings(false)} onSaved={refetch} />}

        {/* Dashboard Stats */}
        {dashboard && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6" data-testid="accounting-dashboard">
            <DashboardCard label="Basarili Sync" value={dashboard.synced || 0} icon={CheckCircle} color="bg-emerald-50/50" testId="stat-synced" />
            <DashboardCard label="Basarisiz" value={dashboard.failed || 0} icon={AlertTriangle} color="bg-red-50/50" testId="stat-failed" />
            <DashboardCard label="Bekleyen" value={(dashboard.pending || 0) + (dashboard.processing || 0)} icon={Clock} color="bg-amber-50/50" testId="stat-pending" />
            <DashboardCard label="Yeniden Deneme" value={dashboard.retry_queue || 0} icon={RotateCcw} color="bg-orange-50/50" testId="stat-retry" />
            <DashboardCard label="Cariler" value={dashboard.customer_stats?.total_customers || 0} icon={Users} color="bg-blue-50/50" testId="stat-customers"
              sub={`${dashboard.customer_stats?.unmatched_count || 0} eslesmeyen`} />
            <DashboardCard label="Luca" value={lucaStatus?.configured ? "Aktif" : "Yok"} icon={lucaStatus?.configured ? Wifi : WifiOff}
              color={lucaStatus?.configured ? "bg-teal-50/50" : "bg-slate-50/50"} testId="stat-luca"
              sub={dashboard.last_sync_at ? `Son: ${new Date(dashboard.last_sync_at).toLocaleString("tr-TR")}` : "Henuz sync yok"} />
          </div>
        )}

        {/* Last Error */}
        {dashboard?.last_error && (
          <div className="rounded-xl border border-red-200 bg-red-50/50 p-4 mb-6 flex items-start gap-3" data-testid="last-error-banner">
            <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
            <div>
              <div className="text-sm font-medium text-red-700">Son Hata</div>
              <div className="text-xs text-red-600 mt-0.5">{dashboard.last_error}</div>
              {dashboard.last_error_type && <Badge variant="outline" className="mt-1 text-xs bg-red-100 text-red-700 border-red-200">{dashboard.last_error_type}</Badge>}
            </div>
          </div>
        )}

        {/* Tab Content */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            <div className="flex gap-2 flex-wrap" data-testid="sync-filters">
              {[
                { value: "", label: "Tumu" },
                { value: "synced", label: "Basarili" },
                { value: "failed", label: "Basarisiz" },
                { value: "pending", label: "Bekleyen" },
                { value: "retrying", label: "Yeniden Deniyor" },
              ].map(f => (
                <Button key={f.value} variant={statusFilter === f.value ? "default" : "outline"} size="sm"
                  onClick={() => setStatusFilter(f.value)} className="text-xs h-7" data-testid={`sync-filter-${f.value || 'all'}`}>
                  {f.label}
                </Button>
              ))}
            </div>

            {isError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600">
                Veriler yuklenemedi
                <Button variant="ghost" size="sm" className="ml-2 h-6 text-xs" onClick={() => refetchJobs()}>Tekrar Dene</Button>
              </div>
            )}

            <DataTable
              data={syncJobs}
              columns={syncColumns}
              loading={isLoading}
              pageSize={20}
              emptyState={
                <div className="flex flex-col items-center gap-2 py-8" data-testid="no-sync-jobs">
                  <Database className="h-12 w-12 opacity-20 text-muted-foreground" />
                  <p className="text-sm font-medium text-muted-foreground">Henuz senkronizasyon isi yok</p>
                </div>
              }
            />
          </div>
        )}

        {activeTab === "rules" && <AutoSyncRulesPanel />}
        {activeTab === "customers" && <CustomerPanel />}
      </div>
    </PageShell>
  );
}
