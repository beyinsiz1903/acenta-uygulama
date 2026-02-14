import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, FileText, ArrowRight, RefreshCw, GripVertical } from "lucide-react";

import {
  DndContext,
  PointerSensor,
  closestCorners,
  useDroppable,
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
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

const LEAD_STATUSES = [
  { key: "new", label: "Yeni", tone: "bg-sky-500/10 text-sky-300 border-sky-500/20" },
  { key: "contacted", label: "İletişim", tone: "bg-amber-500/10 text-amber-300 border-amber-500/20" },
  { key: "won", label: "Kazanıldı", tone: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20" },
  { key: "lost", label: "Kaybedildi", tone: "bg-rose-500/10 text-rose-300 border-rose-500/20" },
];

function LeadCard({ lead, dragging, status }) {
  const tone = LEAD_STATUSES.find((s) => s.key === (status || lead.status))?.tone;

  return (
    <div
      className={
        "group relative rounded-2xl border bg-card px-3 py-2 shadow-sm transition " +
        (dragging ? "opacity-70" : "hover:shadow-md")
      }
    >
      <div className="flex items-start gap-2">
        <div className="mt-0.5 text-muted-foreground group-hover:text-foreground/70">
          <GripVertical className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <div className="truncate text-sm font-semibold text-foreground">
              {lead.customer_name || lead.customer_id}
            </div>
            {tone ? (
              <span className={"shrink-0 rounded-full border px-2 py-0.5 text-xs font-semibold " + tone}>
                {(status || lead.status || "new").toUpperCase()}
              </span>
            ) : null}
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="rounded-full border bg-accent px-2 py-0.5 text-xs font-medium text-foreground/80">
              {lead.source || "-"}
            </span>
            {lead.notes ? (
              <span className="truncate text-xs text-muted-foreground">{lead.notes}</span>
            ) : (
              <span className="text-xs text-muted-foreground">Not yok</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SortableLeadCard({ lead, status }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: lead.id,
    data: { lead },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <LeadCard lead={lead} dragging={isDragging} status={status} />
    </div>
  );
}

function KanbanColumn({ col, items }) {
  const { setNodeRef, isOver } = useDroppable({ id: col.key });

  return (
    <div
      ref={setNodeRef}
      className={
        "rounded-2xl border bg-card/60 p-3 transition shadow-sm " +
        (isOver ? "ring-2 ring-primary/25" : "hover:bg-card")
      }
      data-testid={`lead-col-${col.key}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={"rounded-lg border px-2 py-1 text-xs font-semibold " + (col.tone || "bg-accent text-foreground/80 border-border")}
          >
            {col.label}
          </div>
          <div className="text-xs text-muted-foreground">{items.length} kart</div>
        </div>
        <div className="h-2 w-2 rounded-full bg-primary/50" />
      </div>

      <div className="mt-3 space-y-2 max-h-[520px] overflow-y-auto pr-1">
        <SortableContext items={items.map((l) => l.id)} strategy={verticalListSortingStrategy}>
          {items.length ? (
            items.map((l) => <SortableLeadCard key={l.id} lead={l} status={col.key} />)
          ) : (
            <div className="rounded-xl border border-dashed bg-accent/40 px-3 py-6 text-center text-xs text-muted-foreground">
              Kartı buraya bırakın
            </div>
          )}
        </SortableContext>
      </div>
    </div>
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
  const [customers, setCustomers] = useState([]);
  const [error, setError] = useState("");

  const leadById = useMemo(() => {
    const map = new Map();
    for (const l of leads) map.set(l.id, l);
    return map;
  }, [leads]);

  const [openLeadForm, setOpenLeadForm] = useState(false);
  const [openQuoteForm, setOpenQuoteForm] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const [a, b, c] = await Promise.all([api.get("/leads"), api.get("/quotes"), api.get("/customers")]);
      const custList = c.data || [];
      const custMap = new Map(custList.map((x) => [x.id, x]));

      setCustomers(custList);

      // Lead kartında müşteri adını göstermek için zenginleştir.
      const enrichedLeads = (a.data || []).map((l) => ({
        ...l,
        customer_name: custMap.get(l.customer_id)?.name,
      }));

      setLeads(enrichedLeads);
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
    // Backend zaten sort_index desc döndürüyor; yine de güvenli olsun.
    for (const k of Object.keys(buckets)) {
      buckets[k] = buckets[k].slice().sort((a, b) => Number(b.sort_index || 0) - Number(a.sort_index || 0));
    }
    return buckets;
  }, [leads]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  async function persistLeadMove({ leadId, toStatus, toIndex }) {
    // Not: Hesaplamayı yaparken taşınan kartı listeden çıkarıyoruz ki komşu indeksleri şaşmasın.
    const bucket = (leadBuckets[toStatus] || []).filter((l) => l.id !== leadId);

    // UI index (0 = en üst). backend sort_index büyük => üst.
    // Basit yaklaşım: en üst için max+1, araya koyma için komşuların ortalaması.
    const upper = bucket[toIndex - 1];
    const lower = bucket[toIndex];

    const upperVal = upper ? Number(upper.sort_index || 0) : null;
    const lowerVal = lower ? Number(lower.sort_index || 0) : null;

    let nextSort = null;
    if (upperVal === null && lowerVal === null) nextSort = Date.now() / 1000;
    else if (upperVal === null) nextSort = (lowerVal || 0) + 1;
    else if (lowerVal === null) nextSort = upperVal + 1;
    else nextSort = (upperVal + lowerVal) / 2;

    // Optimistic UI
    setLeads((prev) =>
      prev.map((l) =>
        l.id === leadId
          ? {
              ...l,
              status: toStatus,
              sort_index: nextSort,
            }
          : l
      )
    );

    try {
      await api.patch(`/leads/${leadId}/status`, {
        status: toStatus,
        sort_index: nextSort,
      });
      await load();
    } catch (e) {
      alert(apiErrorMessage(e));
      await load();
    }
  }

  function findStatusOfLead(id) {
    for (const st of Object.keys(leadBuckets)) {
      if ((leadBuckets[st] || []).some((x) => x.id === id)) return st;
    }
    return "new";
  }

  function handleDragEnd(event) {
    const { active, over } = event;
    if (!active?.id || !over?.id) return;

    const activeId = String(active.id);
    const overId = String(over.id);

    const fromStatus = findStatusOfLead(activeId);

    // Eğer kolon üzerine bırakıldıysa overId = statusKey
    const statuses = LEAD_STATUSES.map((s) => s.key);
    if (statuses.includes(overId)) {
      // Kolona bırakınca en üste alıyoruz.
      persistLeadMove({ leadId: activeId, toStatus: overId, toIndex: 0 });
      return;
    }

    // Kartın üstüne bırakıldıysa: hedef kartın status'una git, index'i hesapla
    const overLead = leadById.get(overId);
    if (!overLead) return;

    const toStatus = overLead.status || "new";
    let toIndex = (leadBuckets[toStatus] || []).findIndex((x) => x.id === overId);
    if (toIndex === -1) return;

    // Aynı kolonda reorder yaparken: aktif kartı listeden çıkardığımız için hedef indeks kayabilir.
    if (fromStatus === toStatus) {
      const activeIndex = (leadBuckets[toStatus] || []).findIndex((x) => x.id === activeId);
      if (activeIndex !== -1 && activeIndex < toIndex) toIndex = Math.max(0, toIndex - 1);
    }

    persistLeadMove({ leadId: activeId, toStatus, toIndex });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">CRM</h2>
          <p className="text-sm text-muted-foreground">Lead → Teklif → Rezervasyon</p>
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
          <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={handleDragEnd}>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3" data-testid="lead-board">
              {LEAD_STATUSES.map((col) => (
                <KanbanColumn key={col.key} col={col} items={leadBuckets[col.key] || []} />
              ))}
            </div>
          </DndContext>
        </CardContent>
      </Card>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Teklifler</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table data-testid="quote-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Durum</TableHead>
                  <TableHead>Toplam</TableHead>
                  <TableHead>Para Birimi</TableHead>
                  <TableHead className="text-right">İşlem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {quotes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-6 text-muted-foreground">Kayıt yok.</TableCell>
                  </TableRow>
                ) : (
                  quotes.map((q) => (
                    <TableRow key={q.id}>
                      <TableCell>
                        <span className="rounded-full border bg-accent px-2 py-1 text-xs font-medium text-foreground/80">
                          {q.status}
                        </span>
                      </TableCell>
                      <TableCell className="font-medium text-foreground">{q.total}</TableCell>
                      <TableCell className="text-muted-foreground">{q.currency}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          onClick={() => convertQuote(q.id)}
                          className="gap-2"
                          data-testid={`quote-convert-${q.id}`}
                        >
                          Rezervasyona Çevir <ArrowRight className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <LeadForm open={openLeadForm} onOpenChange={setOpenLeadForm} onSaved={load} />
      <QuoteForm open={openQuoteForm} onOpenChange={setOpenQuoteForm} onSaved={load} />
    </div>
  );
}
