import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Truck, Plus, Edit, Trash2, Wrench, Calendar, X } from "lucide-react";

const VEHICLE_TYPES = [
  { value: "sedan", label: "Sedan" },
  { value: "minivan", label: "Minivan" },
  { value: "minibus", label: "Minibüs" },
  { value: "bus", label: "Otobüs" },
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
  const [maintenanceModal, setMaintenanceModal] = useState(null);
  const [showMaintForm, setShowMaintForm] = useState(false);
  const [calendarModal, setCalendarModal] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-vehicles"],
    queryFn: () => api.get("/admin/vehicles").then((r) => r.data),
  });

  const { data: maintData, isLoading: maintLoading } = useQuery({
    queryKey: ["vehicle-maintenance", maintenanceModal],
    queryFn: () => api.get(`/admin/vehicles/${maintenanceModal}/maintenance`).then((r) => r.data),
    enabled: !!maintenanceModal,
  });

  const { data: calData, isLoading: calLoading } = useQuery({
    queryKey: ["vehicle-calendar", calendarModal],
    queryFn: () => api.get(`/admin/vehicles/${calendarModal}/calendar`).then((r) => r.data),
    enabled: !!calendarModal,
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
  const addMaintMut = useMutation({
    mutationFn: ({ id, body }) => api.post(`/admin/vehicles/${id}/maintenance`, body),
    onSuccess: () => { qc.invalidateQueries(["vehicle-maintenance"]); setShowMaintForm(false); },
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

  const handleMaintSubmit = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    body.cost = parseFloat(body.cost || "0");
    addMaintMut.mutate({ id: maintenanceModal, body });
  };

  const items = data?.items || [];
  const maintRecords = maintData?.records || maintData?.maintenance || [];
  const calEvents = calData?.events || calData?.assignments || [];
  const maintVehicle = items.find((v) => v.id === maintenanceModal);
  const calVehicle = items.find((v) => v.id === calendarModal);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Truck className="w-7 h-7 text-emerald-600" /> Araç / Filo Yönetimi
          </h1>
          <p className="text-gray-500 mt-1">Araçları, şoförleri ve bakım kayıtlarını yönetin</p>
        </div>
        <button onClick={() => { setEditItem(null); setShowForm(true); }} className="flex items-center gap-2 bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700">
          <Plus className="w-4 h-4" /> Yeni Araç
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "Araç Düzenle" : "Yeni Araç"}</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input name="plate_number" defaultValue={editItem?.plate_number || ""} placeholder="Plaka" className="border rounded-lg px-3 py-2" required />
            <select name="vehicle_type" defaultValue={editItem?.vehicle_type || "minibus"} className="border rounded-lg px-3 py-2">
              {VEHICLE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <input name="brand" defaultValue={editItem?.brand || ""} placeholder="Marka" className="border rounded-lg px-3 py-2" />
            <input name="model" defaultValue={editItem?.model || ""} placeholder="Model" className="border rounded-lg px-3 py-2" />
            <input name="year" type="number" defaultValue={editItem?.year || 2024} placeholder="Yıl" className="border rounded-lg px-3 py-2" />
            <input name="capacity" type="number" defaultValue={editItem?.capacity || 0} placeholder="Kapasite" className="border rounded-lg px-3 py-2" />
            <input name="color" defaultValue={editItem?.color || ""} placeholder="Renk" className="border rounded-lg px-3 py-2" />
            <input name="driver_name" defaultValue={editItem?.driver_name || ""} placeholder="Şoför Adı" className="border rounded-lg px-3 py-2" />
            <input name="driver_phone" defaultValue={editItem?.driver_phone || ""} placeholder="Şoför Telefon" className="border rounded-lg px-3 py-2" />
            <input name="insurance_expiry" type="date" defaultValue={editItem?.insurance_expiry || ""} className="border rounded-lg px-3 py-2" />
            <input name="inspection_expiry" type="date" defaultValue={editItem?.inspection_expiry || ""} className="border rounded-lg px-3 py-2" />
            <input name="daily_cost" type="number" step="0.01" defaultValue={editItem?.daily_cost || 0} placeholder="Günlük Maliyet" className="border rounded-lg px-3 py-2" />
            <select name="status" defaultValue={editItem?.status || "active"} className="border rounded-lg px-3 py-2">
              <option value="active">Aktif</option>
              <option value="maintenance">Bakımda</option>
              <option value="inactive">Pasif</option>
            </select>
            <input name="notes" defaultValue={editItem?.notes || ""} placeholder="Notlar" className="border rounded-lg px-3 py-2 md:col-span-2" />
            <div className="flex gap-2 md:col-span-3">
              <button type="submit" className="bg-emerald-600 text-white px-6 py-2 rounded-lg hover:bg-emerald-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazgeç</button>
            </div>
          </form>
        </div>
      )}

      {maintenanceModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => { setMaintenanceModal(null); setShowMaintForm(false); }}>
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl max-h-[70vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Bakım Kayıtları — {maintVehicle?.plate_number}</h3>
              <button onClick={() => { setMaintenanceModal(null); setShowMaintForm(false); }} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>

            {!showMaintForm && (
              <button onClick={() => setShowMaintForm(true)} className="flex items-center gap-2 bg-emerald-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-emerald-700 mb-4">
                <Plus className="w-4 h-4" /> Bakım Ekle
              </button>
            )}

            {showMaintForm && (
              <form onSubmit={handleMaintSubmit} className="bg-gray-50 rounded-lg p-4 mb-4 grid grid-cols-2 gap-3">
                <select name="maintenance_type" className="border rounded-lg px-3 py-2 text-sm col-span-2">
                  <option value="periodic">Periyodik Bakım</option>
                  <option value="repair">Onarım</option>
                  <option value="tire_change">Lastik Değişimi</option>
                  <option value="oil_change">Yağ Değişimi</option>
                  <option value="inspection">Muayene</option>
                  <option value="other">Diğer</option>
                </select>
                <input name="date" type="date" className="border rounded-lg px-3 py-2 text-sm" required />
                <input name="cost" type="number" step="0.01" placeholder="Maliyet" className="border rounded-lg px-3 py-2 text-sm" />
                <input name="description" placeholder="Açıklama" className="border rounded-lg px-3 py-2 text-sm col-span-2" />
                <input name="next_maintenance_date" type="date" placeholder="Sonraki bakım" className="border rounded-lg px-3 py-2 text-sm" />
                <input name="mileage" placeholder="Kilometre" className="border rounded-lg px-3 py-2 text-sm" />
                <div className="col-span-2 flex gap-2">
                  <button type="submit" className="bg-emerald-600 text-white px-4 py-1.5 rounded-lg text-sm">Kaydet</button>
                  <button type="button" onClick={() => setShowMaintForm(false)} className="bg-gray-200 px-4 py-1.5 rounded-lg text-sm">Vazgeç</button>
                </div>
              </form>
            )}

            {maintLoading ? (
              <div className="text-center py-8 text-gray-400">Yükleniyor...</div>
            ) : maintRecords.length === 0 ? (
              <div className="text-center py-8">
                <Wrench className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">Henüz bakım kaydı yok</p>
              </div>
            ) : (
              <div className="space-y-3">
                {maintRecords.map((r, i) => (
                  <div key={i} className="p-3 bg-gray-50 rounded-lg border">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-sm">{r.maintenance_type || r.type}</span>
                      <span className="text-xs text-gray-500">{r.date}</span>
                    </div>
                    {r.description && <p className="text-sm text-gray-600 mt-1">{r.description}</p>}
                    <div className="flex gap-4 mt-2 text-xs text-gray-500">
                      {r.cost > 0 && <span>Maliyet: {r.cost} TRY</span>}
                      {r.mileage && <span>KM: {r.mileage}</span>}
                      {r.next_maintenance_date && <span>Sonraki: {r.next_maintenance_date}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {calendarModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setCalendarModal(null)}>
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl max-h-[70vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">{calVehicle?.plate_number} — Takvim</h3>
              <button onClick={() => setCalendarModal(null)} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>
            {calLoading ? (
              <div className="text-center py-8 text-gray-400">Yükleniyor...</div>
            ) : calEvents.length === 0 ? (
              <div className="text-center py-8">
                <Calendar className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">Atanmış görev yok</p>
              </div>
            ) : (
              <div className="space-y-2">
                {calEvents.map((ev, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full flex-shrink-0" />
                    <div>
                      <div className="font-medium text-sm">{ev.title || ev.type}</div>
                      <div className="text-xs text-gray-500">{ev.date} {ev.time || ""}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <Truck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Henüz araç kaydı yok</p>
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
                    {item.status === "active" ? "Aktif" : item.status === "maintenance" ? "Bakımda" : "Pasif"}
                  </span>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => setMaintenanceModal(item.id)} className="text-yellow-600 hover:text-yellow-800 p-1" title="Bakım"><Wrench className="w-4 h-4" /></button>
                  <button onClick={() => setCalendarModal(item.id)} className="text-orange-500 hover:text-orange-700 p-1" title="Takvim"><Calendar className="w-4 h-4" /></button>
                  <button onClick={() => { setEditItem(item); setShowForm(true); }} className="text-blue-600 hover:text-blue-800 p-1"><Edit className="w-4 h-4" /></button>
                  <button onClick={() => { if (window.confirm("Silmek istediginize emin misiniz?")) deleteMut.mutate(item.id); }} className="text-red-500 hover:text-red-700 p-1"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                <div>Tip: {VEHICLE_TYPES.find((t) => t.value === item.vehicle_type)?.label || item.vehicle_type}</div>
                <div>Kapasite: {item.capacity} kişi</div>
                {item.driver_name && <div>Şoför: {item.driver_name}</div>}
              </div>
              <div className="flex items-center justify-between mt-3 pt-3 border-t text-sm text-gray-500">
                <span>{item.daily_cost} {item.currency}/gün</span>
                {item.insurance_expiry && <span>Sigorta: {item.insurance_expiry}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
