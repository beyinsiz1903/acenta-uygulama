import React from "react";
import { Download, FileSpreadsheet, ListChecks, ShieldCheck } from "lucide-react";

function getDownloadHref(templateName) {
  const backendBase = process.env.REACT_APP_BACKEND_URL || "";
  const path = `/api/admin/sheets/download-template/${templateName}`;
  return backendBase ? `${backendBase}${path}` : path;
}

export const SheetTemplateCenter = ({ templates, configured, serviceAccountEmail }) => {
  const inventory = templates?.inventory_sync || {};
  const writeback = templates?.reservation_writeback || {};
  const downloads = templates?.downloadable_templates || [];

  return (
    <section
      className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]"
      data-testid="sheet-template-center"
    >
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-blue-50 p-3 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300">
            <FileSpreadsheet className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground dark:text-white" data-testid="sheet-template-title">
              Sheet şablon merkezi
            </p>
            <p className="text-sm text-muted-foreground" data-testid="sheet-template-subtitle">
              Bağlantı kurmadan önce doğru kolonları indir, ekipte paylaş ve aynı formatla ilerle.
            </p>
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-gray-200 bg-slate-50 p-4 dark:border-gray-700 dark:bg-gray-900/70">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
              Envanter sync zorunlu kolonlar
            </p>
            <div className="mt-3 flex flex-wrap gap-2" data-testid="sheet-template-required-fields">
              {(inventory.required_fields || []).map((field) => (
                <span
                  key={field.field}
                  className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm dark:bg-gray-800 dark:text-slate-200"
                >
                  {field.label}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-gray-200 bg-slate-50 p-4 dark:border-gray-700 dark:bg-gray-900/70">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
              Rezervasyon write-back başlıkları
            </p>
            <div className="mt-3 flex flex-wrap gap-2" data-testid="sheet-template-writeback-headers">
              {(writeback.headers || []).slice(0, 6).map((header) => (
                <span
                  key={header}
                  className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm dark:bg-gray-800 dark:text-slate-200"
                >
                  {header}
                </span>
              ))}
              {(writeback.headers || []).length > 6 && (
                <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-500 shadow-sm dark:bg-gray-800 dark:text-slate-300">
                  +{writeback.headers.length - 6} alan daha
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          {downloads.map((template) => (
            <a
              key={template.name}
              href={getDownloadHref(template.name)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-transform duration-200 hover:-translate-y-0.5 hover:bg-slate-700 dark:border-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
              data-testid={`sheet-template-download-${template.name}`}
            >
              <Download className="h-4 w-4" />
              {template.label}
            </a>
          ))}
        </div>

        <div
          className="mt-5 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-200"
          data-testid="sheet-template-incoming-reservation-note"
        >
          Rezervasyonları sheet'ten içeri almak için <strong>Rezervasyonlar</strong> sekmesinde
          <code className="mx-1 rounded bg-white px-1.5 py-0.5 text-xs dark:bg-gray-800">Kayit Tipi = incoming_reservation</code>
          veya <code className="mx-1 rounded bg-white px-1.5 py-0.5 text-xs dark:bg-gray-800">external_reservation</code>
          kullanın. Sync sonrası kayıt ilgili otelin rezervasyon akışına düşer.
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-emerald-50 p-3 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-300">
            <ListChecks className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground dark:text-white" data-testid="sheet-checklist-title">
              Kurulum checklist
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Service account hazır olduğunda doğrulama kartı ve bağlantı kaydetme akışı aynı standartla çalışır.
            </p>
          </div>
        </div>

        <div className="mt-4 space-y-3" data-testid="sheet-checklist-items">
          {(templates?.checklist || []).map((item, index) => (
            <div key={`${item}-${index}`} className="flex items-start gap-3 rounded-2xl bg-slate-50 p-3 dark:bg-gray-900/70">
              <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-white text-xs font-semibold text-slate-700 shadow-sm dark:bg-gray-800 dark:text-slate-200">
                {index + 1}
              </div>
              <p className="text-sm text-slate-700 dark:text-slate-200">{item}</p>
            </div>
          ))}
        </div>

        <div
          className={`mt-5 rounded-2xl border p-4 ${configured ? "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-900/20" : "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20"}`}
          data-testid="sheet-template-config-status"
        >
          <div className="flex items-start gap-3">
            <ShieldCheck className={`mt-0.5 h-5 w-5 ${configured ? "text-emerald-600 dark:text-emerald-300" : "text-amber-600 dark:text-amber-300"}`} />
            <div>
              <p className={`text-sm font-semibold ${configured ? "text-emerald-800 dark:text-emerald-200" : "text-amber-800 dark:text-amber-200"}`}>
                {configured ? "Service account aktif" : "Service account bekleniyor"}
              </p>
              <p className={`mt-1 text-sm ${configured ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-300"}`}>
                {configured && serviceAccountEmail
                  ? `Paylaşım yaparken şu hesabı Editor olarak ekleyin: ${serviceAccountEmail}`
                  : "JSON kaydedilmeden canlı doğrulama yapılamaz; ama şablonları indirip sheet yapısını hazır tutabilirsiniz."}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};