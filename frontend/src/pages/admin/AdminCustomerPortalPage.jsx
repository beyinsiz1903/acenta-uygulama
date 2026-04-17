import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Globe, MessageSquare, Shield, XCircle, CheckCircle, Clock, AlertTriangle } from "lucide-react";

const TICKET_STATUS_COLORS = {
  open: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-blue-100 text-blue-800",
  resolved: "bg-green-100 text-green-800",
  closed: "bg-gray-100 text-gray-600",
};

const CANCEL_STATUS_COLORS = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
};

export default function AdminCustomerPortalPage() {
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState("tickets");

  const { data: ticketsData, isLoading: ticketsLoading } = useQuery({
    queryKey: ["portal-support-tickets"],
    queryFn: async () => {
      try {
        const res = await api.get("/admin/support-tickets");
        return res.data;
      } catch { return { items: [], total: 0 }; }
    },
  });

  const { data: cancelData, isLoading: cancelLoading } = useQuery({
    queryKey: ["portal-cancel-requests"],
    queryFn: async () => {
      try {
        const res = await api.get("/admin/cancel-requests");
        return res.data;
      } catch { return { items: [], total: 0 }; }
    },
  });

  const updateTicketMut = useMutation({
    mutationFn: ({ id, status, admin_note }) =>
      api.patch(`/admin/support-tickets/${id}`, { status, admin_note }),
    onSuccess: () => qc.invalidateQueries(["portal-support-tickets"]),
  });

  const updateCancelMut = useMutation({
    mutationFn: ({ id, status, admin_note }) =>
      api.patch(`/admin/cancel-requests/${id}`, { status, admin_note }),
    onSuccess: () => qc.invalidateQueries(["portal-cancel-requests"]),
  });

  const tickets = ticketsData?.items || [];
  const cancelRequests = cancelData?.items || [];
  const portalUrl = `${window.location.origin}/portal`;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Globe className="w-7 h-7 text-cyan-600" /> Müşteri Portalı
          </h1>
          <p className="text-gray-500 mt-1">Müşterilerinizin self-servis portalını yönetin</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center">
              <Globe className="w-5 h-5 text-cyan-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Portal Linki</h3>
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-2 text-xs font-mono text-gray-600 break-all mb-2">
            {portalUrl}
          </div>
          <button
            onClick={() => navigator.clipboard.writeText(portalUrl)}
            className="text-sm text-cyan-600 hover:text-cyan-800 font-medium"
          >
            Linki Kopyala
          </button>
        </div>

        <div className="bg-white border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Açık Talepler</h3>
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {tickets.filter((t) => t.status === "open" || t.status === "in_progress").length}
          </div>
          <p className="text-xs text-gray-500 mt-1">Bekleyen destek talebi</p>
        </div>

        <div className="bg-white border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">İptal Talepleri</h3>
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {cancelRequests.filter((c) => c.status === "pending").length}
          </div>
          <p className="text-xs text-gray-500 mt-1">Bekleyen iptal talebi</p>
        </div>

        <div className="bg-white border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Shield className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Özellikler</h3>
            </div>
          </div>
          <ul className="space-y-1 text-xs text-gray-700">
            <li className="flex items-center gap-1"><span className="w-1.5 h-1.5 bg-green-500 rounded-full" /> Rezervasyon görüntüleme</li>
            <li className="flex items-center gap-1"><span className="w-1.5 h-1.5 bg-green-500 rounded-full" /> Fatura/voucher indirme</li>
            <li className="flex items-center gap-1"><span className="w-1.5 h-1.5 bg-green-500 rounded-full" /> Destek talebi</li>
            <li className="flex items-center gap-1"><span className="w-1.5 h-1.5 bg-green-500 rounded-full" /> İptal talebi</li>
          </ul>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab("tickets")}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${activeTab === "tickets" ? "bg-cyan-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
        >
          <MessageSquare className="w-4 h-4 inline mr-1" />
          Destek Talepleri ({tickets.length})
        </button>
        <button
          onClick={() => setActiveTab("cancels")}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${activeTab === "cancels" ? "bg-cyan-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
        >
          <XCircle className="w-4 h-4 inline mr-1" />
          İptal Talepleri ({cancelRequests.length})
        </button>
      </div>

      {activeTab === "tickets" && (
        <div className="bg-white rounded-xl border">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold text-gray-900">Portaldan Gelen Destek Talepleri</h3>
          </div>
          {ticketsLoading ? (
            <div className="text-center py-12 text-gray-400">Yükleniyor...</div>
          ) : tickets.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">Henüz destek talebi yok</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Müşteri</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Konu</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Mesaj</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Kategori</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Durum</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Tarih</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">İşlemler</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tickets.map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium">{t.customer_email}</div>
                      <div className="text-xs text-gray-500">{t.booking_code}</div>
                    </td>
                    <td className="px-4 py-3 font-medium">{t.subject}</td>
                    <td className="px-4 py-3 text-gray-600 max-w-[200px] truncate">{t.message}</td>
                    <td className="px-4 py-3">{t.category}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${TICKET_STATUS_COLORS[t.status] || "bg-gray-100"}`}>
                        {t.status === "open" ? "Açık" : t.status === "in_progress" ? "Devam Ediyor" : t.status === "resolved" ? "Çözüldü" : "Kapatıldı"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{t.created_at?.substring(0, 10)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {t.status === "open" && (
                          <button
                            onClick={() => updateTicketMut.mutate({ id: t.id, status: "in_progress" })}
                            className="text-blue-600 hover:text-blue-800 p-1" title="İşleme Al"
                          >
                            <Clock className="w-4 h-4" />
                          </button>
                        )}
                        {(t.status === "open" || t.status === "in_progress") && (
                          <button
                            onClick={() => updateTicketMut.mutate({ id: t.id, status: "resolved" })}
                            className="text-green-600 hover:text-green-800 p-1" title="Çözüldü"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                        )}
                        {t.status !== "closed" && (
                          <button
                            onClick={() => updateTicketMut.mutate({ id: t.id, status: "closed" })}
                            className="text-gray-500 hover:text-gray-700 p-1" title="Kapat"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === "cancels" && (
        <div className="bg-white rounded-xl border">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold text-gray-900">Portaldan Gelen İptal Talepleri</h3>
          </div>
          {cancelLoading ? (
            <div className="text-center py-12 text-gray-400">Yükleniyor...</div>
          ) : cancelRequests.length === 0 ? (
            <div className="text-center py-12">
              <XCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">Henüz iptal talebi yok</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Müşteri</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Rezervasyon</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Sebep</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Durum</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Tarih</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">İşlemler</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {cancelRequests.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{c.customer_email}</td>
                    <td className="px-4 py-3">{c.booking_code}</td>
                    <td className="px-4 py-3 text-gray-600 max-w-[250px] truncate">{c.reason}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${CANCEL_STATUS_COLORS[c.status] || "bg-gray-100"}`}>
                        {c.status === "pending" ? "Bekliyor" : c.status === "approved" ? "Onaylandı" : "Reddedildi"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{c.created_at?.substring(0, 10)}</td>
                    <td className="px-4 py-3 text-right">
                      {c.status === "pending" && (
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => updateCancelMut.mutate({ id: c.id, status: "approved" })}
                            className="text-green-600 hover:text-green-800 p-1" title="Onayla"
                          >
                            <CheckCircle className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => updateCancelMut.mutate({ id: c.id, status: "rejected" })}
                            className="text-red-600 hover:text-red-800 p-1" title="Reddet"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                      {c.status !== "pending" && (
                        <span className="text-xs text-gray-400">İşlem yapıldı</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
