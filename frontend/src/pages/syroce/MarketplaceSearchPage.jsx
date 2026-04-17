import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, apiErrorMessage } from "../../lib/api";
import {
  Search, Hotel, Star, Calendar, Users, MapPin, X, Loader2,
  CheckCircle2, AlertTriangle, FileText,
} from "lucide-react";

const today = () => new Date().toISOString().slice(0, 10);
const tomorrow = () => {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
};

const emptySearch = {
  city: "",
  check_in: today(),
  check_out: tomorrow(),
  adults: 2,
  children: 0,
  room_type: "",
  max_price: "",
  q: "",
};

const genPnr = () => `ACT-${Math.random().toString(36).slice(2, 10).toUpperCase()}`;

const emptyReservation = {
  guest_name: "",
  guest_email: "",
  guest_phone: "",
  special_requests: "",
  external_reference: "",
};

function StarRow({ count }) {
  const n = Math.max(0, Math.min(5, Number(count) || 0));
  return (
    <div className="inline-flex items-center gap-0.5 text-amber-500">
      {Array.from({ length: n }).map((_, i) => (
        <Star key={i} size={14} fill="currentColor" />
      ))}
    </div>
  );
}

function Banner({ kind, children, onClose }) {
  const palette = kind === "error"
    ? "bg-red-50 border-red-200 text-red-800"
    : "bg-emerald-50 border-emerald-200 text-emerald-800";
  const Icon = kind === "error" ? AlertTriangle : CheckCircle2;
  return (
    <div className={`flex items-start gap-2 p-3 rounded border ${palette}`}>
      <Icon size={18} className="mt-0.5 shrink-0" />
      <div className="flex-1 text-sm whitespace-pre-line">{children}</div>
      {onClose && (
        <button onClick={onClose} className="opacity-60 hover:opacity-100">
          <X size={16} />
        </button>
      )}
    </div>
  );
}

