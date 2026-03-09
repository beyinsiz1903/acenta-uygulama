import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, CheckCircle2, Database, Loader2 } from "lucide-react";

import { seedDemoData } from "../lib/gtm";
import { getUser } from "../lib/api";
import { hasAnyRole } from "../lib/roles";

const COUNT_LABELS = {
  hotels: "Oteller",
  tours: "Turlar",
  products: "Ürünler",
  customers: "Müşteriler",
  reservations: "Rezervasyonlar",
  inventory: "Envanter kayıtları",
  payments: "Ödemeler",
  ledger_entries: "Cari hareketleri",
  cases: "Operasyon talepleri",
  deals: "CRM fırsatları",
  tasks: "CRM görevleri",
};

export default function DemoSeedButton() {
  const user = getUser();
  const canSeedDemoData = hasAnyRole(user, ["super_admin", "admin", "tenant_admin", "agency_admin"]);
  const [show, setShow] = useState(false);
  const [mode, setMode] = useState("light");
  const [withFinance, setWithFinance] = useState(true);
  const [withCrm, setWithCrm] = useState(true);
  const [force, setForce] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const countRows = useMemo(
    () => Object.entries(result?.counts || {}).map(([key, value]) => ({
      key,
      label: COUNT_LABELS[key] || key,
      value,
    })),
    [result]
  );

  if (!canSeedDemoData) {
    return null;
  }

  async function handleSeed() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await seedDemoData({
        mode,
        with_finance: withFinance,
        with_crm: withCrm,
        force,
      });
      setResult(response);
    } catch (seedError) {
      setError(seedError?.message || "Demo verisi oluşturulamadı.");
    } finally {
      setLoading(false);
    }
  }

  function closeModal() {
    setShow(false);
    setLoading(false);
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setShow(true)}
        className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-700"
        data-testid="demo-seed-open-button"
      >
        <Database className="h-4 w-4" />
        Demo verisi oluştur
      </button>

      {show ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 p-4"
          onClick={closeModal}
          data-testid="demo-seed-modal-overlay"
        >
          <div
            className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_90px_rgba(15,23,42,0.2)]"
            onClick={(event) => event.stopPropagation()}
            data-testid="demo-seed-modal"
          >
            <div className="space-y-2">
              <h2 className="text-lg font-bold text-slate-950" data-testid="demo-seed-modal-title">Demo verisi oluştur</h2>
              <p className="text-sm leading-6 text-slate-600" data-testid="demo-seed-modal-description">
                Tek tıkla oteller, turlar, rezervasyonlar ve isterseniz finans/CRM verileri üretin.
              </p>
            </div>

            {result ? (
              <div className="mt-6 space-y-4" data-testid="demo-seed-result-state">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-center">
                  {result.already_seeded ? (
                    <>
                      <AlertCircle className="mx-auto mb-3 h-8 w-8 text-amber-500" />
                      <p className="font-semibold text-amber-700" data-testid="demo-seed-result-title">Demo verisi zaten hazır</p>
                      <p className="mt-2 text-sm text-slate-600" data-testid="demo-seed-result-subtitle">
                        Aynı tenant için mevcut demo seti bulundu. İsterseniz zorla seçeneğiyle yeniden üretebilirsiniz.
                      </p>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="mx-auto mb-3 h-8 w-8 text-emerald-600" />
                      <p className="font-semibold text-emerald-700" data-testid="demo-seed-result-title">Demo verisi oluşturuldu</p>
                      <p className="mt-2 text-sm text-slate-600" data-testid="demo-seed-result-subtitle">
                        Rezervasyonlar, turlar ve oteller kullanıma hazır. İlgili sayfaları yenileyip kontrol edebilirsiniz.
                      </p>
                    </>
                  )}
                </div>

                {countRows.length > 0 ? (
                  <div className="grid gap-2 sm:grid-cols-2" data-testid="demo-seed-result-counts">
                    {countRows.map((item, index) => (
                      <div
                        key={item.key}
                        className="rounded-2xl border border-slate-200 bg-white px-4 py-3"
                        data-testid={`demo-seed-result-count-${index + 1}`}
                      >
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{item.label}</p>
                        <p className="mt-1 text-lg font-bold text-slate-950">{item.value}</p>
                      </div>
                    ))}
                  </div>
                ) : null}

                <div className="flex flex-wrap justify-end gap-2" data-testid="demo-seed-result-actions">
                  <button
                    type="button"
                    onClick={() => {
                      setResult(null);
                      closeModal();
                    }}
                    className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                    data-testid="demo-seed-result-close-button"
                  >
                    Kapat
                  </button>
                  <Link
                    to="/app/reservations"
                    className="rounded-lg bg-slate-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-800"
                    data-testid="demo-seed-result-reservations-link"
                  >
                    Rezervasyonları gör
                  </Link>
                </div>
              </div>
            ) : (
              <div className="mt-6 space-y-5" data-testid="demo-seed-form-state">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-slate-900" data-testid="demo-seed-mode-label">Seed modu</p>
                  <div className="flex gap-2" data-testid="demo-seed-mode-group">
                    {[
                      { value: "light", label: "Hafif" },
                      { value: "full", label: "Tam" },
                    ].map((item) => (
                      <button
                        key={item.value}
                        type="button"
                        onClick={() => setMode(item.value)}
                        className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${mode === item.value ? "border-sky-600 bg-sky-600 text-white" : "border-slate-200 text-slate-700 hover:bg-slate-50"}`}
                        data-testid={`demo-seed-mode-${item.value}`}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3" data-testid="demo-seed-options-group">
                  <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700" data-testid="demo-seed-finance-option">
                    <input
                      type="checkbox"
                      checked={withFinance}
                      onChange={(event) => setWithFinance(event.target.checked)}
                      className="rounded"
                      data-testid="demo-seed-finance-checkbox"
                    />
                    Finans verilerini dahil et
                  </label>

                  <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700" data-testid="demo-seed-crm-option">
                    <input
                      type="checkbox"
                      checked={withCrm}
                      onChange={(event) => setWithCrm(event.target.checked)}
                      className="rounded"
                      data-testid="demo-seed-crm-checkbox"
                    />
                    CRM fırsat ve görevlerini dahil et
                  </label>

                  <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700" data-testid="demo-seed-force-option">
                    <input
                      type="checkbox"
                      checked={force}
                      onChange={(event) => setForce(event.target.checked)}
                      className="rounded"
                      data-testid="demo-seed-force-checkbox"
                    />
                    Mevcut demo verilerini sil ve yeniden üret
                  </label>
                </div>

                {error ? (
                  <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="demo-seed-error" role="alert">
                    {error}
                  </div>
                ) : null}

                <div className="flex flex-wrap justify-end gap-2" data-testid="demo-seed-form-actions">
                  <button
                    type="button"
                    onClick={closeModal}
                    className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                    data-testid="demo-seed-cancel-button"
                  >
                    İptal
                  </button>
                  <button
                    type="button"
                    onClick={handleSeed}
                    disabled={loading}
                    className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-60"
                    data-testid="demo-seed-submit-button"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
                    {loading ? "Oluşturuluyor..." : "Demo verisini oluştur"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}
