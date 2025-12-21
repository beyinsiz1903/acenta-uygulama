import React, { useEffect, useMemo, useState } from "react";
import { Calendar, Loader2, AlertCircle, XCircle, StickyNote, Info } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { BookingDetailDrawer } from "../components/BookingDetailDrawer";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { useToast } from "../components/ui/use-toast";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { formatMoney } from "../lib/format";

const STATUS_GROUPS = {
  all: null,
  new: new Set(["pending", "awaiting_confirmation", "requested", "created", "new", "" ]),
  confirmed: new Set(["confirmed", "approved", "guaranteed", "checked_in"]),
  cancelled: new Set(["cancelled", "rejected", "declined"]),
};

function mapStatusToGroup(status) {
  const s = String(status || "").toLowerCase();
  if (STATUS_GROUPS.new.has(s)) return "new";
  if (STATUS_GROUPS.confirmed.has(s)) return "confirmed";
  if (STATUS_GROUPS.cancelled.has(s)) return "cancelled";
  return "new";
}

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
  const { toast } = useToast();


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
  const [filterGroup, setFilterGroup] = useState("all");
  const [actionOpen, setActionOpen] = useState(false);
  const [actionType, setActionType] = useState(null); // "confirm" | "reject"
  const [actionBooking, setActionBooking] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);


  const todayArrivals = bookings.filter((b) => (b.stay || {}).check_in === todayStr).length;
  const tomorrowArrivals = bookings.filter((b) => (b.stay || {}).check_in === tomorrowStr).length;


  const enrichedBookings = useMemo(() => {
    const list = bookings || [];
    return list.map((b) => ({ ...b, __group: mapStatusToGroup(b.status) }));
  }, [bookings]);

  const counts = useMemo(() => {
    const base = { total: 0, new: 0, confirmed: 0, cancelled: 0 };
    for (const b of enrichedBookings) {
      base.total += 1;
      const g = b.__group || "new";
  function openAction(type, booking) {
    setActionType(type);
    setActionBooking(booking);
    setRejectReason("");
    setActionOpen(true);
  }

  async function submitAction() {
    if (!actionBooking || !actionType) return;
    setActionLoading(true);
    setActionError("");

    try {
      if (actionType === "confirm") {
        await api.post(`/hotel/bookings/${actionBooking.id}/confirm`, {});
      } else if (actionType === "reject") {
        await api.post(`/bookings/${actionBooking.id}/cancel`, {
          reason: rejectReason?.trim() || undefined,
        });
      }

      setActionOpen(false);
      await loadBookings();
      toast({
        title: actionType === "confirm" ? "Talep onaylandı" : "Talep iptal edildi",
        duration: 2500,
      });
    } catch (err) {
      const msg = apiErrorMessage(err);
      setActionError(msg);
      toast({ title: "İşlem sırasında hata oluştu", description: msg, variant: "destructive" });
    } finally {
      setActionLoading(false);
    }
  }


      base[g] = (base[g] || 0) + 1;
    }
    return base;
  }, [enrichedBookings]);

  const filtered = useMemo(() => {
    const q = (agencyQuery || "").trim().toLowerCase();
    const sorted = [...enrichedBookings].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );

    const byGroup =
      filterGroup === "all" ? sorted : sorted.filter((b) => (b.__group || "new") === filterGroup);

    if (!q) return byGroup;

    return byGroup.filter((b) => {
      const name = (b.agency_name || "").toLowerCase();
      return name.includes(q);
    });
  }, [enrichedBookings, agencyQuery, filterGroup]);

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
          <h1 className="text-2xl font-bold text-foreground">Gelen Rezervasyon Talepleri</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Oteliniz için kayıtlı rezervasyon talepleri yükleniyor...
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
          <h1 className="text-2xl font-bold text-foreground">Gelen Rezervasyon Talepleri</h1>
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
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-1 max-w-xl">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-foreground">Gelen Rezervasyon Talepleri</h1>
            <span className="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs text-muted-foreground">
              <Info className="h-3 w-3" />
              Acentadan gelen talepler
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            Bu ekranda yalnızca <strong>acentalardan gelen rezervasyon taleplerini</strong> görürsünüz. Her talep için
            Onayla / Reddet işlemi yapabilirsiniz.
          </p>
        </div>

        <div className="flex flex-col items-end gap-2 text-sm text-muted-foreground">
          <div>
            Toplam: <span className="font-semibold text-foreground">{counts.total}</span>
          </div>
          <div>
            Yeni: <span className="font-semibold text-foreground">{counts.new}</span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <button
              onClick={loadBookings}
              className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
            >
              Yenile
            </button>
            <button
              onClick={() => window.location.assign("/app/hotel/help")}
              className="px-3 py-2 rounded-lg border text-xs hover:bg-accent/60 transition"
            >
              Yardım
            </button>
          </div>
        </div>
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

      <div className="flex flex-wrap items-center gap-2">
        <div className="inline-flex rounded-full bg-muted px-1 py-1 text-xs">
          <button
            className={`px-3 py-1 rounded-full ${filterGroup === "all" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"}`}
            onClick={() => setFilterGroup("all")}
          >
            Hepsi ({counts.total})
          </button>
          <button
            className={`px-3 py-1 rounded-full ${filterGroup === "new" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"}`}
            onClick={() => setFilterGroup("new")}
          >
            Yeni ({counts.new})
          </button>
          <button
            className={`px-3 py-1 rounded-full ${filterGroup === "confirmed" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"}`}
            onClick={() => setFilterGroup("confirmed")}
          >
            Onaylı ({counts.confirmed})
          </button>
          <button
            className={`px-3 py-1 rounded-full ${filterGroup === "cancelled" ? "bg-background text-foreground shadow-sm" : "text-muted-foreground"}`}
            onClick={() => setFilterGroup("cancelled")}
          >
            İptal ({counts.cancelled})
          </button>
        </div>
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
                  {filterGroup === "new" && "Şu an yeni talep yok."}
                  {filterGroup === "confirmed" && "Onaylı talep bulunmuyor."}
                  {filterGroup === "cancelled" && "İptal edilmiş talep bulunmuyor."}
                  {filterGroup === "all" && "Henüz acentalardan talep gelmedi."}
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((booking) => {
                const stay = booking.stay || {};
                const guest = booking.guest || {};
                const rateSnapshot = booking.rate_snapshot || {};
                const price = rateSnapshot.price || {};
                const isNew = booking.__group === "new";

                return (
                  <TableRow
                    key={booking.id}
                    className={`cursor-pointer hover:bg-accent/50 transition-colors ${isNew ? "bg-muted/30" : ""}`}
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
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      {isNew ? (
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="sm"
                            className="gap-2"
                            onClick={() => openAction("confirm", booking)}
                          >
                            Onayla
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="gap-2"
                            onClick={() => openAction("reject", booking)}
                          >
                            Reddet
                          </Button>
                        </div>
                      ) : (
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
      <Dialog open={actionOpen} onOpenChange={setActionOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionType === "confirm" ? "Talebi Onayla" : "Talebi İptal Et"}
            </DialogTitle>
            <DialogDescription>
              {actionType === "confirm"
                ? "Bu talep acentaya onaylandı olarak iletilir."
                : "Bu talep iptal edildi olarak iletilir. İsterseniz sebep ekleyebilirsiniz."}
            </DialogDescription>
          </DialogHeader>

          {actionType === "reject" && (
            <div className="space-y-2 mt-3">
              <Label>İptal sebebi (opsiyonel)</Label>
              <Textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Örn: Kapalı tarih, fiyat uyuşmazlığı, minimum konaklama..."
                rows={3}
              />
            </div>
          )}

          <DialogFooter className="mt-4 gap-2">
            <Button variant="ghost" onClick={() => setActionOpen(false)} disabled={actionLoading}>
              Vazgeç
            </Button>
            <Button onClick={submitAction} disabled={actionLoading}>
              {actionLoading
                ? "İşleniyor..."
                : actionType === "confirm"
                ? "Onayla"
                : "İptal Et"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

                            <StickyNote className="h-4 w-4" />
                            Misafir notu
                          </button>
                        </div>
                      )}
                    </TableCell>

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
