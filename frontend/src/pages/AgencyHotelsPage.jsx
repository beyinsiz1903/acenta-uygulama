import React, { useEffect, useState } from "react";
import { Hotel, AlertCircle, Loader2 } from "lucide-react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { useNavigate } from "react-router-dom";
import { Input } from "../components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";

export default function AgencyHotelsPage() {
  const navigate = useNavigate();
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

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
      setHotels(resp.data || []);
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
  if (hotels.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Otellerim</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acentanıza bağlı oteller
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
            <Hotel className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center max-w-md">
            <p className="font-semibold text-foreground">
              Henüz acentanıza bağlı bir otel bulunmuyor
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Lütfen yöneticinizle iletişime geçin.
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
            Acentanıza bağlı {hotels.length} otel
          </p>
        </div>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-semibold">Otel Adı</TableHead>
              <TableHead className="font-semibold">Şehir</TableHead>
              <TableHead className="font-semibold">Ülke</TableHead>
              <TableHead className="font-semibold">Durum</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {hotels.map((hotel) => (
              <TableRow 
                key={hotel.id} 
                className="cursor-pointer hover:bg-accent/50"
                onClick={() => navigate(`/app/agency/hotels/${hotel.id}`)}
              >
                <TableCell className="font-medium">{hotel.name}</TableCell>
                <TableCell className="text-muted-foreground">{hotel.city}</TableCell>
                <TableCell className="text-muted-foreground">{hotel.country}</TableCell>
                <TableCell>
                  {hotel.active ? (
                    <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                      Aktif
                    </Badge>
                  ) : (
                    <Badge variant="secondary">Pasif</Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
