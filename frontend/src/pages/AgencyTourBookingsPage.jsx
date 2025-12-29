import React, { useEffect, useMemo, useState } from "react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { toast } from "sonner";

const STATUS_LABELS = {
  new: "Yeni",
  approved: "Onaylandı",
  rejected: "Reddedildi",
  cancelled: "İptal",
};

export default function AgencyTourBookingsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("new");
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const norm = (s) => (s || "").toString().toLowerCase().trim();

  const bookingDate = (it) => {
    const d = it?.desired_date;
    if (d && typeof d === "string" && d.length >= 10) return d.slice(0, 10);
    const c = it?.created_at;
    if (c && typeof c === "string" && c.length >= 10) return c.slice(0, 10);
    return "";
  };

  const matchesQuery = (it, qn) => {
    if (!qn) return true;
    const hay = [
      it?.tour_title,
      it?.guest?.full_name,
      it?.guest?.phone,
      it?.guest?.email,
      it?.note,
      it?.status,
    ]
      .map(norm)
      .join(" ");
    return hay.includes(qn);
  };

  const inDateRange = (it, from, to) => {
    if (!from && !to) return true;
    const d = bookingDate(it);
    if (!d) return false;
    if (from && d < from) return false;
    if (to && d > to) return false;
    return true;
  };

  // Client-side filters
  const [q, setQ] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const resp = await api.get("/agency/tour-bookings", {
        params: status ? { status } : {},
      });
      setItems(Array.isArray(resp.data?.items) ? resp.data.items : []);
    } catch (e) {
      console.error(apiErrorMessage(e) || e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const changeStatus = async (id, nextStatus) => {
    if (!window.confirm(`Bu talebi '${STATUS_LABELS[nextStatus]}' durumuna almak istediğinize emin misiniz?`)) {
      return;
    }
    setActionLoadingId(id + nextStatus);
    try {
      await api.post(`/agency/tour-bookings/${id}/set-status`, { status: nextStatus });
      toast.success(nextStatus === "approved" ? "Talep onaylandı." : "Talep reddedildi.");
      await load();
    } catch (e) {
      toast.error(apiErrorMessage(e) || "İşlem başarısız");
    } finally {
      setActionLoadingId(null);
    }
  };

  const qn = norm(q);

  const filteredItems = useMemo(
    () => items.filter((it) => matchesQuery(it, qn)).filter((it) => inDateRange(it, fromDate, toDate)),
    [items, qn, fromDate, toDate]
  );

  return (
    <div className="max-w-6xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl font-semibold">Tur Rezervasyon Talepleri</h1>
        <div className="flex gap-2 text-sm">
          {[ 
            { key: "new", label: "Yeni" },
            { key: "approved", label: "Onaylandı" },
            { key: "rejected", label: "Reddedildi" },
            { key: "cancelled", label: "İptal" },
            { key: "", label: "Tümü" },
          ].map((s) => (
            <button
              key={s.key || "all"}
              type="button"
              onClick={() => setStatus(s.key)}
              className={`px-3 py-1 rounded-full border text-xs ${
                status === s.key ? "bg-primary text-primary-foreground border-primary" : "bg-white text-gray-700"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between text-xs sm:text-sm">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3 flex-1">
          <div className="flex flex-col gap-1 sm:w-64">
            <label className="font-medium text-xs text-gray-700">Arama</label>
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="İsim, telefon, tur adı, not..."
              className="w-full rounded-md border px-2 py-1.5 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/60 focus:border-primary"
            />
          </div>

          <div className="flex gap-2">
            <div className="flex flex-col gap-1">
              <label className="font-medium text-xs text-gray-700">Başlangıç</label>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="rounded-md border px-2 py-1.5 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/60 focus:border-primary"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="font-medium text-xs text-gray-700">Bitiş</label>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="rounded-md border px-2 py-1.5 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/60 focus:border-primary"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              setQ("");
              setFromDate("");
              setToDate("");
            }}
          >
            Filtreleri Temizle
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="text-sm text-gray-600">Yükleniyor…</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-gray-600">Bu filtre için talep bulunmuyor.</div>
      ) : filteredItems.length === 0 ? (
        <div className="text-sm text-gray-600">Arama veya tarih filtrelerine uyan talep bulunmuyor.</div>
      ) : (
        <div className="space-y-3">
          {filteredItems.map((r) => (
            <div
              key={r.id}
              data-testid="tour-booking-card"
              className="rounded-xl border bg-white p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 cursor-pointer hover:border-primary/60"
              onClick={() => window.location.assign(`/app/agency/tour-bookings/${r.id}`)}
            >
              <div className="flex-1 min-w-0">
                <div className="text-xs text-gray-500 mb-1">{r.tour_title || "Tur"}</div>
                <div className="font-medium text-sm">
                  {r.guest?.full_name} | {r.guest?.phone}
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  Tarih: {r.desired_date || "-"} | Kişi sayısı: {r.pax || 1}
                </div>
                {r.note ? (
                  <div className="text-xs text-gray-500 mt-1 line-clamp-2">Not: {r.note}</div>
                ) : null}
              </div>
              <div className="flex flex-col items-end gap-2 text-xs">
                <span
                  className={`px-2 py-1 rounded-full border ${
                    r.status === "new"
                      ? "bg-amber-50 border-amber-300 text-amber-700"
                      : r.status === "approved"
                      ? "bg-emerald-50 border-emerald-300 text-emerald-700"
                      : r.status === "rejected"
                      ? "bg-rose-50 border-rose-300 text-rose-700"
                      : "bg-gray-50 border-gray-300 text-gray-700"
                  }`}
                >
                  {STATUS_LABELS[r.status] || r.status}
                </span>
                {r.status === "new" && (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={actionLoadingId === r.id + "approved"}
                      onClick={() => changeStatus(r.id, "approved")}
                    >
                      {actionLoadingId === r.id + "approved" ? "Kaydediliyor…" : "Onayla"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={actionLoadingId === r.id + "rejected"}
                      onClick={() => changeStatus(r.id, "rejected")}
                    >
                      {actionLoadingId === r.id + "rejected" ? "Kaydediliyor…" : "Reddet"}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
