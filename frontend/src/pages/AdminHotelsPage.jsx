import React, { useEffect, useState } from "react";
import { Hotel, AlertCircle, Loader2, Plus, X } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { formatDateTime, getActiveStatus } from "../utils/formatters";
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
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Checkbox } from "../components/ui/checkbox";
import { toast } from "sonner";

export default function AdminHotelsPage() {
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    city: "",
    country: "TR",
    active: true,
  });
  const [formError, setFormError] = useState("");

  async function handleToggleForceSales(hotel) {
    const current = Boolean(hotel.force_sales_open);
    try {
      let payload;
      if (!current) {
        const reason = window.prompt(
          "Geçici satış açma sebebi (kısa not):",
          hotel.force_sales_open_reason || ""
        );
        if (reason === null) {
          return; // kullanıcı iptal etti
        }
        const trimmed = reason.trim();
        if (!trimmed) {
          toast.error("Override açmak için kısa bir sebep yazmalısınız.");
          return;
        }
        payload = { force_sales_open: true, ttl_hours: 6, reason: trimmed };
      } else {
        payload = { force_sales_open: false };
      }

      await api.patch(`/admin/hotels/${hotel.id}/force-sales`, payload);
      toast.success(
        !current
          ? "Otel geçici olarak full satışa açıldı (stop-sell & allotment yok sayılacak, 6 saat sonra otomatik kapanır)."
          : "Otel satış override ayarı kapatıldı. Stop-sell ve allotment kuralları tekrar devrede."
      );
      await loadHotels();
    } catch (err) {
      console.error("[AdminHotels] Force sales toggle error:", err);
      toast.error(apiErrorMessage(err));
    }
  }

  useEffect(() => {
    loadHotels();
  }, []);

  async function loadHotels() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/admin/hotels/");
      console.log("[AdminHotels] Loaded:", resp.data?.length || 0);
      const sorted = (resp.data || []).sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      setHotels(sorted);
    } catch (err) {
      console.error("[AdminHotels] Load error:", err);
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setFormError("");

    // Validation
    const name = formData.name.trim();
    if (!name) {
      setFormError("Otel adı boş olamaz");
      return;
    }
    if (name.length < 2) {
      setFormError("Otel adı en az 2 karakter olmalı");
      return;
    }

    setCreateLoading(true);
    try {
      // Explicit defaults
      const payload = {
        name,
        city: formData.city.trim() || undefined,
        country: formData.country.trim() || "TR",
        active: formData.active ?? true,
      };

      await api.post("/admin/hotels", payload);
      console.log("[AdminHotels] Created:", name);
      toast.success("Otel oluşturuldu");
      setFormData({ name: "", city: "", country: "TR", active: true });
      setShowForm(false);
      // Refresh list
      await loadHotels();
    } catch (err) {
      console.error("[AdminHotels] Create error:", err);
      setFormError(apiErrorMessage(err));
    } finally {
      setCreateLoading(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Oteller</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Otel yönetimi
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
          <h1 className="text-2xl font-bold text-foreground">Oteller</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Otel yönetimi
          </p>
        </div>

        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Oteller yüklenemedi</p>
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

  // Main view
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Oteller</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {hotels.length} otel
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} className="gap-2">
          {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showForm ? "İptal" : "Yeni Otel"}
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="rounded-2xl border bg-card shadow-sm p-6">
          <h3 className="font-semibold mb-4">Yeni Otel Oluştur</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="hotel-name">Otel Adı *</Label>
              <Input
                id="hotel-name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Örn: Grand Hotel Istanbul"
                disabled={createLoading}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="hotel-city">Şehir</Label>
                <Input
                  id="hotel-city"
                  value={formData.city}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="Örn: İstanbul"
                  disabled={createLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="hotel-country">Ülke</Label>
                <Input
                  id="hotel-country"
                  value={formData.country}
                  onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                  placeholder="TR"
                  disabled={createLoading}
                />
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="hotel-active"
                checked={formData.active}
                onCheckedChange={(checked) => setFormData({ ...formData, active: checked })}
                disabled={createLoading}
              />
              <Label htmlFor="hotel-active" className="cursor-pointer">
                Aktif
              </Label>
            </div>

            {formError && (
              <div className="text-sm text-destructive">{formError}</div>
            )}

            <div className="flex gap-2">
              <Button type="submit" disabled={createLoading} className="gap-2">
                {createLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {createLoading ? "Oluşturuluyor..." : "Oluştur"}
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Empty state */}
      {hotels.length === 0 && (
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
            <Hotel className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center max-w-md">
            <p className="font-semibold text-foreground">
              Henüz otel yok
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Yeni otel ekleyebilirsiniz.
            </p>
          </div>
        </div>
      )}

      {/* Data table */}
      {hotels.length > 0 && (
        <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="font-semibold">Otel Adı</TableHead>
                <TableHead className="font-semibold">Şehir</TableHead>
                <TableHead className="font-semibold">Ülke</TableHead>
                <TableHead className="font-semibold">Durum</TableHead>
                <TableHead className="font-semibold text-xs">Override (Satış)</TableHead>
                <TableHead className="font-semibold">Oluşturma</TableHead>
                <TableHead className="font-semibold text-xs">Oluşturan</TableHead>
                <TableHead className="font-semibold text-xs text-right">Aksiyon</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {hotels.map((hotel) => (
                <TableRow key={hotel.id}>
                  <TableCell className="font-medium">{hotel.name}</TableCell>
                  <TableCell className="text-muted-foreground">{hotel.city || "-"}</TableCell>
                  <TableCell className="text-muted-foreground">{hotel.country || "-"}</TableCell>
                  <TableCell>
                    {getActiveStatus(hotel) ? (
                      <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                        Aktif
                      </Badge>
                    ) : (
                      <Badge variant="secondary">Pasif</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {hotel.force_sales_open ? (
                      <div className="space-y-1 text-[11px]">
                        <Badge className="bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20">
                          Override: Açık (full satış)
                        </Badge>
                        <div className="text-[10px] text-muted-foreground">
                          Bitiş: {hotel.force_sales_open_expires_at ? formatDateTime(hotel.force_sales_open_expires_at) : "-"}
                          {hotel.force_sales_open_reason && (
                            <>
                              <br />Sebep: {hotel.force_sales_open_reason}
                            </>
                          )}
                        </div>
                      </div>
                    ) : (
                      <Badge variant="outline" className="text-[11px]">
                        Override: Kapalı
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateTime(hotel.created_at)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {hotel.created_by || "-"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant={hotel.force_sales_open ? "outline" : "secondary"}
                      size="sm"
                      className="text-[11px]"
                      onClick={() => handleToggleForceSales(hotel)}
                    >
                      {hotel.force_sales_open ? "Override Kapat" : "Override Aç"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
