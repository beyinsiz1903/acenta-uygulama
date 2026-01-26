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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { toast } from "sonner";

export default function AdminAgenciesPage() {
  const [agencies, setAgencies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [formData, setFormData] = useState({ name: "", parent_agency_id: "" });
  const [formError, setFormError] = useState("");

  const [editOpen, setEditOpen] = useState(false);
  const [editingAgency, setEditingAgency] = useState(null);
  const [editForm, setEditForm] = useState({ parent_agency_id: "", status: "" });
  const [editError, setEditError] = useState("");
  const [editLoading, setEditLoading] = useState(false);

  useEffect(() => {
    loadAgencies();
  }, []);

  async function loadAgencies() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/admin/agencies/");
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
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Örn: ABC Turizm"
                disabled={createLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="parent-agency-id">Üst Acenta ID (opsiyonel)</Label>
              <Input
                id="parent-agency-id"
                value={formData.parent_agency_id}
                onChange={(e) => setFormData((prev) => ({ ...prev, parent_agency_id: e.target.value }))}
                placeholder="Örn: 64f... (var olan bir acenta ID'si)"
                disabled={createLoading}
              />
              <p className="text-[11px] text-muted-foreground">
                Boş bırakırsanız ana acenta olarak kalır. Geçersiz veya kendisine eşit ID gönderildiğinde backend hata döner (SELF_PARENT_NOT_ALLOWED, PARENT_CYCLE_DETECTED).
              </p>
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
                <TableRow
                  key={agency.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => {
                    setEditingAgency(agency);
                    setEditForm({
                      parent_agency_id: agency.parent_agency_id || "",
                      status: agency.status || "active",
                    });
                    setEditError("");
                    setEditOpen(true);
                  }}
                >
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

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Acenta Hiyerarşi / Durum Düzenle</DialogTitle>
            <DialogDescription>
              Üst acentayı belirleyebilir veya acentayı aktif/pasif duruma alabilirsiniz.
            </DialogDescription>
          </DialogHeader>

          {editingAgency && (
            <div className="space-y-4 text-sm">
              <div className="space-y-1">
                <div className="font-medium">{editingAgency.name}</div>
                <div className="text-[11px] text-muted-foreground font-mono">{editingAgency.id}</div>
              </div>

              {editError && <p className="text-xs text-red-600">{editError}</p>}

              <div className="space-y-2">
                <Label htmlFor="edit-parent">Üst Acenta ID</Label>
                <Input
                  id="edit-parent"
                  value={editForm.parent_agency_id}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, parent_agency_id: e.target.value }))
                  }
                  placeholder="Örn: 64f... (boş bırakmak için tamamını silin)"
                  disabled={editLoading}
                />
                <p className="text-[11px] text-muted-foreground">
                  Boş bırakırsanız ana acenta olur. Geçersiz veya kendisine eşit ID gönderildiğinde backend
                  SELF_PARENT_NOT_ALLOWED / PARENT_CYCLE_DETECTED hatası döner.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="edit-status">Durum</Label>
                <select
                  id="edit-status"
                  className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                  value={editForm.status}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, status: e.target.value }))}
                  disabled={editLoading}
                >
                  <option value="active">Aktif</option>
                  <option value="disabled">Pasif</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setEditOpen(false)}
                  disabled={editLoading}
                >
                  İptal
                </Button>
                <Button
                  type="button"
                  size="sm"
                  disabled={editLoading}
                  onClick={async () => {
                    if (!editingAgency) return;
                    setEditError("");
                    setEditLoading(true);
                    try {
                      const payload = {};
                      const trimmed = (editForm.parent_agency_id || "").trim();
                      if (trimmed || editingAgency.parent_agency_id) {
                        // Eğer input boş ama önce parent varsa, bunu temizlemek için explicit null gönderiyoruz
                        payload.parent_agency_id = trimmed || null;
                      }
                      if (editForm.status && editForm.status !== editingAgency.status) {
                        payload.status = editForm.status;
                      }
                      if (Object.keys(payload).length === 0) {
                        setEditOpen(false);
                        return;
                      }
                      await api.put(`/admin/agencies/${editingAgency.id}`, payload);
                      toast.success("Acenta güncellendi");
                      await loadAgencies();
                      setEditOpen(false);
                    } catch (err) {
                      setEditError(apiErrorMessage(err));
                    } finally {
                      setEditLoading(false);
                    }
                  }}
                >
                  {editLoading ? "Kaydediliyor..." : "Kaydet"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

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
