import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import {
  Compass, Plus, Edit, Trash2, X, Users, Calendar,
} from "lucide-react";

const TYPE_OPTIONS = [
  { value: "tour", label: "Tur" },
  { value: "excursion", label: "Gezi" },
  { value: "experience", label: "Deneyim" },
  { value: "transfer_activity", label: "Transfer Aktivite" },
  { value: "water_sport", label: "Su Sporu" },
  { value: "adventure", label: "Macera" },
];

const STATUS_OPTIONS = [
  { value: "active", label: "Aktif", color: "bg-green-100 text-green-800" },
  { value: "inactive", label: "Pasif", color: "bg-gray-100 text-gray-800" },
  { value: "seasonal", label: "Sezonluk", color: "bg-blue-100 text-blue-800" },
  { value: "draft", label: "Taslak", color: "bg-yellow-100 text-yellow-800" },
];

function StatusBadge({ status }) {
  const s = STATUS_OPTIONS.find((o) => o.value === status) || STATUS_OPTIONS[0];
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${s.color}`}>{s.label}</span>;
}

const emptyForm = {
  name: "", activity_type: "tour", destination: "", city: "", description: "",
  duration_hours: 4, capacity: 20, min_participants: 2, price_per_person: 0,
  child_price: 0, currency: "TRY", includes: "", excludes: "", requirements: "",
  meeting_point: "", meeting_time: "", languages: "tr", guide_required: false,
  vehicle_required: false, supplier_name: "", status: "active",
};

export default function AdminActivitiesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [search, setSearch] = useState("");
  const [sessionModal, setSessionModal] = useState(null);
  const [sessionForm, setSessionForm] = useState({ date: "", time: "", notes: "" });

  const { data, isLoading } = useQuery({
    queryKey: ["admin-activities", filterStatus, filterType, search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      if (filterType) params.set("activity_type", filterType);
      if (search) params.set("search", search);
      return api.get(`/admin/activities?${params}`).then((r) => r.data);
    },
  });

  const createMut = useMutation({
    mutationFn: (body) => api.post("/admin/activities", body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-activities"] }); setShowForm(false); },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, ...body }) => api.patch(`/admin/activities/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-activities"] }); setEditItem(null); setShowForm(false); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/activities/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-activities"] }),
  });
  const sessionMut = useMutation({
    mutationFn: ({ activityId, ...body }) => api.post(`/admin/activities/${activityId}/sessions`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-activities"] }); setSessionModal(null); },
  });

  const [form, setForm] = useState(emptyForm);
  const F = (field) => (e) => setForm({ ...form, [field]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const handleSubmit = (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      duration_hours: Number(form.duration_hours),
      capacity: Number(form.capacity),
      min_participants: Number(form.min_participants),
      price_per_person: Number(form.price_per_person),
      child_price: Number(form.child_price),
      includes: typeof form.includes === "string" ? form.includes.split(",").map(s => s.trim()).filter(Boolean) : form.includes,
      excludes: typeof form.excludes === "string" ? form.excludes.split(",").map(s => s.trim()).filter(Boolean) : form.excludes,
      requirements: typeof form.requirements === "string" ? form.requirements.split(",").map(s => s.trim()).filter(Boolean) : form.requirements,
      languages: typeof form.languages === "string" ? form.languages.split(",").map(s => s.trim()).filter(Boolean) : form.languages,
    };
    if (editItem) updateMut.mutate({ id: editItem.id, ...payload });
    else createMut.mutate(payload);
  };

  const openEdit = (item) => {
    setForm({
      ...emptyForm,
      ...item,
      includes: Array.isArray(item.includes) ? item.includes.join(", ") : item.includes || "",
      excludes: Array.isArray(item.excludes) ? item.excludes.join(", ") : item.excludes || "",
      requirements: Array.isArray(item.requirements) ? item.requirements.join(", ") : item.requirements || "",
      languages: Array.isArray(item.languages) ? item.languages.join(", ") : item.languages || "",
    });
    setEditItem(item);
    setShowForm(true);
  };
  const openCreate = () => { setForm(emptyForm); setEditItem(null); setShowForm(true); };

  const items = data?.items || [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Compass className="w-6 h-6 text-orange-600" />
          <h1 className="text-2xl font-bold">Aktivite Yönetimi</h1>
          <span className="text-sm text-gray-500">({data?.total || 0} aktivite)</span>
        </div>
        <button onClick={openCreate} className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700">
          <Plus className="w-4 h-4" /> Yeni Aktivite
        </button>
      </div>

      <div className="flex gap-3 flex-wrap">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="İsim veya destinasyon ara..." className="px-3 py-2 border rounded-lg w-64" />
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="px-3 py-2 border rounded-lg">
          <option value="">Tüm Türler</option>
          {TYPE_OPTIONS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="px-3 py-2 border rounded-lg">
          <option value="">Tüm Durumlar</option>
          {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">{editItem ? "Aktivite Düzenle" : "Yeni Aktivite"}</h2>
              <button onClick={() => { setShowForm(false); setEditItem(null); }}><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
              <div className="col-span-2"><label className="block text-sm font-medium mb-1">Aktivite Adı *</label><input value={form.name} onChange={F("name")} required className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Tür *</label><select value={form.activity_type} onChange={F("activity_type")} className="w-full px-3 py-2 border rounded-lg">{TYPE_OPTIONS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}</select></div>
              <div><label className="block text-sm font-medium mb-1">Destinasyon</label><input value={form.destination} onChange={F("destination")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Şehir</label><input value={form.city} onChange={F("city")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Süre (saat)</label><input type="number" step="0.5" value={form.duration_hours} onChange={F("duration_hours")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Kapasite</label><input type="number" value={form.capacity} onChange={F("capacity")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Min. Katılımcı</label><input type="number" value={form.min_participants} onChange={F("min_participants")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Kişi Başı Fiyat</label><input type="number" value={form.price_per_person} onChange={F("price_per_person")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Çocuk Fiyatı</label><input type="number" value={form.child_price} onChange={F("child_price")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Para Birimi</label><select value={form.currency} onChange={F("currency")} className="w-full px-3 py-2 border rounded-lg"><option value="TRY">TRY</option><option value="EUR">EUR</option><option value="USD">USD</option></select></div>
              <div className="col-span-2"><label className="block text-sm font-medium mb-1">Dahil Olanlar (virgülle)</label><input value={form.includes} onChange={F("includes")} placeholder="Rehber, Öğle yemeği, Transfer" className="w-full px-3 py-2 border rounded-lg" /></div>
              <div className="col-span-2"><label className="block text-sm font-medium mb-1">Hariç Olanlar (virgülle)</label><input value={form.excludes} onChange={F("excludes")} placeholder="İçecekler, Ekstra aktiviteler" className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Buluşma Noktası</label><input value={form.meeting_point} onChange={F("meeting_point")} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Buluşma Saati</label><input value={form.meeting_time} onChange={F("meeting_time")} placeholder="09:00" className="w-full px-3 py-2 border rounded-lg" /></div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2"><input type="checkbox" checked={form.guide_required} onChange={F("guide_required")} /> Rehber Gerekli</label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={form.vehicle_required} onChange={F("vehicle_required")} /> Araç Gerekli</label>
              </div>
              <div><label className="block text-sm font-medium mb-1">Durum</label><select value={form.status} onChange={F("status")} className="w-full px-3 py-2 border rounded-lg">{STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}</select></div>
              <div className="col-span-2 flex gap-3 justify-end">
                <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="px-4 py-2 border rounded-lg">İptal</button>
                <button type="submit" className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700">{editItem ? "Güncelle" : "Oluştur"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {sessionModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Seans Ekle — {sessionModal.name}</h2>
              <button onClick={() => setSessionModal(null)}><X className="w-5 h-5" /></button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); sessionMut.mutate({ activityId: sessionModal.id, ...sessionForm }); }} className="space-y-3">
              <div><label className="block text-sm font-medium mb-1">Tarih *</label><input type="date" value={sessionForm.date} onChange={(e) => setSessionForm({ ...sessionForm, date: e.target.value })} required className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Saat</label><input value={sessionForm.time} onChange={(e) => setSessionForm({ ...sessionForm, time: e.target.value })} placeholder="09:00" className="w-full px-3 py-2 border rounded-lg" /></div>
              <div><label className="block text-sm font-medium mb-1">Not</label><input value={sessionForm.notes} onChange={(e) => setSessionForm({ ...sessionForm, notes: e.target.value })} className="w-full px-3 py-2 border rounded-lg" /></div>
              <div className="flex gap-3 justify-end"><button type="submit" className="px-4 py-2 bg-orange-600 text-white rounded-lg">Seans Oluştur</button></div>
            </form>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-500">Henüz aktivite eklenmemiş</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Aktivite</th>
                <th className="px-4 py-3 text-left font-medium">Tür</th>
                <th className="px-4 py-3 text-left font-medium">Destinasyon</th>
                <th className="px-4 py-3 text-left font-medium">Süre</th>
                <th className="px-4 py-3 text-left font-medium">Fiyat</th>
                <th className="px-4 py-3 text-left font-medium">Kapasite</th>
                <th className="px-4 py-3 text-left font-medium">Durum</th>
                <th className="px-4 py-3 text-left font-medium">Seanslar</th>
                <th className="px-4 py-3 text-right font-medium">İşlem</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((a) => {
                const typeLbl = TYPE_OPTIONS.find((t) => t.value === a.activity_type)?.label || a.activity_type;
                return (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{a.name}</td>
                    <td className="px-4 py-3"><span className="px-2 py-1 bg-orange-50 text-orange-700 text-xs rounded-full">{typeLbl}</span></td>
                    <td className="px-4 py-3">{a.destination || a.city || "—"}</td>
                    <td className="px-4 py-3">{a.duration_hours}h</td>
                    <td className="px-4 py-3 font-medium">{a.price_per_person?.toLocaleString()} {a.currency}</td>
                    <td className="px-4 py-3">{a.capacity}</td>
                    <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                    <td className="px-4 py-3">
                      <button onClick={() => { setSessionForm({ date: "", time: "", notes: "" }); setSessionModal(a); }} className="flex items-center gap-1 text-orange-600 hover:text-orange-800 text-xs">
                        <Calendar className="w-3 h-3" /> {a.sessions?.length || 0} seans
                      </button>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex gap-1 justify-end">
                        <button onClick={() => openEdit(a)} className="p-1.5 hover:bg-gray-100 rounded"><Edit className="w-4 h-4" /></button>
                        <button onClick={() => { if (window.confirm("Bu aktiviteyi silmek istediğinize emin misiniz?")) deleteMut.mutate(a.id); }} className="p-1.5 hover:bg-red-50 rounded text-red-600"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
