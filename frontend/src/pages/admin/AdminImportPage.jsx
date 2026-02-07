import React, { useState, useCallback, useEffect } from "react";
import { api } from "../../lib/api";
import {
  Upload, FileSpreadsheet, Table2, CheckCircle2, AlertTriangle,
  Download, RefreshCw, Clock, ArrowRight, X, Sheet, Link2, ChevronRight,
} from "lucide-react";

const FIELD_OPTIONS = [
  { value: "name", label: "Otel Adı *" },
  { value: "city", label: "Şehir *" },
  { value: "country", label: "Ülke" },
  { value: "description", label: "Açıklama" },
  { value: "price", label: "Fiyat" },
  { value: "stars", label: "Yıldız" },
  { value: "address", label: "Adres" },
  { value: "phone", label: "Telefon" },
  { value: "email", label: "Email" },
  { value: "image_url", label: "Resim URL" },
  { value: "ignore", label: "— Yoksay —" },
];

// ── Tab: Excel Upload (5-step wizard) ────────────────────
function ExcelUploadTab() {
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [mapping, setMapping] = useState({});
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [executing, setExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [error, setError] = useState(null);

  // Step 1: Upload
  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/admin/import/hotels/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadResult(res.data);
      // Auto-detect mapping
      const autoMap = {};
      (res.data.headers || []).forEach((h, i) => {
        const hl = h.toLowerCase().replace(/[_\s-]/g, "");
        if (hl.includes("otel") || hl.includes("hotel") || hl === "name" || hl === "ad") autoMap[String(i)] = "name";
        else if (hl.includes("şehir") || hl.includes("sehir") || hl === "city" || hl === "il") autoMap[String(i)] = "city";
        else if (hl.includes("ülke") || hl.includes("ulke") || hl === "country") autoMap[String(i)] = "country";
        else if (hl.includes("açıklama") || hl.includes("aciklama") || hl === "description") autoMap[String(i)] = "description";
        else if (hl.includes("fiyat") || hl === "price") autoMap[String(i)] = "price";
        else if (hl.includes("yıldız") || hl.includes("yildiz") || hl === "stars") autoMap[String(i)] = "stars";
        else if (hl.includes("adres") || hl === "address") autoMap[String(i)] = "address";
        else if (hl.includes("telefon") || hl === "phone") autoMap[String(i)] = "phone";
        else if (hl === "email" || hl.includes("eposta")) autoMap[String(i)] = "email";
        else if (hl.includes("resim") || hl.includes("image") || hl.includes("foto")) autoMap[String(i)] = "image_url";
        else autoMap[String(i)] = "ignore";
      });
      setMapping(autoMap);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.error?.message || "Yükleme hatası");
    }
    setUploading(false);
  };

  // Step 2→3: Validate
  const handleValidate = async () => {
    if (!uploadResult) return;
    setValidating(true);
    setError(null);
    try {
      const res = await api.post("/admin/import/hotels/validate", {
        job_id: uploadResult.job_id,
        mapping,
      });
      setValidationResult(res.data);
      setStep(3);
    } catch (err) {
      setError(err.response?.data?.error?.message || "Doğrulama hatası");
    }
    setValidating(false);
  };

  // Step 4: Execute
  const handleExecute = async () => {
    if (!uploadResult) return;
    setExecuting(true);
    setError(null);
    try {
      const res = await api.post("/admin/import/hotels/execute", {
        job_id: uploadResult.job_id,
      });
      setExecuteResult(res.data);
      setStep(4);
      // Poll for status
      pollJobStatus(uploadResult.job_id);
    } catch (err) {
      setError(err.response?.data?.error?.message || "Import hatası");
    }
    setExecuting(false);
  };

  const pollJobStatus = useCallback(async (jobId) => {
    for (let i = 0; i < 20; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      try {
        const res = await api.get(`/admin/import/jobs/${jobId}`);
        setJobStatus(res.data);
        if (res.data.status === "completed" || res.data.status === "failed") {
          setStep(5);
          break;
        }
      } catch { break; }
    }
  }, []);

  const reset = () => {
    setStep(1); setFile(null); setUploadResult(null); setMapping({});
    setValidationResult(null); setExecuteResult(null); setJobStatus(null); setError(null);
  };

  return (
    <div className="space-y-6">
      {/* Progress Steps */}
      <div className="flex items-center gap-2">
        {["Dosya", "Eşleştir", "Doğrula", "İmport", "Sonuç"].map((s, i) => (
          <React.Fragment key={s}>
            {i > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
            <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              step > i + 1 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" :
              step === i + 1 ? "bg-primary text-primary-foreground" :
              "bg-muted text-muted-foreground"
            }`}>
              {step > i + 1 ? <CheckCircle2 className="h-3 w-3" /> : <span>{i + 1}</span>}
              <span>{s}</span>
            </div>
          </React.Fragment>
        ))}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 flex items-center gap-2 text-sm text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />{error}
        </div>
      )}

      {/* Step 1: Upload */}
      {step === 1 && (
        <div className="space-y-4">
          <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-primary/50 transition-colors">
            <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-sm font-medium mb-1">CSV veya XLSX dosyanızı seçin</p>
            <p className="text-xs text-muted-foreground mb-4">Maksimum 10MB, ilk satır başlık olmalı</p>
            <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="text-sm file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-primary file:text-primary-foreground file:text-xs file:font-medium hover:file:bg-primary/90 file:cursor-pointer" />
          </div>
          {file && (
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="h-5 w-5 text-emerald-500" />
                <div>
                  <p className="text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
              </div>
              <button onClick={handleUpload} disabled={uploading}
                className="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5">
                {uploading ? <RefreshCw className="h-3 w-3 animate-spin" /> : <ArrowRight className="h-3 w-3" />}
                {uploading ? "Yükleniyor..." : "Yükle ve Devam Et"}
              </button>
            </div>
          )}
          <div className="flex items-center gap-2">
            <a href={`${process.env.REACT_APP_BACKEND_URL || ""}/admin/import/export-template`}
              className="text-xs text-primary hover:underline flex items-center gap-1" target="_blank" rel="noreferrer">
              <Download className="h-3 w-3" /> Örnek şablon indir
            </a>
          </div>
        </div>
      )}

      {/* Step 2: Column Mapping */}
      {step === 2 && uploadResult && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold">Sütun Eşleştirmesi</h3>
          <p className="text-xs text-muted-foreground">Otomatik eşleşme yapıldı. Gerekirse düzenleyin.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(uploadResult.headers || []).map((header, idx) => (
              <div key={idx} className="flex items-center gap-2 rounded-lg border p-3">
                <div className="flex-1">
                  <p className="text-xs text-muted-foreground">Dosya Sütunu</p>
                  <p className="text-sm font-medium truncate">{header}</p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
                <select value={mapping[String(idx)] || "ignore"} onChange={(e) => setMapping({ ...mapping, [String(idx)]: e.target.value })}
                  className="flex-1 text-sm rounded-lg border border-border bg-background px-2 py-1.5">
                  {FIELD_OPTIONS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
                </select>
              </div>
            ))}
          </div>
          {/* Preview */}
          {uploadResult.preview?.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground mb-2">Önizleme (ilk {Math.min(5, uploadResult.preview.length)} satır)</h4>
              <div className="overflow-x-auto rounded-lg border">
                <table className="w-full text-xs">
                  <thead><tr className="bg-muted/50">
                    {uploadResult.headers.map((h, i) => <th key={i} className="px-3 py-2 text-left font-medium">{h}</th>)}
                  </tr></thead>
                  <tbody>
                    {uploadResult.preview.slice(0, 5).map((row, ri) => (
                      <tr key={ri} className="border-t">
                        {row.map((cell, ci) => <td key={ci} className="px-3 py-1.5 truncate max-w-[200px]">{cell}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button onClick={() => setStep(1)} className="px-4 py-2 text-sm rounded-lg border hover:bg-muted">Geri</button>
            <button onClick={handleValidate} disabled={validating}
              className="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5">
              {validating ? <RefreshCw className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
              {validating ? "Doğrulanıyor..." : "Doğrula"}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Validation Results */}
      {step === 3 && validationResult && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-lg border p-3 text-center">
              <p className="text-2xl font-bold">{validationResult.total_rows}</p>
              <p className="text-xs text-muted-foreground">Toplam Satır</p>
            </div>
            <div className="rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-3 text-center">
              <p className="text-2xl font-bold text-emerald-600">{validationResult.valid_count}</p>
              <p className="text-xs text-muted-foreground">Geçerli</p>
            </div>
            <div className={`rounded-lg border p-3 text-center ${validationResult.error_count > 0 ? "border-destructive/30 bg-destructive/5" : "border-border"}`}>
              <p className={`text-2xl font-bold ${validationResult.error_count > 0 ? "text-destructive" : ""}`}>{validationResult.error_count}</p>
              <p className="text-xs text-muted-foreground">Hatalı</p>
            </div>
          </div>
          {validationResult.errors?.length > 0 && (
            <div className="rounded-lg border overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="bg-muted/50">
                  <th className="px-3 py-2 text-left">Satır</th>
                  <th className="px-3 py-2 text-left">Alan</th>
                  <th className="px-3 py-2 text-left">Hata</th>
                </tr></thead>
                <tbody>
                  {validationResult.errors.slice(0, 20).map((e, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-3 py-1.5">{e.row_number}</td>
                      <td className="px-3 py-1.5 font-medium">{e.field}</td>
                      <td className="px-3 py-1.5 text-destructive">{e.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button onClick={() => setStep(2)} className="px-4 py-2 text-sm rounded-lg border hover:bg-muted">Geri</button>
            <button onClick={handleExecute} disabled={executing || validationResult.valid_count === 0}
              className="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5">
              {executing ? <RefreshCw className="h-3 w-3 animate-spin" /> : <Upload className="h-3 w-3" />}
              {executing ? "Import ediliyor..." : `${validationResult.valid_count} Otel Import Et`}
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Processing */}
      {step === 4 && (
        <div className="text-center py-12 space-y-4">
          <RefreshCw className="h-12 w-12 mx-auto text-primary animate-spin" />
          <h3 className="text-lg font-semibold">Import Ediliyor...</h3>
          <p className="text-sm text-muted-foreground">Oteller oluşturuluyor ve resimler indiriliyor.</p>
        </div>
      )}

      {/* Step 5: Result */}
      {step === 5 && jobStatus && (
        <div className="space-y-4">
          <div className={`rounded-xl border p-6 text-center ${jobStatus.status === "completed" ? "border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30" : "border-destructive/30 bg-destructive/5"}`}>
            {jobStatus.status === "completed" ? <CheckCircle2 className="h-12 w-12 mx-auto text-emerald-500 mb-3" /> : <AlertTriangle className="h-12 w-12 mx-auto text-destructive mb-3" />}
            <h3 className="text-lg font-semibold">{jobStatus.status === "completed" ? "Import Tamamlandı!" : "Import Başarısız"}</h3>
            <div className="flex items-center justify-center gap-6 mt-4">
              <div><p className="text-2xl font-bold text-emerald-600">{jobStatus.success_count}</p><p className="text-xs text-muted-foreground">Başarılı</p></div>
              <div><p className="text-2xl font-bold text-destructive">{jobStatus.error_count}</p><p className="text-xs text-muted-foreground">Hatalı</p></div>
              <div><p className="text-2xl font-bold">{jobStatus.images_downloaded || 0}</p><p className="text-xs text-muted-foreground">Resim</p></div>
            </div>
          </div>
          <button onClick={reset} className="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90">
            Yeni Import Başlat
          </button>
        </div>
      )}
    </div>
  );
}

// ── Tab: Google Sheets (MOCKED) ────────────────────────
function GoogleSheetsTab() {
  const [config, setConfig] = useState(null);
  const [connection, setConnection] = useState(null);
  const [status, setStatus] = useState(null);
  const [sheetId, setSheetId] = useState("");
  const [worksheet, setWorksheet] = useState("Sheet1");
  const [syncEnabled, setSyncEnabled] = useState(false);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState(null);
  const [msgType, setMsgType] = useState("info");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get("/admin/import/sheet/config").then((r) => setConfig(r.data)).catch(() => {});
    api.get("/admin/import/sheet/connection").then((r) => setConnection(r.data)).catch(() => {});
    api.get("/admin/import/sheet/status").then((r) => setStatus(r.data)).catch(() => {});
  }, []);

  const copyEmail = () => {
    const email = config?.service_account_email;
    if (email) {
      navigator.clipboard.writeText(email).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
    }
  };

  const handleConnect = async () => {
    if (!sheetId.trim()) return;
    setSaving(true); setMessage(null);
    try {
      const res = await api.post("/admin/import/sheet/connect", {
        sheet_id: sheetId, worksheet_name: worksheet, sync_enabled: syncEnabled,
      });
      setConnection(res.data);
      setMessage("Bağlantı kaydedildi."); setMsgType("success");
      setSheetId("");
    } catch (err) {
      setMessage(err.response?.data?.error?.message || "Bağlantı hatası"); setMsgType("error");
    }
    setSaving(false);
  };

  const handleSync = async () => {
    setSyncing(true); setMessage(null);
    try {
      const res = await api.post("/admin/import/sheet/sync");
      if (res.data.status === "not_configured") {
        setMessage(res.data.message); setMsgType("warn");
      } else if (res.data.status === "ok") {
        setMessage(`Sync tamamlandı: ${res.data.upserts} otel güncellendi.`); setMsgType("success");
      } else if (res.data.status === "error") {
        setMessage(`Sync hatası: ${res.data.error_message}`); setMsgType("error");
      } else {
        setMessage(`Sync: ${res.data.rows_fetched} satır, ${res.data.upserts} upsert`); setMsgType("info");
      }
      api.get("/admin/import/sheet/status").then((r) => setStatus(r.data)).catch(() => {});
    } catch (err) {
      setMessage(err.response?.data?.error?.message || "Sync hatası"); setMsgType("error");
    }
    setSyncing(false);
  };

  const isConfigured = config?.configured;

  return (
    <div className="space-y-6">
      {/* Configuration Status */}
      {!isConfigured && (
        <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4 space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Google Sheets entegrasyonu henüz yapılandırılmamış
          </div>
          <p className="text-xs text-amber-600 dark:text-amber-400">
            Sistem yöneticisi <code className="bg-amber-100 dark:bg-amber-900/50 px-1 rounded">GOOGLE_SERVICE_ACCOUNT_JSON</code> env var'ını eklediğinde otomatik aktif olur.
          </p>
          <p className="text-xs text-amber-600 dark:text-amber-400">Bağlantıları şimdiden kaydedebilirsiniz — key geldiğinde plug-and-play çalışır.</p>
        </div>
      )}

      {/* Service Account Email (when configured) */}
      {isConfigured && config?.service_account_email && (
        <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-4 space-y-2">
          <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
            Sheet'i şu email'e paylaşın:
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-emerald-100 dark:bg-emerald-900/50 px-3 py-1.5 rounded text-sm font-mono break-all">
              {config.service_account_email}
            </code>
            <button onClick={copyEmail}
              className="px-3 py-1.5 text-xs rounded-lg border border-emerald-300 dark:border-emerald-700 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 flex items-center gap-1 shrink-0">
              {copied ? <CheckCircle2 className="h-3 w-3 text-emerald-600" /> : <Link2 className="h-3 w-3" />}
              {copied ? "Kopyalandı!" : "Kopyala"}
            </button>
          </div>
        </div>
      )}

      {/* Sync Status Card */}
      {status?.connected && (
        <div className="rounded-xl border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Sync Durumu</h3>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${
              status.last_sync_status === "ok" ? "bg-emerald-100 text-emerald-700" :
              status.last_sync_status === "error" ? "bg-destructive/10 text-destructive" :
              "bg-muted text-muted-foreground"
            }`}>
              {status.last_sync_status || "Henüz sync yok"}
            </span>
          </div>
          <div className="grid grid-cols-4 gap-3">
            <div className="text-center">
              <p className="text-lg font-bold">{status.stats?.last_rows || 0}</p>
              <p className="text-[10px] text-muted-foreground">Satır</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-emerald-600">{status.stats?.last_upserts || 0}</p>
              <p className="text-[10px] text-muted-foreground">Upsert</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-destructive">{status.stats?.last_errors || 0}</p>
              <p className="text-[10px] text-muted-foreground">Hata</p>
            </div>
            <div className="text-center">
              <p className="text-xs font-medium">{status.last_sync_at ? new Date(status.last_sync_at).toLocaleString("tr-TR") : "-"}</p>
              <p className="text-[10px] text-muted-foreground">Son Sync</p>
            </div>
          </div>
          {status.last_sync_error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
              {status.last_sync_error}
            </div>
          )}
          <div className="flex items-center gap-2">
            <button onClick={handleSync} disabled={syncing}
              className="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5">
              <RefreshCw className={`h-3 w-3 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "Sync ediliyor..." : "Sync Now"}
            </button>
            <span className="text-xs text-muted-foreground">
              Auto-sync: {status.sync_enabled ? "Açık (5dk)" : "Kapalı"}
            </span>
          </div>
        </div>
      )}

      {message && (
        <div className={`rounded-lg border p-3 text-sm flex items-center gap-2 ${
          msgType === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300" :
          msgType === "error" ? "border-destructive/30 bg-destructive/5 text-destructive" :
          msgType === "warn" ? "border-amber-200 bg-amber-50 text-amber-700" :
          "border-border"
        }`}>
          {msgType === "success" ? <CheckCircle2 className="h-4 w-4" /> : msgType === "error" ? <AlertTriangle className="h-4 w-4" /> : null}
          {message}
        </div>
      )}

      {/* Connect Form */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold">{connection?.connected ? "Yeni Bağlantı Ekle" : "Sheet Bağla"}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-muted-foreground">Sheet ID</label>
            <input value={sheetId} onChange={(e) => setSheetId(e.target.value)} placeholder="1BxiMVs0XRA5..." className="w-full mt-1 px-3 py-2 text-sm rounded-lg border border-border bg-background" />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Worksheet Adı</label>
            <input value={worksheet} onChange={(e) => setWorksheet(e.target.value)} className="w-full mt-1 px-3 py-2 text-sm rounded-lg border border-border bg-background" />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={syncEnabled} onChange={(e) => setSyncEnabled(e.target.checked)} className="rounded" />
          Otomatik senkronizasyon (5dk)
        </label>
        <button onClick={handleConnect} disabled={saving || !sheetId.trim()}
          className="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5">
          <Link2 className="h-3 w-3" /> {saving ? "Kaydediliyor..." : "Bağlan ve Kaydet"}
        </button>
      </div>

      {/* How-to Guide */}
      <div className="rounded-xl border border-border bg-muted/20 p-4">
        <h3 className="text-sm font-semibold mb-2">Nasıl Yapılır?</h3>
        <ol className="space-y-1 text-xs text-muted-foreground list-decimal list-inside">
          <li>Google Sheets'te otel listenizi hazırlayın (ilk satır başlık)</li>
          <li>{isConfigured ? "Yukarıdaki service account email'ine sheet'i paylaşın (Viewer yeterli)" : "Sistem yöneticisi Google API yapılandırmasını tamamladığında email görünecek"}</li>
          <li>Sheet URL'deki ID'yi kopyalayın: <code className="bg-muted px-1 rounded">docs.google.com/spreadsheets/d/<strong>SHEET_ID</strong>/edit</code></li>
          <li>Yukarıdaki forma yapıştırın ve "Bağlan" butonuna tıklayın</li>
          <li>Auto-sync açıksa sistem 5 dakikada bir otomatik günceller</li>
        </ol>
      </div>
    </div>
  );
}

// ── Tab: Import History ────────────────────────────────
function ImportHistoryTab() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/admin/import/jobs").then((r) => { setJobs(r.data || []); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const statusBadge = (status) => {
    const map = {
      uploaded: "bg-blue-100 text-blue-700",
      validated: "bg-amber-100 text-amber-700",
      processing: "bg-purple-100 text-purple-700",
      completed: "bg-emerald-100 text-emerald-700",
      failed: "bg-destructive/10 text-destructive",
    };
    return map[status] || "bg-muted text-muted-foreground";
  };

  if (loading) return <div className="text-center py-8"><RefreshCw className="h-6 w-6 animate-spin mx-auto text-muted-foreground" /></div>;

  return (
    <div>
      {jobs.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Clock className="h-10 w-10 mx-auto mb-3 opacity-50" />
          <p className="text-sm">Henüz import geçmişi yok.</p>
        </div>
      ) : (
        <div className="rounded-lg border overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="bg-muted/50">
              <th className="px-3 py-2 text-left text-xs font-medium">Dosya</th>
              <th className="px-3 py-2 text-left text-xs font-medium">Kaynak</th>
              <th className="px-3 py-2 text-left text-xs font-medium">Durum</th>
              <th className="px-3 py-2 text-right text-xs font-medium">Toplam</th>
              <th className="px-3 py-2 text-right text-xs font-medium">Başarılı</th>
              <th className="px-3 py-2 text-right text-xs font-medium">Hata</th>
              <th className="px-3 py-2 text-left text-xs font-medium">Tarih</th>
            </tr></thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} className="border-t hover:bg-muted/30">
                  <td className="px-3 py-2 text-xs font-medium">{j.filename || "-"}</td>
                  <td className="px-3 py-2 text-xs">{j.source}</td>
                  <td className="px-3 py-2"><span className={`inline-flex px-2 py-0.5 rounded-full text-[10px] font-medium ${statusBadge(j.status)}`}>{j.status}</span></td>
                  <td className="px-3 py-2 text-xs text-right">{j.total_rows}</td>
                  <td className="px-3 py-2 text-xs text-right text-emerald-600">{j.success_count}</td>
                  <td className="px-3 py-2 text-xs text-right text-destructive">{j.error_count}</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">{j.created_at ? new Date(j.created_at).toLocaleString("tr-TR") : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────
export default function AdminImportPage() {
  const [tab, setTab] = useState("excel");

  const tabs = [
    { key: "excel", label: "Excel Yükle", icon: FileSpreadsheet },
    { key: "sheets", label: "Google Sheets", icon: Sheet },
    { key: "history", label: "Import Geçmişi", icon: Clock },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <Upload className="h-6 w-6 text-muted-foreground" />
          Portföy Taşı
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Excel'den çıkmadan çalışmaya devam edin. Otel portföyünüzü hızla aktarın.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tab === t.key ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
              }`}>
              <Icon className="h-4 w-4" />{t.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {tab === "excel" && <ExcelUploadTab />}
      {tab === "sheets" && <GoogleSheetsTab />}
      {tab === "history" && <ImportHistoryTab />}
    </div>
  );
}
