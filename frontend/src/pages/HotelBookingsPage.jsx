import React, { useEffect, useMemo, useState } from "react";
import { Calendar, Loader2, AlertCircle, XCircle, StickyNote, Info } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { BookingDetailDrawer } from "../components/BookingDetailDrawer";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { formatMoney } from "../lib/format";

export default function HotelBookingsPage() {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [status, setStatus] = useState("");
  const [agencyQuery, setAgencyQuery] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  const [actionError, setActionError] = useState("");

  async function loadBookings() {
    setLoading(true);
    setError("");
    setActionError("");
    try {
      const params = {};
      if (status) params.status = status;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      // Note: agency filter via agency_id would require selecting exact agency; for MVP we do client-side by name.

      const resp = await api.get("/hotel/bookings", { params });
      const list = resp.data || [];
      setBookings(list);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadBookings();
    // eslint-disable-next-line
  }, []);
  const todayStr = new Date().toISOString().slice(0, 10);
  const tomorrowStr = new Date(Date.now() + 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 10);

  const todayArrivals = bookings.filter((b) => (b.stay || {}).check_in === todayStr).length;
  const tomorrowArrivals = bookings.filter((b) => (b.stay || {}).check_in === tomorrowStr).length;



  const filtered = useMemo(() => {
    const q = (agencyQuery || "").trim().toLowerCase();
    const sorted = [...(bookings || [])].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );

    if (!q) return sorted;

    return sorted.filter((b) => {
      const name = (b.agency_name || "").toLowerCase();
      return name.includes(q);
    });
  }, [bookings, agencyQuery]);

  async function doCancelRequest(booking) {
    setActionError("");
    const reason = window.prompt("İptal talebi sebebi (opsiyonel):") || "";
    try {
      await api.post(`/hotel/bookings/${booking.id}/cancel-request`, { reason });
      await loadBookings();
    } catch (e) {
      setActionError(apiErrorMessage(e));
    }
  }

  async function doAddHotelNote(booking) {
    setActionError("");
    const note = window.prompt("Not:");
    if (!note) return;
    try {
      await api.post(`/hotel/bookings/${booking.id}/note`, { note });
      await loadBookings();
    } catch (e) {
      setActionError(apiErrorMessage(e));
    }
  }

  async function doSetGuestNote(booking) {
    setActionError("");
    const note = window.prompt("Misafir notu:");
    if (!note) return;
    try {
      await api.post(`/hotel/bookings/${booking.id}/guest-note`, { note });
      await loadBookings();
    } catch (e) {
      setActionError(apiErrorMessage(e));
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Otel Rezervasyonları</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {filtered.length} kayıt - Bugün giriş: {todayArrivals}, Yarın giriş: {tomorrowArrivals}
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Rezervasyonlar yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Otel Rezervasyonları</h1>
        </div>

        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Rezervasyonlar yüklenemedi</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <button onClick={loadBookings} className="mt-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition">
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Otel Rezervasyonları</h1>
          <p className="text-sm text-muted-foreground mt-1">{filtered.length} kayıt</p>
        </div>

        <button
          onClick={loadBookings}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
        >
          Yenile
        </button>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Tarih (from)</div>
            <input
              type="date"
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Tarih (to)</div>
            <input
              type="date"
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Durum</div>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">Tümü</option>
              <option value="confirmed">Onaylı</option>
              <option value="cancelled">İptal</option>
            </select>
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Acenta (isim)</div>
            <input
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={agencyQuery}
              onChange={(e) => setAgencyQuery(e.target.value)}
              placeholder="örn: Demo"
            />
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            onClick={loadBookings}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
          >
            Filtrele
          </button>
          <button
            onClick={() => {
              setStatus("");
              setAgencyQuery("");
              setDateFrom("");
              setDateTo("");
              setTimeout(loadBookings, 0);
            }}
            className="px-4 py-2 rounded-lg border hover:bg-accent transition"
          >
            Sıfırla
          </button>
          <button
            onClick={() => {
              setDateFrom(todayStr);
              setDateTo(todayStr);
              setTimeout(loadBookings, 0);
            }}
            className="px-3 py-1.5 rounded-lg border text-xs hover:bg-accent/60 transition"
          >
            Bugün girişler
          </button>
          <button
            onClick={() => {
              setDateFrom(tomorrowStr);
              setDateTo(tomorrowStr);
              setTimeout(loadBookings, 0);
            }}
            className="px-3 py-1.5 rounded-lg border text-xs hover:bg-accent/60 transition"
          >
            Yarın girişler
          </button>
        </div>

        {actionError ? (
          <div className="mt-3 rounded-xl border border-destructive/50 bg-destructive/5 px-3 py-2 text-sm">
            {actionError}
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-semibold">Check-in / Check-out</TableHead>
              <TableHead className="font-semibold">Misafir</TableHead>
              <TableHead className="font-semibold">Durum</TableHead>
              <TableHead className="font-semibold">Tutar</TableHead>
              <TableHead className="font-semibold">Acenta</TableHead>
              <TableHead className="font-semibold">Aksiyon</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  Kayıt yok.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((booking) => {
                const stay = booking.stay || {};
                const guest = booking.guest || {};
                const rateSnapshot = booking.rate_snapshot || {};
                const price = rateSnapshot.price || {};

                return (
                  <TableRow
                    key={booking.id}
                    className="cursor-pointer hover:bg-accent/50"
                    onClick={() => {
                      setSelectedId(booking.id);
                      setDrawerOpen(true);
                    }}
                  >
                    <TableCell className="text-sm">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-muted-foreground" />
                        {stay.check_in}
                      </div>
                      <div className="flex items-center gap-1 text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        {stay.check_out}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {stay.nights} gece
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{guest.full_name || "-"}</div>
                      {guest.email ? (
                        <div className="text-xs text-muted-foreground">{guest.email}</div>
                      ) : null}
                    </TableCell>
                    <TableCell className="text-sm">
                      {(() => {
                        const status = booking.status;
                        if (["confirmed", "guaranteed", "checked_in"].includes(status)) {
                          return (
                            <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                              Onaylı
                            </Badge>
                          );
                        }
                        if (status === "cancelled") {
                          return (
                            <Badge className="bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20">
                              İptal
                            </Badge>
                          );
                        }
                        if (status === "draft") {
                          return <Badge variant="secondary">Taslak</Badge>;
                        }
                        return <Badge variant="outline">{status}</Badge>;
                      })()}
                    </TableCell>
                    <TableCell className="font-semibold">
                      {formatMoney(price.total || 0, price.currency || "TRY")}
                    </TableCell>
                    <TableCell className="text-sm">{booking.agency_name || "-"}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => doCancelRequest(booking)}
                          className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-accent transition"
                        >
                          <XCircle className="h-4 w-4" />
                          İptal talebi
                        </button>
                        <button
                          onClick={() => doAddHotelNote(booking)}
                          className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-accent transition"
                        >
                          <StickyNote className="h-4 w-4" />
                          Not ekle
                        </button>
                        <button
                          onClick={() => doSetGuestNote(booking)}
                          className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-accent transition"
                        >
                          <StickyNote className="h-4 w-4" />
                          Misafir notu
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      <BookingDetailDrawer
        bookingId={selectedId}
        mode="hotel"
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </div>
  );
}
