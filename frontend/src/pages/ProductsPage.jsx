import React, { useEffect, useMemo, useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { PageShell, DataTable, SortableHeader, FilterBar } from "../design-system";
import { useProducts, useDeleteProduct } from "../features/bookings/hooks";
import { ConfirmDialog } from "../design-system";
import { toast } from "sonner";

const TYPES = [
  { value: "tour", label: "Tur" },
  { value: "activity", label: "Aktivite" },
  { value: "accommodation", label: "Konaklama" },
  { value: "transfer", label: "Transfer" },
];

const TYPE_COLORS = {
  tour: "text-violet-700 bg-violet-50 border-violet-200",
  activity: "text-teal-700 bg-teal-50 border-teal-200",
  accommodation: "text-blue-700 bg-blue-50 border-blue-200",
  hotel: "text-blue-700 bg-blue-50 border-blue-200",
  transfer: "text-amber-700 bg-amber-50 border-amber-200",
};

function ProductForm({ open, onOpenChange, initial, onSaved }) {
  const [title, setTitle] = useState(initial?.title || "");
  const [type, setType] = useState(initial?.type || "tour");
  const [description, setDescription] = useState(initial?.description || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setTitle(initial?.title || "");
      setType(initial?.type || "tour");
      setDescription(initial?.description || "");
      setError("");
    }
  }, [open, initial]);

  async function save() {
    setLoading(true);
    setError("");
    try {
      if (initial?.id) {
        await api.put(`/products/${initial.id}`, { title, type, description });
      } else {
        await api.post(`/products`, { title, type, description });
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
      <DialogContent className="max-w-lg" data-testid="product-form-dialog">
        <DialogHeader>
          <DialogTitle>{initial?.id ? "Ürün Düzenle" : "Yeni Ürün"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Ürün Tipi</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger data-testid="product-type"><SelectValue placeholder="Seç" /></SelectTrigger>
              <SelectContent>
                {TYPES.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Başlık</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} data-testid="product-title" />
          </div>
          <div className="space-y-2">
            <Label>Açıklama</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} data-testid="product-desc" />
          </div>
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600" data-testid="product-error">{error}</div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Vazgeç</Button>
          <Button onClick={save} disabled={loading} data-testid="product-save">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function ProductsPage() {
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [openForm, setOpenForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const filters = useMemo(() => ({ q: q || undefined, type: type || undefined }), [q, type]);
  const { data: rows = [], isLoading, isError, error, refetch } = useProducts(filters);
  const deleteMutation = useDeleteProduct();

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget.id);
      setDeleteTarget(null);
    } catch (e) {
      toast.error(apiErrorMessage(e));
    }
  }

  const columns = useMemo(() => [
    {
      accessorKey: "type",
      header: "Tip",
      cell: ({ row }) => {
        const typeLabel = TYPES.find((t) => t.value === row.original.type)?.label || row.original.type;
        const colorClass = TYPE_COLORS[row.original.type] || "text-foreground bg-slate-50 border-slate-200";
        return (
          <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-2xs font-semibold tracking-wide ${colorClass}`}>
            {typeLabel}
          </span>
        );
      },
      size: 120,
    },
    {
      accessorKey: "title",
      header: ({ column }) => <SortableHeader column={column}>Başlık</SortableHeader>,
      cell: ({ row }) => <span className="text-sm font-semibold tracking-tight text-foreground">{row.original.title}</span>,
    },
    {
      accessorKey: "description",
      header: "Açıklama",
      cell: ({ row }) => <span className="text-xs text-muted-foreground/70 max-w-[300px] truncate block">{row.original.description || "—"}</span>,
    },
    {
      id: "actions",
      header: () => <span className="sr-only">İşlem</span>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-1.5">
          <Button
            variant="ghost" size="sm"
            className="gap-1 text-xs font-medium h-7 text-primary hover:text-primary"
            onClick={(e) => { e.stopPropagation(); setEditing(row.original); setOpenForm(true); }}
            data-testid={`product-edit-${row.original.id}`}
          >
            <Pencil className="h-3 w-3" /> Düzenle
          </Button>
          <Button
            variant="ghost" size="sm"
            className="gap-1 text-xs font-medium h-7 text-rose-500 hover:text-rose-600 hover:bg-rose-50"
            onClick={(e) => { e.stopPropagation(); setDeleteTarget(row.original); }}
            data-testid={`product-delete-${row.original.id}`}
          >
            <Trash2 className="h-3 w-3" /> Sil
          </Button>
        </div>
      ),
      enableSorting: false,
    },
  ], []);

  return (
    <PageShell
      title="Ürünler"
      description="Tur, konaklama ve transfer ürünlerini yönetin"
      actions={
        <Button onClick={() => { setEditing(null); setOpenForm(true); }} size="sm" className="gap-1.5 text-xs font-medium h-9" data-testid="product-new">
          <Plus className="h-3.5 w-3.5" /> Yeni Ürün
        </Button>
      }
    >
      <div className="space-y-3">
        <FilterBar
          search={{ placeholder: "Ürün adı ile ara...", value: q, onChange: setQ }}
          filters={[
            { key: "type", label: "Tip", value: type, onChange: setType, options: TYPES },
          ]}
          onReset={() => { setQ(""); setType(""); }}
        />

        {isError && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600" data-testid="product-list-error">
            {error?.message || "Veriler yüklenemedi"}
            <Button variant="ghost" size="sm" className="ml-2 h-6 text-xs" onClick={() => refetch()}>Tekrar Dene</Button>
          </div>
        )}

        <DataTable
          data={rows}
          columns={columns}
          loading={isLoading}
          pageSize={20}
          emptyState={
            <div className="flex flex-col items-center gap-3 py-8">
              <p className="text-sm font-medium text-muted-foreground">Henüz ürün yok</p>
              <p className="text-xs text-muted-foreground/70">Katalogunuza ilk ürünü ekleyerek başlayın.</p>
              <Button onClick={() => { setEditing(null); setOpenForm(true); }} size="sm" className="text-xs" data-testid="product-empty-create">İlk ürünü oluştur</Button>
            </div>
          }
        />
      </div>

      <ProductForm open={openForm} onOpenChange={setOpenForm} initial={editing} onSaved={() => refetch()} />
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => { if (!v) setDeleteTarget(null); }}
        title="Ürünü Sil"
        description={`"${deleteTarget?.title}" ürünü kalıcı olarak silinecektir.`}
        confirmLabel="Sil"
        variant="destructive"
        loading={deleteMutation.isPending}
        onConfirm={handleDelete}
      />
    </PageShell>
  );
}
