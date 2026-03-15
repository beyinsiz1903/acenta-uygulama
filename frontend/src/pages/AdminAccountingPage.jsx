import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  RefreshCw, CheckCircle, Clock, AlertTriangle, X,
  Settings, Shield, Wifi, WifiOff, Key, Trash2,
  ArrowUpRight, RotateCcw, Database, Activity,
  TrendingUp, ChevronDown, ChevronUp
} from "lucide-react";
import { cn } from "../lib/utils";
import { toast } from "sonner";

const SYNC_STATUS_MAP = {
  pending: { label: "Bekliyor", icon: Clock, color: "bg-amber-50 text-amber-700 border-amber-200" },
  in_progress: { label: "Isleniyor", icon: RefreshCw, color: "bg-blue-50 text-blue-700 border-blue-200" },
  synced: { label: "Senkronize", icon: CheckCircle, color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  failed: { label: "Basarisiz", icon: AlertTriangle, color: "bg-red-50 text-red-700 border-red-200" },
};

function SyncStatusBadge({ status }) {
  const s = SYNC_STATUS_MAP[status] || { label: status, icon: Clock, color: "" };
  const Icon = s.icon;
  return (
    <Badge variant="outline" className={cn("gap-1 font-medium", s.color)} data-testid={`sync-status-${status}`}>
      <Icon className="h-3 w-3" /> {s.label}
    </Badge>
  );
}

function DashboardCard({ label, value, icon: Icon, color, sub }) {
  return (
    <div className={cn("rounded-xl border p-4 flex items-start gap-3 transition-all", color)} data-testid={`dashboard-stat-${label.toLowerCase().replace(/\s/g, '-')}`}>
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

function LucaCredentialSettings({ onClose, onSaved }) {
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

  useEffect(() => { loadData(); }, [loadData]);

  const handleSave = async () => {
    if (!selectedProvider) return;
    const missing = selectedProvider.credential_fields.filter(f => f.required && !credentials[f.key]);
    if (missing.length) {
      toast.error(`Zorunlu alanlar: ${missing.map(f => f.label).join(", ")}`);
      return;
    }
    setSaving(true);
    try {
      await api.post("/accounting/credentials", {
        provider: selectedProvider.code,
        credentials,
      });
      toast.success("Kimlik bilgileri kaydedildi");
      setSelectedProvider(null);
      setCredentials({});
      loadData();
      onSaved?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setSaving(false); }
  };

  const handleTest = async (provider) => {
    setTesting(true);
    try {
      const res = await api.post("/accounting/test-connection", { provider });
      if (res.data.success) {
        toast.success(res.data.message || "Baglanti basarili");
      } else {
        toast.error(res.data.message || "Baglanti basarisiz");
      }
      loadData();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setTesting(false); }
  };

  const handleDelete = async (provider) => {
    if (!window.confirm("Bu muhasebe yapilandirmasini silmek istediginize emin misiniz?")) return;
    try {
      await api.delete(`/accounting/credentials/${provider}`);
      toast.success("Yapilandirma silindi");
      loadData();
      onSaved?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  return (
    <div className="rounded-xl border bg-card shadow-sm p-5 mb-6" data-testid="accounting-settings">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold flex items-center gap-2"><Settings className="h-4 w-4" /> Muhasebe Entegrator Ayarlari</h3>
        <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
      </div>

      {loading ? (
        <div className="animate-pulse h-20 bg-muted rounded-lg" />
      ) : (
        <div className="space-y-4">
          {configs.length > 0 && (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">Yapilandirilmis Muhasebe Sistemleri</div>
              {configs.map(cfg => (
                <div key={cfg.provider} className="rounded-lg border p-3 flex items-center justify-between mb-2" data-testid={`acct-config-${cfg.provider}`}>
                  <div className="flex items-center gap-3">
                    <div className={cn("h-8 w-8 rounded-lg flex items-center justify-center text-xs font-bold",
                      cfg.status === "active" ? "bg-emerald-100 text-emerald-700" :
                      cfg.status === "error" ? "bg-red-100 text-red-700" :
                      "bg-amber-100 text-amber-700"
                    )}>
                      {cfg.status === "active" ? <Wifi className="h-4 w-4" /> : cfg.status === "error" ? <WifiOff className="h-4 w-4" /> : <Key className="h-4 w-4" />}
                    </div>
                    <div>
                      <div className="font-medium text-sm">{cfg.provider?.toUpperCase()}</div>
                      <div className="text-xs text-muted-foreground">
                        {cfg.masked_credentials?.username && `Kullanici: ${cfg.masked_credentials.username}`}
                        {cfg.last_test && ` | Son test: ${new Date(cfg.last_test).toLocaleString("tr-TR")}`}
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
                    className="rounded-lg border-2 border-dashed p-3 text-left hover:border-primary hover:bg-primary/5 transition-all"
                    data-testid={`add-acct-provider-${p.code}`}>
                    <Shield className="h-5 w-5 mb-1 text-primary" />
                    <div className="font-medium text-sm">{p.name}</div>
                    <div className="text-xs text-muted-foreground">{p.description}</div>
                  </button>
                ))}
              </div>
              {providers.length === configs.length && configs.length > 0 && (
                <div className="text-xs text-muted-foreground text-center py-3">Tum muhasebe sistemleri yapilandirilmis</div>
              )}
            </div>
          ) : (
            <div data-testid="acct-credential-form">
              <div className="text-xs font-medium text-muted-foreground mb-2">{selectedProvider.name} - Kimlik Bilgileri</div>
              <div className="space-y-2">
                {selectedProvider.credential_fields.map(field => (
                  <div key={field.key}>
                    <label className="text-xs font-medium block mb-1">{field.label} {field.required && <span className="text-destructive">*</span>}</label>
                    <input
                      type={field.type === "password" ? "password" : "text"}
                      value={credentials[field.key] || ""}
                      onChange={e => setCredentials(c => ({ ...c, [field.key]: e.target.value }))}
                      className="w-full rounded-lg border px-3 py-2 text-sm bg-background"
                      placeholder={field.placeholder || ""}
                      data-testid={`acct-field-${field.key}`}
                    />
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-2 mt-3">
                <Button variant="outline" size="sm" onClick={() => setSelectedProvider(null)}>Vazgec</Button>
                <Button size="sm" onClick={handleSave} disabled={saving} data-testid="save-acct-credentials-btn">
                  {saving ? "Kaydediliyor..." : "Kaydet"}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AdminAccountingPage() {
  const [dashboard, setDashboard] = useState(null);
  const [syncLogs, setSyncLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [statusFilter, setStatusFilter] = useState("");
  const [syncing, setSyncing] = useState(null);
  const [retrying, setRetrying] = useState(null);
  const [logsExpanded, setLogsExpanded] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [dashRes, logsRes] = await Promise.all([
        api.get("/accounting/dashboard"),
        api.get("/accounting/sync-logs", { params: { limit: 100, ...(statusFilter ? { status: statusFilter } : {}) } }),
      ]);
      setDashboard(dashRes.data);
      setSyncLogs(logsRes.data?.items || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleSync = async (invoiceId) => {
    setSyncing(invoiceId);
    try {
      const res = await api.post(`/accounting/sync/${invoiceId}`, { provider: "luca" });
      if (res.data?.error === "duplicate") {
        toast.info(res.data.message || "Zaten senkronize edilmis");
      } else {
        toast.success("Senkronizasyon tamamlandi");
      }
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setSyncing(null); }
  };

  const handleRetry = async (syncId) => {
    setRetrying(syncId);
    try {
      await api.post("/accounting/retry", { sync_id: syncId });
      toast.success("Yeniden deneme basarili");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setRetrying(null); }
  };

  const lucaStatus = dashboard?.providers?.find(p => p.provider === "luca");

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="accounting-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="accounting-page-title">
            <Database className="h-6 w-6 text-primary" /> Muhasebe Senkronizasyon
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Fatura muhasebe sistemi entegrasyonu ve senkronizasyon durumu</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowSettings(!showSettings)} data-testid="acct-settings-btn">
            <Settings className="h-4 w-4 mr-1" /> Ayarlar
          </Button>
          <Button variant="outline" size="sm" onClick={load} data-testid="acct-refresh-btn">
            <RefreshCw className="h-4 w-4 mr-1" /> Yenile
          </Button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <LucaCredentialSettings onClose={() => setShowSettings(false)} onSaved={load} />
      )}

      {/* Dashboard Stats */}
      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6" data-testid="accounting-dashboard">
          <DashboardCard label="Toplam Sync" value={dashboard.total_syncs} icon={Activity} />
          <DashboardCard label="Basarili" value={dashboard.success} icon={CheckCircle} color="bg-emerald-50/50" />
          <DashboardCard label="Basarisiz" value={dashboard.failed} icon={AlertTriangle} color="bg-red-50/50" />
          <DashboardCard label="Bekleyen" value={dashboard.pending + dashboard.in_progress} icon={Clock} color="bg-amber-50/50" />
          <DashboardCard
            label="Luca Baglantisi"
            value={lucaStatus?.configured ? "Aktif" : "Yok"}
            icon={lucaStatus?.configured ? Wifi : WifiOff}
            color={lucaStatus?.configured ? "bg-teal-50/50" : "bg-slate-50/50"}
            sub={dashboard.last_sync_at ? `Son: ${new Date(dashboard.last_sync_at).toLocaleString("tr-TR")}` : "Henuz sync yok"}
          />
        </div>
      )}

      {/* Last Error Banner */}
      {dashboard?.last_error && (
        <div className="rounded-xl border border-red-200 bg-red-50/50 p-4 mb-6 flex items-start gap-3" data-testid="last-error-banner">
          <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <div className="text-sm font-medium text-red-700">Son Hata</div>
            <div className="text-xs text-red-600 mt-0.5">{dashboard.last_error}</div>
            {dashboard.last_error_type && (
              <Badge variant="outline" className="mt-1 text-xs bg-red-100 text-red-700 border-red-200">
                {dashboard.last_error_type}
              </Badge>
            )}
          </div>
        </div>
      )}

      {/* Sync Logs */}
      <div className="rounded-xl border shadow-sm" data-testid="sync-logs-section">
        <button
          className="w-full flex items-center justify-between px-5 py-3 hover:bg-muted/30 transition-colors"
          onClick={() => setLogsExpanded(!logsExpanded)}
          data-testid="toggle-sync-logs"
        >
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <Activity className="h-4 w-4" /> Senkronizasyon Kayitlari
            <Badge variant="outline" className="text-xs">{syncLogs.length}</Badge>
          </h2>
          {logsExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {logsExpanded && (
          <>
            {/* Filters */}
            <div className="flex gap-2 px-5 pb-3 flex-wrap" data-testid="sync-filters">
              {[
                { value: "", label: "Tumu" },
                { value: "synced", label: "Basarili" },
                { value: "failed", label: "Basarisiz" },
                { value: "pending", label: "Bekleyen" },
              ].map(f => (
                <Button key={f.value} variant={statusFilter === f.value ? "default" : "outline"} size="sm"
                  onClick={() => setStatusFilter(f.value)} className="text-xs h-7" data-testid={`sync-filter-${f.value || 'all'}`}>
                  {f.label}
                </Button>
              ))}
            </div>

            {loading ? (
              <div className="p-5 space-y-3">{[1,2,3].map(i => <div key={i} className="animate-pulse h-14 bg-muted rounded-lg" />)}</div>
            ) : syncLogs.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground" data-testid="no-sync-logs">
                <Database className="h-12 w-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm font-medium">Henuz senkronizasyon kaydi yok</p>
                <p className="text-xs mt-1">Kesilmis faturayi Luca'ya senkronize etmek icin Fatura Motoru sayfasindan aksiyona gecin.</p>
              </div>
            ) : (
              <div className="overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/40 border-t border-b">
                      <th className="text-left px-5 py-2.5 font-medium text-xs uppercase tracking-wider">Sync ID</th>
                      <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Fatura No</th>
                      <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Saglayici</th>
                      <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Durum</th>
                      <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Ref</th>
                      <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Deneme</th>
                      <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Hata</th>
                      <th className="text-left px-4 py-2.5 font-medium text-xs uppercase tracking-wider">Tarih</th>
                      <th className="text-right px-5 py-2.5 font-medium text-xs uppercase tracking-wider">Aksiyon</th>
                    </tr>
                  </thead>
                  <tbody>
                    {syncLogs.map(log => (
                      <tr key={log.sync_id} className="border-b last:border-0 hover:bg-muted/20 transition-colors" data-testid={`sync-row-${log.sync_id}`}>
                        <td className="px-5 py-3 font-mono text-xs font-medium">{log.sync_id}</td>
                        <td className="px-4 py-3 font-mono text-xs">{log.invoice_id}</td>
                        <td className="px-4 py-3">
                          <Badge variant="outline" className="text-xs bg-teal-50 text-teal-700 border-teal-200">
                            {log.provider?.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="px-4 py-3"><SyncStatusBadge status={log.sync_status} /></td>
                        <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                          {log.external_accounting_ref || "-"}
                        </td>
                        <td className="px-4 py-3 text-xs text-center">{log.sync_attempt_count || 0}</td>
                        <td className="px-4 py-3 text-xs text-muted-foreground max-w-[200px] truncate" title={log.last_error || ""}>
                          {log.last_error ? (
                            <span className="text-red-600">{log.last_error}</span>
                          ) : "-"}
                        </td>
                        <td className="px-4 py-3 text-xs text-muted-foreground">
                          {log.updated_at ? new Date(log.updated_at).toLocaleString("tr-TR") : "-"}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {log.sync_status === "failed" && (
                            <Button size="sm" variant="outline" className="h-7 text-xs gap-1"
                              onClick={() => handleRetry(log.sync_id)}
                              disabled={retrying === log.sync_id}
                              data-testid={`retry-btn-${log.sync_id}`}>
                              <RotateCcw className="h-3 w-3" />
                              {retrying === log.sync_id ? "..." : "Tekrarla"}
                            </Button>
                          )}
                          {log.sync_status === "synced" && (
                            <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                              <CheckCircle className="h-3 w-3 mr-1" /> Tamam
                            </Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
