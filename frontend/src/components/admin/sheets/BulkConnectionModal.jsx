import React, { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Download,
  FileSpreadsheet,
  Loader2,
  Link2,
  Table2,
  Upload,
  X,
} from "lucide-react";
import { api } from "../../../lib/api";
import { toast } from "sonner";

const SOURCE_OPTIONS = [
  { key: "upload", label: "Dosya Yükle", icon: Upload },
  { key: "paste", label: "Tablo Yapıştır", icon: Table2 },
  { key: "master_sheet", label: "Master Google Sheet", icon: Link2 },
];

function getScopeMeta(scope) {
  if (scope === "agency") {
    return {
      title: "Toplu Acenta Bağlantısı",
      subtitle: "hotel_id + agency_id bazlı bağlantıları tek seferde önizleyip kaydedin.",
      columns: ["hotel_id", "agency_id", "sheet_id", "sheet_tab", "writeback_tab", "sync_enabled", "sync_interval_minutes"],
      templateHref: `${process.env.REACT_APP_BACKEND_URL || ""}/api/admin/sheets/bulk-template/agency`,
      defaultMasterTab: "AgencyConnections",
    };
  }

  return {
    title: "Toplu Otel Bağlantısı",
    subtitle: "300+ otel için bağlantıları tek tabloda önizleyip kaydedin.",
    columns: ["hotel_id", "sheet_id", "sheet_tab", "writeback_tab", "sync_enabled", "sync_interval_minutes"],
    templateHref: `${process.env.REACT_APP_BACKEND_URL || ""}/api/admin/sheets/bulk-template/hotel`,
    defaultMasterTab: "Connections",
  };
}

