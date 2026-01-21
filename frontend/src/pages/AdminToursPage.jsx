import React, { useEffect, useState } from "react";
import { AlertCircle, Loader2, Plus, X } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function AdminToursPage() {
  const [tours, setTours] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [formData, setFormData] = useState({ name: "", destination: "", base_price: "", currency: "EUR" });
  const [formError, setFormError] = useState("");

  useEffect(() => {
    void loadTours();
  }, []);

  async function loadTours() {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/admin/tours");
      setTours(res.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setFormError("");

    const name = formData.name.trim();
    if (!name) {
      setFormError("Tur adı boş olamaz");
      return;
    }

    const basePrice = parseFloat(formData.base_price || "0");
    if (Number.isNaN(basePrice) || basePrice <= 0) {
      setFormError("Geçerli bir temel fiyat girin");
      return;
    }

    setCreateLoading(true);
    try {
      await api.post("/admin/tours", {
        name,
        destination: formData.destination.trim(),
        base_price: basePrice,
        currency: formData.currency.trim() || "EUR",
      });
      setFormData({ name: "", destination: "", base_price: "", currency: "EUR" });
      setShowForm(false);
      await loadTours();
    } catch (e) {
      setFormError(apiErrorMessage(e));
    } finally {
      setCreateLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Turlar</h1>
          <p className="text-sm text-muted-foreground mt-1">Tur yönetimi</p>
        </div>
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Turlar yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Turlar</h1>
          <p className="text-sm text-muted-foreground mt-1">Tur yönetimi</p>
        </div>
        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Turlar yüklenemedi</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <button
            onClick={loadTours}
            className="mt-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Turlar</h1>
          <p className="text-sm text-muted-foreground mt-1">{tours.length} tur</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} className="gap-2">
          {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showForm ? "İptal" : "Yeni Tur"}
        </Button>
      </div>

      {showForm && (
        <div className="rounded-2xl border bg-card shadow-sm p-6">
          <h3 className="font-semibold mb-4">Yeni Tur Oluştur</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tour-name">Tur Adı *</Label>
              <Input
                id="tour-name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Örn: Kapadokya Balon Turu"
                disabled={createLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tour-destination">Bölge / Destinasyon</Label>
              <Input
                id="tour-destination"
                value={formData.destination}
                onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
                placeholder="Örn: Kapadokya"
                disabled={createLoading}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="tour-price">Temel Fiyat</Label>
                <Input
                  id="tour-price"
                  type="number"
                  min={0}
                  step="0.01"
                  value={formData.base_price}
                  onChange={(e) => setFormData({ ...formData, base_price: e.target.value })}
                  placeholder="Örn: 150.00"
                  disabled={createLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tour-currency">Para Birimi</Label>
                <Input
                  id="tour-currency"
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  placeholder="EUR"
                  disabled={createLoading}
                />
              </div>
            </div>
            {formError && <div className="text-sm text-destructive">{formError}</div>}
            <div className="flex gap-2">
              <Button type="submit" disabled={createLoading} className="gap-2">
                {createLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {createLoading ? "Oluşturuluyor..." : "Oluştur"}
              </Button>
            </div>
          </form>
        </div>
      )}

      {tours.length === 0 && (
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="text-center max-w-md">
            <p className="font-semibold text-foreground">Henüz tur yok</p>
            <p className="text-sm text-muted-foreground mt-2">Yeni tur ekleyebilirsiniz.</p>
          </div>
        </div>
      )}

      {tours.length > 0 && (
        <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="font-semibold">Tur Adı</TableHead>
                <TableHead className="font-semibold">Bölge / Destinasyon</TableHead>
                <TableHead className="font-semibold text-right">Temel Fiyat</TableHead>
                <TableHead className="font-semibold text-right">Para Birimi</TableHead>
                <TableHead className="font-semibold">Durum</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tours.map((tour) => (
                <TableRow key={tour.id}>
                  <TableCell className="font-medium">{tour.name}</TableCell>
                  <TableCell className="text-muted-foreground">{tour.destination || "-"}</TableCell>
                  <TableCell className="text-right font-mono text-sm">{tour.base_price.toFixed(2)}</TableCell>
                  <TableCell className="text-right text-muted-foreground">{tour.currency}</TableCell>
                  <TableCell>
                    {tour.status === "active" ? (
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
      )}
    </div>
  );
}
