import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, FileText, ArrowRight, RefreshCw, GripVertical } from "lucide-react";

import {
  DndContext,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

function LeadForm({ open, onOpenChange, onSaved }) {
  const [customers, setCustomers] = useState([]);
  const [customerId, setCustomerId] = useState("");
  const [source, setSource] = useState("");
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("new");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    (async () => {
      setError("");
      try {
        const c = await api.get("/customers");
        setCustomers(c.data || []);
        setCustomerId((c.data || [])[0]?.id || "");
      } catch (e) {
        setError(apiErrorMessage(e));
      }
    })();
  }, [open]);

  async function save() {
    setLoading(true);
    setError("");
    try {
      await api.post("/leads", { customer_id: customerId, source, notes, status });
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
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Yeni Lead</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>Müşteri</Label>
            <Select value={customerId} onValueChange={setCustomerId}>
              <SelectTrigger data-testid="lead-customer">
                <SelectValue placeholder="Müşteri seç" />
              </SelectTrigger>
              <SelectContent>
                {customers.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Kaynak</Label>
            <Input value={source} onChange={(e) => setSource(e.target.value)} data-testid="lead-source" />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label>Not</Label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="lead-notes" />
          </div>
          <div className="space-y-2">
            <Label>Durum</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger data-testid="lead-status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="new">Yeni</SelectItem>
                <SelectItem value="contacted">İletişim Kuruldu</SelectItem>
                <SelectItem value="won">Kazanıldı</SelectItem>
                <SelectItem value="lost">Kaybedildi</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {error ? (
          <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="lead-error">
            {error}
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button onClick={save} disabled={loading} data-testid="lead-save">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function QuoteForm({ open, onOpenChange, onSaved }) {
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);

  const [customerId, setCustomerId] = useState("");
  const [productId, setProductId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [pax, setPax] = useState(1);
  const [unitPrice, setUnitPrice] = useState(0);
  const [currency, setCurrency] = useState("TRY");
  const [status, setStatus] = useState("draft");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    (async () => {
      setError("");
      try {
        const [c, p] = await Promise.all([api.get("/customers"), api.get("/products")]);
        setCustomers(c.data || []);
        setProducts(p.data || []);
        setCustomerId((c.data || [])[0]?.id || "");
        setProductId((p.data || [])[0]?.id || "");
      } catch (e) {
        setError(apiErrorMessage(e));
      }
    })();
  }, [open]);

  async function save() {
    setLoading(true);
    setError("");
    try {
      const total = Number(unitPrice || 0) * Number(pax || 1);
      await api.post("/quotes", {
        customer_id: customerId,
        currency,
        status,
        items: [
          {
            product_id: productId,
            start_date: startDate,
            end_date: endDate || null,
            pax: Number(pax || 1),
            unit_price: Number(unitPrice || 0),
            total,
          },
        ],
      });
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
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Yeni Teklif</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="space-y-2 md:col-span-2">
            <Label>Müşteri</Label>
            <Select value={customerId} onValueChange={setCustomerId}>
              <SelectTrigger data-testid="quote-customer">
                <SelectValue placeholder="Müşteri seç" />
              </SelectTrigger>
              <SelectContent>
                {customers.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Durum</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger data-testid="quote-status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="draft">Taslak</SelectItem>
                <SelectItem value="sent">Gönderildi</SelectItem>
                <SelectItem value="accepted">Kabul</SelectItem>
                <SelectItem value="rejected">Red</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label>Ürün</Label>
            <Select value={productId} onValueChange={setProductId}>
              <SelectTrigger data-testid="quote-product">
                <SelectValue placeholder="Ürün seç" />
              </SelectTrigger>
              <SelectContent>
                {products.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Birim Fiyat</Label>
            <Input type="number" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} data-testid="quote-unit" />
          </div>
          <div className="space-y-2">
            <Label>Başlangıç</Label>
            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} data-testid="quote-start" />
          </div>
          <div className="space-y-2">
            <Label>Bitiş</Label>
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} data-testid="quote-end" />
          </div>
          <div className="space-y-2">
            <Label>Pax</Label>
            <Input type="number" value={pax} onChange={(e) => setPax(e.target.value)} data-testid="quote-pax" />
          </div>
          <div className="space-y-2">
            <Label>Para Birimi</Label>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger data-testid="quote-currency">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="TRY">TRY</SelectItem>
                <SelectItem value="EUR">EUR</SelectItem>
                <SelectItem value="USD">USD</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {error ? (
          <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="quote-error">
            {error}
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button onClick={save} disabled={loading} data-testid="quote-save">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function CrmPage() {
  const [leads, setLeads] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [error, setError] = useState("");

  const [openLeadForm, setOpenLeadForm] = useState(false);
  const [openQuoteForm, setOpenQuoteForm] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const [a, b] = await Promise.all([api.get("/leads"), api.get("/quotes")]);
      setLeads(a.data || []);
      setQuotes(b.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      load();
    }, 0);
    return () => clearTimeout(t);
  }, [load]);

  async function convertQuote(id) {
    try {
      const resp = await api.post("/quotes/convert", { quote_id: id });
      alert(`Teklif rezervasyona çevrildi. PNR: ${resp.data.pnr}`);
      await load();
    } catch (e) {
      alert(apiErrorMessage(e));
    }
  }

  const leadBuckets = useMemo(() => {
    const buckets = { new: [], contacted: [], won: [], lost: [] };
    for (const l of leads) {
      const st = l.status || "new";
      if (!buckets[st]) buckets[st] = [];
      buckets[st].push(l);
    }
    return buckets;
  }, [leads]);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">CRM</h2>
          <p className="text-sm text-slate-600">Lead → Teklif → Rezervasyon</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} className="gap-2" data-testid="crm-refresh">
            <RefreshCw className="h-4 w-4" />
            Yenile
          </Button>
          <Button onClick={() => setOpenLeadForm(true)} className="gap-2" data-testid="lead-new">
            <Plus className="h-4 w-4" />
            Lead
          </Button>
          <Button onClick={() => setOpenQuoteForm(true)} className="gap-2" data-testid="quote-new">
            <FileText className="h-4 w-4" />
            Teklif
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="crm-error">
          {error}
        </div>
      ) : null}

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Lead Pipeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3" data-testid="lead-board">
            {Object.entries(leadBuckets).map(([status, arr]) => (
              <div key={status} className="rounded-2xl border bg-white p-3">
                <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
                  {status}
                </div>
                <div className="mt-2 space-y-2">
                  {arr.length === 0 ? (
                    <div className="text-xs text-slate-500">Boş</div>
                  ) : (
                    arr.map((l) => (
                      <div key={l.id} className="rounded-xl border bg-slate-50 px-3 py-2">
                        <div className="text-sm font-medium text-slate-900">{l.customer_id}</div>
                        <div className="text-xs text-slate-600">{l.source || "-"}</div>
                        <div className="text-xs text-slate-500">{l.notes || ""}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Teklifler</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="quote-table">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-2">Durum</th>
                  <th className="py-2">Toplam</th>
                  <th className="py-2">Para Birimi</th>
                  <th className="py-2 text-right">İşlem</th>
                </tr>
              </thead>
              <tbody>
                {quotes.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-slate-500">Kayıt yok.</td>
                  </tr>
                ) : (
                  quotes.map((q) => (
                    <tr key={q.id} className="border-t">
                      <td className="py-3">
                        <span className="rounded-full border bg-slate-50 px-2 py-1 text-xs font-medium text-slate-700">
                          {q.status}
                        </span>
                      </td>
                      <td className="py-3 font-medium text-slate-900">{q.total}</td>
                      <td className="py-3 text-slate-600">{q.currency}</td>
                      <td className="py-3 text-right">
                        <Button
                          size="sm"
                          onClick={() => convertQuote(q.id)}
                          className="gap-2"
                          data-testid={`quote-convert-${q.id}`}
                        >
                          Rezervasyona Çevir <ArrowRight className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <LeadForm open={openLeadForm} onOpenChange={setOpenLeadForm} onSaved={load} />
      <QuoteForm open={openQuoteForm} onOpenChange={setOpenQuoteForm} onSaved={load} />
    </div>
  );
}
