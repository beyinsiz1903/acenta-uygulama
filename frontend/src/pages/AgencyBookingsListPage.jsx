import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Ticket, Calendar, Users, Loader2, AlertCircle, Search } from "lucide-react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { formatMoney } from "../lib/format";
import { formatDateTime } from "../utils/formatters";
import { BookingDetailDrawer } from "../components/BookingDetailDrawer";


function todayIso() {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

export default function AgencyBookingsListPage() {
  const navigate = useNavigate();
  const user = getUser();

  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  const [error, setError] = useState("");

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [arrivalFilter, setArrivalFilter] = useState("all"); // all|today

  useEffect(() => {
    loadBookings();
  }, []);

  async function loadBookings() {
    setLoading(true);
    setError("");
    try {
      // Fetch all confirmed bookings for this agency
      const resp = await api.get("/agency/bookings");
      console.log("[AgencyBookings] Loaded:", resp.data?.length || 0);
      
      // Sort by created_at desc
      const sorted = (resp.data || []).sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      
      setBookings(sorted);
    } catch (err) {
      console.error("[AgencyBookings] Load error:", err);
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Rezervasyonlarım</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acentanızın rezervasyonları
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Rezervasyonlar yükleniyor...</p>
        </div>
      </div>
    );
  }

  const today = todayIso();

  const todayArrivals = bookings.filter((b) => {
    const stay = b.stay || {};
    return stay.check_in === today;
  }).length;

  const filteredBookings = bookings.filter((booking) => {
    const stay = booking.stay || {};
    const guest = booking.guest || {};

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      const hay = `${booking.id} ${booking.hotel_name || ""} ${guest.full_name || ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }

    if (statusFilter) {
      if (booking.status !== statusFilter) return false;
    }

    if (arrivalFilter === "today") {
      if (stay.check_in !== today) return false;
    }

    return true;
  });


  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Rezervasyonlarım</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acentanızın rezervasyonları
          </p>
        </div>

        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Rezervasyonlar yüklenemedi</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <button
            onClick={loadBookings}
            className="mt-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (bookings.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Rezervasyonlarım</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Acentanızın rezervasyonları
            </p>
          </div>
          <Button onClick={() => navigate("/app/agency/hotels")} className="gap-2">
            <Search className="h-4 w-4" />
            Yeni Arama
          </Button>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
            <Ticket className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center max-w-md">
            <p className="font-semibold text-foreground">
              Henüz rezervasyon yok
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Hızlı Rezervasyon ekranından arama yapıp rezervasyon oluşturabilirsiniz.
            </p>
          </div>
          <Button onClick={() => navigate("/app/agency/hotels")} className="mt-4 gap-2">
            <Search className="h-4 w-4" />
            Otel Ara
          </Button>
        </div>
      </div>
    );
  }

  // Data table
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Rezervasyonlarım</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {bookings.length} rezervasyon - Bugün giriş: {todayArrivals}
          </p>
        </div>
        <Button onClick={() => navigate("/app/agency/hotels")} className="gap-2">
          <Search className="h-4 w-4" />
          Yeni Arama
        </Button>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-semibold">Booking ID</TableHead>
              <TableHead className="font-semibold">Otel</TableHead>
              <TableHead className="font-semibold">Tarihler</TableHead>
              <TableHead className="font-semibold">Misafir</TableHead>
              <TableHead className="font-semibold">Tutar</TableHead>
              <TableHead className="font-semibold">Durum</TableHead>
              <TableHead className="font-semibold">Oluşturma</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredBookings.map((booking) => {
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
                  <TableCell className="font-mono text-sm">{booking.id}</TableCell>
                  <TableCell className="font-medium">{booking.hotel_name || "-"}</TableCell>
                  <TableCell className="text-sm">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3 text-muted-foreground" />
                      {stay.check_in} - {stay.check_out}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {stay.nights} gece
      <div className="rounded-2xl border bg-card shadow-sm p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Arama</div>
            <input
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Misafir, otel veya Booking ID ara..."
            />
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Durum</div>
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">Tüm durumlar</option>
              <option value="confirmed">Onaylı</option>
              <option value="cancelled">İptal</option>
              <option value="draft">Taslak</option>
            </select>
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Giriş Tarihi</div>
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={arrivalFilter}
              onChange={(e) => setArrivalFilter(e.target.value)}
            >
              <option value="all">Tümü</option>
              <option value="today">Bugün giriş</option>
            </select>
          </div>
        </div>
      </div>


                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Users className="h-3 w-3 text-muted-foreground" />
                      {guest.full_name || "-"}
                    </div>
                  </TableCell>
                  <TableCell className="font-semibold">
                    {formatMoney(price.total || 0, price.currency || "TRY")}
                  </TableCell>
                  <TableCell>
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
                        return (
                          <Badge variant="secondary">
                            Taslak
                          </Badge>
                        );
                      }
                      return <Badge variant="outline">{status}</Badge>;
                    })()}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateTime(booking.created_at)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <BookingDetailDrawer
        bookingId={selectedId}
        mode="agency"
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
      />
    </div>
  );
}
