import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { Plane, Plus, Edit, Trash2, Users } from "lucide-react";

const STATUS_COLORS = {
  scheduled: "bg-blue-100 text-blue-800",
  confirmed: "bg-green-100 text-green-800",
  delayed: "bg-yellow-100 text-yellow-800",
  cancelled: "bg-red-100 text-red-800",
  completed: "bg-gray-100 text-gray-700",
};

export default function AdminFlightsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-flights"],
    queryFn: () => api.get("/admin/flights").then((r) => r.data),
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

  const items = data?.items || [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Plane className="w-7 h-7 text-sky-600" /> U\u00e7u\u015f Y\u00f6netimi
          </h1>
          <p className="text-gray-500 mt-1">Charter u\u00e7u\u015flar\u0131 ve kontenjanlar\u0131 y\u00f6netin</p>
        </div>
        <button onClick={() => { setEditItem(null); setShowForm(true); }} className="flex items-center gap-2 bg-sky-600 text-white px-4 py-2 rounded-lg hover:bg-sky-700">
          <Plus className="w-4 h-4" /> Yeni U\u00e7u\u015f
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-6 mb-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">{editItem ? "U\u00e7u\u015f D\u00fczenle" : "Yeni U\u00e7u\u015f"}</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input name="airline" defaultValue={editItem?.airline || ""} placeholder="Havayolu" className="border rounded-lg px-3 py-2" required />
            <input name="flight_number" defaultValue={editItem?.flight_number || ""} placeholder="U\u00e7u\u015f No" className="border rounded-lg px-3 py-2" />
            <select name="flight_type" defaultValue={editItem?.flight_type || "charter"} className="border rounded-lg px-3 py-2">
              <option value="charter">Charter</option>
              <option value="scheduled">Tarifeli</option>
            </select>
            <input name="departure_airport" defaultValue={editItem?.departure_airport || ""} placeholder="Kalk\u0131\u015f Havaliman\u0131 (IATA)" className="border rounded-lg px-3 py-2" />
            <input name="arrival_airport" defaultValue={editItem?.arrival_airport || ""} placeholder="Var\u0131\u015f Havaliman\u0131 (IATA)" className="border rounded-lg px-3 py-2" />
            <input name="aircraft_type" defaultValue={editItem?.aircraft_type || ""} placeholder="U\u00e7ak Tipi" className="border rounded-lg px-3 py-2" />
            <input name="departure_date" type="date" defaultValue={editItem?.departure_date || ""} className="border rounded-lg px-3 py-2" required />
            <input name="departure_time" type="time" defaultValue={editItem?.departure_time || ""} className="border rounded-lg px-3 py-2" />
            <input name="arrival_date" type="date" defaultValue={editItem?.arrival_date || ""} className="border rounded-lg px-3 py-2" />
            <input name="arrival_time" type="time" defaultValue={editItem?.arrival_time || ""} className="border rounded-lg px-3 py-2" />
            <input name="total_seats" type="number" defaultValue={editItem?.total_seats || 0} placeholder="Toplam Koltuk" className="border rounded-lg px-3 py-2" />
            <input name="available_seats" type="number" defaultValue={editItem?.available_seats || 0} placeholder="Bo\u015f Koltuk" className="border rounded-lg px-3 py-2" />
            <input name="base_price" type="number" step="0.01" defaultValue={editItem?.base_price || 0} placeholder="Fiyat" className="border rounded-lg px-3 py-2" />
            <input name="baggage_allowance" defaultValue={editItem?.baggage_allowance || "20kg"} placeholder="Bagaj" className="border rounded-lg px-3 py-2" />
            <select name="status" defaultValue={editItem?.status || "scheduled"} className="border rounded-lg px-3 py-2">
              <option value="scheduled">Planland\u0131</option>
              <option value="confirmed">Onayland\u0131</option>
              <option value="delayed">Gecikmeli</option>
              <option value="cancelled">\u0130ptal</option>
              <option value="completed">Tamamland\u0131</option>
            </select>
            <div className="flex gap-2 md:col-span-3">
              <button type="submit" className="bg-sky-600 text-white px-6 py-2 rounded-lg hover:bg-sky-700">Kaydet</button>
              <button type="button" onClick={() => { setShowForm(false); setEditItem(null); }} className="bg-gray-200 px-6 py-2 rounded-lg">Vazge\u00e7</button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Y\u00fckleniyor...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border">
          <Plane className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Hen\u00fcz u\u00e7u\u015f kayd\u0131 yok</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">U\u00e7u\u015f</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">G\u00fczergah</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Tarih</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Koltuk</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Fiyat</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Durum</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">\u0130\u015flemler</th>
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
                      {item.status}
                    </span>
                  </td>
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
