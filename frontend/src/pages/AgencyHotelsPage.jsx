import React, { useEffect, useMemo, useState } from "react";
import { Hotel, AlertCircle, Loader2 } from "lucide-react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { useNavigate } from "react-router-dom";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Card, CardContent } from "../components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

export default function AgencyHotelsPage() {
  const navigate = useNavigate();
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const user = getUser();

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

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div>
  const locationOptions = useMemo(() => {
    const uniq = new Set();
    hotels.forEach((h) => {
      const loc = (h?.location || "").trim();
      if (loc) uniq.add(loc);
    });
    return ["all", ...Array.from(uniq).sort((a, b) => a.localeCompare(b))];
  }, [hotels]);

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

  // Empty state
  if (!loading && filtered.length === 0) {
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
              Bu ekranda satış yapabileceğiniz oteller listelenir. Lütfen çalıştığınız tesisin Syroce panelinden sizi acenta olarak tanımlamasını isteyin.
            </p>
          </div>
        </div>
      </div>
    );
  }

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
      </div>

      <div className="rounded-2xl border bg-card shadow-sm p-4 mb-2 flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[200px]">
          <Input
            placeholder="🔍 Otel ara..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            className="h-10 rounded-md border bg-background px-3 text-sm"
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
          >
            <option value="">Lokasyon (Tümü)</option>
            {[...new Set(hotels.map((h) => h.location).filter(Boolean))].map((loc) => (
              <option key={loc} value={loc}>{loc}</option>
            ))}
          </select>
          <select
            className="h-10 rounded-md border bg-background px-3 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Durum (Tümü)</option>
            <option value="Satışa Açık">Açık</option>
            <option value="Kısıtlı">Kısıtlı</option>
            <option value="Satışa Kapalı">Kapalı</option>
          </select>
        </div>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-semibold">Otel Adı</TableHead>
              <TableHead className="font-semibold">Lokasyon</TableHead>
              <TableHead className="font-semibold">Kanal</TableHead>
              <TableHead className="font-semibold">Durum</TableHead>
              <TableHead className="font-semibold text-right">Aksiyon</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((hotel) => (
              <TableRow key={hotel.hotel_id} className="hover:bg-accent/40">
                <TableCell className="font-medium">{hotel.hotel_name}</TableCell>
                <TableCell className="text-muted-foreground">{hotel.location || "-"}</TableCell>
                <TableCell className="text-muted-foreground">{hotel.channel || "agency_extranet"}</TableCell>
                <TableCell>
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
                </TableCell>
                <TableCell className="text-right">
                  <button
                    className="inline-flex items-center rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition"
                    onClick={() => navigate(`/app/agency/hotels/${hotel.hotel_id}/search`)}
                  >
                    Rezervasyon Oluştur
                  </button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
