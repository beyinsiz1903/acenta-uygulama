import React, { useEffect, useMemo, useState } from "react";
import { Hotel, AlertCircle, Loader2 } from "lucide-react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { useNavigate } from "react-router-dom";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Card, CardContent } from "../components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Button } from "../components/ui/button";


const CM_META = {
  connected: { label: "CM: Connected", variant: "default" },
  configured: { label: "CM: Configured", variant: "secondary" },
  error: { label: "CM: Error", variant: "destructive" },
  disabled: { label: "CM: Disabled", variant: "outline" },
  not_configured: { label: "CM: Not configured", variant: "outline" },
};

function isLinkActive(hotel) {
  if (typeof hotel?.active === "boolean") return hotel.active;
  const status = (hotel?.status_label || "").toLowerCase();
  if (status === "satışa açık") return true;
  return false;
}

export default function AgencyHotelsPage() {
  const navigate = useNavigate();
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const user = getUser();

  const goHotelBookings = (hotelId) => {
    navigate(`/app/agency/bookings?hotel_id=${encodeURIComponent(hotelId)}`);
  };

  const goHotelDetail = (hotelId) => {
    navigate(`/app/agency/hotels/${encodeURIComponent(hotelId)}`);
  };

  useEffect(() => {
    // Debug: agency_id kontrolü
    console.log("[AgencyHotelsPage] User context:", {
      email: user?.email,
      agency_id: user?.agency_id,
      roles: user?.roles,
    });

    loadHotels();
  }, []);

  async function loadHotels() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/agency/hotels");
      console.log("[AgencyHotelsPage] Loaded hotels:", resp.data);
      const items = resp.data?.items || resp.data || [];
      setHotels(items);
    } catch (err) {
      console.error("[AgencyHotelsPage] Load error:", err);
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();

    return hotels.filter((h) => {
      const statusKey = (h.status_label || "").toLowerCase();

      const matchesQuery =
        !query ||
        (h?.hotel_name || "").toLowerCase().includes(query) ||
        (h?.location || "").toLowerCase().includes(query);

      const matchesLocation =
        locationFilter === "all" || (h?.location || "") === locationFilter;

      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "open" && statusKey === "satışa açık") ||
        (statusFilter === "restricted" && statusKey === "kısıtlı") ||
        (statusFilter === "closed" && statusKey === "satışa kapalı");

      return matchesQuery && matchesLocation && matchesStatus;
    });
  }, [hotels, search, locationFilter, statusFilter]);

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Otellerim</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acentanıza bağlı oteller
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Oteller yükleniyor...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Otellerim</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acentanıza bağlı oteller
          </p>
        </div>

        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Otel listesi yüklenemedi</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <button
            onClick={loadHotels}
            className="mt-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  // Empty state (hiç hotel yok)
  if (!loading && hotels.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Otellerim</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Anlaşmalı olduğunuz ve satış yapabileceğiniz tesisler
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
            <Hotel className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center max-w-md space-y-2">
            <p className="font-semibold text-foreground">
              Henüz size tanımlı bir tesis yok
            </p>
            <p className="text-sm text-muted-foreground">
              Bu ekranda satış yapabileceğiniz oteller listelenir. Merkez ekip otel eklediğinde burada göreceksiniz.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const hasFiltered = filtered.length > 0;

  // Data table
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Otellerim</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Anlaşmalı olduğunuz ve satış yapabileceğiniz {hotels.length} tesis
          </p>
        </div>
        <div>
          <Button variant="outline" size="sm" onClick={loadHotels} disabled={loading}>
            Yenile
          </Button>
        </div>
      </div>

      <Card className="rounded-2xl border bg-card shadow-sm p-4 mb-2">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <Input
              placeholder="🔍 Otel ara... (ad / lokasyon)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select value={locationFilter} onValueChange={setLocationFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Lokasyon" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm Lokasyonlar</SelectItem>
                {(() => {
                  const uniq = new Set();
                  hotels.forEach((h) => {
                    const loc = (h?.location || "").trim();
                    if (loc) uniq.add(loc);
                  });
                  return Array.from(uniq).sort((a, b) => a.localeCompare(b));
                })()
                  .map((loc) => (
                    <SelectItem key={loc} value={loc}>
                      {loc}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Durum" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm Durumlar</SelectItem>
                <SelectItem value="open">Satışa Açık</SelectItem>
                <SelectItem value="restricted">Kısıtlı</SelectItem>
                <SelectItem value="closed">Satışa Kapalı</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {filtered.map((hotel) => (
          <Card key={hotel.hotel_id} className="rounded-2xl border bg-card shadow-sm">
            <CardContent className="p-5 flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="text-lg font-semibold">{hotel.hotel_name || "-"}</div>
                  <Badge
                    className={
                      hotel.status_label === "Satışa Açık"
                        ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                        : hotel.status_label === "Kısıtlı"
                        ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20"
                        : "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20"
                    }
                  >
                    {hotel.status_label || "-"}
                  </Badge>
                  {(() => {
                    const cmStatus = hotel.cm_status || "not_configured";
                    const meta = CM_META[cmStatus] || CM_META.not_configured;
                    return (
                      <Badge variant={meta.variant}>{meta.label}</Badge>
                    );
                  })()}
                </div>
                <div className="text-sm text-muted-foreground">
                  {hotel.location || "-"}
                </div>
                <div className="flex flex-wrap gap-2 pt-2 text-xs">
                  <Badge variant="outline">Kanal: {hotel.channel || "agency_extranet"}</Badge>
                  <Badge variant="outline">Satış: {hotel.sales_mode || "free_sale"}</Badge>
                  {typeof hotel.allocation_available === "number" && hotel.sales_mode === "allocation" ? (
                    <Badge variant="outline">Allotment: {hotel.allocation_available}</Badge>
                  ) : null}
                </div>
              </div>

              <div className="flex flex-col gap-2 shrink-0">
                <Button
                  className="px-3 py-1.5 text-xs font-medium"
                  onClick={() => navigate(`/app/agency/hotels/${hotel.hotel_id}/search`)}
                  disabled={!isLinkActive(hotel) || hotel.status_label === "Satışa Kapalı"}
                >
                  Rezervasyon Oluştur
                </Button>
                <Button
                  variant="outline"
                  className="px-3 py-1.5 text-xs font-medium"
                  type="button"
                  onClick={() => goHotelBookings(hotel.hotel_id)}
                >
                  Rezervasyonlar
                </Button>
                <Button
                  variant="ghost"
                  className="px-3 py-1.5 text-xs font-medium"
                  type="button"
                  onClick={() => goHotelDetail(hotel.hotel_id)}
                >
                  Detay
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
