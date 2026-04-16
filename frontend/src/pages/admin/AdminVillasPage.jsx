import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import {
  Home, Plus, Edit, Trash2, X, Calendar, DollarSign, Eye,
} from "lucide-react";

const STATUS_OPTIONS = [
  { value: "active", label: "Aktif", color: "bg-green-100 text-green-800" },
  { value: "inactive", label: "Pasif", color: "bg-gray-100 text-gray-800" },
  { value: "maintenance", label: "Bakım", color: "bg-yellow-100 text-yellow-800" },
  { value: "seasonal", label: "Sezonluk", color: "bg-blue-100 text-blue-800" },
];

function StatusBadge({ status }) {
  const s = STATUS_OPTIONS.find((o) => o.value === status) || STATUS_OPTIONS[0];
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${s.color}`}>{s.label}</span>;
}

const emptyForm = {
  name: "", location: "", city: "", district: "", address: "", description: "",
  capacity: 6, bedrooms: 3, bathrooms: 2, pool: false, pool_type: "",
  area_sqm: 0, features: [], images: [], price_per_night: 0, currency: "TRY",
  min_stay_nights: 3, owner_name: "", owner_phone: "", owner_email: "",
  commission_rate: 15, ical_url: "", status: "active",
};

export default function AdminVillasPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [search, setSearch] = useState("");
  const [detailItem, setDetailItem] = useState(null);
  const [blockModal, setBlockModal] = useState(null);
  const [blockForm, setBlockForm] = useState({ start_date: "", end_date: "", reason: "", guest_name: "" });

  const { data, isLoading } = useQuery({
    queryKey: ["admin-villas", filterStatus, search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      if (search) params.set("search", search);
      return api.get(`/admin/villas?${params}`).then((r) => r.data);
    },
  });

  const createMut = useMutation({
    mutationFn: (body) => api.post("/admin/villas", body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-villas"] }); setShowForm(false); },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, ...body }) => api.patch(`/admin/villas/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-villas"] }); setEditItem(null); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/villas/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-villas"] }),
  });
  const blockMut = useMutation({
    mutationFn: ({ villaId, ...body }) => api.post(`/admin/villas/${villaId}/block-dates`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-villas"] }); setBlockModal(null); },
  });

  const [form, setForm] = useState(emptyForm);
  const F = (field) => (e) => setForm({ ...form, [field]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = { ...form, price_per_night: Number(form.price_per_night), capacity: Number(form.capacity), bedrooms: Number(form.bedrooms), bathrooms: Number(form.bathrooms), area_sqm: Number(form.area_sqm), min_stay_nights: Number(form.min_stay_nights), commission_rate: Number(form.commission_rate) };
    if (editItem) updateMut.mutate({ id: editItem.id, ...payload });
    else createMut.mutate(payload);
  };

  const openEdit = (item) => { setForm({ ...emptyForm, ...item }); setEditItem(item); setShowForm(true); };
  const openCreate = () => { setForm(emptyForm); setEditItem(null); setShowForm(true); };

  const items = data?.items || [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Home className="w-6 h-6 text-emerald-600" />
          <h1 className="text-2xl font-bold">Villa Yönetimi</h1>
          <span className="text-sm text-gray-500">({data?.total || 0} villa)</span>
        </div>
        <button onClick={openCreate} className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700">
          <Plus className="w-4 h-4" /> Yeni Villa
        </button>
      </div>

      <div className="flex gap-3 flex-wrap">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="İsim veya konum ara..." className="px-3 py-2 border rounded-lg w-64" />
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="px-3 py-2 border rounded-lg">
          <option value="">Tüm Durumlar</option>
          {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">{editItem ? "Villa Düzenle" : "Yeni Villa"}</h2>
              <button onClick={() => { setShowForm(false); setEditItem(null); }}><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
              <div className="col-span-2"><label className="block text-sm font-medium mb-1">Villa Adı *</label><input value={form.name} onChange={F("name")} required className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Şehir</label><input value={form.city} onChange={F("city")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">İlçe</label><input value={form.district} onChange={F("district")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div className="col-span-2"><label className="block text-sm font-medium mb-1">Adres</label><input value={form.address} onChange={F("address")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Kapasite</label><input type="number" value={form.capacity} onChange={F("capacity")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Yatak Odası</label><input type="number" value={form.bedrooms} onChange={F("bedrooms")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Banyo</label><input type="number" value={form.bathrooms} onChange={F("bathrooms")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Alan (m²)</label><input type="number" value={form.area_sqm} onChange={F("area_sqm")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div className="flex items-center gap-2"><input type="checkbox" checked={form.pool} onChange={F("pool")} /><label className="text-sm font-medium">Havuz</label></div>
              {form.pool && <div><label className="block text-sm font-medium mb-1">Havuz Tipi</label><input value={form.pool_type} onChange={F("pool_type")} placeholder="Özel / Ortak / Kapalı" className="w-full px-3 py-2 border rounded-lg" /></div>}
              <div><label className="block text-sm font-medium mb-1">Gecelik Fiyat</label><input type="number" value={form.price_per_night} onChange={F("price_per_night")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Para Birimi</label><select value={form.currency} onChange={F("currency")} className="w-full px-3 py-2 border rounded-lg"><option value="TRY">TRY</option><option value="EUR">EUR</option><option value="USD">USD</option><option value="GBP">GBP</option></select></div>
              <div><label className="block text-sm font-medium mb-1">Min. Konaklama (gece)</label><input type="number" value={form.min_stay_nights} onChange={F("min_stay_nights")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Komisyon (%)</label><input type="number" value={form.commission_rate} onChange={F("commission_rate")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Mal Sahibi</label><input value={form.owner_name} onChange={F("owner_name")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Mal Sahibi Tel</label><input value={form.owner_phone} onChange={F("owner_phone")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div className="col-span-2"><label className="block text-sm font-medium mb-1">iCal URL</label><input value={form.ical_url} onChange={F("ical_url")} placeholder="https://..." className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Durum</label><select value={form.status} onChange={F("status")} className="w-full px-3 py-2 border rounded-lg">{STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}</select></div>
              <div className="col-span-2 flex gap-3 justify-end">
                <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="px-4 py-2 border rounded-lg">İptal</button>
                <button type="submit" className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700">{editItem ? "Güncelle" : "Oluştur"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {blockModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Tarih Blokla — {blockModal.name}</h2>
              <button onClick={() => setBlockModal(null)}><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); blockMut.mutate({ villaId: blockModal.id, ...blockForm }); }} className="space-y-3">
              <div><label className="block text-sm font-medium mb-1">Başlangıç *</label><input type="date" value={blockForm.start_date} onChange={(e) => setBlockForm({ ...blockForm, start_date: e.target.value })} required className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Bitiş *</label><input type="date" value={blockForm.end_date} onChange={(e) => setBlockForm({ ...blockForm, end_date: e.target.value })} required className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Sebep</label><input value={blockForm.reason} onChange={(e) => setBlockForm({ ...blockForm, reason: e.target.value })} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Misafir</label><input value={blockForm.guest_name} onChange={(e) => setBlockForm({ ...blockForm, guest_name: e.target.value })} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div className="flex gap-3 justify-end"><button type="submit" className="px-4 py-2 bg-emerald-600 text-white rounded-lg">Blokla</button></div>
            </form>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Henüz villa eklenmemiş</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((v) => (
            <div key={v.id} className="border rounded-xl p-4 hover:shadow-lg transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-lg">{v.name}</h3>
                <StatusBadge status={v.status} />
              </div>
              <p className="text-sm text-gray-500 mb-2">{v.city}{v.district ? ` / ${v.district}` : ""}</p>
              <div className="grid grid-cols-3 gap-2 text-sm text-gray-600 mb-3">
                <span>{v.capacity} kişi</span>
                <span>{v.bedrooms} oda</span>
                <span>{v.bathrooms} banyo</span>
              </div>
              {v.pool && <span className="inline-block px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full mb-2">Havuzlu</span>}
              <div className="text-lg font-bold text-emerald-600 mb-3">{v.price_per_night?.toLocaleString()} {v.currency}/gece</div>
              <div className="flex gap-2">
                <button onClick={() => openEdit(v)} className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50"><Edit className="w-3 h-3" /> Düzenle</button>
                <button onClick={() => { setBlockForm({ start_date: "", end_date: "", reason: "", guest_name: "" }); setBlockModal(v); }} className="flex items-center gap-1 px-3 py-1.5 border rounded-lg text-sm hover:bg-gray-50"><Calendar className="w-3 h-3" /></button>
                <button onClick={() => { if (window.confirm("Bu villayı silmek istediğinize emin misiniz?")) deleteMut.mutate(v.id); }} className="flex items-center gap-1 px-3 py-1.5 border rounded-lg text-sm text-red-600 hover:bg-red-50"><Trash2 className="w-3 h-3" /></button>
              </div>
              {v.blocked_dates?.length > 0 && (
                <div className="mt-3 border-t pt-2">
                  <p className="text-xs font-medium text-gray-500 mb-1">Bloklu Tarihler ({v.blocked_dates.length})</p>
                  {v.blocked_dates.slice(0, 3).map((bd) => (
                    <div key={bd.id} className="text-xs text-gray-600">{bd.start_date} → {bd.end_date} {bd.reason && `(${bd.reason})`}</div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
