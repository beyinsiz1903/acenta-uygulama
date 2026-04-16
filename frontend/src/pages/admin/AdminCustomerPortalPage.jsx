import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Globe, Users, MessageSquare, ExternalLink, Shield } from "lucide-react";

export default function AdminCustomerPortalPage() {
  const { data: tickets, isLoading } = useQuery({
    queryKey: ["portal-support-tickets"],
    queryFn: async () => {
      try {
        const res = await api.get("/admin/support-tickets");
        return res.data?.items || [];
      } catch { return []; }
    },
  });

  const portalUrl = `${window.location.origin}/portal`;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Globe className="w-7 h-7 text-cyan-600" /> M\u00fc\u015fteri Portal\u0131
          </h1>
          <p className="text-gray-500 mt-1">M\u00fc\u015fterilerinizin self-servis portal\u0131n\u0131 y\u00f6netin</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white border rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-cyan-100 rounded-lg flex items-center justify-center">
              <Globe className="w-5 h-5 text-cyan-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Portal Linki</h3>
              <p className="text-xs text-gray-500">M\u00fc\u015fterilerinize g\u00f6nderin</p>
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-sm font-mono text-gray-600 break-all">
            {portalUrl}
          </div>
          <button
            onClick={() => navigator.clipboard.writeText(portalUrl)}
            className="mt-3 text-sm text-cyan-600 hover:text-cyan-800 font-medium"
          >
            Linki Kopyala
          </button>
        </div>

        <div className="bg-white border rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Shield className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Portal \u00d6zellikleri</h3>
              <p className="text-xs text-gray-500">Aktif \u00f6zellikler</p>
            </div>
          </div>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-center gap-2"><span className="w-2 h-2 bg-green-500 rounded-full" /> Rezervasyon g\u00f6r\u00fcnt\u00fcleme</li>
            <li className="flex items-center gap-2"><span className="w-2 h-2 bg-green-500 rounded-full" /> Fatura ve voucher indirme</li>
            <li className="flex items-center gap-2"><span className="w-2 h-2 bg-green-500 rounded-full" /> Destek talebi olu\u015fturma</li>
            <li className="flex items-center gap-2"><span className="w-2 h-2 bg-green-500 rounded-full" /> \u0130ptal talebi g\u00f6nderme</li>
          </ul>
        </div>

        <div className="bg-white border rounded-xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Nas\u0131l \u00c7al\u0131\u015f\u0131r</h3>
              <p className="text-xs text-gray-500">M\u00fc\u015fteri giri\u015fi</p>
            </div>
          </div>
          <div className="text-sm text-gray-600 space-y-2">
            <p>1. M\u00fc\u015fteri e-posta + rezervasyon kodu ile giri\u015f yapar</p>
            <p>2. Rezervasyonlar\u0131n\u0131, faturalar\u0131n\u0131 g\u00f6r\u00fcr</p>
            <p>3. Destek veya iptal talebi olu\u015fturabilir</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">Portaldan Gelen Destek Talepleri</h3>
        </div>
        {isLoading ? (
          <div className="text-center py-12 text-gray-400">Y\u00fckleniyor...</div>
        ) : !tickets || tickets.length === 0 ? (
          <div className="text-center py-12">
            <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">Hen\u00fcz destek talebi yok</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">M\u00fc\u015fteri</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Konu</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Kategori</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Durum</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tarih</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {tickets.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{t.customer_email}</td>
                  <td className="px-4 py-3 font-medium">{t.subject}</td>
                  <td className="px-4 py-3">{t.category}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${t.status === "open" ? "bg-yellow-100 text-yellow-800" : "bg-green-100 text-green-800"}`}>{t.status}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{t.created_at?.substring(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
