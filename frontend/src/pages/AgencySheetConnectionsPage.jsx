import React, { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import {
  FileSpreadsheet, Plus, Trash2, Loader2,
  CheckCircle2, AlertCircle, Hotel, Link2,
  ExternalLink, RefreshCw, XCircle, Clock,
  WifiOff, Zap,
} from "lucide-react";

function formatDate(d) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString("tr-TR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return "—"; }
}

export default function AgencySheetConnectionsPage() {
  const [connections, setConnections] = useState([]);
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Form state
  const [selectedHotel, setSelectedHotel] = useState("");
  const [sheetId, setSheetId] = useState("");
  const [sheetTab, setSheetTab] = useState("Sheet1");
  const [writebackTab, setWritebackTab] = useState("Rezervasyonlar");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [connRes, hotelRes] = await Promise.all([
        api.get("/agency/sheets/connections"),
        api.get("/agency/sheets/hotels"),
      ]);
      setConnections(connRes.data || []);
      setHotels(hotelRes.data || []);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
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
    } finally {
      setSaving(false);
    }
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
          {connections.map((conn) => (
            <div
              key={conn._id}
              className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between"
              data-testid={`connection-${conn._id}`}
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Hotel className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <div className="font-medium text-sm">{conn.hotel_name || conn.hotel_id}</div>
                  <div className="text-xs text-muted-foreground mt-0.5 flex items-center gap-3">
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
                    <span>Olusturulma: {formatDate(conn.created_at)}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                    conn.status === "active"
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                  }`}
                  data-testid={`status-${conn._id}`}
                >
                  {conn.status === "active" ? <CheckCircle2 className="w-3 h-3" /> : null}
                  {conn.status === "active" ? "Aktif" : conn.status || "—"}
                </span>
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
          ))}
        </div>
      )}
    </div>
  );
}
