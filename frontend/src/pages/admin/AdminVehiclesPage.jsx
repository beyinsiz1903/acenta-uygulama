import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Truck, Plus, Edit, Trash2, Wrench, Calendar } from "lucide-react";

const VEHICLE_TYPES = [
  { value: "sedan", label: "Sedan" },
  { value: "minivan", label: "Minivan" },
  { value: "minibus", label: "Minib\u00fcs" },
  { value: "bus", label: "Otob\u00fcs" },
  { value: "vip", label: "VIP" },
  { value: "suv", label: "SUV" },
];

const STATUS_COLORS = {
  active: "bg-green-100 text-green-800",
  maintenance: "bg-yellow-100 text-yellow-800",
  inactive: "bg-gray-100 text-gray-600",
};

export default function AdminVehiclesPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-vehicles"],
    queryFn: () => api.get("/admin/vehicles").then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: (body) => api.post("/admin/vehicles", body),
    onSuccess: () => { qc.invalidateQueries(["admin-vehicles"]); setShowForm(false); setEditItem(null); },
  });
  const patchMut = useMutation({
    mutationFn: ({ id, body }) => api.patch(`/admin/vehicles/${id}`, body),
    onSuccess: () => { qc.invalidateQueries(["admin-vehicles"]); setShowForm(false); setEditItem(null); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/vehicles/${id}`),
    onSuccess: () => qc.invalidateQueries(["admin-vehicles"]),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    body.capacity = parseInt(body.capacity || "0", 10);
    body.year = parseInt(body.year || "2024", 10);
    body.daily_cost = parseFloat(body.daily_cost || "0");
    if (editItem) patchMut.mutate({ id: editItem.id, body });
    else createMut.mutate(body);
  };

  const items = data?.items || [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Truck className="w-7 h-7 text-emerald-600" /> Ara\u00e7 / Filo Y\u00f6netimi
          </h1>
          <p className="text-gray-500 mt-1">Ara\u00e7lar\u0131, \u015fof\u00f6rleri ve bak\u0131m kay\u0131tlar\u0131n\u0131 y\u00f6netin</p>
        </div>
        <button onClick={() => { setEditItem(null); setShowForm(true); }} className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700">
          <Plus className="w-4 h-4" /> Yeni Ara\u00e7
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "Ara\u00e7 D\u00fczenle" : "Yeni Ara\u00e7"}</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input name="plate_number" defaultValue={editItem?.plate_number || ""} placeholder="Plaka" className="border rounded-lg px-3 py-2" required />
            <select name="vehicle_type" defaultValue={editItem?.vehicle_type || "minibus"} className="border rounded-lg px-3 py-2">
              {VEHICLE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <input name="brand" defaultValue={editItem?.brand || ""} placeholder="Marka" className="border rounded-lg px-3 py-2" />
            <input name="model" defaultValue={editItem?.model || ""} placeholder="Model" className="border rounded-lg px-3 py-2" />
            <input name="year" type="number" defaultValue={editItem?.year || 2024} placeholder="Y\u0131l" className="border rounded-lg px-3 py-2" />
            <input name="capacity" type="number" defaultValue={editItem?.capacity || 0} placeholder="Kapasite" className="border rounded-lg px-3 py-2" />
            <input name="color" defaultValue={editItem?.color || ""} placeholder="Renk" className="border rounded-lg px-3 py-2" />
            <input name="driver_name" defaultValue={editItem?.driver_name || ""} placeholder="\u015eof\u00f6r Ad\u0131" className="border rounded-lg px-3 py-2" />
            <input name="driver_phone" defaultValue={editItem?.driver_phone || ""} placeholder="\u015eof\u00f6r Telefon" className="border rounded-lg px-3 py-2" />
            <input name="insurance_expiry" type="date" defaultValue={editItem?.insurance_expiry || ""} className="border rounded-lg px-3 py-2" />
            <input name="inspection_expiry" type="date" defaultValue={editItem?.inspection_expiry || ""} className="border rounded-lg px-3 py-2" />
            <input name="daily_cost" type="number" step="0.01" defaultValue={editItem?.daily_cost || 0} placeholder="G\u00fcnl\u00fck Maliyet" className="border rounded-lg px-3 py-2" />
            <select name="status" defaultValue={editItem?.status || "active"} className="border rounded-lg px-3 py-2">
              <option value="active">Aktif</option>
              <option value="maintenance">Bak\u0131mda</option>
              <option value="inactive">Pasif</option>
            </select>
            <input name="notes" defaultValue={editItem?.notes || ""} placeholder="Notlar" className="border rounded-lg px-3 py-2 md:col-span-2" />
            <div className="flex gap-2 md:col-span-3">
              <button type="submit" className="bg-emerald-600 text-white px-6 py-2 rounded-lg hover:bg-emerald-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazge\u00e7</button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Y\u00fckleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <Truck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Hen\u00fcz ara\u00e7 kayd\u0131 yok</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item) => (
            <div key={item.id} className="bg-white border rounded-xl p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-bold text-gray-900 text-lg">{item.plate_number}</h3>
                  <p className="text-sm text-gray-600">{item.brand} {item.model} ({item.year})</p>
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium mt-1 ${STATUS_COLORS[item.status] || STATUS_COLORS.inactive}`}>
                    {item.status === "active" ? "Aktif" : item.status === "maintenance" ? "Bak\u0131mda" : "Pasif"}
                  </span>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => { setEditItem(item); setShowForm(true); }} className="text-blue-600 hover:text-blue-800 p-1"><Edit className="w-4 h-4" /></button>
                  <button onClick={() => { if (window.confirm("Silmek istediginize emin misiniz?")) deleteMut.mutate(item.id); }} className="text-red-500 hover:text-red-700 p-1"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <div>Tip: {VEHICLE_TYPES.find((t) => t.value === item.vehicle_type)?.label || item.vehicle_type}</div>
                <div>Kapasite: {item.capacity} ki\u015fi</div>
                {item.driver_name && <div>\u015eof\u00f6r: {item.driver_name}</div>}
              </div>
              <div className="flex items-center justify-between mt-3 pt-3 border-t text-sm text-gray-500">
                <span>{item.daily_cost} {item.currency}/g\u00fcn</span>
                {item.insurance_expiry && <span>Sigorta: {item.insurance_expiry}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
