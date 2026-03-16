import React, { useMemo, useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { PageShell, DataTable, SortableHeader, FilterBar } from "../design-system";
import { ConfirmDialog } from "../design-system";

/* ───────── Customer Form Dialog ───────── */
function CustomerForm({ open, onOpenChange, initial, onSaved }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setName(initial?.name || "");
      setEmail(initial?.email || "");
      setPhone(initial?.phone || "");
      setNotes(initial?.notes || "");
      setError("");
    }
  }, [open, initial]);

  async function save() {
    setLoading(true);
    setError("");
    try {
      if (initial?.id) {
        await api.put(`/customers/${initial.id}`, { name, email, phone, notes });
      } else {
        await api.post(`/customers`, { name, email, phone, notes });
      }
      onSaved?.();
      onOpenChange(false);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{initial?.id ? "Müşteri Düzenle" : "Yeni Müşteri"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Ad Soyad</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} data-testid="customer-name" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} data-testid="customer-email" />
            </div>
            <div className="space-y-2">
              <Label>Telefon</Label>
              <Input value={phone} onChange={(e) => setPhone(e.target.value)} data-testid="customer-phone" />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Not</Label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="customer-notes" />
          </div>
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="customer-error">{error}</div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Vazgeç</Button>
          <Button onClick={save} disabled={loading} data-testid="customer-save">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ═══════════════════════ MAIN PAGE ═══════════════════════ */
export default function CustomersPage() {
  const [q, setQ] = useState("");
  const [openForm, setOpenForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const queryClient = useQueryClient();

  const { data: rows = [], isLoading: loading, error: fetchError, refetch } = useQuery({
    queryKey: ["customers", "list", q],
    queryFn: async () => {
      const { data } = await api.get("/customers", { params: { q: q || undefined } });
      return data || [];
    },
    staleTime: 30_000,
    retry: (count, err) => err?.response?.status === 404 ? false : count < 2,
  });
  const error = fetchError ? (fetchError?.response?.status === 404 ? "" : apiErrorMessage(fetchError)) : "";

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/customers/${id}`),
    onSuccess: () => {
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (e) => alert(apiErrorMessage(e)),
  });

  function handleDelete() {
    if (!deleteTarget) return;
    deleteMutation.mutate(deleteTarget.id);
  }

  const columns = useMemo(() => [
    {
      accessorKey: "name",
      header: ({ column }) => <SortableHeader column={column}>Ad Soyad</SortableHeader>,
      cell: ({ row }) => <span className="font-medium text-foreground">{row.original.name}</span>,
    },
    {
      accessorKey: "email",
      header: "Email",
      cell: ({ row }) => <span className="text-muted-foreground">{row.original.email || "-"}</span>,
    },
    {
      accessorKey: "phone",
      header: "Telefon",
      cell: ({ row }) => <span className="text-muted-foreground">{row.original.phone || "-"}</span>,
    },
    {
      id: "actions",
      header: () => <span className="sr-only">İşlem</span>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button
            variant="outline" size="sm" className="gap-1.5 h-7 text-xs"
            onClick={(e) => { e.stopPropagation(); setEditing(row.original); setOpenForm(true); }}
            data-testid={`customer-edit-${row.original.id}`}
          >
            <Pencil className="h-3 w-3" />Düzenle
          </Button>
          <Button
            variant="outline" size="sm" className="gap-1.5 h-7 text-xs text-destructive border-destructive/30 hover:bg-destructive/5"
            onClick={(e) => { e.stopPropagation(); setDeleteTarget(row.original); }}
            data-testid={`customer-delete-${row.original.id}`}
          >
            <Trash2 className="h-3 w-3" />Sil
          </Button>
        </div>
      ),
      enableSorting: false,
    },
  ], []);

  return (
    <PageShell
      title="Müşteriler"
      description="CRM altyapısı: müşteri kartları"
      actions={
        <Button onClick={() => { setEditing(null); setOpenForm(true); }} className="gap-2" data-testid="customer-new">
          <Plus className="h-4 w-4" />Yeni Müşteri
        </Button>
      }
    >
      <div className="space-y-3">
        <FilterBar
          search={{ placeholder: "Ara (isim/email/telefon)", value: q, onChange: setQ }}
          onReset={() => setQ("")}
        />

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="customer-list-error">{error}</div>
        )}

        <DataTable
          data={rows}
          columns={columns}
          loading={loading}
          pageSize={20}
          emptyState={
            <div className="flex flex-col items-center gap-3 py-8">
              <p className="text-sm font-medium text-muted-foreground">Henüz müşteri yok</p>
              <p className="text-xs text-muted-foreground/70">İlk müşteri kaydını ekleyerek CRM akışını başlatabilirsiniz.</p>
              <Button onClick={() => { setEditing(null); setOpenForm(true); }} size="sm" data-testid="customer-empty-create">İlk müşteriyi ekle</Button>
            </div>
          }
        />
      </div>

      <CustomerForm open={openForm} onOpenChange={setOpenForm} initial={editing} onSaved={() => refetch()} />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
        title="Müşteriyi Sil"
        description={`"${deleteTarget?.name}" müşterisini silmek istediğinizden emin misiniz?`}
        variant="destructive"
        confirmLabel="Sil"
        cancelLabel="Vazgeç"
        onConfirm={handleDelete}
        loading={deleteMutation.isPending}
      />
    </PageShell>
  );
}
