import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Search, Trash2, Pencil, Layers } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import EmptyState from "../components/EmptyState";

const TYPES = [
  { value: "tour", label: "Tur" },
  { value: "activity", label: "Aktivite" },
  { value: "accommodation", label: "Konaklama" },
  { value: "transfer", label: "Transfer" },
];

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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{initial?.id ? "Ürün Düzenle" : "Yeni Ürün"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Ürün Tipi</Label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger data-testid="product-type">
                <SelectValue placeholder="Seç" />
              </SelectTrigger>
              <SelectContent>
                {TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
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
          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="product-error">
              {error}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button onClick={save} disabled={loading} data-testid="product-save">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function ProductsPage() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [type, setType] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [openForm, setOpenForm] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/products", {
        params: { q, type: type && type !== "all" ? type : undefined },
      });
      setRows(resp.data || []);
    } catch (e) {
      const msg = apiErrorMessage(e);
      if (msg === "Not Found" || msg === "Request failed with status code 404") {
        setRows([]);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [q, type]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => rows, [rows]);

  async function remove(id) {
    if (!window.confirm("Ürünü silmek istiyor musun?")) return;
    try {
      await api.delete(`/products/${id}`);
      await load();
    } catch (e) {
      alert(apiErrorMessage(e));
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">Ürünler</h2>
          <p className="mt-0.5 text-xs text-muted-foreground/70 font-medium">
            Tur, konaklama ve transfer ürünlerini yönetin
          </p>
        </div>
        <Button
          onClick={() => {
            setEditing(null);
            setOpenForm(true);
          }}
          size="sm"
          className="gap-1.5 text-xs font-medium h-9"
          data-testid="product-new"
        >
          <Plus className="h-3.5 w-3.5" />
          Yeni Ürün
        </Button>
      </div>

      <Card className="rounded-xl shadow-sm border-border/60">
        <CardHeader className="pb-3 px-5 pt-5">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5">
            <div className="relative md:col-span-5">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground/50" />
              <Input
                placeholder="Ürün adı ile ara..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="pl-9 h-9 text-xs"
                data-testid="product-search"
              />
            </div>
            <div className="md:col-span-4">
              <Select value={type} onValueChange={setType}>
                <SelectTrigger data-testid="product-filter-type" className="h-9 text-xs">
                  <SelectValue placeholder="Tüm tipler" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tüm Tipler</SelectItem>
                  {TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-3">
              <Button variant="outline" onClick={load} className="w-full h-9 gap-1.5 text-xs font-medium" data-testid="product-filter-apply">
                <Search className="h-3 w-3" />
                Filtrele
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-5 pb-5">
          {error && error !== "Not Found" ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600 mb-3" data-testid="product-list-error">
              {error}
            </div>
          ) : null}

          <div className="overflow-x-auto rounded-lg border border-border/40">
            <Table data-testid="product-table">
              <TableHeader>
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Tip</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Başlık</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Açıklama</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9 text-right">İşlem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-12 text-center">
                      <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        Yükleniyor...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-8">
                      <EmptyState
                        title="Henüz ürün yok"
                        description="Katalogunuza ilk ürünü ekleyerek rezervasyon akışını test etmeye başlayın."
                        action={
                          <Button
                            onClick={() => { setEditing(null); setOpenForm(true); }}
                            size="sm"
                            className="text-xs"
                          >
                            İlk ürünü oluştur
                          </Button>
                        }
                      />
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((r) => {
                    const typeLabel = TYPES.find(t => t.value === r.type)?.label || r.type;
                    const typeColor = r.type === "tour" ? "text-violet-700 bg-violet-50 border-violet-200"
                      : r.type === "accommodation" || r.type === "hotel" ? "text-blue-700 bg-blue-50 border-blue-200"
                      : r.type === "transfer" ? "text-amber-700 bg-amber-50 border-amber-200"
                      : "text-slate-700 bg-slate-50 border-slate-200";
                    return (
                      <TableRow key={r.id} className="group hover:bg-muted/20 transition-colors">
                        <TableCell className="py-3">
                          <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold tracking-wide ${typeColor}`}>
                            {typeLabel}
                          </span>
                        </TableCell>
                        <TableCell className="text-[13px] font-semibold tracking-tight text-foreground py-3">{r.title}</TableCell>
                        <TableCell className="text-[12px] text-muted-foreground/70 py-3 max-w-[300px] truncate">{r.description || "—"}</TableCell>
                        <TableCell className="text-right py-3">
                          <div className="inline-flex gap-1.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="gap-1 text-[11px] font-medium h-7 text-primary hover:text-primary"
                              onClick={() => { setEditing(r); setOpenForm(true); }}
                              data-testid={`product-edit-${r.id}`}
                            >
                              <Pencil className="h-3 w-3" />
                              Düzenle
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="gap-1 text-[11px] font-medium h-7 text-rose-500 hover:text-rose-600 hover:bg-rose-50"
                              onClick={() => remove(r.id)}
                              data-testid={`product-delete-${r.id}`}
                            >
                              <Trash2 className="h-3 w-3" />
                              Sil
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <ProductForm open={openForm} onOpenChange={setOpenForm} initial={editing} onSaved={load} />
    </div>
  );
}
