import React, { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { api, apiErrorMessage } from "../../lib/api";

export default function B2BAccountPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const resp = await api.get("/b2b/account/summary");
        setData(resp.data);
      } catch (err) {
        setError(apiErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-semibold">Cari Hesap</h1>
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Cari özet yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-semibold">Cari Hesap</h1>
        <div className="rounded-2xl border bg-card shadow-sm p-6 text-sm text-red-600">
          Cari özet yüklenemedi. Lütfen tekrar deneyin.
          <div className="mt-2 text-xs text-muted-foreground">{error}</div>
        </div>
      </div>
    );
  }

  const currency = data?.currency || "";
  const totalDebit = data?.total_debit || 0;
  const totalCredit = data?.total_credit || 0;
  const net = data?.net || 0;
  const recent = data?.recent || [];

  const exposureEur = data?.exposure_eur ?? null;
  const creditLimit = data?.credit_limit ?? null;
  const softLimit = data?.soft_limit ?? null;
  const paymentTerms = data?.payment_terms ?? null;
  const status = data?.status || "ok";
  const aging = data?.aging || { age_0_30: 0, age_31_60: 0, age_61_plus: 0 };

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Cari Hesap</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <KpiCard label="Toplam Borç" value={totalDebit} currency={currency} />
        <KpiCard label="Toplam Alacak" value={totalCredit} currency={currency} />
        <KpiCard label="Net Bakiye" value={net} currency={currency} emphasize />
      </div>

      <div className="space-y-3">
        <h2 className="text-sm font-semibold">Son Hareketler</h2>
        {recent.length === 0 ? (
          <div className="rounded-2xl border bg-card shadow-sm p-6 text-sm text-muted-foreground">
            Henüz cari hareket bulunmuyor.
            <div className="text-xs mt-1">
              İlk rezervasyon / ödeme sonrası hareketler burada görünecek.
            </div>
          </div>
        ) : (
          <div className="rounded-2xl border bg-card shadow-sm divide-y">
            {recent.map((m) => (
              <div key={m.id} className="p-3 flex items-center justify-between gap-3 text-sm">
                <div className="space-y-0.5">
                  <div className="text-xs text-muted-foreground">
                    {m.date ? new Date(m.date).toLocaleString() : ""}
                  </div>
                  <div className="text-sm font-medium">{m.description}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {m.type} · {m.direction === "credit" ? "Alacak" : "Borç"}
                  </div>
                </div>
                <div className="text-sm font-semibold text-right min-w-[100px]">
                  {m.direction === "credit" ? "+" : "-"}
                  {m.amount?.toFixed ? m.amount.toFixed(2) : m.amount} {m.currency || currency}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function KpiCard({ label, value, currency, emphasize }) {
  const isNegative = value < 0;
  const formatted = (typeof value === "number" ? value.toFixed(2) : value) + (currency ? ` ${currency}` : "");

  return (
    <div className="rounded-2xl border bg-card shadow-sm p-4 space-y-1">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div
        className={
          "text-lg font-semibold" +
          (emphasize ? (isNegative ? " text-rose-600" : " text-emerald-600") : "")
        }
      >
        {formatted}
      </div>
    </div>
  );
}