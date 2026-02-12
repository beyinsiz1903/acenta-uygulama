import React, { useState, useCallback, useEffect, useMemo } from "react";
import { api } from "../../lib/api";
import {
  Sheet, Link2, RefreshCw, CheckCircle2, AlertTriangle, XCircle,
  ChevronRight, ChevronDown, Clock, Zap, ArrowRight, Search,
  Plus, Settings, Trash2, Activity, Database, WifiOff, Copy,
  BarChart3, Eye, Loader2, Info, X,
} from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   PORTFOLIO SYNC ENGINE — Enterprise Admin Page
   Multi-hotel Google Sheets sync (300 otel / 300 sheet)
   ═══════════════════════════════════════════════════════════════ */

// ── Badge helpers ──────────────────────────────────────────────

function StatusBadge({ status }) {
  const map = {
    success: { bg: "bg-emerald-50 dark:bg-emerald-900/30", text: "text-emerald-700 dark:text-emerald-300", icon: CheckCircle2, label: "Basarili" },
    no_change: { bg: "bg-blue-50 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-300", icon: CheckCircle2, label: "Degisiklik Yok" },
    error: { bg: "bg-red-50 dark:bg-red-900/30", text: "text-red-700 dark:text-red-300", icon: XCircle, label: "Hata" },
    failed: { bg: "bg-red-50 dark:bg-red-900/30", text: "text-red-700 dark:text-red-300", icon: XCircle, label: "Basarisiz" },
    partial: { bg: "bg-amber-50 dark:bg-amber-900/30", text: "text-amber-700 dark:text-amber-300", icon: AlertTriangle, label: "Kismi" },
    not_configured: { bg: "bg-gray-50 dark:bg-gray-800", text: "text-gray-500 dark:text-gray-400", icon: WifiOff, label: "Yapilandirilmamis" },
    running: { bg: "bg-blue-50 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-300", icon: Loader2, label: "Calisiyor" },
    skipped: { bg: "bg-gray-50 dark:bg-gray-800", text: "text-gray-500 dark:text-gray-400", icon: Clock, label: "Atlandi" },
    active: { bg: "bg-emerald-50 dark:bg-emerald-900/30", text: "text-emerald-700 dark:text-emerald-300", icon: CheckCircle2, label: "Aktif" },
  };
  const s = map[status] || map.error;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${s.bg} ${s.text}`}>
      <Icon className={`w-3 h-3 ${status === "running" ? "animate-spin" : ""}`} />
      {s.label}
    </span>
  );
}

function StatCard({ icon: Icon, label, value, color = "blue" }) {
  const colors = {
    blue: "from-blue-500 to-blue-600",
    green: "from-emerald-500 to-emerald-600",
    amber: "from-amber-500 to-amber-600",
    red: "from-red-500 to-red-600",
    gray: "from-gray-400 to-gray-500",
    purple: "from-purple-500 to-purple-600",
  };
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center gap-3">
        <div className={`p-2.5 rounded-lg bg-gradient-to-br ${colors[color]} text-white shadow-sm`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
        </div>
      </div>
    </div>
  );
}

function formatDate(d) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch { return "—"; }
}

// ── Config Banner ──────────────────────────────────────────────

function ConfigBanner({ config, onConfigSaved }) {
  const [copied, setCopied] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [jsonInput, setJsonInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  if (!config) return null;

  const copyEmail = () => {
    if (config.service_account_email) {
      navigator.clipboard.writeText(config.service_account_email);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const res = await api.post("/admin/sheets/service-account", {
        service_account_json: jsonInput,
      });
      setShowSetup(false);
      setJsonInput("");
      if (onConfigSaved) onConfigSaved(res.data);
    } catch (e) {
      setSaveError(e.response?.data?.error?.message || e.message || "Kaydetme hatasi");
    } finally {
      setSaving(false);
    }
  };

  if (config.configured) {
    return (
      <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-4 flex items-center gap-3">
        <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium text-emerald-800 dark:text-emerald-200">Google Sheets Yapilandirildi</p>
          <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5">
            Servis hesabi: <code className="bg-emerald-100 dark:bg-emerald-800 px-1.5 py-0.5 rounded">{config.service_account_email}</code>
            <button onClick={copyEmail} className="ml-2 text-emerald-700 dark:text-emerald-300 hover:text-emerald-900">
              <Copy className="w-3.5 h-3.5 inline" /> {copied ? "Kopyalandi!" : "Kopyala"}
            </button>
          </p>
          <p className="text-[10px] text-emerald-500 mt-1">
            Kaynak: {config.source === "env" ? "Environment Variable" : "Admin Paneli"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4 flex items-start gap-3">
        <WifiOff className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-200">Google Sheets Yapilandirilmamis</p>
          <p className="text-xs text-amber-600 dark:text-amber-400 mt-1">
            Google Service Account JSON ayarlanmamis. Asagidaki butona tiklayarak yapilandirabilirsiniz.
            Baglanti kayitlari saklanir, anahtar eklendigi anda otomatik calisir.
          </p>
          <button
            onClick={() => setShowSetup(!showSetup)}
            className="mt-2 px-3 py-1.5 text-xs bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors"
          >
            {showSetup ? "Kapat" : "Service Account Ayarla"}
          </button>
        </div>
      </div>

      {showSetup && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Google Service Account JSON</h3>
          <p className="text-xs text-gray-500">
            1. <a href="https://console.cloud.google.com/iam-admin/serviceaccounts" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">Google Cloud Console</a>'dan bir Service Account olusturun.
            2. JSON anahtarini indirin.
            3. Asagiya yapistirin.
            4. Sheet'leri bu service account'un email adresi ile paylasin.
          </p>
          <textarea
            value={jsonInput}
            onChange={e => setJsonInput(e.target.value)}
            placeholder='{"type": "service_account", "project_id": "...", "client_email": "...", "private_key": "..."}'
            rows={6}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-xs font-mono bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {saveError && (
            <div className="text-xs text-red-600 bg-red-50 rounded p-2">{saveError}</div>
          )}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={!jsonInput.trim() || saving}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Kaydediliyor..." : "Kaydet ve Etkinlestir"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Health Dashboard ────────────────────────────────────────────

function HealthDashboard({ status, onRefresh, refreshing }) {
  if (!status) return null;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-600" /> Portfolio Saglik Paneli
        </h2>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} /> Yenile
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard icon={Database} label="Toplam Baglanti" value={status.total || 0} color="blue" />
        <StatCard icon={Zap} label="Aktif Sync" value={status.enabled || 0} color="purple" />
        <StatCard icon={CheckCircle2} label="Saglikli" value={status.healthy || 0} color="green" />
        <StatCard icon={CheckCircle2} label="Degisiklik Yok" value={status.no_change || 0} color="gray" />
        <StatCard icon={XCircle} label="Basarisiz" value={status.failed || 0} color="red" />
        <StatCard icon={WifiOff} label="Yapilandirilmamis" value={status.not_configured || 0} color="amber" />
      </div>
    </div>
  );
}

// ── Connections Table ────────────────────────────────────────────

function ConnectionsTable({ connections, onSync, onToggle, onDelete, onViewRuns, syncing }) {
  if (!connections || connections.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 text-center">
        <Sheet className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">Henuz Sheet Baglantisi Yok</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">Otelleri Google Sheet'lerine baglamak icin "Yeni Baglanti" butonunu kullanin.</p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300">Otel</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600 dark:text-gray-300">Sheet</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-gray-300">Durum</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-gray-300">Son Sync</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-gray-300">Sync</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600 dark:text-gray-300">Islemler</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {connections.map((c) => (
              <tr key={c._id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-900 dark:text-white">{c.hotel_name || "—"}</p>
                  <p className="text-xs text-gray-400 truncate max-w-[180px]">{c.hotel_id}</p>
                </td>
                <td className="px-4 py-3">
                  <p className="text-gray-700 dark:text-gray-300 text-xs truncate max-w-[200px]" title={c.sheet_id}>{c.sheet_title || c.sheet_id}</p>
                  <p className="text-xs text-gray-400">{c.sheet_tab}</p>
                </td>
                <td className="px-4 py-3 text-center">
                  <StatusBadge status={c.last_sync_status || c.status || "active"} />
                </td>
                <td className="px-4 py-3 text-center text-xs text-gray-500 dark:text-gray-400">
                  {formatDate(c.last_sync_at)}
                </td>
                <td className="px-4 py-3 text-center">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={c.sync_enabled}
                      onChange={() => onToggle(c)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
                  </label>
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="flex items-center justify-center gap-1">
                    <button
                      onClick={() => onSync(c)}
                      disabled={syncing === c.hotel_id}
                      className="p-1.5 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 disabled:opacity-40 transition-colors"
                      title="Simdi Sync Et"
                    >
                      <RefreshCw className={`w-4 h-4 ${syncing === c.hotel_id ? "animate-spin" : ""}`} />
                    </button>
                    <button
                      onClick={() => onViewRuns(c)}
                      className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 transition-colors"
                      title="Sync Gecmisi"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete(c)}
                      className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/30 text-red-500 dark:text-red-400 transition-colors"
                      title="Baglantiyi Sil"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Connect Wizard (3 adim) ────────────────────────────────────

function ConnectWizard({ hotels, onConnect, onClose }) {
  const [step, setStep] = useState(1);
  const [selectedHotel, setSelectedHotel] = useState(null);
  const [sheetId, setSheetId] = useState("");
  const [sheetTab, setSheetTab] = useState("Sheet1");
  const [syncEnabled, setSyncEnabled] = useState(true);
  const [syncInterval, setSyncInterval] = useState(5);
  const [mapping, setMapping] = useState({});
  const [detectedMapping, setDetectedMapping] = useState({});
  const [detectedHeaders, setDetectedHeaders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");

  const availableHotels = useMemo(() =>
    (hotels || []).filter(h => !h.connected && h.name?.toLowerCase().includes(searchTerm.toLowerCase())),
    [hotels, searchTerm]
  );

  const handleConnect = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post("/admin/sheets/connect", {
        hotel_id: selectedHotel._id,
        sheet_id: sheetId,
        sheet_tab: sheetTab,
        mapping: Object.keys(mapping).length > 0 ? mapping : detectedMapping,
        sync_enabled: syncEnabled,
        sync_interval_minutes: syncInterval,
      });
      if (res.data.detected_headers) setDetectedHeaders(res.data.detected_headers);
      if (res.data.detected_mapping) setDetectedMapping(res.data.detected_mapping);
      onConnect(res.data);
    } catch (e) {
      setError(e.response?.data?.error?.message || e.message || "Baglanti hatasi");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Yeni Sheet Baglantisi</h2>
            <p className="text-xs text-gray-500 mt-0.5">Adim {step} / 3</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Steps indicator */}
        <div className="px-5 pt-4 flex items-center gap-2">
          {[1, 2, 3].map(s => (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                s <= step ? "bg-blue-600 text-white" : "bg-gray-200 dark:bg-gray-700 text-gray-500"
              }`}>{s}</div>
              <span className={`text-xs hidden sm:block ${s <= step ? "text-blue-600 font-medium" : "text-gray-400"}`}>
                {s === 1 ? "Otel Sec" : s === 2 ? "Sheet Bilgisi" : "Ayarlar"}
              </span>
              {s < 3 && <ChevronRight className="w-4 h-4 text-gray-300 hidden sm:block" />}
            </div>
          ))}
        </div>

        <div className="p-5 space-y-4">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Step 1: Select Hotel */}
          {step === 1 && (
            <div className="space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Otel ara..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div className="max-h-60 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg divide-y divide-gray-100 dark:divide-gray-700">
                {availableHotels.length === 0 ? (
                  <div className="p-4 text-sm text-gray-500 text-center">Baglanabilir otel bulunamadi</div>
                ) : availableHotels.map(h => (
                  <button
                    key={h._id}
                    onClick={() => { setSelectedHotel(h); setStep(2); }}
                    className={`w-full text-left px-4 py-3 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors ${selectedHotel?._id === h._id ? "bg-blue-50 dark:bg-blue-900/20" : ""}`}
                  >
                    <p className="font-medium text-gray-900 dark:text-white text-sm">{h.name}</p>
                    <p className="text-xs text-gray-400">{h.city}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Sheet Info */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 text-xs text-blue-700 dark:text-blue-300 flex items-start gap-2">
                <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>Otel: <strong>{selectedHotel?.name}</strong> — Sheet ID'yi URL'den kopyalayin: docs.google.com/spreadsheets/d/<strong>[SHEET_ID]</strong>/edit</span>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Google Sheet ID</label>
                <input
                  type="text"
                  value={sheetId}
                  onChange={e => setSheetId(e.target.value)}
                  placeholder="1BxiMVs0XRA5nFMdKvBdBZjg..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sayfa (Tab)</label>
                <input
                  type="text"
                  value={sheetTab}
                  onChange={e => setSheetTab(e.target.value)}
                  placeholder="Sheet1"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setStep(1)} className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">Geri</button>
                <button onClick={() => sheetId ? setStep(3) : setError("Sheet ID zorunlu")} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">Devam <ChevronRight className="w-4 h-4 inline" /></button>
              </div>
            </div>
          )}

          {/* Step 3: Settings & Confirm */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Otel:</span> <span className="font-medium text-gray-900 dark:text-white">{selectedHotel?.name}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Sheet ID:</span> <span className="font-mono text-xs text-gray-700 dark:text-gray-300 truncate max-w-[300px]">{sheetId}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Sayfa:</span> <span className="font-medium text-gray-900 dark:text-white">{sheetTab}</span></div>
              </div>

              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Otomatik Sync</label>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={syncEnabled} onChange={e => setSyncEnabled(e.target.checked)} className="sr-only peer" />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sync Araligi (dakika)</label>
                <select
                  value={syncInterval}
                  onChange={e => setSyncInterval(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                >
                  <option value={1}>1 dk</option>
                  <option value={5}>5 dk</option>
                  <option value={15}>15 dk</option>
                  <option value={30}>30 dk</option>
                  <option value={60}>60 dk</option>
                </select>
              </div>

              <div className="flex gap-2 justify-end pt-2">
                <button onClick={() => setStep(2)} className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">Geri</button>
                <button onClick={handleConnect} disabled={loading} className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 transition-colors">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />}
                  Bagla
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sync Runs Drawer ────────────────────────────────────────────

function SyncRunsDrawer({ hotelId, hotelName, onClose }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get(`/admin/sheets/runs?hotel_id=${hotelId}&limit=20`);
        setRuns(res.data || []);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    }
    load();
  }, [hotelId]);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex justify-end" onClick={onClose}>
      <div className="bg-white dark:bg-gray-800 w-full max-w-lg h-full shadow-2xl overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800 z-10">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Sync Gecmisi</h2>
            <p className="text-xs text-gray-500">{hotelName}</p>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="p-5 space-y-3">
          {loading ? (
            <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-blue-600" /></div>
          ) : runs.length === 0 ? (
            <div className="text-center py-12 text-gray-500 text-sm">Henuz sync calismadi</div>
          ) : runs.map(r => (
            <div key={r._id} className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between">
                <StatusBadge status={r.status} />
                <span className="text-xs text-gray-400">{formatDate(r.started_at)}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div><span className="text-gray-400">Okunan:</span> <span className="font-medium text-gray-700 dark:text-gray-300">{r.rows_read || 0}</span></div>
                <div><span className="text-gray-400">Degisen:</span> <span className="font-medium text-gray-700 dark:text-gray-300">{r.rows_changed || 0}</span></div>
                <div><span className="text-gray-400">Upsert:</span> <span className="font-medium text-gray-700 dark:text-gray-300">{r.upserted || 0}</span></div>
              </div>
              {r.duration_ms > 0 && <p className="text-xs text-gray-400">Sure: {r.duration_ms}ms | Trigger: {r.trigger}</p>}
              {r.errors && r.errors.length > 0 && (
                <div className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                  {r.errors.slice(0, 3).map((e, i) => <p key={i}>{e.message || JSON.stringify(e)}</p>)}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═══════════════════════════════════════════════════════════════

export default function AdminPortfolioSyncPage() {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState(null);
  const [connections, setConnections] = useState([]);
  const [availableHotels, setAvailableHotels] = useState([]);
  const [writebackStats, setWritebackStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [syncing, setSyncing] = useState(null);
  const [showWizard, setShowWizard] = useState(false);
  const [runsDrawer, setRunsDrawer] = useState(null);
  const [error, setError] = useState(null);

  const loadAll = useCallback(async (showLoader = true) => {
    if (showLoader) setLoading(true);
    setRefreshing(true);
    try {
      const [configRes, statusRes, connsRes, wbRes] = await Promise.all([
        api.get("/admin/sheets/config"),
        api.get("/admin/sheets/status"),
        api.get("/admin/sheets/connections"),
        api.get("/admin/sheets/writeback/stats").catch(() => ({ data: null })),
      ]);
      setConfig(configRes.data);
      setStatus(statusRes.data);
      setConnections(connsRes.data || []);
      setWritebackStats(wbRes.data);
    } catch (e) {
      setError(e.response?.data?.error?.message || e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const loadHotels = useCallback(async () => {
    try {
      const res = await api.get("/admin/sheets/available-hotels");
      setAvailableHotels(res.data || []);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleSync = async (conn) => {
    setSyncing(conn.hotel_id);
    try {
      await api.post(`/admin/sheets/sync/${conn.hotel_id}`);
      await loadAll(false);
    } catch (e) { console.error(e); }
    finally { setSyncing(null); }
  };

  const handleToggle = async (conn) => {
    try {
      await api.patch(`/admin/sheets/connections/${conn.hotel_id}`, {
        sync_enabled: !conn.sync_enabled,
      });
      await loadAll(false);
    } catch (e) { console.error(e); }
  };

  const handleDelete = async (conn) => {
    if (!window.confirm(`"${conn.hotel_name}" baglantisini silmek istediginizden emin misiniz?`)) return;
    try {
      await api.delete(`/admin/sheets/connections/${conn.hotel_id}`);
      await loadAll(false);
    } catch (e) { console.error(e); }
  };

  const handleConnect = async (result) => {
    setShowWizard(false);
    await loadAll(false);
  };

  const openWizard = async () => {
    await loadHotels();
    setShowWizard(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Sheet className="w-7 h-7 text-blue-600" /> Portfolio Sync Engine
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Otel sheet'lerini bagla, fiyat ve musaitlik verisini otomatik sync et
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => loadAll(false)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} /> Yenile
          </button>
          <button
            onClick={openWizard}
            className="flex items-center gap-1.5 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" /> Yeni Baglanti
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-800 dark:text-red-200">Hata</p>
            <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Config Banner */}
      <ConfigBanner config={config} onConfigSaved={() => loadAll(true)} />

      {/* Health Dashboard */}
      <HealthDashboard status={status} onRefresh={() => loadAll(false)} refreshing={refreshing} />

      {/* Write-Back Panel */}
      {writebackStats && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <ArrowRight className="w-5 h-5 text-purple-600" /> Write-Back (Sistem &rarr; Sheet)
            </h2>
            <span className="text-xs text-gray-400">Rezervasyon olusturulunca sheet'e otomatik yazilir</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-gray-900 dark:text-white">{writebackStats.queued || 0}</p>
              <p className="text-xs text-gray-500">Kuyrukta</p>
            </div>
            <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-emerald-700 dark:text-emerald-300">{writebackStats.completed || 0}</p>
              <p className="text-xs text-emerald-600">Tamamlanan</p>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-red-700 dark:text-red-300">{writebackStats.failed || 0}</p>
              <p className="text-xs text-red-600">Basarisiz</p>
            </div>
            <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-amber-700 dark:text-amber-300">{writebackStats.retry || 0}</p>
              <p className="text-xs text-amber-600">Yeniden Denenecek</p>
            </div>
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3 text-center">
              <p className="text-xl font-bold text-blue-700 dark:text-blue-300">{writebackStats.skipped || 0}</p>
              <p className="text-xs text-blue-600">Atlanan</p>
            </div>
          </div>
        </div>
      )}

      {/* Connections Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Link2 className="w-5 h-5 text-blue-600" /> Sheet Baglantilari
          <span className="text-sm font-normal text-gray-400">({connections.length})</span>
        </h2>
      </div>

      {/* Connections Table */}
      <ConnectionsTable
        connections={connections}
        onSync={handleSync}
        onToggle={handleToggle}
        onDelete={handleDelete}
        onViewRuns={(c) => setRunsDrawer(c)}
        syncing={syncing}
      />

      {/* Wizard Modal */}
      {showWizard && (
        <ConnectWizard
          hotels={availableHotels}
          onConnect={handleConnect}
          onClose={() => setShowWizard(false)}
        />
      )}

      {/* Runs Drawer */}
      {runsDrawer && (
        <SyncRunsDrawer
          hotelId={runsDrawer.hotel_id}
          hotelName={runsDrawer.hotel_name}
          onClose={() => setRunsDrawer(null)}
        />
      )}
    </div>
  );
}
