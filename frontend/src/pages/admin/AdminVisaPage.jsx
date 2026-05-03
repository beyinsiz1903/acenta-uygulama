import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { FileCheck, Plus, Edit, Trash2, Search } from "lucide-react";
import { toast } from "sonner";

const VISA_STATUSES = {
  draft: { label: "Taslak", color: "bg-gray-100 text-gray-700" },
  documents_collecting: { label: "Belge Toplama", color: "bg-blue-100 text-blue-800" },
  documents_ready: { label: "Belgeler Hazır", color: "bg-indigo-100 text-indigo-800" },
  submitted: { label: "Başvuru Yapıldı", color: "bg-purple-100 text-purple-800" },
  appointment_scheduled: { label: "Randevu Alındı", color: "bg-yellow-100 text-yellow-800" },
  at_consulate: { label: "Konsoloslukta", color: "bg-orange-100 text-orange-800" },
  approved: { label: "Onaylandı", color: "bg-green-100 text-green-800" },
  rejected: { label: "Reddedildi", color: "bg-red-100 text-red-800" },
  cancelled: { label: "İptal", color: "bg-red-50 text-red-600" },
};

function CustomerSearch({ value, onChange, customers }) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);

  const filtered = useMemo(() => {
    if (!search) return customers.slice(0, 20);
    const q = search.toLowerCase();
    return customers.filter(
      (c) =>
        (c.name || "").toLowerCase().includes(q) ||
        (c.email || "").toLowerCase().includes(q) ||
        (c.phone || "").includes(q)
    ).slice(0, 20);
  }, [search, customers]);

  const selected = customers.find((c) => c.id === value);

  return (
    <div className="relative">
      <div
        onClick={() => setOpen(!open)}
        className="border rounded-lg px-3 py-2 cursor-pointer flex items-center justify-between"
      >
        <span className={selected ? "text-gray-900" : "text-gray-400"}>
          {selected ? `${selected.name} (${selected.email || ""})` : "Müşteri Seçin"}
        </span>
        <Search className="w-4 h-4 text-gray-400" />
      </div>
      {open && (
        <div className="absolute z-20 mt-1 w-full bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto">
          <div className="p-2 border-b">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Ara: isim, e-posta, telefon..."
              className="w-full border rounded px-2 py-1 text-sm"
              autoFocus
            />
          </div>
          {filtered.length === 0 && (
            <div className="p-3 text-sm text-gray-500">Sonuç bulunamadı</div>
          )}
          {filtered.map((c) => (
            <button
              key={c.id}
              onClick={() => { onChange(c); setOpen(false); setSearch(""); }}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-blue-50 ${c.id === value ? "bg-blue-50" : ""}`}
            >
              <div className="font-medium">{c.name}</div>
              <div className="text-xs text-gray-500">{c.email} {c.phone ? `· ${c.phone}` : ""}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AdminVisaPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-visa", filterStatus],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      return api.get(`/admin/visa?${params}`).then((r) => r.data);
    },
  });

  const { data: customersData } = useQuery({
    queryKey: ["crm-customers-list"],
    queryFn: async () => {
      try {
        const res = await api.get("/crm/customers?page_size=500");
        return res.data?.items || res.data?.customers || [];
      } catch { return []; }
    },
  });

  const createMut = useMutation({
    mutationFn: (body) => api.post("/admin/visa", body),
    onSuccess: () => { qc.invalidateQueries(["admin-visa"]); setShowForm(false); setEditItem(null); setSelectedCustomer(null); },
  });
  const patchMut = useMutation({
    mutationFn: ({ id, body }) => api.patch(`/admin/visa/${id}`, body),
    onSuccess: () => { qc.invalidateQueries(["admin-visa"]); setShowForm(false); setEditItem(null); setSelectedCustomer(null); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/visa/${id}`),
    onSuccess: () => qc.invalidateQueries(["admin-visa"]),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    body.fee = parseFloat(body.fee || "0");
    if (selectedCustomer) {
      body.customer_id = selectedCustomer.id;
      body.customer_name = selectedCustomer.name;
    }
    if (!editItem && !body.customer_id) {
      toast("Lütfen bir müşteri seçin");
      return;
    }
    if (editItem) patchMut.mutate({ id: editItem.id, body });
    else createMut.mutate(body);
  };

  const openEdit = (item) => {
    setEditItem(item);
    const cust = (customersData || []).find((c) => c.id === item.customer_id);
    setSelectedCustomer(cust || (item.customer_id ? { id: item.customer_id, name: item.customer_name } : null));
    setShowForm(true);
  };

  const items = data?.items || [];
  const customers = customersData || [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileCheck className="w-7 h-7 text-purple-600" /> Vize Takip
          </h1>
          <p className="text-gray-500 mt-1">Vize başvurularını ve belge süreçlerini yönetin</p>
        </div>
        <button onClick={() => { setEditItem(null); setSelectedCustomer(null); setShowForm(true); }} className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700">
          <Plus className="w-4 h-4" /> Yeni Başvuru
        </button>
      </div>

      <div className="flex gap-3 mb-4">
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">Tüm Durumlar</option>
          {Object.entries(VISA_STATUSES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "Başvuru Düzenle" : "Yeni Vize Başvurusu"}</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Müşteri</label>
              <CustomerSearch
                value={selectedCustomer?.id || editItem?.customer_id || ""}
                onChange={(c) => setSelectedCustomer(c)}
                customers={customers}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Müşteri Adı</label>
              <input name="customer_name" value={selectedCustomer?.name || editItem?.customer_name || ""} readOnly className="border rounded-lg px-3 py-2 w-full bg-gray-50" />
            </div>
            <input name="destination_country" defaultValue={editItem?.destination_country || ""} placeholder="Hedef Ülke" className="border rounded-lg px-3 py-2" required />
            <select name="visa_type" defaultValue={editItem?.visa_type || "tourist"} className="border rounded-lg px-3 py-2">
              <option value="tourist">Turist</option>
              <option value="business">İş</option>
              <option value="transit">Transit</option>
              <option value="student">Öğrenci</option>
            </select>
            <input name="passport_number" defaultValue={editItem?.passport_number || ""} placeholder="Pasaport No" className="border rounded-lg px-3 py-2" />
            <input name="passport_expiry" type="date" defaultValue={editItem?.passport_expiry || ""} className="border rounded-lg px-3 py-2" />
            <input name="consulate" defaultValue={editItem?.consulate || ""} placeholder="Konsolosluk" className="border rounded-lg px-3 py-2" />
            <input name="appointment_date" type="date" defaultValue={editItem?.appointment_date || ""} className="border rounded-lg px-3 py-2" />
            <input name="fee" type="number" step="0.01" defaultValue={editItem?.fee || 0} placeholder="Ücret" className="border rounded-lg px-3 py-2" />
            <select name="status" defaultValue={editItem?.status || "draft"} className="border rounded-lg px-3 py-2">
              {Object.entries(VISA_STATUSES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
            <input name="notes" defaultValue={editItem?.notes || ""} placeholder="Notlar" className="border rounded-lg px-3 py-2 md:col-span-2" />
            <div className="flex gap-2 md:col-span-3">
              <button type="submit" className="bg-purple-600 text-white px-6 py-2 rounded-lg hover:bg-purple-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); setSelectedCustomer(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazgeç</button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <FileCheck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Henüz vize başvurusu yok</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Müşteri</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ülke</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tip</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Randevu</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Durum</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((item) => {
                const st = VISA_STATUSES[item.status] || VISA_STATUSES.draft;
                return (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium">{item.customer_name}</div>
                      <div className="text-xs text-gray-500">Pasaport: {item.passport_number}</div>
                    </td>
                    <td className="px-4 py-3 font-medium">{item.destination_country}</td>
                    <td className="px-4 py-3">{item.visa_type === "tourist" ? "Turist" : item.visa_type === "business" ? "İş" : item.visa_type === "transit" ? "Transit" : "Öğrenci"}</td>
                    <td className="px-4 py-3">{item.appointment_date || "-"}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 rounded-full text-xs font-medium ${st.color}`}>{st.label}</span></td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => openEdit(item)} className="text-blue-600 hover:text-blue-800 mr-2"><Edit className="w-4 h-4" /></button>
                      <button onClick={() => { if (window.confirm("Silmek istediginize emin misiniz?")) deleteMut.mutate(item.id); }} className="text-red-500 hover:text-red-700"><Trash2 className="w-4 h-4" /></button>
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
