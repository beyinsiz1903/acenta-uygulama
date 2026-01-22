import React, { useCallback, useEffect, useState } from "react";
import { Plus, Search, Trash2, Pencil, Users } from "lucide-react";

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

          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="customer-error">
              {error}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button onClick={save} disabled={loading} data-testid="customer-save">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function CustomersPage() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [openForm, setOpenForm] = useState(false);
  const [editing, setEditing] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/customers", { params: { q: q || undefined } });
      setRows(resp.data || []);
    } catch (e) {
      const msg = apiErrorMessage(e);
      // "Not Found" durumunda liste boşmuş gibi davran, kırmızı hata gösterme.
      if (msg === "Not Found") {
        setRows([]);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [q]);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(id) {
    if (!window.confirm("Müşteriyi silmek istiyor musun?")) return;
    try {
      await api.delete(`/customers/${id}`);
      await load();
    } catch (e) {
      alert(apiErrorMessage(e));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Müşteriler</h2>
          <p className="text-sm text-muted-foreground">CRM altyapısı: müşteri kartları.</p>
        </div>
        <Button
          onClick={() => {
            setEditing(null);
            setOpenForm(true);
          }}
          className="gap-2"
          data-testid="customer-new"
        >
          <Plus className="h-4 w-4" />
          Yeni Müşteri
        </Button>
      </div>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            Liste
          </CardTitle>
          <div className="mt-3 flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Ara (isim/email/telefon)"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="pl-9"
                data-testid="customer-search"
              />
            </div>
            <Button variant="outline" onClick={load} data-testid="customer-search-btn">
              Ara
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="customer-list-error">
              {error}
            </div>
          ) : null}

          <div className="overflow-x-auto">
            <Table data-testid="customer-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Ad Soyad</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Telefon</TableHead>
                  <TableHead className="text-right">İşlem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-6 text-muted-foreground">
                      Yükleniyor...
                    </TableCell>
                  </TableRow>
                ) : rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-6 text-muted-foreground">
                      Kayıt yok.
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium text-foreground">{r.name}</TableCell>
                      <TableCell className="text-muted-foreground">{r.email || "-"}</TableCell>
                      <TableCell className="text-muted-foreground">{r.phone || "-"}</TableCell>
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
                            data-testid={`customer-edit-${r.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                            Düzenle
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            className="gap-2"
                            onClick={() => remove(r.id)}
                            data-testid={`customer-delete-${r.id}`}
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

      <CustomerForm open={openForm} onOpenChange={setOpenForm} initial={editing} onSaved={load} />
    </div>
  );
}
