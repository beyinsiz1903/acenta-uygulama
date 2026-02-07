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
  const [sheetId, setSheetId] = useState("");
  const [worksheet, setWorksheet] = useState("Sheet1");
  const [syncEnabled, setSyncEnabled] = useState(false);
  const [saving, setSaving] = useState(false);
  const [connections, setConnections] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    api.get("/admin/import/sheet/connections").then((r) => setConnections(r.data || [])).catch(() => {});
  }, []);

  const handleConnect = async () => {
    if (!sheetId.trim()) return;
    setSaving(true);
    try {
      const res = await api.post("/admin/import/sheet/connect", {
        sheet_id: sheetId, worksheet_name: worksheet, sync_enabled: syncEnabled,
      });
      setConnections((prev) => [res.data, ...prev]);
      setMessage("Bağlantı kaydedildi.");
      setSheetId("");
    } catch (err) {
      setMessage(err.response?.data?.error?.message || "Hata");
    }
    setSaving(false);
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await api.post("/admin/import/sheet/sync");
      setMessage(res.data.message);
    } catch (err) {
      setMessage(err.response?.data?.error?.message || "Sync hatası");
    }
    setSyncing(false);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-3 flex items-center gap-2 text-sm text-amber-700 dark:text-amber-300">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        Google Sheets senkronizasyonu şu an MOCK modunda. Gerçek API key entegrasyonu için admin ile iletişime geçin.
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold">Yeni Bağlantı</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-muted-foreground">Sheet ID</label>
            <input value={sheetId} onChange={(e) => setSheetId(e.target.value)} placeholder="1BxiMVs0XRA..." className="w-full mt-1 px-3 py-2 text-sm rounded-lg border border-border bg-background" />
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
          <Link2 className="h-3 w-3" /> {saving ? "Kaydediliyor..." : "Bağlan"}
        </button>
      </div>

      {message && (
        <div className="rounded-lg border p-3 text-sm">{message}</div>
      )}

      {connections.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-2">Bağlantılar</h3>
          <div className="space-y-2">
            {connections.map((c) => (
              <div key={c.id} className="rounded-lg border p-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sheet className="h-4 w-4 text-emerald-500" />
                  <div>
                    <p className="text-sm font-medium">{c.sheet_id?.substring(0, 20)}...</p>
                    <p className="text-xs text-muted-foreground">{c.worksheet_name} · {c.status}</p>
                  </div>
                </div>
                <button onClick={handleSync} disabled={syncing}
                  className="px-3 py-1 text-xs rounded-lg border hover:bg-muted flex items-center gap-1">
                  <RefreshCw className={`h-3 w-3 ${syncing ? "animate-spin" : ""}`} /> Sync
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
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