function SummaryCard({ label, value, tone = "slate", dataTestId }) {
  const toneClass = {
    slate: "border-slate-200 bg-slate-50 text-slate-800",
    green: "border-emerald-200 bg-emerald-50 text-emerald-800",
    red: "border-red-200 bg-red-50 text-red-800",
  };

  return (
    <div className={`rounded-2xl border px-4 py-3 ${toneClass[tone] || toneClass.slate}`} data-testid={dataTestId}>
      <p className="text-xs uppercase tracking-[0.18em] opacity-75">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

export const BulkConnectionModal = ({ scope, open, onClose, onCompleted }) => {
  const meta = useMemo(() => getScopeMeta(scope), [scope]);
  const [source, setSource] = useState("upload");
  const [file, setFile] = useState(null);
  const [rawText, setRawText] = useState("");
  const [masterSheetId, setMasterSheetId] = useState("");
  const [masterSheetTab, setMasterSheetTab] = useState(meta.defaultMasterTab);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [applyLoading, setApplyLoading] = useState(false);
  const [error, setError] = useState("");
  const [previewResult, setPreviewResult] = useState(null);

  useEffect(() => {
    if (!open) return;
    setSource("upload");
    setFile(null);
    setRawText("");
    setMasterSheetId("");
    setMasterSheetTab(meta.defaultMasterTab);
    setPreviewLoading(false);
    setApplyLoading(false);
    setError("");
    setPreviewResult(null);
  }, [open, meta.defaultMasterTab]);

  if (!open) return null;

  const previewSummary = previewResult?.summary || { total_rows: 0, valid_rows: 0, invalid_rows: 0 };
  const validRows = previewResult?.valid_rows || [];
  const invalidRows = previewResult?.invalid_rows || [];
  const canApply = validRows.length > 0 && previewResult?.configured !== false;

  const handlePreview = async () => {
    setPreviewLoading(true);
    setError("");
    setPreviewResult(null);
    try {
      let response;
      if (source === "upload") {
        if (!file) {
          setError("Lütfen bir CSV/XLSX dosyası seçin.");
          setPreviewLoading(false);
          return;
        }
        const formData = new FormData();
        formData.append("scope", scope);
        formData.append("file", file);
        response = await api.post("/admin/sheets/bulk/preview-upload", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else if (source === "paste") {
        if (!rawText.trim()) {
          setError("Yapıştırılacak tablo içeriği zorunlu.");
          setPreviewLoading(false);
          return;
        }
        response = await api.post("/admin/sheets/bulk/preview-text", {
          scope,
          raw_text: rawText,
        });
      } else {
        if (!masterSheetId.trim()) {
          setError("Master sheet ID zorunlu.");
          setPreviewLoading(false);
          return;
        }
        response = await api.post("/admin/sheets/bulk/preview-master-sheet", {
          scope,
          sheet_id: masterSheetId.trim(),
          sheet_tab: masterSheetTab.trim() || meta.defaultMasterTab,
        });
      }

      setPreviewResult(response.data);
      if (response.data?.configured === false) {
        toast.error(response.data?.message || "Master sheet önizlemesi için Google erişimi gerekli");
      } else {
        toast.success(`Önizleme hazır: ${response.data?.summary?.valid_rows || 0} geçerli satır`);
      }
    } catch (err) {
      const message = err.response?.data?.error?.message || err.message || "Önizleme oluşturulamadı";
      setError(message);
      toast.error(message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleApply = async () => {
    if (!canApply) return;
    setApplyLoading(true);
    setError("");
    try {
      const response = await api.post("/admin/sheets/bulk/execute", {
        scope,
        rows: validRows,
      });
      const createdCount = response.data?.created_count || 0;
      const errorCount = response.data?.error_count || 0;
      toast.success(`${createdCount} bağlantı oluşturuldu${errorCount ? ` · ${errorCount} satır hata verdi` : ""}`);
      if (onCompleted) {
        await onCompleted(response.data);
      }
      onClose();
    } catch (err) {
      const message = err.response?.data?.error?.message || err.message || "Toplu kayıt başarısız";
      setError(message);
      toast.error(message);
    } finally {
      setApplyLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/55 p-4" onClick={onClose} data-testid={`portfolio-sync-bulk-${scope}-overlay`}>
      <div
        className="mx-auto flex h-full max-w-6xl flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        data-testid={`portfolio-sync-bulk-${scope}-modal`}
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500" data-testid={`portfolio-sync-bulk-${scope}-eyebrow`}>
              Bulk Connection Studio
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950" data-testid={`portfolio-sync-bulk-${scope}-title`}>
              {meta.title}
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600" data-testid={`portfolio-sync-bulk-${scope}-subtitle`}>
              {meta.subtitle}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-slate-200 p-2 text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900"
            data-testid={`portfolio-sync-bulk-${scope}-close-button`}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <div className="grid gap-5 lg:grid-cols-[0.92fr_1.08fr]">
            <div className="space-y-5">
              <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-4" data-testid={`portfolio-sync-bulk-${scope}-source-card`}>
                <div className="flex flex-wrap gap-2">
                  {SOURCE_OPTIONS.map(({ key, label, icon: Icon }) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setSource(key)}
                      className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors ${source === key ? "bg-slate-900 text-white" : "bg-white text-slate-700 hover:bg-slate-100"}`}
                      data-testid={`portfolio-sync-bulk-${scope}-source-${key}`}
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                    </button>
                  ))}
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <a
                    href={meta.templateHref}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100"
                    data-testid={`portfolio-sync-bulk-${scope}-download-template`}
                  >
                    <Download className="h-4 w-4" /> Şablon indir
                  </a>
                  <p className="text-xs leading-6 text-slate-500" data-testid={`portfolio-sync-bulk-${scope}-columns-note`}>
                    Beklenen kolonlar: {meta.columns.join(", ")}
                  </p>
                </div>
              </div>

              {source === "upload" && (
                <div className="rounded-[24px] border border-slate-200 bg-white p-5" data-testid={`portfolio-sync-bulk-${scope}-upload-panel`}>
                  <div className="flex items-start gap-3">
                    <div className="rounded-2xl bg-blue-50 p-3 text-blue-600">
                      <FileSpreadsheet className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-950">CSV / Excel yükleme</p>
                      <p className="mt-1 text-sm text-slate-600">CSV, XLSX ve XLS dosyaları desteklenir. İlk satır başlık olmalı.</p>
                    </div>
                  </div>
                  <div className="mt-4 rounded-2xl border border-dashed border-slate-300 p-4">
                    <input
                      type="file"
                      accept=".csv,.xlsx,.xls"
                      onChange={(event) => setFile(event.target.files?.[0] || null)}
                      data-testid={`portfolio-sync-bulk-${scope}-file-input`}
                    />
                    {file && (
                      <p className="mt-3 text-sm text-slate-700" data-testid={`portfolio-sync-bulk-${scope}-file-name`}>
                        Seçilen dosya: <strong>{file.name}</strong>
                      </p>
                    )}
                  </div>
                </div>
              )}

              {source === "paste" && (
                <div className="rounded-[24px] border border-slate-200 bg-white p-5" data-testid={`portfolio-sync-bulk-${scope}-paste-panel`}>
                  <p className="text-sm font-semibold text-slate-950">Tablo yapıştır</p>
                  <p className="mt-1 text-sm text-slate-600">Excel / Google Sheets satırlarını doğrudan yapıştırabilirsiniz.</p>
                  <textarea
                    value={rawText}
                    onChange={(event) => setRawText(event.target.value)}
                    rows={12}
                    placeholder={meta.columns.join("\t")}
                    className="mt-4 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-xs text-slate-800 outline-none transition-colors focus:border-blue-500"
                    data-testid={`portfolio-sync-bulk-${scope}-paste-input`}
                  />
                </div>
              )}

              {source === "master_sheet" && (
                <div className="rounded-[24px] border border-slate-200 bg-white p-5" data-testid={`portfolio-sync-bulk-${scope}-master-sheet-panel`}>
                  <p className="text-sm font-semibold text-slate-950">Master Google Sheet</p>
                  <p className="mt-1 text-sm text-slate-600">Tek sheet içinde 300 otelin bağlantı satırlarını tutup önizleyebilirsiniz.</p>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <label className="space-y-2">
                      <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sheet ID</span>
                      <input
                        value={masterSheetId}
                        onChange={(event) => setMasterSheetId(event.target.value)}
                        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500"
                        placeholder="1BxiMVs0XRA5nFMdKvBdBZ..."
                        data-testid={`portfolio-sync-bulk-${scope}-master-sheet-id-input`}
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Sekme</span>
                      <input
                        value={masterSheetTab}
                        onChange={(event) => setMasterSheetTab(event.target.value)}
                        className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition-colors focus:border-blue-500"
                        placeholder={meta.defaultMasterTab}
                        data-testid={`portfolio-sync-bulk-${scope}-master-sheet-tab-input`}
                      />
                    </label>
                  </div>
                </div>
              )}

              {error && (
                <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" data-testid={`portfolio-sync-bulk-${scope}-error`}>
                  {error}
                </div>
              )}

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={handlePreview}
                  disabled={previewLoading}
                  className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-slate-700 disabled:opacity-60"
                  data-testid={`portfolio-sync-bulk-${scope}-preview-button`}
                >
                  {previewLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Table2 className="h-4 w-4" />}
                  {previewLoading ? "Önizleme hazırlanıyor" : "Önizle ve doğrula"}
                </button>
                <button
                  type="button"
                  onClick={handleApply}
                  disabled={!canApply || applyLoading}
                  className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
                  data-testid={`portfolio-sync-bulk-${scope}-apply-button`}
                >
                  {applyLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  {applyLoading ? "Kaydediliyor" : `Geçerli satırları kaydet (${validRows.length})`}
                </button>
              </div>
            </div>

            <div className="space-y-5">
              <div className="grid gap-3 md:grid-cols-3">
                <SummaryCard label="Toplam satır" value={previewSummary.total_rows} dataTestId={`portfolio-sync-bulk-${scope}-summary-total`} />
                <SummaryCard label="Geçerli" value={previewSummary.valid_rows} tone="green" dataTestId={`portfolio-sync-bulk-${scope}-summary-valid`} />
                <SummaryCard label="Hatalı" value={previewSummary.invalid_rows} tone="red" dataTestId={`portfolio-sync-bulk-${scope}-summary-invalid`} />
              </div>

              {previewResult?.configured === false && (
                <div className="rounded-[24px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800" data-testid={`portfolio-sync-bulk-${scope}-master-sheet-warning`}>
                  {previewResult?.message || "Master sheet önizlemesi için Google Service Account JSON gerekli."}
                </div>
              )}

              <div className="rounded-[24px] border border-slate-200 bg-white p-5" data-testid={`portfolio-sync-bulk-${scope}-valid-rows-card`}>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-950">Geçerli satırlar</p>
                    <p className="mt-1 text-sm text-slate-600">İlk 12 geçerli satır aşağıda listelenir.</p>
                  </div>
                  <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700" data-testid={`portfolio-sync-bulk-${scope}-valid-count-badge`}>
                    {validRows.length} satır
                  </span>
                </div>

                {validRows.length === 0 ? (
                  <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-6 text-sm text-slate-500" data-testid={`portfolio-sync-bulk-${scope}-valid-empty-state`}>
                    Henüz önizleme oluşturulmadı.
                  </div>
                ) : (
                  <div className="mt-4 overflow-x-auto rounded-2xl border border-slate-200">
                    <table className="w-full text-sm" data-testid={`portfolio-sync-bulk-${scope}-valid-table`}>
                      <thead className="bg-slate-50 text-left text-slate-500">
                        <tr>
                          <th className="px-3 py-2">#</th>
                          {meta.columns.slice(0, 5).map((column) => (
                            <th key={column} className="px-3 py-2">{column}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {validRows.slice(0, 12).map((row) => (
                          <tr key={`valid-${row.row_number}`} className="border-t border-slate-100" data-testid={`portfolio-sync-bulk-${scope}-valid-row-${row.row_number}`}>
                            <td className="px-3 py-2">{row.row_number}</td>
                            {meta.columns.slice(0, 5).map((column) => (
                              <td key={`${row.row_number}-${column}`} className="px-3 py-2 text-slate-700">{String(row[column] ?? "-")}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="rounded-[24px] border border-slate-200 bg-white p-5" data-testid={`portfolio-sync-bulk-${scope}-invalid-rows-card`}>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-950">Hatalı satırlar</p>
                    <p className="mt-1 text-sm text-slate-600">Satır bazlı hataları düzeltip tekrar önizleme alabilirsiniz.</p>
                  </div>
                  <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-700" data-testid={`portfolio-sync-bulk-${scope}-invalid-count-badge`}>
                    {invalidRows.length} satır
                  </span>
                </div>

                {invalidRows.length === 0 ? (
                  <div className="mt-4 rounded-2xl bg-emerald-50 px-4 py-6 text-sm text-emerald-700" data-testid={`portfolio-sync-bulk-${scope}-invalid-empty-state`}>
                    Önizlemede hata bulunmadı.
                  </div>
                ) : (
                  <div className="mt-4 space-y-3" data-testid={`portfolio-sync-bulk-${scope}-invalid-list`}>
                    {invalidRows.slice(0, 10).map((item) => (
                      <div key={`invalid-${item.row_number}`} className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3" data-testid={`portfolio-sync-bulk-${scope}-invalid-row-${item.row_number}`}>
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="mt-0.5 h-4 w-4 text-red-600" />
                          <div>
                            <p className="text-sm font-semibold text-red-900">Satır {item.row_number}</p>
                            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-red-700">
                              {(item.errors || []).map((errorItem, index) => (
                                <li key={`${item.row_number}-${index}`}>{errorItem.message}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};