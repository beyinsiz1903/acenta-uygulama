import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  SearchCheck,
  Sparkles,
  ShieldAlert,
} from "lucide-react";

import { api } from "../../../lib/api";

function SummaryPill({ label, tone = "slate" }) {
  const toneMap = {
    slate: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
    green: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
    amber: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    red: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
    blue: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  };

  return (
    <span className={`rounded-full px-3 py-1 text-xs font-medium ${toneMap[tone] || toneMap.slate}`}>
      {label}
    </span>
  );
}

export const SheetValidationPanel = ({ configured, serviceAccountEmail }) => {
  const [sheetId, setSheetId] = useState("");
  const [sheetTab, setSheetTab] = useState("Sheet1");
  const [writebackTab, setWritebackTab] = useState("Rezervasyonlar");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const validationTone = useMemo(() => {
    if (!result) return "slate";
    if (result.configured === false) return "amber";
    return result.valid ? "green" : "red";
  }, [result]);

  const handleValidate = async () => {
    if (!sheetId.trim()) {
      setError("Sheet ID zorunlu.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await api.post("/admin/sheets/validate-sheet", {
        sheet_id: sheetId.trim(),
        sheet_tab: sheetTab.trim() || "Sheet1",
        writeback_tab: writebackTab.trim() || "Rezervasyonlar",
      });
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.error?.message || err.message || "Doğrulama sırasında hata oluştu.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const missingLabels = result?.validation_summary?.missing_required_labels || [];
  const recognizedHeaders = result?.validation_summary?.recognized_headers || [];
  const unrecognizedHeaders = result?.validation_summary?.unrecognized_headers || [];
  const writebackValidation = result?.writeback_validation;

  return (
    <section
      className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800"
      data-testid="sheet-validation-panel"
    >
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-orange-50 p-3 text-orange-600 dark:bg-orange-900/30 dark:text-orange-300">
              <SearchCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground dark:text-white" data-testid="sheet-validation-title">
                Sheet doğrulama merkezi
              </p>
              <p className="mt-1 text-sm text-muted-foreground" data-testid="sheet-validation-subtitle">
                Sheet erişimi, sekme isimleri, zorunlu kolonlar ve write-back sekmesini kayıt öncesi kontrol edin.
              </p>
            </div>
          </div>
        </div>

        <SummaryPill
          label={configured ? "Canlı doğrulama aktif" : "Canlı doğrulama için service account gerekli"}
          tone={configured ? "green" : "amber"}
        />
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr_1fr_auto]" data-testid="sheet-validation-form">
        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">Sheet ID</span>
          <input
            value={sheetId}
            onChange={(event) => setSheetId(event.target.value)}
            placeholder="1BxiMVs0XRA5nFMdKvBdBZ..."
            className="w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-foreground outline-none transition-colors focus:border-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
            data-testid="sheet-validation-sheet-id-input"
          />
        </label>

        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">Envanter sekmesi</span>
          <input
            value={sheetTab}
            onChange={(event) => setSheetTab(event.target.value)}
            className="w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-foreground outline-none transition-colors focus:border-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
            data-testid="sheet-validation-sheet-tab-input"
          />
        </label>

        <label className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">Write-back sekmesi</span>
          <input
            value={writebackTab}
            onChange={(event) => setWritebackTab(event.target.value)}
            className="w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-foreground outline-none transition-colors focus:border-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white"
            data-testid="sheet-validation-writeback-tab-input"
          />
        </label>

        <button
          type="button"
          onClick={handleValidate}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition-transform duration-200 hover:-translate-y-0.5 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          data-testid="sheet-validation-submit-button"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {loading ? "Doğrulanıyor" : "Sheet'i doğrula"}
        </button>
      </div>

      <div className="mt-3 rounded-2xl bg-slate-50 p-4 text-sm text-slate-700 dark:bg-gray-900/70 dark:text-slate-200" data-testid="sheet-validation-helper-copy">
        {configured && serviceAccountEmail
          ? `Doğrulama hata verirse önce sheet paylaşımında ${serviceAccountEmail} hesabının Editor yetkisi olduğundan emin olun.`
          : "Kimlik bilgileri henüz tanımlı değilse bu panel yapı önerisini gösterir; canlı erişim kontrolü service account kaydedildikten sonra devreye girer."}
      </div>

      {error && (
        <div
          className="mt-4 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300"
          data-testid="sheet-validation-error"
        >
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div className="mt-5 space-y-4" data-testid="sheet-validation-result">
          <div
            className={`rounded-2xl border p-4 ${validationTone === "green" ? "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20" : validationTone === "red" ? "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20" : "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20"}`}
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="flex items-start gap-3">
                {result.valid ? (
                  <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-600 dark:text-emerald-300" />
                ) : (
                  <ShieldAlert className="mt-0.5 h-5 w-5 text-amber-600 dark:text-amber-300" />
                )}
                <div>
                  <p className="text-sm font-semibold text-foreground dark:text-white" data-testid="sheet-validation-status">
                    {result.configured === false
                      ? "Doğrulama beklemede"
                      : result.valid
                        ? "Sheet yapısı doğrulandı"
                        : "Sheet yapısında aksiyon gerekiyor"}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground" data-testid="sheet-validation-status-message">
                    {result.configured === false
                      ? result.message
                      : `${result.sheet_title || "Sheet"} için sekme ve kolon kontrolü tamamlandı.`}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <SummaryPill
                  label={result.validation_summary?.inventory_valid ? "Envanter kolonları hazır" : "Eksik zorunlu kolon var"}
                  tone={result.validation_summary?.inventory_valid ? "green" : "red"}
                />
                <SummaryPill
                  label={result.validation_summary?.writeback_valid ? "Write-back hazır" : "Write-back aksiyon bekliyor"}
                  tone={result.validation_summary?.writeback_valid ? "green" : "amber"}
                />
              </div>
            </div>
          </div>

          {result.configured !== false && (
            <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
              <div className="space-y-4">
                <div className="rounded-2xl border border-gray-200 bg-slate-50 p-4 dark:border-gray-700 dark:bg-gray-900/70">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">Sekmeler</p>
                  <div className="mt-3 flex flex-wrap gap-2" data-testid="sheet-validation-worksheets">
                    {(result.available_tabs || []).map((tab) => (
                      <SummaryPill key={tab} label={tab} tone={tab === result.sheet_tab ? "blue" : "slate"} />
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl border border-gray-200 bg-slate-50 p-4 dark:border-gray-700 dark:bg-gray-900/70">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">Algılanan başlıklar</p>
                  <div className="mt-3 flex flex-wrap gap-2" data-testid="sheet-validation-detected-headers">
                    {(result.detected_headers || []).map((header) => (
                      <SummaryPill key={header} label={header} tone={recognizedHeaders.includes(header) ? "green" : "slate"} />
                    ))}
                  </div>
                </div>

                <div className="rounded-2xl border border-gray-200 bg-slate-50 p-4 dark:border-gray-700 dark:bg-gray-900/70">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">Algılanan eşleştirme</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2" data-testid="sheet-validation-detected-mapping">
                    {Object.entries(result.detected_mapping || {}).length === 0 ? (
                      <p className="text-sm text-muted-foreground">Otomatik eşleşme bulunamadı.</p>
                    ) : (
                      Object.entries(result.detected_mapping || {}).map(([source, target]) => (
                        <div key={`${source}-${target}`} className="rounded-2xl bg-white px-3 py-2 text-sm shadow-sm dark:bg-gray-800">
                          <span className="font-medium text-foreground dark:text-white">{source}</span>
                          <span className="mx-2 text-muted-foreground">→</span>
                          <span className="text-muted-foreground">{target}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-2xl border border-gray-200 bg-slate-50 p-4 dark:border-gray-700 dark:bg-gray-900/70">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">Zorunlu kolon özeti</p>
                  <div className="mt-3 flex flex-wrap gap-2" data-testid="sheet-validation-missing-fields">
                    {missingLabels.length === 0 ? (
                      <SummaryPill label="Eksik kolon yok" tone="green" />
                    ) : (
                      missingLabels.map((label) => <SummaryPill key={label} label={label} tone="red" />)
                    )}
                  </div>
                  {unrecognizedHeaders.length > 0 && (
                    <p className="mt-3 text-sm text-muted-foreground" data-testid="sheet-validation-unrecognized-headers">
                      Tanınmayan başlıklar: {unrecognizedHeaders.join(", ")}
                    </p>
                  )}
                </div>

                <div className="rounded-2xl border border-gray-200 bg-slate-50 p-4 dark:border-gray-700 dark:bg-gray-900/70">
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">Write-back sekmesi</p>
                  <div className="mt-3 flex flex-wrap gap-2" data-testid="sheet-validation-writeback-status">
                    <SummaryPill
                      label={writebackValidation?.exists ? "Sekme bulundu" : "Sekme eksik"}
                      tone={writebackValidation?.exists ? "green" : "amber"}
                    />
                    <SummaryPill
                      label={writebackValidation?.valid ? "Başlıklar uyumlu" : "Başlık aksiyonu gerekli"}
                      tone={writebackValidation?.valid ? "green" : "amber"}
                    />
                  </div>
                  {writebackValidation?.action_required && (
                    <p className="mt-3 text-sm text-muted-foreground" data-testid="sheet-validation-writeback-action">
                      Önerilen aksiyon: {writebackValidation.action_required}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
};