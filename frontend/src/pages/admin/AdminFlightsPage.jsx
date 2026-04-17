import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Plane, Plus, Edit, Trash2, Users, X, UserPlus, UserMinus } from "lucide-react";

const STATUS_COLORS = {
  scheduled: "bg-blue-100 text-blue-800",
  confirmed: "bg-green-100 text-green-800",
  delayed: "bg-yellow-100 text-yellow-800",
  cancelled: "bg-red-100 text-red-800",
  completed: "bg-gray-100 text-gray-700",
};
const STATUS_LABELS = {
  scheduled: "Planlandı",
  confirmed: "Onaylandı",
  delayed: "Gecikmeli",
  cancelled: "İptal",
  completed: "Tamamlandı",
};

export default function AdminFlightsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [passengerModal, setPassengerModal] = useState(null);
  const [addPaxForm, setAddPaxForm] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-flights"],
    queryFn: () => api.get("/admin/flights").then((r) => r.data),
  });

  const { data: paxData, isLoading: paxLoading } = useQuery({
    queryKey: ["flight-passengers", passengerModal],
    queryFn: () => api.get(`/admin/flights/${passengerModal}/passengers`).then((r) => r.data),
    enabled: !!passengerModal,
  });

  const createMut = useMutation({
    mutationFn: (body) => api.post("/admin/flights", body),
    onSuccess: () => { qc.invalidateQueries(["admin-flights"]); setShowForm(false); setEditItem(null); },
  });
  const patchMut = useMutation({
    mutationFn: ({ id, body }) => api.patch(`/admin/flights/${id}`, body),
    onSuccess: () => { qc.invalidateQueries(["admin-flights"]); setShowForm(false); setEditItem(null); },
  });
  const deleteMut = useMutation({
    mutationFn: (id) => api.delete(`/admin/flights/${id}`),
    onSuccess: () => qc.invalidateQueries(["admin-flights"]),
  });
  const addPaxMut = useMutation({
    mutationFn: ({ flightId, body }) => api.post(`/admin/flights/${flightId}/passengers`, body),
    onSuccess: () => { qc.invalidateQueries(["flight-passengers"]); qc.invalidateQueries(["admin-flights"]); setAddPaxForm(false); },
  });
  const removePaxMut = useMutation({
    mutationFn: ({ flightId, passengerId }) => api.delete(`/admin/flights/${flightId}/passengers/${passengerId}`),
    onSuccess: () => { qc.invalidateQueries(["flight-passengers"]); qc.invalidateQueries(["admin-flights"]); },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    body.total_seats = parseInt(body.total_seats || "0", 10);
    body.available_seats = parseInt(body.available_seats || "0", 10);
    body.base_price = parseFloat(body.base_price || "0");
    if (editItem) patchMut.mutate({ id: editItem.id, body });
    else createMut.mutate(body);
  };

  const handleAddPax = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd.entries());
    addPaxMut.mutate({ flightId: passengerModal, body });
  };

  const items = data?.items || [];
  const passengers = paxData?.passengers || [];
  const currentFlight = items.find((f) => f.id === passengerModal);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Plane className="w-7 h-7 text-sky-600" /> Uçuş Yönetimi
          </h1>
          <p className="text-gray-500 mt-1">Charter uçuşları ve kontenjanları yönetin</p>
        </div>
        <button onClick={() => { setEditItem(null); setShowForm(true); }} className="flex items-center gap-2 bg-sky-600 text-white px-4 py-2 rounded-lg hover:bg-sky-700">
          <Plus className="w-4 h-4" /> Yeni Uçuş
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "Uçuş Düzenle" : "Yeni Uçuş"}</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input name="airline" defaultValue={editItem?.airline || ""} placeholder="Havayolu" className="border rounded-lg px-3 py-2" required />
            <input name="flight_number" defaultValue={editItem?.flight_number || ""} placeholder="Uçuş No" className="border rounded-lg px-3 py-2" />
            <select name="flight_type" defaultValue={editItem?.flight_type || "charter"} className="border rounded-lg px-3 py-2">
              <option value="charter">Charter</option>
              <option value="scheduled">Tarifeli</option>
            </select>
            <input name="departure_airport" defaultValue={editItem?.departure_airport || ""} placeholder="Kalkış (IATA)" className="border rounded-lg px-3 py-2" />
            <input name="arrival_airport" defaultValue={editItem?.arrival_airport || ""} placeholder="Varış (IATA)" className="border rounded-lg px-3 py-2" />
            <input name="aircraft_type" defaultValue={editItem?.aircraft_type || ""} placeholder="Uçak Tipi" className="border rounded-lg px-3 py-2" />
            <input name="departure_date" type="date" defaultValue={editItem?.departure_date || ""} className="border rounded-lg px-3 py-2" required />
            <input name="departure_time" type="time" defaultValue={editItem?.departure_time || ""} className="border rounded-lg px-3 py-2" />
            <input name="arrival_date" type="date" defaultValue={editItem?.arrival_date || ""} className="border rounded-lg px-3 py-2" />
            <input name="arrival_time" type="time" defaultValue={editItem?.arrival_time || ""} className="border rounded-lg px-3 py-2" />
            <input name="total_seats" type="number" defaultValue={editItem?.total_seats || 0} placeholder="Toplam Koltuk" className="border rounded-lg px-3 py-2" />
            <input name="available_seats" type="number" defaultValue={editItem?.available_seats || 0} placeholder="Boş Koltuk" className="border rounded-lg px-3 py-2" />
            <input name="base_price" type="number" step="0.01" defaultValue={editItem?.base_price || 0} placeholder="Fiyat" className="border rounded-lg px-3 py-2" />
            <input name="baggage_allowance" defaultValue={editItem?.baggage_allowance || "20kg"} placeholder="Bagaj" className="border rounded-lg px-3 py-2" />
            <select name="status" defaultValue={editItem?.status || "scheduled"} className="border rounded-lg px-3 py-2">
              {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <div className="flex gap-2 md:col-span-3">
              <button type="submit" className="bg-sky-600 text-white px-6 py-2 rounded-lg hover:bg-sky-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazgeç</button>
            </div>
          </form>
        </div>
      )}

      {passengerModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => { setPassengerModal(null); setAddPaxForm(false); }}>
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl shadow-xl max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">
                Yolcu Listesi — {currentFlight?.airline} {currentFlight?.flight_number}
              </h3>
              <button onClick={() => { setPassengerModal(null); setAddPaxForm(false); }} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
            </div>

            {!addPaxForm && (
              <button onClick={() => setAddPaxForm(true)} className="flex items-center gap-2 bg-sky-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-sky-700 mb-4">
                <UserPlus className="w-4 h-4" /> Yolcu Ekle
              </button>
            )}

            {addPaxForm && (
              <form onSubmit={handleAddPax} className="bg-gray-50 rounded-lg p-4 mb-4 grid grid-cols-2 gap-3">
                <input name="name" placeholder="Ad Soyad" className="border rounded-lg px-3 py-2 text-sm" required />
                <input name="passport_number" placeholder="Pasaport No" className="border rounded-lg px-3 py-2 text-sm" />
                <input name="seat_number" placeholder="Koltuk No" className="border rounded-lg px-3 py-2 text-sm" />
                <input name="ticket_number" placeholder="Bilet No" className="border rounded-lg px-3 py-2 text-sm" />
                <div className="col-span-2 flex gap-2">
                  <button type="submit" className="bg-sky-600 text-white px-4 py-1.5 rounded-lg text-sm">Ekle</button>
                  <button type="button" onClick={() => setAddPaxForm(false)} className="bg-gray-200 px-4 py-1.5 rounded-lg text-sm">Vazgeç</button>
                </div>
              </form>
            )}

            {paxLoading ? (
              <div className="text-center py-8 text-gray-400">Yükleniyor...</div>
            ) : passengers.length === 0 ? (
              <div className="text-center py-8">
                <Users className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-gray-500 text-sm">Henüz yolcu eklenmedi</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-3 py-2 font-medium text-gray-600">Ad Soyad</th>
                    <th className="text-left px-3 py-2 font-medium text-gray-600">Pasaport</th>
                    <th className="text-left px-3 py-2 font-medium text-gray-600">Koltuk</th>
                    <th className="text-left px-3 py-2 font-medium text-gray-600">Bilet</th>
                    <th className="text-right px-3 py-2 font-medium text-gray-600">İşlem</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {passengers.map((p) => (
                    <tr key={p.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 font-medium">{p.name}</td>
                      <td className="px-3 py-2">{p.passport_number}</td>
                      <td className="px-3 py-2">{p.seat_number}</td>
                      <td className="px-3 py-2">{p.ticket_number}</td>
                      <td className="px-3 py-2 text-right">
                        <button
                          onClick={() => { if (window.confirm("Yolcuyu silmek istediginize emin misiniz?")) removePaxMut.mutate({ flightId: passengerModal, passengerId: p.id }); }}
                          className="text-red-500 hover:text-red-700"
                        >
                          <UserMinus className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="mt-3 text-xs text-gray-400">Toplam: {passengers.length} yolcu</div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Yükleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <Plane className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Henüz uçuş kaydı yok</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Uçuş</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Güzergah</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tarih</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Koltuk</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fiyat</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Durum</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium">{item.airline} {item.flight_number}</div>
                    <div className="text-xs text-gray-500">{item.aircraft_type}</div>
                  </td>
                  <td className="px-4 py-3 font-medium">{item.departure_airport} → {item.arrival_airport}</td>
                  <td className="px-4 py-3">
                    <div>{item.departure_date}</div>
                    <div className="text-xs text-gray-500">{item.departure_time}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <Users className="w-3 h-3" /> {item.available_seats}/{item.total_seats}
                    </div>
                  </td>
                  <td className="px-4 py-3">{item.base_price} {item.currency}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[item.status] || "bg-gray-100"}`}>
                      {STATUS_LABELS[item.status] || item.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => setPassengerModal(item.id)} className="text-indigo-600 hover:text-indigo-800 mr-2" title="Yolcu Listesi">
                      <Users className="w-4 h-4" />
                    </button>
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
