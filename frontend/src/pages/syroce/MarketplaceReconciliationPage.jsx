import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, apiErrorMessage } from "../../lib/api";
import { Calculator, Loader2, AlertTriangle, X, Download } from "lucide-react";

const firstOfMonth = () => {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
};
const today = () => new Date().toISOString().slice(0, 10);

export default function MarketplaceReconciliationPage() {
  const [period, setPeriod] = useState({ start: firstOfMonth(), end: today(), tenant_id: "" });
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const mut = useMutation({
    mutationFn: () => {
      const p = new URLSearchParams({ period_start: period.start, period_end: period.end });
      if (period.tenant_id) p.set("tenant_id", period.tenant_id);
      return api.get(`/syroce-marketplace/reconciliation?${p}`).then((r) => r.data);
    },
    onMutate: () => setError(""),
    onSuccess: (d) => setData(d),
    onError: (err) => {
      setData(null);
      setError(apiErrorMessage(err) || "Mutabakat alınamadı.");
    },
  });

  const csvMut = useMutation({
    mutationFn: async () => {
      const p = new URLSearchParams({
        period_start: period.start,
        period_end: period.end,
        format: "csv",
      });
      if (period.tenant_id) p.set("tenant_id", period.tenant_id);
      const resp = await api.get(`/syroce-marketplace/reconciliation?${p}`, { responseType: "blob" });
      const blob = new Blob([resp.data], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mutabakat_${period.start}_${period.end}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      return true;
    },
    onError: (err) => setError(apiErrorMessage(err) || "CSV indirilemedi."),
  });

  const rows = data?.rows || data?.hotels || data?.items || [];
  const totals = data?.totals || data?.summary || {};

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Calculator className="text-blue-600" /> Mutabakat
        </h1>
        <p className="text-sm text-gray-500">Otel bazında ciro, komisyon ve ödenmesi gereken net tutar.</p>
      </div>

      <form onSubmit={(e) => { e.preventDefault(); mut.mutate(); }}
        className="bg-white border rounded-lg p-4 grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Başlangıç</label>
          <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={period.start}
            onChange={(e) => setPeriod((s) => ({ ...s, start: e.target.value }))} />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Bitiş</label>
          <input type="date" className="w-full border rounded px-3 py-2 text-sm" value={period.end}
            onChange={(e) => setPeriod((s) => ({ ...s, end: e.target.value }))} />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Otel (Tenant ID, opsiyonel)</label>
          <input className="w-full border rounded px-3 py-2 text-sm font-mono text-xs" value={period.tenant_id}
            onChange={(e) => setPeriod((s) => ({ ...s, tenant_id: e.target.value }))} />
        </div>
        <div className="flex justify-end gap-2">
          <button type="submit" disabled={mut.isPending}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-4 py-2 rounded text-sm">
            {mut.isPending ? <Loader2 size={16} className="animate-spin" /> : null}
            Mutabakatı Getir
          </button>
          <button type="button" onClick={() => csvMut.mutate()} disabled={csvMut.isPending}
            className="inline-flex items-center gap-2 bg-white border hover:bg-gray-50 disabled:opacity-60 px-4 py-2 rounded text-sm">
            {csvMut.isPending ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            CSV İndir
          </button>
        </div>
      </form>

      {error && (
        <div className="flex items-start gap-2 p-3 rounded border bg-red-50 border-red-200 text-red-800">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <div className="flex-1 text-sm whitespace-pre-line">{error}</div>
          <button onClick={() => setError("")} className="opacity-60 hover:opacity-100"><X size={16} /></button>
        </div>
      )}

      {data && (
        <>
          {Object.keys(totals).length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(totals).map(([k, v]) => (
                <div key={k} className="bg-white border rounded p-3">
                  <div className="text-xs text-gray-500 uppercase">{k}</div>
                  <div className="text-lg font-semibold">
                    {typeof v === "number" ? v.toLocaleString("tr-TR", { maximumFractionDigits: 2 }) : String(v)}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="bg-white border rounded-lg overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="text-left px-3 py-2">Otel</th>
                  <th className="text-right px-3 py-2">Rezervasyon</th>
                  <th className="text-right px-3 py-2">Toplam Ciro</th>
                  <th className="text-right px-3 py-2">Komisyon</th>
                  <th className="text-right px-3 py-2">Net Ödenmesi</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr><td colSpan={5} className="text-center py-6 text-gray-500">Bu dönemde kayıt yok.</td></tr>
                )}
                {rows.map((row, i) => (
                  <tr key={row.tenant_id || row.hotel_name || i} className="border-t">
                    <td className="px-3 py-2">{row.hotel_name || row.tenant_id}</td>
                    <td className="px-3 py-2 text-right">{row.reservations_count ?? row.bookings_count ?? "-"}</td>
                    <td className="px-3 py-2 text-right">{Number(row.total_revenue ?? row.gross_total ?? 0).toFixed(2)}</td>
                    <td className="px-3 py-2 text-right text-amber-700">{Number(row.commission_total ?? row.agency_commission ?? 0).toFixed(2)}</td>
                    <td className="px-3 py-2 text-right text-emerald-700 font-semibold">{Number(row.net_to_hotel ?? row.net_total ?? 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <details className="bg-white border rounded p-3 text-xs">
            <summary className="cursor-pointer text-gray-600">Ham yanıt (debug)</summary>
            <pre className="mt-2 overflow-x-auto">{JSON.stringify(data, null, 2)}</pre>
          </details>
        </>
      )}
    </div>
  );
}
