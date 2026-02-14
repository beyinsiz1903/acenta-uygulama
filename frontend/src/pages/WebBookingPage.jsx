import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";

export default function WebBookingPage() {
  const [hotels, setHotels] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [form, setForm] = useState({
    hotel_id: "",
    room_type_id: "",
    package_id: "",
    check_in: "",
    check_out: "",
    adults: 2,
    children: 0,
    full_name: "",
    email: "",
    phone: "",
    price_total: 5000,
    currency: "TRY",
  });

  useEffect(() => {
    async function loadHotels() {
      try {
        const res = await api.get("/web/hotels");
        setHotels(res.data || []);
      } catch (e) {
        console.error("[WebBooking] hotels load error", e);
      }
    }
    void loadHotels();
  }, []);

  useEffect(() => {
    async function loadHotelDeps() {
      if (!form.hotel_id) {
        setRooms([]);
        setPackages([]);
        setForm((prev) => ({ ...prev, room_type_id: "", package_id: "" }));
        return;
      }
      try {
        const [roomsRes, packagesRes] = await Promise.all([
          api.get(`/web/hotels/${form.hotel_id}/rooms`),
          api.get(`/web/hotels/${form.hotel_id}/packages`),
        ]);
        setRooms(roomsRes.data || []);
        setPackages(packagesRes.data || []);
        setForm((prev) => ({ ...prev, room_type_id: "", package_id: "" }));
      } catch (e) {
        console.error("[WebBooking] hotel deps load error", e);
        setRooms([]);
        setPackages([]);
      }
    }
    void loadHotelDeps();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.hotel_id]);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!form.hotel_id || !form.check_in || !form.check_out || !form.full_name || !form.email || !form.phone) {
      setError("Lütfen zorunlu alanları doldurun.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        hotel_id: form.hotel_id,
        room_type_id: form.room_type_id || null,
        check_in: form.check_in,
        check_out: form.check_out,
        adults: Number(form.adults) || 1,
        children: Number(form.children) || 0,
        price_total: Number(form.price_total) || 0,
        currency: form.currency || "TRY",
        package_id: form.package_id || undefined,
        guest: {
          full_name: form.full_name,
          email: form.email,
          phone: form.phone,
        },
      };

      await api.post("/web/bookings", payload);
      setSuccess("Rezervasyon talebiniz alınmıştır.");
      setForm((prev) => ({
        ...prev,
        check_in: "",
        check_out: "",
        adults: 2,
        children: 0,
        price_total: 5000,
        full_name: "",
        email: "",
        phone: "",
      }));
    } catch (e) {
      console.error("[WebBooking] submit error", e);
      setError(apiErrorMessage ? apiErrorMessage(e) : "Bir hata oluştu");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-xl rounded-xl bg-white shadow-sm border p-6 space-y-4">
        <h1 className="text-2xl font-semibold mb-2">Rezervasyon Talebi</h1>
        <p className="text-sm text-muted-foreground mb-4">
          Bu form üzerinden hızlıca rezervasyon talebi oluşturabilirsiniz. Talebiniz acenta ekibi tarafından işlenerek
          otele iletilir.
        </p>

        {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-2">{error}</div>}
        {success && (
          <div className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md p-2">
            {success}
          </div>
        )}

        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Otel *</label>
            <select
              name="hotel_id"
              value={form.hotel_id}
              onChange={handleChange}
              className="w-full h-9 rounded-md border bg-white px-2 text-sm"
              required
            >
              <option value="">Otel seçin</option>
              {hotels.map((h) => (
                <option key={h.id || h._id} value={h.id || h._id}>
                  {h.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Oda Tipi</label>
            <select
              name="room_type_id"
              value={form.room_type_id}
              onChange={handleChange}
              className="w-full h-9 rounded-md border bg-white px-2 text-sm"
            >
              <option value="">Farketmez</option>
              {rooms.map((r) => (
                <option key={r.id || r._id} value={r.id || r._id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Paket (opsiyonel)</label>
            <select
              name="package_id"
              value={form.package_id}
              onChange={handleChange}
              className="w-full h-9 rounded-md border bg-white px-2 text-sm"
            >
              <option value="">Paket seçmeden devam et</option>
              {packages.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {p.price != null ? ` — ${p.price} ${p.currency || "TRY"}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Giriş Tarihi *</label>
              <input
                type="date"
                name="check_in"
                value={form.check_in}
                onChange={handleChange}
                className="w-full h-9 rounded-md border bg-white px-2 text-sm"
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Çıkış Tarihi *</label>
              <input
                type="date"
                name="check_out"
                value={form.check_out}
                onChange={handleChange}
                className="w-full h-9 rounded-md border bg-white px-2 text-sm"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Yetişkin</label>
              <input
                type="number"
                name="adults"
                min={1}
                max={10}
                value={form.adults}
                onChange={handleChange}
                className="w-full h-9 rounded-md border bg-white px-2 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-foreground">Çocuk</label>
              <input
                type="number"
                name="children"
                min={0}
                max={10}
                value={form.children}
                onChange={handleChange}
                className="w-full h-9 rounded-md border bg-white px-2 text-sm"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Toplam Fiyat (TRY)</label>
            <input
              type="number"
              name="price_total"
              min={1}
              value={form.price_total}
              onChange={handleChange}
              className="w-full h-9 rounded-md border bg-white px-2 text-sm"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Ad Soyad *</label>
            <input
              type="text"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              className="w-full h-9 rounded-md border bg-white px-2 text-sm"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Email *</label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              className="w-full h-9 rounded-md border bg-white px-2 text-sm"
              required
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-medium text-foreground">Telefon *</label>
            <input
              type="text"
              name="phone"
              value={form.phone}
              onChange={handleChange}
              className="w-full h-9 rounded-md border bg-white px-2 text-sm"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-10 rounded-md bg-primary text-primary-foreground text-sm font-medium mt-2 disabled:opacity-60"
          >
            {loading ? "Gönderiliyor..." : "Rezervasyon Talebi Gönder"}
          </button>
        </form>
      </div>
    </div>
  );
}
