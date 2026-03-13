import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, CheckCircle2, Database, Loader2, Users } from "lucide-react";

import { getDemoSeedTargets, seedDemoData } from "../lib/gtm";
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

export default function DemoSeedButton({
  buttonLabel = "Demo verisi oluştur",
  defaultTargetUserId = "",
  triggerClassName = "inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-700",
  triggerTestId = "demo-seed-open-button",
}) {
  const user = getUser();
  const canSeedDemoData = hasAnyRole(user, ["super_admin"]);
  const [show, setShow] = useState(false);
  const [mode, setMode] = useState("light");
  const [withFinance, setWithFinance] = useState(true);
  const [withCrm, setWithCrm] = useState(true);
  const [force, setForce] = useState(false);
  const [targetUserId, setTargetUserId] = useState(defaultTargetUserId || "");
  const [targets, setTargets] = useState([]);
  const [targetsLoading, setTargetsLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const activeTargets = useMemo(
    () => (targets || []).filter((item) => item.status === "active"),
    [targets]
  );

  const selectedTarget = useMemo(
    () => activeTargets.find((item) => item.id === targetUserId) || null,
    [activeTargets, targetUserId]
  );

  const countRows = useMemo(
    () => Object.entries(result?.counts || {}).map(([key, value]) => ({
      key,
      label: COUNT_LABELS[key] || key,
      value,
    })),
    [result]
  );

   
  useEffect(() => {
    if (!canSeedDemoData || !show) {
      return;
    }

    let cancelled = false;

    async function loadTargets() {
      setTargetsLoading(true);
      try {
        const items = await getDemoSeedTargets();
        if (cancelled) {
          return;
        }
        setTargets(items || []);
        const preferredTarget = defaultTargetUserId || targetUserId;
        if (preferredTarget && (items || []).some((item) => item.id === preferredTarget && item.status === "active")) {
          setTargetUserId(preferredTarget);
          return;
        }
        const firstActive = (items || []).find((item) => item.status === "active");
        setTargetUserId(firstActive?.id || "");
      } catch (targetsError) {
        if (!cancelled) {
          setError(targetsError?.message || "Hedef kullanıcı listesi alınamadı.");
        }
      } finally {
        if (!cancelled) {
          setTargetsLoading(false);
        }
      }
    }

    void loadTargets();

    return () => {
      cancelled = true;
    };
  }, [show, defaultTargetUserId]);

  if (!canSeedDemoData) {
    return null;
  }

  async function handleSeed() {
    if (!targetUserId) {
      setError("Lütfen demo verisi yüklenecek agency kullanıcısını seçin.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await seedDemoData({
        mode,
        with_finance: withFinance,
        with_crm: withCrm,
        force,
        target_user_id: targetUserId,
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
        className={triggerClassName}
        data-testid={triggerTestId}
      >
        <Database className="h-4 w-4" />
        {buttonLabel}
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

                {(result.target_user_email || result.target_agency_name) ? (
                  <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800" data-testid="demo-seed-result-target-summary">
                    <p className="font-semibold">Yüklenen hedef</p>
                    <p className="mt-1">
                      {result.target_user_name || result.target_user_email}
                      {result.target_user_email ? ` · ${result.target_user_email}` : ""}
                    </p>
                    {result.target_agency_name ? <p className="mt-1 text-xs">Acenta: {result.target_agency_name}</p> : null}
                  </div>
                ) : null}

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
                  <p className="text-sm font-medium text-slate-900" data-testid="demo-seed-target-label">Hedef agency kullanıcı</p>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" data-testid="demo-seed-target-group">
                    {targetsLoading ? (
                      <div className="flex items-center gap-2 text-sm text-slate-600" data-testid="demo-seed-target-loading">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Kullanıcılar yükleniyor...
                      </div>
                    ) : activeTargets.length === 0 ? (
                      <div className="text-sm text-rose-700" data-testid="demo-seed-target-empty">
                        Demo verisi yüklenebilecek aktif agency kullanıcısı bulunamadı.
                      </div>
                    ) : (
                      <>
                        <label className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500" htmlFor="demo-seed-target-select">
                          Kullanıcı seçin
                        </label>
                        <div className="mt-2 relative">
                          <Users className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                          <select
                            id="demo-seed-target-select"
                            value={targetUserId}
                            onChange={(event) => setTargetUserId(event.target.value)}
                            className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm text-slate-900 outline-none transition-colors focus:border-sky-500"
                            data-testid="demo-seed-target-select"
                          >
                            <option value="">Kullanıcı seçin...</option>
                            {activeTargets.map((item) => (
                              <option key={item.id} value={item.id}>
                                {item.agency_name ? `${item.agency_name} — ` : ""}
                                {item.name || item.email}
                              </option>
                            ))}
                          </select>
                        </div>
                        {selectedTarget ? (
                          <div className="mt-3 rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-700" data-testid="demo-seed-target-summary">
                            <p className="font-semibold text-slate-900">{selectedTarget.name || selectedTarget.email}</p>
                            <p className="mt-1 text-xs text-slate-500">{selectedTarget.email}</p>
                            <p className="mt-1 text-xs text-slate-500">Acenta: {selectedTarget.agency_name || "-"}</p>
                          </div>
                        ) : null}
                      </>
                    )}
                  </div>
                </div>

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
                    disabled={loading || targetsLoading || !targetUserId}
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
