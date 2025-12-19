import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Hotel, Calendar, Users, Loader2, AlertCircle, Building2 } from "lucide-react";
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

export default function HotelBookingsPage() {
  const navigate = useNavigate();
  const user = getUser();

  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    console.log("[HotelBookings] User context:", {
      email: user?.email,
      hotel_id: user?.hotel_id,
      roles: user?.roles,
    });
    loadBookings();
  }, []);

  async function loadBookings() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/hotel/bookings");
      console.log("[HotelBookings] Loaded:", resp.data?.length || 0);
      
      const sorted = (resp.data || []).sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      
      setBookings(sorted);
    } catch (err) {
      console.error("[HotelBookings] Load error:", err);
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Acenta Rezervasyonları</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Otel rezervasyonları
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
          <h1 className="text-2xl font-bold text-foreground">Acenta Rezervasyonları</h1>
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

  if (bookings.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Acenta Rezervasyonları</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Otel rezervasyonları
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
            <Hotel className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center max-w-md">
            <p className="font-semibold text-foreground">
              Henüz rezervasyon yok
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Acentalardan rezervasyon geldiğinde burada görünecek.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Acenta Rezervasyonları</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {bookings.length} rezervasyon
          </p>
        </div>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-semibold">Booking ID</TableHead>
              <TableHead className="font-semibold">Check-in / Check-out</TableHead>
              <TableHead className="font-semibold">Misafir</TableHead>
              <TableHead className="font-semibold">Oda</TableHead>
              <TableHead className="font-semibold">Tutar</TableHead>
              <TableHead className="font-semibold">Durum</TableHead>
              <TableHead className="font-semibold">Oluşturma</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {bookings.map((booking) => {
              const stay = booking.stay || {};
              const guest = booking.guest || {};
              const rateSnapshot = booking.rate_snapshot || {};
              const price = rateSnapshot.price || {};
              
              return (
                <TableRow key={booking.id} className="hover:bg-accent/50">
                  <TableCell className="font-mono text-xs">{booking.id}</TableCell>
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
                    {guest.email && (
                      <div className="text-xs text-muted-foreground">{guest.email}</div>
                    )}
                  </TableCell>
                  <TableCell className="text-sm">
                    <div>{rateSnapshot.room_type_name || "-"}</div>
                    <div className="text-xs text-muted-foreground">
                      {rateSnapshot.rate_plan_name}
                    </div>
                  </TableCell>
                  <TableCell className="font-semibold">
                    {formatMoney(price.total || 0, price.currency || "TRY")}
                  </TableCell>
                  <TableCell>
                    <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                      {booking.status === "confirmed" ? "Onaylı" : booking.status}
                    </Badge>
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
    </div>
  );
}
