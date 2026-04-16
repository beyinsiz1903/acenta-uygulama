import React, { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import {
  Bus, Plus, Search, Filter, Trash2, Edit, MapPin, Clock, Users, ChevronDown, X,
} from "lucide-react";

const TRANSFER_TYPES = [
  { value: "private", label: "Private Transfer" },
  { value: "shuttle", label: "Shuttle" },
  { value: "vip", label: "VIP Transfer" },
];

const STATUS_OPTIONS = [
  { value: "planned", label: "Planland\u0131", color: "bg-blue-100 text-blue-800" },
  { value: "confirmed", label: "Onayland\u0131", color: "bg-green-100 text-green-800" },
  { value: "in_progress", label: "Devam Ediyor", color: "bg-yellow-100 text-yellow-800" },
  { value: "completed", label: "Tamamland\u0131", color: "bg-gray-100 text-gray-800" },
  { value: "cancelled", label: "\u0130ptal", color: "bg-red-100 text-red-800" },
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

  const { data, isLoading } = useQuery({
    queryKey: ["admin-transfers", filterStatus, filterType],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      if (filterType) params.set("transfer_type", filterType);
      return api.get(`/admin/transfers?${params}`).then((r) => r.data);
    },
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

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Bus className="w-7 h-7 text-blue-600" /> Transfer Y\u00f6netimi
          </h1>
          <p className="text-gray-500 mt-1">Havalimanı, otel ve tur transferlerini y\u00f6netin</p>
        </div>
        <button onClick={() => { setEditItem(null); setShowForm(true); }} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
          <Plus className="w-4 h-4" /> Yeni Transfer
        </button>
      </div>

      <div className="flex gap-3 mb-4">
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">T\u00fcm Durumlar</option>
          {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">T\u00fcm Tipler</option>
          {TRANSFER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "Transfer D\u00fczenle" : "Yeni Transfer"}</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <select name="transfer_type" defaultValue={editItem?.transfer_type || "private"} className="border rounded-lg px-3 py-2">
              {TRANSFER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <input name="date" type="date" defaultValue={editItem?.date || ""} className="border rounded-lg px-3 py-2" required />
            <input name="pickup_time" type="time" defaultValue={editItem?.pickup_time || ""} className="border rounded-lg px-3 py-2" />
            <input name="pickup_location" defaultValue={editItem?.pickup_location || ""} placeholder="Al\u0131\u015f Noktas\u0131" className="border rounded-lg px-3 py-2" />
            <input name="dropoff_location" defaultValue={editItem?.dropoff_location || ""} placeholder="B\u0131rak\u0131\u015f Noktas\u0131" className="border rounded-lg px-3 py-2" />
            <input name="route_name" defaultValue={editItem?.route_name || ""} placeholder="G\u00fczergah Ad\u0131" className="border rounded-lg px-3 py-2" />
            <input name="driver_name" defaultValue={editItem?.driver_name || ""} placeholder="\u015eof\u00f6r Ad\u0131" className="border rounded-lg px-3 py-2" />
            <input name="pax_count" type="number" defaultValue={editItem?.pax_count || 1} placeholder="Yolcu Say\u0131s\u0131" className="border rounded-lg px-3 py-2" />
            <input name="price" type="number" step="0.01" defaultValue={editItem?.price || 0} placeholder="Fiyat" className="border rounded-lg px-3 py-2" />
            <select name="status" defaultValue={editItem?.status || "planned"} className="border rounded-lg px-3 py-2">
              {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <input name="notes" defaultValue={editItem?.notes || ""} placeholder="Notlar" className="border rounded-lg px-3 py-2 md:col-span-2" />
            <div className="flex gap-2 md:col-span-3">
              <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazge\u00e7</button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Y\u00fckleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <Bus className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Hen\u00fcz transfer kayd\u0131 yok</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tarih/Saat</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tip</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">G\u00fczergah</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">\u015eof\u00f6r</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Pax</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Durum</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">\u0130\u015flemler</th>
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
                  <td className="px-4 py-3">{item.driver_name || "-"}</td>
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
