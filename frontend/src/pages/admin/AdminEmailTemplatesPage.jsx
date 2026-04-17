import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Mail, Plus, Edit, Trash2, Eye, Zap, Copy } from "lucide-react";

export default function AdminEmailTemplatesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [previewHtml, setPreviewHtml] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-email-templates"],
    queryFn: () => api.get("/admin/email-templates").then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: (body) => api.post("/admin/email-templates", body),
    onSuccess: () => { qc.invalidateQueries(["admin-email-templates"]); setShowForm(false); setEditItem(null); },
  });
  const patchMut = useMutation({
    mutationFn: ({ id, body }) => api.patch(`/admin/email-templates/${id}`, body),
    onSuccess: () => { qc.invalidateQueries(["admin-email-templates"]); setShowForm(false); setEditItem(null); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/email-templates/${id}`),
    onSuccess: () => qc.invalidateQueries(["admin-email-templates"]),
  });
  const seedMut = useMutation({
    mutationFn: () => api.post("/admin/email-templates/seed-defaults"),
    onSuccess: () => qc.invalidateQueries(["admin-email-templates"]),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    body.is_active = body.is_active === "true";
    if (editItem) patchMut.mutate({ id: editItem.id, body });
    else createMut.mutate(body);
  };

  const handlePreview = async (item) => {
    try {
      const res = await api.post(`/admin/email-templates/${item.id}/preview`, {
        data: { customer_name: "Örnek Müşteri", reservation_code: "RSV-001", check_in: "2025-06-01", check_out: "2025-06-07", amount: "1500", currency: "EUR", quote_code: "QT-001" },
      });
      setPreviewHtml(res.data);
    } catch { }
  };

  const items = data?.items || [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Mail className="w-7 h-7 text-rose-600" /> E-posta Şablonları
          </h1>
          <p className="text-gray-500 mt-1">Otomatik e-posta şablonlarını yönetin ve ön izleyin</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => seedMut.mutate()} className="flex items-center gap-2 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200">
            <Zap className="w-4 h-4" /> Varsayılanları Yükle
          </button>
          <button onClick={() => { setEditItem(null); setShowForm(true); }} className="flex items-center gap-2 bg-rose-600 text-white px-4 py-2 rounded-lg hover:bg-rose-700">
            <Plus className="w-4 h-4" /> Yeni Şablon
          </button>
        </div>
      </div>

      {previewHtml && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Ön İzleme</h3>
            <button onClick={() => setPreviewHtml(null)} className="text-gray-400 hover:text-gray-600">Kapat</button>
          </div>
          <div className="border-b pb-3 mb-3"><strong>Konu:</strong> {previewHtml.subject}</div>
          <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: previewHtml.body_html }} />
        </div>
      )}

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "Şablon Düzenle" : "Yeni Şablon"}</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <input name="name" defaultValue={editItem?.name || ""} placeholder="Şablon Adı" className="border rounded-lg px-3 py-2" required />
              <input name="key" defaultValue={editItem?.key || ""} placeholder="Anahtar (oto üretilir)" className="border rounded-lg px-3 py-2" />
              <select name="trigger" defaultValue={editItem?.trigger || ""} className="border rounded-lg px-3 py-2">
                <option value="">Tetikleyici Seçin</option>
                <option value="reservation.confirmed">Rezervasyon Onay</option>
                <option value="reservation.cancelled">Rezervasyon İptal</option>
                <option value="reservation.reminder">Rezervasyon Hatırlatma</option>
                <option value="payment.received">Ödeme Alındı</option>
                <option value="payment.reminder">Ödeme Hatırlatma</option>
                <option value="quote.sent">Teklif Gönderildi</option>
                <option value="visa.status_changed">Vize Durum Değişikliği</option>
                <option value="transfer.confirmed">Transfer Onay</option>
                <option value="welcome">Hoş Geldiniz</option>
              </select>
            </div>
            <input name="subject" defaultValue={editItem?.subject || ""} placeholder="E-posta Konusu ({{degisken}} kullanabilirsiniz)" className="w-full border rounded-lg px-3 py-2" />
            <textarea name="body_html" defaultValue={editItem?.body_html || ""} placeholder="HTML İçerik ({{degisken}} kullanabilirsiniz)" className="w-full border rounded-lg px-3 py-2 h-40 font-mono text-sm" />
            <div className="grid grid-cols-2 gap-4">
              <select name="language" defaultValue={editItem?.language || "tr"} className="border rounded-lg px-3 py-2">
                <option value="tr">Türkçe</option>
                <option value="en">İngilizce</option>
                <option value="de">Almanca</option>
                <option value="ru">Rusça</option>
              </select>
              <select name="is_active" defaultValue={String(editItem?.is_active ?? true)} className="border rounded-lg px-3 py-2">
                <option value="true">Aktif</option>
                <option value="false">Pasif</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="bg-rose-600 text-white px-6 py-2 rounded-lg hover:bg-rose-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazgeç</button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <Mail className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Henüz e-posta şablonu yok</p>
          <button onClick={() => seedMut.mutate()} className="mt-3 text-rose-600 hover:text-rose-800 text-sm font-medium">Varsayılan şablonları yükle</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map((item) => (
            <div key={item.id} className="bg-white border rounded-xl p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="font-semibold text-gray-900">{item.name}</h3>
                  <p className="text-xs text-gray-500 mt-0.5">Tetikleyici: {item.trigger || "-"}</p>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => handlePreview(item)} className="text-gray-500 hover:text-gray-700 p-1" title="Ön izle"><Eye className="w-4 h-4" /></button>
                  <button onClick={() => { setEditItem(item); setShowForm(true); }} className="text-blue-600 hover:text-blue-800 p-1"><Edit className="w-4 h-4" /></button>
                  <button onClick={() => { if (window.confirm("Silmek istediginize emin misiniz?")) deleteMut.mutate(item.id); }} className="text-red-500 hover:text-red-700 p-1"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <div className="text-sm text-gray-600 mb-2">Konu: {item.subject}</div>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span className={`px-2 py-0.5 rounded-full ${item.is_active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"}`}>
                  {item.is_active ? "Aktif" : "Pasif"}
                </span>
                <span>{item.language?.toUpperCase()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
