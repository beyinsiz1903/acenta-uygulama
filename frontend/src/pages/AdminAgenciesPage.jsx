import React, { useEffect, useState } from "react";
import { Building2, AlertCircle, Loader2, Plus, X } from "lucide-react";
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
import { toast } from "sonner";

export default function AdminAgenciesPage() {
  const [agencies, setAgencies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [formData, setFormData] = useState({ name: "", parent_agency_id: "" });
  const [formError, setFormError] = useState("");

  useEffect(() => {
    loadAgencies();
  }, []);

  async function loadAgencies() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/admin/agencies");
      console.log("[AdminAgencies] Loaded:", resp.data?.length || 0);
      const sorted = (resp.data || []).sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      setAgencies(sorted);
    } catch (err) {
      console.error("[AdminAgencies] Load error:", err);
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
      setFormError("Acenta adı boş olamaz");
      return;
    }
    if (name.length < 2) {
      setFormError("Acenta adı en az 2 karakter olmalı");
      return;
    }

    setCreateLoading(true);
    try {
      const payload = { name };
      if (formData.parent_agency_id.trim()) {
        payload.parent_agency_id = formData.parent_agency_id.trim();
      }
      await api.post("/admin/agencies", payload);
      console.log("[AdminAgencies] Created:", name);
      toast.success("Acenta oluşturuldu");
      setFormData({ name: "", parent_agency_id: "" });
      setShowForm(false);
      // Refresh list
      await loadAgencies();
    } catch (err) {
      console.error("[AdminAgencies] Create error:", err);
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
          <h1 className="text-2xl font-bold text-foreground">Acentalar</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acenta yönetimi
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Acentalar yükleniyor...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Acentalar</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acenta yönetimi
          </p>
        </div>

        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Acentalar yüklenemedi</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <button
            onClick={loadAgencies}
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
          <h1 className="text-2xl font-bold text-foreground">Acentalar</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {agencies.length} acenta
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} className="gap-2">
          {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showForm ? "İptal" : "Yeni Acenta"}
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="rounded-2xl border bg-card shadow-sm p-6">
          <h3 className="font-semibold mb-4">Yeni Acenta Oluştur</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="agency-name">Acenta Adı *</Label>
              <Input
                id="agency-name"
                value={formData.name}
                onChange={(e) => setFormData({ name: e.target.value })}
                placeholder="Örn: ABC Turizm"
                disabled={createLoading}
              />
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
      {agencies.length === 0 && (
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
            <Building2 className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center max-w-md">
            <p className="font-semibold text-foreground">
              Henüz acenta yok
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Yeni acenta ekleyebilirsiniz.
            </p>
          </div>
        </div>
      )}

      {/* Data table */}
      {agencies.length > 0 && (
        <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="font-semibold">Ad</TableHead>
                <TableHead className="font-semibold">Durum</TableHead>
                <TableHead className="font-semibold">Oluşturma</TableHead>
                <TableHead className="font-semibold text-xs">Oluşturan</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {agencies.map((agency) => (
                <TableRow key={agency.id}>
                  <TableCell className="font-medium">{agency.name}</TableCell>
                  <TableCell>
                    {getActiveStatus(agency) ? (
                      <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                        Aktif
                      </Badge>
                    ) : (
                      <Badge variant="secondary">Pasif</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateTime(agency.created_at)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {agency.created_by || "-"}
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
