import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Shield, Plus, Edit, Trash2, Search } from "lucide-react";
import { toast } from "sonner";

const STATUS_COLORS = {
  active: "bg-green-100 text-green-800",
  expired: "bg-gray-100 text-gray-600",
  cancelled: "bg-red-100 text-red-800",
  pending: "bg-yellow-100 text-yellow-800",
};

const STATUS_LABELS = {
  active: "Aktif",
  expired: "Süresi Dolmuş",
  cancelled: "İptal",
  pending: "Beklemede",
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

export default function AdminInsurancePage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-insurance", filterStatus],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      return api.get(`/admin/insurance?${params}`).then((r) => r.data);
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
    mutationFn: (body) => api.post("/admin/insurance", body),
    onSuccess: () => { qc.invalidateQueries(["admin-insurance"]); setShowForm(false); setEditItem(null); setSelectedCustomer(null); },
  });
  const patchMut = useMutation({
    mutationFn: ({ id, body }) => api.patch(`/admin/insurance/${id}`, body),
    onSuccess: () => { qc.invalidateQueries(["admin-insurance"]); setShowForm(false); setEditItem(null); setSelectedCustomer(null); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/insurance/${id}`),
    onSuccess: () => qc.invalidateQueries(["admin-insurance"]),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    body.coverage_amount = parseFloat(body.coverage_amount || "0");
    body.premium = parseFloat(body.premium || "0");
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
            <Shield className="w-7 h-7 text-teal-600" /> Sigorta Yönetimi
          </h1>
          <p className="text-gray-500 mt-1">Seyahat sigortası poliçelerini yönetin</p>
        </div>
        <button onClick={() => { setEditItem(null); setSelectedCustomer(null); setShowForm(true); }} className="flex items-center gap-2 bg-teal-600 text-white px-4 py-2 rounded-lg hover:bg-teal-700">
          <Plus className="w-4 h-4" /> Yeni Poliçe
        </button>
      </div>

      <div className="flex gap-3 mb-4">
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">Tüm Durumlar</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "Poliçe Düzenle" : "Yeni Sigorta Poliçesi"}</h3>
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
            <select name="policy_type" defaultValue={editItem?.policy_type || "travel"} className="border rounded-lg px-3 py-2">
              <option value="travel">Seyahat</option>
              <option value="health">Sağlık</option>
              <option value="cancellation">İptal</option>
              <option value="baggage">Bagaj</option>
              <option value="comprehensive">Kapsamlı</option>
            </select>
            <select name="provider" defaultValue={editItem?.provider || ""} className="border rounded-lg px-3 py-2">
              <option value="">Sağlayıcı Seçin</option>
              <option value="Mapfre">Mapfre</option>
              <option value="Allianz">Allianz</option>
              <option value="Axa">Axa</option>
              <option value="Eureko">Eureko</option>
              <option value="Groupama">Groupama</option>
              <option value="HDI">HDI</option>
            </select>
            <input name="policy_number" defaultValue={editItem?.policy_number || ""} placeholder="Poliçe No" className="border rounded-lg px-3 py-2" />
            <input name="destination" defaultValue={editItem?.destination || ""} placeholder="Destinasyon" className="border rounded-lg px-3 py-2" />
            <input name="start_date" type="date" defaultValue={editItem?.start_date || ""} className="border rounded-lg px-3 py-2" required />
            <input name="end_date" type="date" defaultValue={editItem?.end_date || ""} className="border rounded-lg px-3 py-2" required />
            <input name="coverage_amount" type="number" step="0.01" defaultValue={editItem?.coverage_amount || 0} placeholder="Teminat Tutarı" className="border rounded-lg px-3 py-2" />
            <input name="premium" type="number" step="0.01" defaultValue={editItem?.premium || 0} placeholder="Prim" className="border rounded-lg px-3 py-2" />
            <select name="status" defaultValue={editItem?.status || "active"} className="border rounded-lg px-3 py-2">
              {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <input name="notes" defaultValue={editItem?.notes || ""} placeholder="Notlar" className="border rounded-lg px-3 py-2" />
            <div className="flex gap-2 md:col-span-3">
              <button type="submit" className="bg-teal-600 text-white px-6 py-2 rounded-lg hover:bg-teal-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); setSelectedCustomer(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazgeç</button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Henüz sigorta poliçesi yok</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Poliçe</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Müşteri</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Sağlayıcı</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tarih</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Teminat</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Durum</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium">{item.policy_number || "-"}</div>
                    <div className="text-xs text-gray-500">{item.policy_type === "travel" ? "Seyahat" : item.policy_type === "health" ? "Sağlık" : item.policy_type === "cancellation" ? "İptal" : item.policy_type === "baggage" ? "Bagaj" : "Kapsamlı"}</div>
                  </td>
                  <td className="px-4 py-3">{item.customer_name}</td>
                  <td className="px-4 py-3">{item.provider}</td>
                  <td className="px-4 py-3 text-xs">{item.start_date} - {item.end_date}</td>
                  <td className="px-4 py-3">{item.coverage_amount} {item.currency}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[item.status] || "bg-gray-100"}`}>
                      {STATUS_LABELS[item.status] || item.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => openEdit(item)} className="text-blue-600 hover:text-blue-800 mr-2"><Edit className="w-4 h-4" /></button>
                    <button onClick={() => { if (window.confirm("Silmek istediginize emin misiniz?")) deleteMut.mutate(item.id); }} className="text-red-500 hover:text-red-700"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