export default function MarketplaceSearchPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [form, setForm] = useState(emptySearch);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [bookModal, setBookModal] = useState(null); // { hotel, room }
  const [resForm, setResForm] = useState(emptyReservation);

  const F = (k) => ({
    value: form[k] ?? "",
    onChange: (e) => setForm((s) => ({ ...s, [k]: e.target.type === "number" ? e.target.value : e.target.value })),
  });

  const searchMut = useMutation({
    mutationFn: (payload) => api.post("/syroce-marketplace/search", payload).then((r) => r.data),
    onMutate: () => { setError(""); setSuccess(""); },
    onSuccess: (data) => setResults(data),
    onError: (err) => {
      setResults(null);
      setError(apiErrorMessage(err) || "Arama başarısız oldu.");
    },
  });

  const bookMut = useMutation({
    mutationFn: (payload) => api.post("/syroce-marketplace/reservations", payload).then((r) => r.data),
    onSuccess: (data) => {
      const code = data?.reservation?.syroce_confirmation_code || data?.reservation?.id;
      setSuccess(`Rezervasyon onaylandı: ${code}`);
      setBookModal(null);
      setResForm(emptyReservation);
      qc.invalidateQueries({ queryKey: ["marketplace-reservations"] });
    },
    onError: (err) => {
      setError(apiErrorMessage(err) || "Rezervasyon oluşturulamadı.");
    },
  });

  const handleSearch = (e) => {
    e?.preventDefault?.();
    if (form.check_out <= form.check_in) {
      setError("Çıkış tarihi giriş tarihinden büyük olmalı.");
      return;
    }
    const payload = {
      check_in: form.check_in,
      check_out: form.check_out,
      adults: Number(form.adults) || 1,
      children: Number(form.children) || 0,
    };
    if (form.city) payload.city = form.city;
    if (form.q) payload.q = form.q;
    if (form.room_type) payload.room_type = form.room_type;
    if (form.max_price) payload.max_price = Number(form.max_price);
    searchMut.mutate(payload);
  };

  const openBook = (hotel, room) => {
    setError("");
    setSuccess("");
    setResForm({ ...emptyReservation, external_reference: genPnr() });
    setBookModal({ hotel, room });
  };

  const submitBook = (e) => {
    e?.preventDefault?.();
    if (!bookModal) return;
    if (!resForm.guest_name || !resForm.guest_email || !resForm.guest_phone) {
      setError("Misafir adı, e-posta ve telefon zorunludur.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(resForm.guest_email)) {
      setError("Geçerli bir e-posta adresi girin.");
      return;
    }
    bookMut.mutate({
      tenant_id: bookModal.hotel.tenant_id,
      hotel_name: bookModal.hotel.hotel_name,
      room_type: bookModal.room.room_type,
      check_in: form.check_in,
      check_out: form.check_out,
      adults: Number(form.adults) || 1,
      children: Number(form.children) || 0,
      guest_name: resForm.guest_name,
      guest_email: resForm.guest_email,
      guest_phone: resForm.guest_phone,
      external_reference: resForm.external_reference || genPnr(),
      special_requests: resForm.special_requests || undefined,
      // total_amount intentionally NOT sent — server tarafı hesabı kabul edilir.
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Hotel className="text-blue-600" /> Otel Ara
          </h1>
          <p className="text-sm text-gray-500">
            Yalnızca onaylı sözleşmeniz olan oteller listelenir. Yeni bir otelle çalışmak için önce sözleşme teklif edin.
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate("/app/admin/syroce-marketplace/contracts?propose=1")}
          className="inline-flex items-center gap-2 border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 px-3 py-2 rounded text-sm"
        >
          <FileText size={16} /> Yeni Otelle Sözleşme Teklif Et
        </button>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="bg-white border rounded-lg p-4 grid grid-cols-2 md:grid-cols-6 gap-3 items-end">
        <div className="col-span-2 md:col-span-2">
          <label className="block text-xs text-gray-600 mb-1">Şehir / Otel ara</label>
          <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Antalya, İstanbul..." {...F("city")} />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Giriş</label>
          <input type="date" className="w-full border rounded px-3 py-2 text-sm" {...F("check_in")} />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Çıkış</label>
          <input type="date" className="w-full border rounded px-3 py-2 text-sm" {...F("check_out")} />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Yetişkin</label>
          <input type="number" min="1" max="20" className="w-full border rounded px-3 py-2 text-sm" {...F("adults")} />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Çocuk</label>
          <input type="number" min="0" max="20" className="w-full border rounded px-3 py-2 text-sm" {...F("children")} />
        </div>
        <div className="col-span-2 md:col-span-2">
          <label className="block text-xs text-gray-600 mb-1">Oda tipi (opsiyonel)</label>
          <input className="w-full border rounded px-3 py-2 text-sm" placeholder="standard, suite..." {...F("room_type")} />
        </div>
        <div className="col-span-2 md:col-span-2">
          <label className="block text-xs text-gray-600 mb-1">Maksimum toplam fiyat (TRY)</label>
          <input type="number" min="0" className="w-full border rounded px-3 py-2 text-sm" {...F("max_price")} />
        </div>
        <div className="col-span-2 md:col-span-2 flex justify-end">
          <button
            type="submit"
            disabled={searchMut.isPending}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-4 py-2 rounded text-sm"
          >
            {searchMut.isPending ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Ara
          </button>
        </div>
      </form>

      {error && <Banner kind="error" onClose={() => setError("")}>{error}</Banner>}
      {success && <Banner kind="success" onClose={() => setSuccess("")}>{success}</Banner>}

      {/* Results */}
      {results && (
        <div className="space-y-3">
          <div className="text-sm text-gray-600">
            Toplam <b>{results.total_hotels ?? results.results?.length ?? 0}</b> otel bulundu.
          </div>
          {(results.results || []).length === 0 && (
            <div className="bg-white border rounded p-6 text-center text-sm space-y-3">
              <div className="text-gray-500">
                Bu kriterlere uygun müsait oda bulunamadı.
              </div>
              <div className="text-xs text-gray-500">
                Aradığınız otelle henüz sözleşmeniz yoksa, sözleşme teklif edin — otelci onayladığında burada görünür.
              </div>
              <button
                type="button"
                onClick={() => navigate("/app/admin/syroce-marketplace/contracts?propose=1")}
                className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm"
              >
                <FileText size={16} /> Sözleşme Teklif Et
              </button>
            </div>
          )}
          {(results.results || []).map((hotel) => (
            <div key={hotel.tenant_id} className="bg-white border rounded-lg overflow-hidden">
              <div className="p-4 border-b bg-gray-50 flex flex-wrap items-center gap-3 justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-lg">{hotel.hotel_name}</h3>
                    <StarRow count={hotel.star_rating} />
                  </div>
                  <div className="text-xs text-gray-600 flex items-center gap-1 mt-1">
                    <MapPin size={12} /> {[hotel.city, hotel.country].filter(Boolean).join(", ")}
                  </div>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-600">
                    <tr>
                      <th className="text-left px-3 py-2">Oda Tipi</th>
                      <th className="text-right px-3 py-2">Geceler</th>
                      <th className="text-right px-3 py-2">Müşteri Fiyatı</th>
                      <th className="text-right px-3 py-2">Sizin Maliyetiniz</th>
                      <th className="text-center px-3 py-2">Komisyon</th>
                      <th className="px-3 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {(hotel.available_room_types || []).map((room, idx) => (
                      <tr key={`${room.room_type}-${idx}`} className="border-t">
                        <td className="px-3 py-2 font-medium">{room.room_type}</td>
                        <td className="px-3 py-2 text-right">{room.nights}</td>
                        <td className="px-3 py-2 text-right">{Number(room.total_price).toFixed(2)} TRY</td>
                        <td className="px-3 py-2 text-right text-emerald-700 font-medium">
                          {Number(room.agency_payable).toFixed(2)} TRY
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span className="inline-block bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded">
                            %{Number(room.commission_pct).toFixed(2)}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-right">
                          <button
                            onClick={() => openBook(hotel, room)}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-3 py-1.5 rounded"
                          >
                            Rezerve Et
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reservation modal */}
      {bookModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <form onSubmit={submitBook} className="bg-white rounded-lg w-full max-w-lg shadow-xl">
            <div className="flex items-center justify-between p-4 border-b">
              <div>
                <h3 className="font-semibold">Rezervasyon Oluştur</h3>
                <div className="text-xs text-gray-500">
                  {bookModal.hotel.hotel_name} • {bookModal.room.room_type} • {form.check_in} → {form.check_out}
                </div>
              </div>
              <button type="button" onClick={() => setBookModal(null)} className="text-gray-400 hover:text-gray-700">
                <X />
              </button>
            </div>
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs text-gray-600 mb-1">Misafir Adı *</label>
                  <input className="w-full border rounded px-3 py-2 text-sm" required value={resForm.guest_name}
                    onChange={(e) => setResForm((s) => ({ ...s, guest_name: e.target.value }))} />
                </div>
                <div>
                  <label className="block text-xs text-gray-600 mb-1">E-posta *</label>
                  <input type="email" className="w-full border rounded px-3 py-2 text-sm" required value={resForm.guest_email}
                    onChange={(e) => setResForm((s) => ({ ...s, guest_email: e.target.value }))} />
                </div>
                <div>
                  <label className="block text-xs text-gray-600 mb-1">Telefon *</label>
                  <input className="w-full border rounded px-3 py-2 text-sm" required value={resForm.guest_phone}
                    onChange={(e) => setResForm((s) => ({ ...s, guest_phone: e.target.value }))} />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs text-gray-600 mb-1">PNR (kendi referansınız) *</label>
                  <input className="w-full border rounded px-3 py-2 text-sm font-mono" required value={resForm.external_reference}
                    onChange={(e) => setResForm((s) => ({ ...s, external_reference: e.target.value }))} />
                  <div className="text-xs text-gray-500 mt-1">Tekrar gönderilemez (idempotency).</div>
                </div>
                <div className="col-span-2">
                  <label className="block text-xs text-gray-600 mb-1">Özel İstek</label>
                  <textarea rows={2} className="w-full border rounded px-3 py-2 text-sm" value={resForm.special_requests}
                    onChange={(e) => setResForm((s) => ({ ...s, special_requests: e.target.value }))} />
                </div>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-900 space-y-1">
                <div><b>Müşteri Fiyatı:</b> {Number(bookModal.room.total_price).toFixed(2)} TRY</div>
                <div><b>Sizin Maliyetiniz:</b> {Number(bookModal.room.agency_payable).toFixed(2)} TRY</div>
                <div><b>Komisyon:</b> %{Number(bookModal.room.commission_pct).toFixed(2)} ({Number(bookModal.room.agency_commission_amount).toFixed(2)} TRY)</div>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t bg-gray-50 rounded-b-lg">
              <button type="button" onClick={() => setBookModal(null)} className="px-4 py-2 text-sm border rounded">İptal</button>
              <button type="submit" disabled={bookMut.isPending} className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white rounded">
                {bookMut.isPending && <Loader2 size={14} className="animate-spin" />}
                Onayla & Rezerve Et
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
