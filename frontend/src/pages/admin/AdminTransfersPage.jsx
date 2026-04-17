import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import {
  Bus, Plus, Edit, Trash2, MapPin, UserCheck, Truck, X,
} from "lucide-react";

const TRANSFER_TYPES = [
  { value: "private", label: "Private Transfer" },
  { value: "shuttle", label: "Shuttle" },
  { value: "vip", label: "VIP Transfer" },
];

const STATUS_OPTIONS = [
  { value: "planned", label: "Planlandı", color: "bg-blue-100 text-blue-800" },
  { value: "confirmed", label: "Onaylandı", color: "bg-green-100 text-green-800" },
  { value: "in_progress", label: "Devam Ediyor", color: "bg-yellow-100 text-yellow-800" },
  { value: "completed", label: "Tamamlandı", color: "bg-gray-100 text-gray-800" },
  { value: "cancelled", label: "İptal", color: "bg-red-100 text-red-800" },
];

function StatusBadge({ status }) {
  const s = STATUS_OPTIONS.find((o) => o.value === status) || STATUS_OPTIONS[0];
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${s.color}`}>{s.label}</span>;
}

export default function AdminTransfersPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [assignModal, setAssignModal] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-transfers", filterStatus, filterType],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      if (filterType) params.set("transfer_type", filterType);
      return api.get(`/admin/transfers?${params}`).then((r) => r.data);
    },
  });

  const { data: guidesData } = useQuery({
    queryKey: ["admin-guides-list"],
    queryFn: () => api.get("/admin/guides?page_size=200").then((r) => r.data),
  });

  const { data: vehiclesData } = useQuery({
    queryKey: ["admin-vehicles-list"],
    queryFn: () => api.get("/admin/vehicles?page_size=200").then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: (body) => api.post("/admin/transfers", body),
    onSuccess: () => { qc.invalidateQueries(["admin-transfers"]); setShowForm(false); setEditItem(null); },
  });
  const patchMut = useMutation({
    mutationFn: ({ id, body }) => api.patch(`/admin/transfers/${id}`, body),
    onSuccess: () => { qc.invalidateQueries(["admin-transfers"]); setShowForm(false); setEditItem(null); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/transfers/${id}`),
    onSuccess: () => qc.invalidateQueries(["admin-transfers"]),
  });
  const assignVehicleMut = useMutation({
    mutationFn: ({ id, vehicle_id, driver_name }) =>
      api.post(`/admin/transfers/${id}/assign-vehicle`, { vehicle_id, driver_name }),
    onSuccess: () => { qc.invalidateQueries(["admin-transfers"]); setAssignModal(null); },
  });
  const assignGuideMut = useMutation({
    mutationFn: ({ id, guide_id }) =>
      api.post(`/admin/transfers/${id}/assign-guide`, { guide_id }),
    onSuccess: () => { qc.invalidateQueries(["admin-transfers"]); setAssignModal(null); },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    body.pax_count = parseInt(body.pax_count || "1", 10);
    body.price = parseFloat(body.price || "0");
    if (editItem) patchMut.mutate({ id: editItem.id, body });
    else createMut.mutate(body);
  };

  const items = data?.items || [];
  const guides = guidesData?.items || [];
  const vehicles = vehiclesData?.items || [];

  const getGuideName = (id) => guides.find((g) => g.id === id)?.name || "";
  const getVehiclePlate = (id) => {
    const v = vehicles.find((v) => v.id === id);
    return v ? `${v.plate_number} (${v.brand || ""})` : "";
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Bus className="w-7 h-7 text-blue-600" /> Transfer Yönetimi
          </h1>
          <p className="text-gray-500 mt-1">Havalimanı, otel ve tur transferlerini yönetin</p>
        </div>
        <button onClick={() => { setEditItem(null); setShowForm(true); }} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" /> Yeni Transfer
        </button>
      </div>

      <div className="flex gap-3 mb-4">
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">Tüm Durumlar</option>
          {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">Tüm Tipler</option>
          {TRANSFER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "Transfer Düzenle" : "Yeni Transfer"}</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <select name="transfer_type" defaultValue={editItem?.transfer_type || "private"} className="border rounded-lg px-3 py-2">
              {TRANSFER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <input name="date" type="date" defaultValue={editItem?.date || ""} className="border rounded-lg px-3 py-2" required />
            <input name="pickup_time" type="time" defaultValue={editItem?.pickup_time || ""} className="border rounded-lg px-3 py-2" />
            <input name="pickup_location" defaultValue={editItem?.pickup_location || ""} placeholder="Alış Noktası" className="border rounded-lg px-3 py-2" />
            <input name="dropoff_location" defaultValue={editItem?.dropoff_location || ""} placeholder="Bırakış Noktası" className="border rounded-lg px-3 py-2" />
            <input name="route_name" defaultValue={editItem?.route_name || ""} placeholder="Güzergah Adı" className="border rounded-lg px-3 py-2" />
            <select name="vehicle_id" defaultValue={editItem?.vehicle_id || ""} className="border rounded-lg px-3 py-2">
              <option value="">Araç Seçin (opsiyonel)</option>
              {vehicles.filter((v) => v.status === "active").map((v) => (
                <option key={v.id} value={v.id}>{v.plate_number} - {v.brand} {v.model} ({v.capacity} kişi)</option>
              ))}
            </select>
            <select name="guide_id" defaultValue={editItem?.guide_id || ""} className="border rounded-lg px-3 py-2">
              <option value="">Rehber Seçin (opsiyonel)</option>
              {guides.filter((g) => g.status === "active").map((g) => (
                <option key={g.id} value={g.id}>{g.name} - {g.languages?.join(", ")}</option>
              ))}
            </select>
            <input name="driver_name" defaultValue={editItem?.driver_name || ""} placeholder="Şoför Adı" className="border rounded-lg px-3 py-2" />
            <input name="pax_count" type="number" defaultValue={editItem?.pax_count || 1} placeholder="Yolcu Sayısı" className="border rounded-lg px-3 py-2" />
            <input name="price" type="number" step="0.01" defaultValue={editItem?.price || 0} placeholder="Fiyat" className="border rounded-lg px-3 py-2" />
            <select name="status" defaultValue={editItem?.status || "planned"} className="border rounded-lg px-3 py-2">
              {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <input name="booking_id" defaultValue={editItem?.booking_id || ""} placeholder="Rezervasyon ID (opsiyonel)" className="border rounded-lg px-3 py-2" />
            <input name="notes" defaultValue={editItem?.notes || ""} placeholder="Notlar" className="border rounded-lg px-3 py-2 md:col-span-2" />
            <div className="flex gap-2 md:col-span-3">
              <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazgeç</button>
            </div>
          </form>
        </div>
      )}

      {assignModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setAssignModal(null)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">
                {assignModal.type === "vehicle" ? "Araç Ata" : "Rehber Ata"}
              </h3>
              <button onClick={() => setAssignModal(null)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            {assignModal.type === "vehicle" ? (
              <div className="space-y-3">
                {vehicles.filter((v) => v.status === "active").map((v) => (
                  <button
                    key={v.id}
                    onClick={() => assignVehicleMut.mutate({ id: assignModal.transferId, vehicle_id: v.id, driver_name: v.driver_name || "" })}
                    className={`w-full text-left p-3 rounded-lg border hover:bg-blue-50 hover:border-blue-300 transition ${assignModal.currentId === v.id ? "bg-blue-50 border-blue-400" : ""}`}
                  >
                    <div className="font-medium">{v.plate_number}</div>
                    <div className="text-sm text-gray-500">{v.brand} {v.model} · {v.capacity} kişi · Şoför: {v.driver_name || "-"}</div>
                  </button>
                ))}
                {vehicles.filter((v) => v.status === "active").length === 0 && (
                  <p className="text-gray-500 text-center py-4">Aktif araç bulunamadı</p>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {guides.filter((g) => g.status === "active").map((g) => (
                  <button
                    key={g.id}
                    onClick={() => assignGuideMut.mutate({ id: assignModal.transferId, guide_id: g.id })}
                    className={`w-full text-left p-3 rounded-lg border hover:bg-indigo-50 hover:border-indigo-300 transition ${assignModal.currentId === g.id ? "bg-indigo-50 border-indigo-400" : ""}`}
                  >
                    <div className="font-medium">{g.name}</div>
                    <div className="text-sm text-gray-500">{g.languages?.join(", ")} · {g.daily_rate} {g.currency}/gün</div>
                  </button>
                ))}
                {guides.filter((g) => g.status === "active").length === 0 && (
                  <p className="text-gray-500 text-center py-4">Aktif rehber bulunamadı</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <Bus className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Henüz transfer kaydı yok</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tarih/Saat</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tip</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Güzergah</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Araç</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Rehber</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Pax</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Durum</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium">{item.date}</div>
                    <div className="text-xs text-gray-500">{item.pickup_time}</div>
                  </td>
                  <td className="px-4 py-3">{TRANSFER_TYPES.find((t) => t.value === item.transfer_type)?.label || item.transfer_type}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-gray-400" />
                      {item.pickup_location} → {item.dropoff_location}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setAssignModal({ type: "vehicle", transferId: item.id, currentId: item.vehicle_id })}
                      className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg border ${item.vehicle_id ? "bg-emerald-50 border-emerald-300 text-emerald-700" : "bg-gray-50 border-gray-300 text-gray-500 hover:bg-blue-50"}`}
                    >
                      <Truck className="w-3 h-3" />
                      {item.vehicle_id ? getVehiclePlate(item.vehicle_id) || item.driver_name || "Atandı" : "Ata"}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => setAssignModal({ type: "guide", transferId: item.id, currentId: item.guide_id })}
                      className={`flex items-center gap-1 text-xs px-2 py-1 rounded-lg border ${item.guide_id ? "bg-indigo-50 border-indigo-300 text-indigo-700" : "bg-gray-50 border-gray-300 text-gray-500 hover:bg-blue-50"}`}
                    >
                      <UserCheck className="w-3 h-3" />
                      {item.guide_id ? getGuideName(item.guide_id) || "Atandı" : "Ata"}
                    </button>
                  </td>
                  <td className="px-4 py-3">{item.pax_count}</td>
                  <td className="px-4 py-3"><StatusBadge status={item.status} /></td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => { setEditItem(item); setShowForm(true); }} className="text-blue-600 hover:text-blue-800 mr-2"><Edit className="w-4 h-4" /></button>
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
