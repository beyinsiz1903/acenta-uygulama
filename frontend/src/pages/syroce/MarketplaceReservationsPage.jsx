import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, apiErrorMessage } from "../../lib/api";
import { CalendarCheck, Eye, X, Trash2, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";

function StatusBadge({ status }) {
  const map = {
    confirmed: "bg-emerald-100 text-emerald-800",
    cancelled: "bg-red-100 text-red-800",
    completed: "bg-blue-100 text-blue-800",
  };
  return <span className={`px-2 py-0.5 text-xs rounded ${map[status] || "bg-gray-100 text-gray-700"}`}>{status || "-"}</span>;
}

function Banner({ kind, children, onClose }) {
  const palette = kind === "error" ? "bg-red-50 border-red-200 text-red-800" : "bg-emerald-50 border-emerald-200 text-emerald-800";
  const Icon = kind === "error" ? AlertTriangle : CheckCircle2;
  return (
    <div className={`flex items-start gap-2 p-3 rounded border ${palette}`}>
      <Icon size={18} className="mt-0.5 shrink-0" />
      <div className="flex-1 text-sm whitespace-pre-line">{children}</div>
      {onClose && <button onClick={onClose} className="opacity-60 hover:opacity-100"><X size={16} /></button>}
    </div>
  );
}

export default function MarketplaceReservationsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [detail, setDetail] = useState(null);
  const [cancelTarget, setCancelTarget] = useState(null);
  const [cancelReason, setCancelReason] = useState("agency_request");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["marketplace-reservations", statusFilter],
    queryFn: () => {
      const p = new URLSearchParams();
      if (statusFilter) p.set("status", statusFilter);
      return api.get(`/syroce-marketplace/reservations?${p}`).then((r) => r.data);
    },
  });

  const detailMut = useMutation({
    mutationFn: (id) => api.get(`/syroce-marketplace/reservations/${id}`).then((r) => r.data),
    onSuccess: (d) => setDetail(d),
    onError: (err) => setError(apiErrorMessage(err) || "Detay alınamadı."),
  });

  const cancelMut = useMutation({
    mutationFn: ({ id, reason }) => api.delete(`/syroce-marketplace/reservations/${id}`, { data: { reason } }).then((r) => r.data),
    onSuccess: () => {
      setSuccess("Rezervasyon iptal edildi.");
      setCancelTarget(null);
      qc.invalidateQueries({ queryKey: ["marketplace-reservations"] });
    },
    onError: (err) => setError(apiErrorMessage(err) || "İptal başarısız."),
  });

  const items = data?.items || [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <CalendarCheck className="text-blue-600" /> Rezervasyonlarım
          </h1>
          <p className="text-sm text-gray-500">Syroce Marketplace üzerinden yapılan rezervasyonlar.</p>
        </div>
        <div className="flex gap-2">
          <select className="border rounded px-3 py-2 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">Tümü</option>
            <option value="confirmed">Onaylı</option>
            <option value="cancelled">İptal</option>
            <option value="completed">Tamamlandı</option>
          </select>
        </div>
      </div>

      {error && <Banner kind="error" onClose={() => setError("")}>{error}</Banner>}
      {success && <Banner kind="success" onClose={() => setSuccess("")}>{success}</Banner>}

      <div className="bg-white border rounded-lg overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="text-left px-3 py-2">PNR</th>
              <th className="text-left px-3 py-2">Onay Kodu</th>
              <th className="text-left px-3 py-2">Otel</th>
              <th className="text-left px-3 py-2">Misafir</th>
              <th className="text-left px-3 py-2">Tarih</th>
              <th className="text-right px-3 py-2">Tutar</th>
              <th className="text-center px-3 py-2">Durum</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={8} className="text-center py-6 text-gray-500"><Loader2 className="inline animate-spin" size={16} /> Yükleniyor...</td></tr>
            )}
            {!isLoading && items.length === 0 && (
              <tr><td colSpan={8} className="text-center py-8 text-gray-500">Henüz rezervasyon yok.</td></tr>
            )}
            {items.map((r) => (
              <tr key={r.id} className="border-t hover:bg-gray-50">
                <td className="px-3 py-2 font-mono text-xs">{r.external_reference}</td>
                <td className="px-3 py-2 font-mono text-xs">{r.syroce_confirmation_code || "-"}</td>
                <td className="px-3 py-2">{r.syroce_hotel_name || "-"}<div className="text-xs text-gray-500">{r.room_type}</div></td>
                <td className="px-3 py-2">{r.guest_name}<div className="text-xs text-gray-500">{r.guest_email}</div></td>
                <td className="px-3 py-2 text-xs">{r.check_in} → {r.check_out}</td>
                <td className="px-3 py-2 text-right">{r.total_amount != null ? `${Number(r.total_amount).toFixed(2)} TRY` : "-"}</td>
                <td className="px-3 py-2 text-center"><StatusBadge status={r.status} /></td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  <button onClick={() => detailMut.mutate(r.id)} className="text-blue-600 hover:bg-blue-50 p-1 rounded" title="Detay">
                    <Eye size={16} />
                  </button>
                  {r.status !== "cancelled" && (
                    <button onClick={() => { setCancelTarget(r); setCancelReason("agency_request"); }} className="text-red-600 hover:bg-red-50 p-1 rounded ml-1" title="İptal Et">
                      <Trash2 size={16} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Detail modal */}
      {detail && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg w-full max-w-2xl max-h-[80vh] overflow-y-auto shadow-xl">
            <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-white">
              <h3 className="font-semibold">Rezervasyon Detayı</h3>
              <button onClick={() => setDetail(null)} className="text-gray-400 hover:text-gray-700"><X /></button>
            </div>
            <div className="p-4 space-y-3 text-sm">
              <div>
                <div className="font-semibold mb-1">Yerel Kayıt</div>
                <pre className="bg-gray-50 border rounded p-2 text-xs overflow-x-auto">{JSON.stringify(detail.local, null, 2)}</pre>
              </div>
              <div>
                <div className="font-semibold mb-1">PMS Kaydı</div>
                <pre className="bg-gray-50 border rounded p-2 text-xs overflow-x-auto">{JSON.stringify(detail.pms, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cancel modal */}
      {cancelTarget && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="font-semibold">Rezervasyon İptali</h3>
              <button onClick={() => setCancelTarget(null)} className="text-gray-400 hover:text-gray-700"><X /></button>
            </div>
            <div className="p-4 space-y-3 text-sm">
              <div>{cancelTarget.syroce_hotel_name} - <b>{cancelTarget.guest_name}</b> rezervasyonunu iptal etmek üzeresiniz.</div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">İptal Nedeni</label>
                <select className="w-full border rounded px-3 py-2 text-sm" value={cancelReason} onChange={(e) => setCancelReason(e.target.value)}>
                  <option value="agency_request">Acenta Talebi</option>
                  <option value="customer_request">Müşteri Talebi</option>
                  <option value="payment_failed">Ödeme Başarısız</option>
                  <option value="duplicate">Mükerrer Kayıt</option>
                  <option value="other">Diğer</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t bg-gray-50 rounded-b-lg">
              <button onClick={() => setCancelTarget(null)} className="px-4 py-2 text-sm border rounded">Vazgeç</button>
              <button onClick={() => cancelMut.mutate({ id: cancelTarget.id, reason: cancelReason })} disabled={cancelMut.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white rounded">
                {cancelMut.isPending && <Loader2 size={14} className="animate-spin" />}
                İptal Et
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
