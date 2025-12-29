import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Ticket, Calendar, Users, Loader2, AlertCircle, Search } from "lucide-react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { useToast } from "../hooks/use-toast";
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
import { Textarea } from "../components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { formatMoney } from "../lib/format";
import { formatDateTime } from "../utils/formatters";
import { BookingDetailDrawer } from "../components/BookingDetailDrawer";


function todayIso() {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

function buildShareText(booking) {
  const stay = booking?.stay || {};
  const guest = booking?.guest || {};
  const customer = booking?.customer || {};
  const snap = booking?.catalog_snapshot || {};
  const commission = snap?.commission?.value;
  const markup = snap?.pricing_policy?.markup_percent;

  const lines = [];

  lines.push(`📌 REZERVASYON TALEBİ`);
  lines.push(
    `Kaynak: ${
      booking?.source === "public_booking"
        ? "Public Booking"
        : booking?.source || "-"
    }`,
  );
  lines.push(`Durum: ${booking?.status || "-"}`);
  lines.push("");

  lines.push(`🏨 Otel: ${booking?.hotel_name || "-"}`);
  lines.push(`📅 Tarih: ${stay?.check_in || "-"} → ${stay?.check_out || "-"}`);
  lines.push(
    `👤 Pax: ${booking?.adults ?? "-"} yetişkin / ${booking?.children ?? 0} çocuk`,
  );
  lines.push("");

  if (booking?.source === "public_booking") {
    lines.push(`🙋 Müşteri: ${customer?.name || "-"}`);
    lines.push(`📞 Telefon: ${customer?.phone || "-"}`);
    if (customer?.email) lines.push(`✉️ E-posta: ${customer.email}`);
    lines.push("");
  } else {
    lines.push(`🙋 Misafir: ${guest?.full_name || "-"}`);
    if (guest?.email) lines.push(`✉️ E-posta: ${guest.email}`);
    lines.push("");
  }

  if (booking?.source === "public_booking") {
    lines.push(`🧾 Katalog Koşulları`);
    lines.push(`• Min gece: ${snap?.min_nights ?? "-"}`);
    lines.push(
      `• Komisyon: ${
        commission != null && commission !== "" ? `%${commission}` : "-"
      }`,
    );
    lines.push(
      `• Markup: ${
        markup != null && markup !== "" ? `%${markup}` : "-"
      }`,
    );
    lines.push("");
  }

  if (booking?.note) {
    lines.push(`📝 Not: ${booking.note}`);
    lines.push("");
  }

  lines.push(`— Syroce Acenta`);

  return lines.join("\n");
}

export default function AgencyBookingsListPage() {
  const navigate = useNavigate();
  const user = getUser();
  const { toast } = useToast();

  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  const [error, setError] = useState("");

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [arrivalFilter, setArrivalFilter] = useState("all"); // all|today
  const [sourceTab, setSourceTab] = useState("all"); // all|public
  const [onlyPendingPublic, setOnlyPendingPublic] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [shareText, setShareText] = useState("");

  useEffect(() => {
    loadBookings();
  }, []);

  useEffect(() => {
    if (sourceTab !== "public" && onlyPendingPublic) {
      setOnlyPendingPublic(false);
    }
  }, [sourceTab, onlyPendingPublic]);

  async function loadBookings() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/agency/bookings");
      console.log("[AgencyBookings] Loaded:", resp.data?.length || 0);

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

  async function copyShareText(booking) {
    try {
      const text = buildShareText(booking);
      await navigator.clipboard.writeText(text);
      toast({
        title: "Kopyalandı",
        description: "Paylaşım metni panoya alındı.",
      });
    } catch (e) {
      toast({
        title: "Kopyalanamadı",
        description: "Tarayıcı panoya kopyalamaya izin vermedi.",
        variant: "destructive",
      });
    }
  }

  function openShareDialog(booking) {
    setShareText(buildShareText(booking));
    setShareOpen(true);
  }

  async function copyShareTextFromDialog() {
    try {
      await navigator.clipboard.writeText(shareText);
      toast({
        title: "Kopyalandı",
        description: "Paylaşım metni panoya alındı.",
      });
    } catch (e) {
      toast({
        title: "Kopyalanamadı",
        description: "Metni seçip manuel kopyalayabilirsin.",
        variant: "destructive",
      });
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

    const isPublic = booking.source === "public_booking";
    const st = (booking.status || "").toLowerCase();
    const isPending = st === "pending" || st === "new";

    if (sourceTab === "public" && !isPublic) {
      return false;
    }

    if (onlyPendingPublic) {
      if (!isPublic || !isPending) return false;
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

      <div className="mt-2 flex items-center justify-between gap-3">
        <div className="inline-flex rounded-full bg-muted px-1 py-1 text-xs">
          <button
            className={`px-3 py-1 rounded-full ${
              sourceTab === "all"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground"
            }`}
            onClick={() => setSourceTab("all")}
          >
            Tümü
          </button>
          <button
            className={`px-3 py-1 rounded-full ${
              sourceTab === "public"
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground"
            }`}
            onClick={() => setSourceTab("public")}
          >
            Public Talepler
          </button>
        </div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={onlyPendingPublic}
              onChange={(e) => setOnlyPendingPublic(e.target.checked)}
              disabled={sourceTab !== "public"}
            />
            Sadece Pending Public
          </label>
        </div>
      </div>

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
              <option value="pending">Otel onayı bekleniyor</option>
              <option value="confirmed">Onaylı</option>
              <option value="rejected">Reddedildi</option>
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
              const customer = booking.customer || {};
              const snap = booking.catalog_snapshot || {};
              const isPublic = booking.source === "public_booking";
              
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
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Users className="h-3 w-3 text-muted-foreground" />
                      {guest.full_name || customer.name || "-"}
                      {isPublic ? (
                        <Badge variant="outline" className="ml-2">
                          Public
                        </Badge>
                      ) : null}
                    </div>
                    {isPublic ? (
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {customer.name && <span>{customer.name}</span>}
                        {customer.phone && (
                          <span>{customer.name ? " • " : ""}{customer.phone}</span>
                        )}
                        {customer.email && (
                          <span>{(customer.name || customer.phone) ? " • " : ""}{customer.email}</span>
                        )}
                      </div>
                    ) : null}
                  </TableCell>
                  <TableCell className="font-semibold">
                    {formatMoney(price.total || 0, price.currency || "TRY")}
                    {isPublic ? (
                      <div className="mt-1 flex flex-wrap gap-1 text-xs">
                        <Badge variant="secondary">Min {snap?.min_nights ?? "-"}</Badge>
                        <Badge variant="secondary">
                          Kom %{snap?.commission?.value ?? "-"}
                        </Badge>
                        <Badge variant="secondary">
                          Mk %{snap?.pricing_policy?.markup_percent ?? "-"}
                        </Badge>
                      </div>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateTime(booking.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    {booking.source === "public_booking" ? (
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyShareText(booking);
                          }}
                        >
                          Kopyala
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            openShareDialog(booking);
                          }}
                        >
                          Özet
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/app/agency/bookings/${booking.id || booking._id}/print`);
                          }}
                        >
                          Yazdır
                        </Button>
                      </div>
                    ) : null}
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
                      if (status === "pending") {
                        return (
                          <Badge className="bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20">
                            Otel onayı bekleniyor
                          </Badge>
                        );
                      }
                      if (status === "rejected") {
                        return (
                          <Badge className="bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20">
                            Reddedildi
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
                  <TableCell className="text-right">
                    {booking.source === "public_booking" ? (
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyShareText(booking);
                          }}
                        >
                          Kopyala
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            openShareDialog(booking);
                          }}
                        >
                          Özet
                        </Button>
                      </div>
                    ) : null}
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

      <Dialog open={shareOpen} onOpenChange={setShareOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Paylaşım Özeti</DialogTitle>
            <DialogDescription>
              WhatsApp / mail için metni kopyalayabilirsin.
            </DialogDescription>
          </DialogHeader>

          <Textarea value={shareText} readOnly className="min-h-[260px]" />

          <DialogFooter>
            <Button variant="outline" onClick={() => setShareOpen(false)}>
              Kapat
            </Button>
            <Button onClick={copyShareTextFromDialog}>Kopyala</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
