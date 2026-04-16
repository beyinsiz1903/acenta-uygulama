import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { UserCheck, Plus, Edit, Trash2, Star, Globe, Phone, Mail } from "lucide-react";

const STATUS_COLORS = {
  active: "bg-green-100 text-green-800",
  inactive: "bg-gray-100 text-gray-600",
  on_leave: "bg-yellow-100 text-yellow-800",
};

export default function AdminGuidesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-guides"],
    queryFn: () => api.get("/admin/guides").then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: (body) => api.post("/admin/guides", body),
    onSuccess: () => { qc.invalidateQueries(["admin-guides"]); setShowForm(false); setEditItem(null); },
  });
  const patchMut = useMutation({
    mutationFn: ({ id, body }) => api.patch(`/admin/guides/${id}`, body),
    onSuccess: () => { qc.invalidateQueries(["admin-guides"]); setShowForm(false); setEditItem(null); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/guides/${id}`),
    onSuccess: () => qc.invalidateQueries(["admin-guides"]),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    body.languages = (body.languages || "").split(",").map((l) => l.trim()).filter(Boolean);
    body.specialties = (body.specialties || "").split(",").map((s) => s.trim()).filter(Boolean);
    body.daily_rate = parseFloat(body.daily_rate || "0");
    if (editItem) patchMut.mutate({ id: editItem.id, body });
    else createMut.mutate(body);
  };

  const items = data?.items || [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <UserCheck className="w-7 h-7 text-indigo-600" /> Rehber Y\u00f6netimi
          </h1>
          <p className="text-gray-500 mt-1">Tur rehberlerini y\u00f6netin, atay\u0131n ve performanslar\u0131n\u0131 takip edin</p>
        </div>
        <button onClick={() => { setEditItem(null); setShowForm(true); }} className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700">
          <Plus className="w-4 h-4" /> Yeni Rehber
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "Rehber D\u00fczenle" : "Yeni Rehber"}</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input name="name" defaultValue={editItem?.name || ""} placeholder="Ad Soyad" className="border rounded-lg px-3 py-2" required />
            <input name="phone" defaultValue={editItem?.phone || ""} placeholder="Telefon" className="border rounded-lg px-3 py-2" />
            <input name="email" defaultValue={editItem?.email || ""} placeholder="E-posta" className="border rounded-lg px-3 py-2" />
            <input name="languages" defaultValue={editItem?.languages?.join(", ") || ""} placeholder="Diller (virg\u00fclle ay\u0131r\u0131n)" className="border rounded-lg px-3 py-2" />
            <input name="specialties" defaultValue={editItem?.specialties?.join(", ") || ""} placeholder="Uzmanl\u0131k Alanlar\u0131" className="border rounded-lg px-3 py-2" />
            <input name="license_number" defaultValue={editItem?.license_number || ""} placeholder="Rehber Belgesi No" className="border rounded-lg px-3 py-2" />
            <input name="license_expiry" type="date" defaultValue={editItem?.license_expiry || ""} className="border rounded-lg px-3 py-2" />
            <input name="daily_rate" type="number" step="0.01" defaultValue={editItem?.daily_rate || 0} placeholder="G\u00fcnl\u00fck \u00dccret" className="border rounded-lg px-3 py-2" />
            <select name="status" defaultValue={editItem?.status || "active"} className="border rounded-lg px-3 py-2">
              <option value="active">Aktif</option>
              <option value="inactive">Pasif</option>
              <option value="on_leave">\u0130zinli</option>
            </select>
            <input name="notes" defaultValue={editItem?.notes || ""} placeholder="Notlar" className="border rounded-lg px-3 py-2 md:col-span-2" />
            <div className="flex gap-2 md:col-span-3">
              <button type="submit" className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazge\u00e7</button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Y\u00fckleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <UserCheck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Hen\u00fcz rehber kayd\u0131 yok</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item) => (
            <div key={item.id} className="bg-white border rounded-xl p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-gray-900">{item.name}</h3>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mt-1 ${STATUS_COLORS[item.status] || STATUS_COLORS.inactive}`}>
                    {item.status === "active" ? "Aktif" : item.status === "on_leave" ? "\u0130zinli" : "Pasif"}
                  </span>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => { setEditItem(item); setShowForm(true); }} className="text-blue-600 hover:text-blue-800 p-1"><Edit className="w-4 h-4" /></button>
                  <button onClick={() => { if (window.confirm("Silmek istediginize emin misiniz?")) deleteMut.mutate(item.id); }} className="text-red-500 hover:text-red-700 p-1"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              {item.phone && <div className="flex items-center gap-2 text-sm text-gray-600 mb-1"><Phone className="w-3 h-3" />{item.phone}</div>}
              {item.email && <div className="flex items-center gap-2 text-sm text-gray-600 mb-1"><Mail className="w-3 h-3" />{item.email}</div>}
              {item.languages?.length > 0 && (
                <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                  <Globe className="w-3 h-3" />{item.languages.join(", ")}
                </div>
              )}
              {item.license_number && <div className="text-xs text-gray-400 mt-2">Belge: {item.license_number}</div>}
              <div className="flex items-center justify-between mt-3 pt-3 border-t">
                <div className="flex items-center gap-1">
                  <Star className="w-4 h-4 text-yellow-500" />
                  <span className="text-sm font-medium">{item.rating || 0}/5</span>
                </div>
                <span className="text-sm text-gray-500">{item.daily_rate} {item.currency}/g\u00fcn</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
