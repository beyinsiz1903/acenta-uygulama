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
      setError(apiErrorMessage(e));
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
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Ürünler</h2>
          <p className="text-sm text-muted-foreground">
            Tur / konaklama / transfer ürünlerini yönetin.
          </p>
        </div>
        <Button
          onClick={() => {
            setEditing(null);
            setOpenForm(true);
          }}
          className="gap-2"
          data-testid="product-new"
        >
          <Plus className="h-4 w-4" />
          Yeni Ürün
        </Button>
      </div>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-4 w-4 text-muted-foreground" />
            Katalog
          </CardTitle>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Ara (başlık)"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="pl-9"
                data-testid="product-search"
              />
            </div>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger data-testid="product-filter-type">
                <SelectValue placeholder="Tüm tipler" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tümü</SelectItem>
                {TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={load} data-testid="product-filter-apply">
              Filtrele
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && error !== "Not Found" ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="product-list-error">
              {error}
            </div>
          ) : null}

          <div className="overflow-x-auto">
            <Table data-testid="product-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Tip</TableHead>
                  <TableHead>Başlık</TableHead>
                  <TableHead>Açıklama</TableHead>
                  <TableHead className="text-right">İşlem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-6 text-muted-foreground">Yükleniyor...</TableCell>
                  </TableRow>
                ) : filtered.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-6 text-muted-foreground">Kayıt yok.</TableCell>
                  </TableRow>
                ) : (
                  filtered.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>
                        <span className="rounded-full border bg-accent px-2 py-1 text-xs font-medium text-foreground/80">
                          {r.type}
                        </span>
                      </TableCell>
                      <TableCell className="font-medium text-foreground">{r.title}</TableCell>
                      <TableCell className="text-muted-foreground">{r.description || "-"}</TableCell>
                      <TableCell className="text-right">
                        <div className="inline-flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-2"
                            onClick={() => {
                              setEditing(r);
                              setOpenForm(true);
                            }}
                            data-testid={`product-edit-${r.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                            Düzenle
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            className="gap-2"
                            onClick={() => remove(r.id)}
                            data-testid={`product-delete-${r.id}`}
                          >
                            <Trash2 className="h-4 w-4" />
                            Sil
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
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
