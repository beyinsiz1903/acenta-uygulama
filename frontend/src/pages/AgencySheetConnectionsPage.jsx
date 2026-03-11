import React, { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import {
  FileSpreadsheet, Plus, Trash2, Loader2,
  CheckCircle2, AlertCircle, Hotel, Link2,
  ExternalLink, RefreshCw, XCircle, Clock,
  WifiOff, Zap, Settings, History, Key,
  Shield, ChevronDown, ChevronUp, ToggleLeft,
  ToggleRight, Upload, Eye, EyeOff, Timer,
} from "lucide-react";

function formatDate(d) {
  if (!d) return "\u2014";
  try {
    return new Date(d).toLocaleString("tr-TR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return "\u2014"; }
}

function SyncStatusBadge({ status, error }) {
  const map = {
    success: { bg: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400", icon: CheckCircle2, label: "Basarili" },
    no_change: { bg: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", icon: CheckCircle2, label: "Degisiklik Yok" },
    error: { bg: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400", icon: XCircle, label: "Hata" },
    failed: { bg: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400", icon: XCircle, label: "Basarisiz" },
    not_configured: { bg: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400", icon: WifiOff, label: "Yapilandirilmamis" },
    running: { bg: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", icon: Loader2, label: "Calisiyor" },
    active: { bg: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400", icon: CheckCircle2, label: "Aktif" },
  };
  const s = map[status] || map.active;
  const Icon = s.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${s.bg} cursor-default`}
      title={error || ""}
      data-testid={`sync-status-badge-${status}`}
    >
      <Icon className={`w-3 h-3 ${status === "running" ? "animate-spin" : ""}`} />
      {s.label}
    </span>
  );
}

function IntervalSelector({ value, onChange, disabled }) {
  const options = [
    { val: 5, label: "5 dk" },
    { val: 15, label: "15 dk" },
    { val: 30, label: "30 dk" },
    { val: 60, label: "1 saat" },
  ];
  return (
    <select
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      disabled={disabled}
      className="rounded-lg border border-gray-300 dark:border-gray-600 px-2 py-1 text-xs bg-white dark:bg-gray-900 disabled:opacity-50"
      data-testid="interval-selector"
    >
      {options.map((o) => (
        <option key={o.val} value={o.val}>{o.label}</option>
      ))}
    </select>
  );
}

function CredentialsSection() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [jsonInput, setJsonInput] = useState("");
  const [showJson, setShowJson] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const loadStatus = useCallback(async () => {
    try {
      const res = await api.get("/agency/sheets/credentials/status");
      setStatus(res.data);
    } catch { /* silent */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await api.post("/agency/sheets/credentials", { service_account_json: jsonInput });
      setSuccess(`Kimlik bilgileri kaydedildi: ${res.data.client_email}`);
      setShowForm(false);
      setJsonInput("");
      await loadStatus();
      setTimeout(() => setSuccess(null), 4000);
    } catch (e) {
      setError(e.response?.data?.error?.message || "Kaydetme hatasi");
    } finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!window.confirm("Kendi kimlik bilgilerinizi silmek istediginize emin misiniz? Global ayara geri donulecektir.")) return;
    setDeleting(true);
    try {
      await api.delete("/agency/sheets/credentials");
      setSuccess("Kimlik bilgileri silindi. Global ayar kullanilacak.");
      await loadStatus();
      setTimeout(() => setSuccess(null), 4000);
    } catch (e) {
      setError(e.response?.data?.error?.message || "Silme hatasi");
    } finally { setDeleting(false); }
  };

  if (loading) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5" data-testid="credentials-section">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Key className="w-5 h-5 text-amber-500" />
          <h3 className="font-semibold text-sm">Google Sheets Kimlik Bilgileri</h3>
        </div>
        <div className="flex items-center gap-2">
          {status?.has_own_credentials && (
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="text-xs text-red-500 hover:text-red-700 transition-colors"
              data-testid="delete-credentials-btn"
            >
              {deleting ? "Siliniyor..." : "Kendi Kimligimi Sil"}
            </button>
          )}
          <button
            onClick={() => { setShowForm(!showForm); setError(null); }}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-xs"
            data-testid="toggle-credentials-form"
          >
            <Upload className="w-3 h-3" />
            {status?.has_own_credentials ? "Guncelle" : "Kendi Hesabimi Ekle"}
          </button>
        </div>
      </div>

      {/* Current Status */}
      <div className="flex items-center gap-6 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5" />
          <span>Aktif Kaynak:</span>
          <span className={`font-medium ${status?.active_source === "agency" ? "text-amber-600" : status?.active_source === "global" ? "text-blue-600" : "text-red-600"}`}>
            {status?.active_source === "agency" ? "Kendi Hesabiniz" : status?.active_source === "global" ? "Global (Admin)" : "Yapilandirilmamis"}
          </span>
        </div>
        {status?.own_service_account_email && (
          <span className="text-emerald-600 dark:text-emerald-400">{status.own_service_account_email}</span>
        )}
        {!status?.has_own_credentials && status?.global_service_account_email && (
          <span className="text-blue-600 dark:text-blue-400">{status.global_service_account_email}</span>
        )}
      </div>

      {/* Success / Error */}
      {success && <div className="mt-2 text-xs text-emerald-600 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" />{success}</div>}
      {error && <div className="mt-2 text-xs text-red-600 flex items-center gap-1"><AlertCircle className="w-3 h-3" />{error}</div>}

      {/* Form */}
      {showForm && (
        <div className="mt-3 space-y-3 border-t border-gray-100 dark:border-gray-700 pt-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Google Service Account JSON
            </label>
            <div className="relative">
              <textarea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                placeholder='{"type": "service_account", "project_id": "...", "client_email": "...", ...}'
                rows={showJson ? 8 : 3}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-xs font-mono bg-white dark:bg-gray-900"
                data-testid="credentials-json-input"
              />
              <button
                onClick={() => setShowJson(!showJson)}
                className="absolute top-2 right-2 p-1 text-muted-foreground hover:text-foreground"
              >
                {showJson ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
              </button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Google Cloud Console'dan indirdiginiz Service Account JSON dosyasinin icerigini buraya yapistirin.
            </p>
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => { setShowForm(false); setError(null); }}
              className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Vazgec
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !jsonInput.trim()}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-50 transition-colors text-xs font-medium"
              data-testid="save-credentials-btn"
            >
              {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Key className="w-3 h-3" />}
              Kaydet
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function SyncHistoryPanel() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/agency/sheets/sync-history?limit=15");
      setHistory(res.data?.items || []);
    } catch { /* silent */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { if (expanded) loadHistory(); }, [expanded, loadHistory]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700" data-testid="sync-history-panel">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors rounded-xl"
        data-testid="toggle-sync-history"
      >
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-blue-500" />
          <span className="font-semibold text-sm">Senkronizasyon Gecmisi</span>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          {loading ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground py-3">
              <Loader2 className="w-4 h-4 animate-spin" /> Yukleniyor...
            </div>
          ) : history.length === 0 ? (
            <p className="text-xs text-muted-foreground py-3">Henuz sync gecmisi yok.</p>
          ) : (
            <div className="space-y-1.5 max-h-64 overflow-y-auto">
              {history.map((run) => (
                <div
                  key={run.run_id}
                  className="flex items-center justify-between text-xs py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  data-testid={`history-row-${run.run_id}`}
                >
                  <div className="flex items-center gap-3">
                    <SyncStatusBadge status={run.status} />
                    <span className="text-muted-foreground">{run.hotel_name || run.hotel_id}</span>
                    <span className="text-muted-foreground/70">
                      {run.trigger === "scheduled" ? "Otomatik" : "Manuel"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-muted-foreground">
                    <span>{run.upserted > 0 ? `${run.upserted} guncellendi` : "Degisiklik yok"}</span>
                    <span>{run.duration_ms}ms</span>
                    <span>{formatDate(run.started_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
          <button
            onClick={loadHistory}
            className="mt-2 text-xs text-blue-500 hover:text-blue-700 flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> Yenile
          </button>
        </div>
      )}
    </div>
  );
}

export default function AgencySheetConnectionsPage() {
  const [connections, setConnections] = useState([]);
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [syncing, setSyncing] = useState(null);
  const [updatingSettings, setUpdatingSettings] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);

  // Form state
  const [selectedHotel, setSelectedHotel] = useState("");
  const [sheetId, setSheetId] = useState("");
  const [sheetTab, setSheetTab] = useState("Sheet1");
  const [writebackTab, setWritebackTab] = useState("Rezervasyonlar");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [connRes, hotelRes, statusRes] = await Promise.all([
        api.get("/agency/sheets/connections"),
        api.get("/agency/sheets/hotels"),
        api.get("/agency/sheets/sync-status"),
      ]);
      setConnections(connRes.data || []);
      setHotels(hotelRes.data || []);
      setSyncStatus(statusRes.data || null);
    } catch { /* silent */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleConnect = async () => {
    if (!selectedHotel || !sheetId) {
      setError("Otel ve Google Sheet ID zorunludur.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.post("/agency/sheets/connect", {
        hotel_id: selectedHotel,
        sheet_id: sheetId,
        sheet_tab: sheetTab,
        writeback_tab: writebackTab,
      });
      setSuccess("Sheet baglantisi olusturuldu!");
      setShowForm(false);
      setSelectedHotel("");
      setSheetId("");
      setSheetTab("Sheet1");
      setWritebackTab("Rezervasyonlar");
      await loadData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (e) {
      setError(e.response?.data?.error?.message || e.message || "Baglanti hatasi");
    } finally { setSaving(false); }
  };

  const handleDelete = async (connId, hotelName) => {
    if (!window.confirm(`"${hotelName}" sheet baglantisini silmek istediginize emin misiniz?`)) return;
    try {
      await api.delete(`/agency/sheets/connections/${connId}`);
      await loadData();
    } catch (e) {
      setError(e.response?.data?.error?.message || "Silme hatasi");
    }
  };

  const handleSync = async (connId) => {
    setSyncing(connId);
    setError(null);
    try {
      const res = await api.post(`/agency/sheets/sync/${connId}`);
      if (res.data?.status === "not_configured") {
        setError("Google Sheets yapilandirilmamis. Lutfen admin ile iletisime gecin.");
      } else if (res.data?.status === "success" || res.data?.status === "no_change") {
        setSuccess(`Sync tamamlandi (${res.data.upserted || 0} satir guncellendi)`);
        setTimeout(() => setSuccess(null), 4000);
      } else if (res.data?.status === "failed") {
        setError("Sync basarisiz oldu. Detaylar icin duruma tiklayin.");
      }
      await loadData();
    } catch (e) {
      setError(e.response?.data?.error?.message || "Sync hatasi");
    } finally { setSyncing(null); }
  };

  const handleToggleSync = async (connId, currentEnabled) => {
    setUpdatingSettings(connId);
    try {
      await api.patch(`/agency/sheets/connections/${connId}/settings`, {
        sync_enabled: !currentEnabled,
      });
      await loadData();
    } catch (e) {
      setError(e.response?.data?.error?.message || "Ayar guncelleme hatasi");
    } finally { setUpdatingSettings(null); }
  };

  const handleIntervalChange = async (connId, minutes) => {
    setUpdatingSettings(connId);
    try {
      await api.patch(`/agency/sheets/connections/${connId}/settings`, {
        sync_interval_minutes: minutes,
      });
      await loadData();
    } catch (e) {
      setError(e.response?.data?.error?.message || "Ayar guncelleme hatasi");
    } finally { setUpdatingSettings(null); }
  };

  const availableHotels = hotels.filter((h) => !h.connected);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20" data-testid="sheet-connections-loading">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Yukleniyor...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="agency-sheet-connections-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2" data-testid="page-title">
            <FileSpreadsheet className="w-6 h-6 text-primary" />
            Sheet Baglantilari
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Otellerinizi Google Sheet'lere baglayarak musaitlik verilerini otomatik senkronize edin.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm"
            data-testid="refresh-btn"
          >
            <RefreshCw className="w-4 h-4" />
            Yenile
          </button>
          {availableHotels.length > 0 && (
            <button
              onClick={() => { setShowForm(true); setError(null); }}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm font-medium"
              data-testid="add-connection-btn"
            >
              <Plus className="w-4 h-4" />
              Yeni Baglanti
            </button>
          )}
        </div>
      </div>

      {/* Auto-Sync Status Overview */}
      {syncStatus && syncStatus.total_connections > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="sync-status-overview">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
            <div className="text-lg font-bold text-primary">{syncStatus.total_connections}</div>
            <div className="text-xs text-muted-foreground">Toplam Baglanti</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
            <div className="text-lg font-bold text-blue-600">{syncStatus.sync_enabled_count}</div>
            <div className="text-xs text-muted-foreground">Otomatik Sync Aktif</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
            <div className="text-lg font-bold text-emerald-600">{syncStatus.healthy_count}</div>
            <div className="text-xs text-muted-foreground">Saglikli</div>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-3 text-center">
            <div className="text-lg font-bold text-red-600">{syncStatus.failed_count}</div>
            <div className="text-xs text-muted-foreground">Hatali</div>
          </div>
        </div>
      )}

      {/* Credentials Section */}
      <CredentialsSection />

      {/* Success / Error messages */}
      {success && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-sm" data-testid="success-message">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          {success}
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm" data-testid="error-message">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-xs underline">Kapat</button>
        </div>
      )}

      {/* New Connection Form */}
      {showForm && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-4" data-testid="connection-form">
          <h3 className="font-semibold text-base">Yeni Sheet Baglantisi</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">Otel</label>
              <select
                value={selectedHotel}
                onChange={(e) => setSelectedHotel(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm bg-white dark:bg-gray-900"
                data-testid="hotel-select"
              >
                <option value="">Otel Secin...</option>
                {availableHotels.map((h) => (
                  <option key={h._id} value={h._id}>{h.name}{h.city ? ` (${h.city})` : ""}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">Google Sheet ID</label>
              <input
                type="text"
                value={sheetId}
                onChange={(e) => setSheetId(e.target.value)}
                placeholder="1BxilMVsOXRA5nFMdKvBdBZg..."
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm bg-white dark:bg-gray-900"
                data-testid="sheet-id-input"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Sheet URL'sindeki /d/ ile /edit arasindaki kisim
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">Musaitlik Sayfasi</label>
              <input
                type="text"
                value={sheetTab}
                onChange={(e) => setSheetTab(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm bg-white dark:bg-gray-900"
                data-testid="sheet-tab-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">Rez. Geri Yazim Sayfasi</label>
              <input
                type="text"
                value={writebackTab}
                onChange={(e) => setWritebackTab(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm bg-white dark:bg-gray-900"
                data-testid="writeback-tab-input"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => { setShowForm(false); setError(null); }}
              className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              data-testid="cancel-btn"
            >
              Vazgec
            </button>
            <button
              onClick={handleConnect}
              disabled={saving || !selectedHotel || !sheetId}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors text-sm font-medium"
              data-testid="connect-btn"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />}
              Bagla
            </button>
          </div>
        </div>
      )}

      {/* Connections List */}
      {connections.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-10 text-center" data-testid="empty-state">
          <FileSpreadsheet className="w-10 h-10 mx-auto text-muted-foreground/40" />
          <p className="mt-3 font-medium">Henuz Sheet Baglantiniz Yok</p>
          <p className="text-sm text-muted-foreground mt-1">
            "Yeni Baglanti" butonuyla otellerinizi Google Sheet'lere baglayabilirsiniz.
          </p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="connections-list">
          {connections.map((conn) => {
            const isUpdating = updatingSettings === conn._id;
            return (
              <div
                key={conn._id}
                className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4"
                data-testid={`connection-${conn._id}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Hotel className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <div className="font-medium text-sm">{conn.hotel_name || conn.hotel_id}</div>
                      <div className="text-xs text-muted-foreground mt-0.5 flex items-center gap-3 flex-wrap">
                        <span className="flex items-center gap-1">
                          <FileSpreadsheet className="w-3 h-3" />
                          {conn.sheet_tab || "Sheet1"}
                        </span>
                        <span className="flex items-center gap-1">
                          <ExternalLink className="w-3 h-3" />
                          <a
                            href={`https://docs.google.com/spreadsheets/d/${conn.sheet_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline"
                          >
                            Sheet Ac
                          </a>
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Son Sync: {formatDate(conn.last_sync_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <SyncStatusBadge
                      status={conn.last_sync_status || conn.status || "active"}
                      error={conn.last_error}
                    />
                    <button
                      onClick={() => handleSync(conn._id)}
                      disabled={syncing === conn._id}
                      className="p-1.5 rounded-lg text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors disabled:opacity-50"
                      title="Simdi Senkronize Et"
                      data-testid={`sync-${conn._id}`}
                    >
                      {syncing === conn._id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Zap className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      onClick={() => handleDelete(conn._id, conn.hotel_name)}
                      className="p-1.5 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      title="Baglantiyi Sil"
                      data-testid={`delete-${conn._id}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Auto-Sync Controls */}
                <div className="mt-3 ml-14 flex items-center gap-4 text-xs border-t border-gray-100 dark:border-gray-700 pt-3">
                  <button
                    onClick={() => handleToggleSync(conn._id, conn.sync_enabled)}
                    disabled={isUpdating}
                    className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
                    data-testid={`toggle-sync-${conn._id}`}
                  >
                    {isUpdating ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : conn.sync_enabled ? (
                      <ToggleRight className="w-5 h-5 text-emerald-500" />
                    ) : (
                      <ToggleLeft className="w-5 h-5 text-gray-400" />
                    )}
                    <span className={conn.sync_enabled ? "text-emerald-600 font-medium" : "text-gray-500"}>
                      Otomatik Sync {conn.sync_enabled ? "Acik" : "Kapali"}
                    </span>
                  </button>

                  {conn.sync_enabled && (
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Timer className="w-3.5 h-3.5" />
                      <span>Her</span>
                      <IntervalSelector
                        value={conn.sync_interval_minutes || 5}
                        onChange={(val) => handleIntervalChange(conn._id, val)}
                        disabled={isUpdating}
                      />
                    </div>
                  )}
                </div>

                {/* Error details */}
                {conn.last_error && (conn.last_sync_status === "error" || conn.last_sync_status === "failed") && (
                  <div className="mt-2 ml-14 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg" data-testid={`error-detail-${conn._id}`}>
                    <span className="font-medium">Hata detayi:</span> {conn.last_error}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Sync History */}
      <SyncHistoryPanel />
    </div>
  );
}
