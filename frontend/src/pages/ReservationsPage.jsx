import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Ticket, Search, CheckCircle2, XCircle, ExternalLink, Plus, MessageCircle,
  Calendar, CreditCard, User, Hash, FileText, Clock, ArrowRight, Banknote,
  CircleDollarSign, Tag, Receipt
} from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { formatMoney, statusBadge } from "../lib/format";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter } from "../components/ui/sheet";
import EmptyState from "../components/EmptyState";

/* ───────── Status helpers ───────── */
function statusConfig(status) {
  const s = (status || "").toLowerCase();
  if (s === "confirmed" || s === "CONFIRMED")
    return { label: "Onaylandı", color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200", dot: "bg-emerald-500" };
  if (s === "paid" || s === "PAID")
    return { label: "Ödendi", color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-200", dot: "bg-blue-500" };
  if (s === "cancelled" || s === "CANCELLED")
    return { label: "İptal", color: "text-rose-700", bg: "bg-rose-50", border: "border-rose-200", dot: "bg-rose-500" };
  if (s === "completed" || s === "COMPLETED")
    return { label: "Tamamlandı", color: "text-violet-700", bg: "bg-violet-50", border: "border-violet-200", dot: "bg-violet-500" };
  return { label: "Beklemede", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200", dot: "bg-amber-500" };
}

function StatusPill({ status }) {
  const cfg = statusConfig(status);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide ${cfg.bg} ${cfg.color} ${cfg.border} border`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

/* ───────── Info Card Component ───────── */
function InfoCard({ icon: Icon, label, value, accent, className = "" }) {
  return (
    <div className={`group relative overflow-hidden rounded-xl border border-border/60 bg-gradient-to-br from-background to-muted/30 p-3.5 transition-all hover:shadow-sm hover:border-primary/20 ${className}`}>
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/5 text-primary/60 group-hover:bg-primary/10 transition-colors">
            <Icon className="h-3.5 w-3.5" />
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">{label}</div>
          <div className={`mt-0.5 text-[13px] font-semibold tracking-tight truncate ${accent ? "text-primary" : "text-foreground"}`}>{value || "—"}</div>
        </div>
      </div>
    </div>
  );
}

/* ───────── Reservation Form (create) ───────── */
function ReservationForm({ open, onOpenChange, onSaved }) {
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);

  const [productId, setProductId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [pax, setPax] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    (async () => {
      setError("");
      try {
        const [a, b] = await Promise.all([api.get("/products"), api.get("/customers")]);
        setProducts(a.data || []);
        setCustomers(b.data || []);
        setProductId((a.data || [])[0]?.id || "");
        setCustomerId((b.data || [])[0]?.id || "");
      } catch (e) {
        setError(apiErrorMessage(e));
      }
    })();
  }, [open]);

  async function save() {
    setLoading(true);
    setError("");
    try {
      await api.post("/reservations/reserve", {
        product_id: productId,
        customer_id: customerId,
        start_date: startDate,
        end_date: endDate || null,
        pax: Number(pax || 1),
        channel: "direct",
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
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold tracking-tight">Yeni Rezervasyon</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Ürün</Label>
            <Select value={productId} onValueChange={setProductId}>
              <SelectTrigger data-testid="res-form-product">
                <SelectValue placeholder="Ürün seç" />
              </SelectTrigger>
              <SelectContent>
                {products.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.title} ({p.type})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Müşteri</Label>
            <Select value={customerId} onValueChange={setCustomerId}>
              <SelectTrigger data-testid="res-form-customer">
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
            <Label className="text-xs font-medium text-muted-foreground">Başlangıç</Label>
            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} data-testid="res-form-start" />
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Bitiş</Label>
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} data-testid="res-form-end" />
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Kişi Sayısı</Label>
            <Input type="number" min={1} value={pax} onChange={(e) => setPax(e.target.value)} data-testid="res-form-pax" />
          </div>
        </div>

        {error ? <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600">{error}</div> : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>İptal</Button>
          <Button onClick={save} disabled={loading} className="gap-2">
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ───────── Payment Form ───────── */
function PaymentForm({ reservationId, currency, onSaved }) {
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("cash");
  const [reference, setReference] = useState("");
  const [loading, setLoading] = useState(false);

  async function addPayment() {
    setLoading(true);
    try {
      await api.post("/payments", {
        reservation_id: reservationId,
        method,
        amount: Number(amount || 0),
        currency,
        reference,
        status: "paid",
      });
      setAmount("");
      setReference("");
      onSaved?.();
    } catch (e) {
      alert(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  const methodLabels = { cash: "Nakit", bank_transfer: "Havale", card: "Kredi Kartı", manual: "Manuel" };

  return (
    <div className="rounded-xl border border-border/60 bg-gradient-to-br from-background to-muted/20 p-4">
      <div className="flex items-center gap-2 mb-3">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/5">
          <Banknote className="h-3.5 w-3.5 text-primary/60" />
        </div>
        <span className="text-[13px] font-semibold tracking-tight text-foreground">Tahsilat Ekle</span>
      </div>
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-4">
        <div className="space-y-1.5">
          <Label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">Tutar</Label>
          <Input value={amount} onChange={(e) => setAmount(e.target.value)} type="number" placeholder="0.00" className="h-9 text-[13px]" data-testid="pay-amount" />
        </div>
        <div className="space-y-1.5">
          <Label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">Yöntem</Label>
          <Select value={method} onValueChange={setMethod}>
            <SelectTrigger data-testid="pay-method" className="h-9 text-[13px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="cash">Nakit</SelectItem>
              <SelectItem value="bank_transfer">Havale</SelectItem>
              <SelectItem value="card">Kredi Kartı</SelectItem>
              <SelectItem value="manual">Manuel</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">Referans</Label>
          <Input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Dekont no / açıklama" className="h-9 text-[13px]" data-testid="pay-ref" />
        </div>
      </div>
      <div className="mt-3">
        <Button onClick={addPayment} disabled={loading} size="sm" className="gap-1.5 text-xs font-medium" data-testid="pay-save">
          <CreditCard className="h-3 w-3" />
          {loading ? "Kaydediliyor..." : "Tahsilatı Kaydet"}
        </Button>
      </div>
    </div>
  );
}

/* ───────── Reservation Detail Sheet ───────── */
function ReservationDetails({ open, onOpenChange, reservationId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!reservationId) return;
    setLoading(true);
    setError("");
    try {
      const resp = await api.get(`/reservations/${reservationId}`);
      setData(resp.data);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [reservationId]);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  async function confirm() {
    await api.post(`/reservations/${reservationId}/confirm`);
    await load();
  }

  async function cancel() {
    if (!window.confirm("Rezervasyonu iptal etmek istiyor musunuz?")) return;
    await api.post(`/reservations/${reservationId}/cancel`);
    await load();
  }

  const openVoucher = useCallback(async () => {
    if (!reservationId) return;
    try {
      const resp = await api.get(`/reservations/${reservationId}/voucher`, {
        responseType: "text",
        headers: { Accept: "text/html" },
      });
      const html = typeof resp.data === "string" ? resp.data : String(resp.data);
      const blob = new Blob([html], { type: "text/html; charset=utf-8" });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
      console.error("Voucher açılamadı:", e);
      alert("Voucher açılamadı. Lütfen tekrar deneyin.");
    }
  }, [reservationId]);

  const sendWhatsApp = useCallback(() => {
    if (!data) return;
    const guestName = data.customer_name || data.guest_name || "Misafir";
    const pnr = data.pnr || "-";
    const voucherNo = data.voucher_no || "-";
    const status = data.status || "-";
    const total = data.total_price || 0;
    const currency = data.currency || "TRY";
    const startDate = data.start_date || "";
    const endDate = data.end_date || "";
    const productTitle = data.product_title || "";

    const message = [
      `🏨 Rezervasyon Bilgisi`,
      ``,
      `📋 PNR: ${pnr}`,
      `📄 Voucher No: ${voucherNo}`,
      productTitle ? `🏠 Ürün: ${productTitle}` : "",
      `👤 Misafir: ${guestName}`,
      `📅 Tarih: ${startDate}${endDate ? " - " + endDate : ""}`,
      `💰 Toplam: ${Number(total).toLocaleString("tr-TR")} ${currency}`,
      `📊 Durum: ${status}`,
      ``,
      `Voucher linki:`,
      `${process.env.REACT_APP_BACKEND_URL}/api/reservations/${reservationId}/voucher`,
    ].filter(Boolean).join("\n");

    const phone = (data.customer_phone || data.guest_phone || "").replace(/[^0-9+]/g, "");
    const encoded = encodeURIComponent(message);

    if (phone) {
      let cleanPhone = phone.replace(/^\+/, "");
      if (cleanPhone.startsWith("0")) cleanPhone = "90" + cleanPhone.slice(1);
      if (!cleanPhone.startsWith("90") && cleanPhone.length === 10) cleanPhone = "90" + cleanPhone;
      window.open(`https://wa.me/${cleanPhone}?text=${encoded}`, "_blank");
    } else {
      window.open(`https://api.whatsapp.com/send?text=${encoded}`, "_blank");
    }
  }, [data, reservationId]);

  const dueAmount = data ? (data.due_amount ?? Math.max(0, (data.total_price || 0) - (data.paid_amount || 0))) : 0;
  const paidPercent = data && data.total_price > 0 ? Math.min(100, Math.round(((data.paid_amount || 0) / data.total_price) * 100)) : 0;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="p-0 w-full sm:w-[580px] sm:max-w-none">
        {/* ── Header ── */}
        <div className="sticky top-0 z-10 border-b bg-gradient-to-r from-slate-50 to-background backdrop-blur supports-[backdrop-filter]:bg-background/90">
          <div className="px-5 py-4">
            <SheetHeader>
              <div className="flex items-center justify-between">
                <SheetTitle className="text-base font-semibold tracking-tight text-foreground">
                  Rezervasyon Detayı
                </SheetTitle>
                {data && <StatusPill status={data.status} />}
              </div>
            </SheetHeader>
            {data && (
              <div className="mt-3 flex items-center gap-3 text-[11px] text-muted-foreground">
                <span className="flex items-center gap-1"><Hash className="h-3 w-3" /> {data.pnr}</span>
                <span className="text-border">|</span>
                <span className="flex items-center gap-1"><FileText className="h-3 w-3" /> {data.voucher_no || "—"}</span>
                {data.channel && (
                  <>
                    <span className="text-border">|</span>
                    <span className="flex items-center gap-1"><Tag className="h-3 w-3" /> {data.channel}</span>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Body ── */}
        <div className="max-h-[calc(100vh-140px)] overflow-y-auto">
          <div className="px-5 py-4 space-y-5">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                <span className="ml-2 text-xs text-muted-foreground">Yükleniyor...</span>
              </div>
            )}
            {error && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-xs text-rose-600 font-medium" data-testid="res-detail-error">
                {error}
              </div>
            )}

            {data && (
              <>
                {/* ── Financial Summary ── */}
                <div className="rounded-xl border border-border/60 bg-gradient-to-br from-primary/[0.02] to-primary/[0.06] p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
                      <CircleDollarSign className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <span className="text-[13px] font-semibold tracking-tight text-foreground">Finansal Özet</span>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-lg bg-background/80 border border-border/40 p-3 text-center">
                      <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">Toplam</div>
                      <div className="mt-1 text-base font-bold tracking-tight text-foreground">{formatMoney(data.total_price, data.currency)}</div>
                    </div>
                    <div className="rounded-lg bg-background/80 border border-border/40 p-3 text-center">
                      <div className="text-[10px] font-medium uppercase tracking-wider text-emerald-600/70">Ödenen</div>
                      <div className="mt-1 text-base font-bold tracking-tight text-emerald-600">{formatMoney(data.paid_amount, data.currency)}</div>
                    </div>
                    <div className="rounded-lg bg-background/80 border border-border/40 p-3 text-center">
                      <div className="text-[10px] font-medium uppercase tracking-wider text-amber-600/70">Kalan</div>
                      <div className={`mt-1 text-base font-bold tracking-tight ${dueAmount > 0 ? "text-amber-600" : "text-emerald-600"}`}>
                        {formatMoney(dueAmount, data.currency)}
                      </div>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
                      <span>Ödeme İlerlemesi</span>
                      <span className="font-semibold text-foreground">%{paidPercent}</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-border/40 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${paidPercent >= 100 ? "bg-emerald-500" : "bg-primary"}`}
                        style={{ width: `${paidPercent}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* ── Detail Cards ── */}
                <div>
                  <div className="flex items-center gap-2 mb-2.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60">Rezervasyon Bilgileri</span>
                    <div className="flex-1 h-px bg-border/40" />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <InfoCard icon={Hash} label="PNR" value={data.pnr} accent />
                    <InfoCard icon={FileText} label="Voucher No" value={data.voucher_no} />
                    <InfoCard icon={Calendar} label="Başlangıç" value={data.start_date || data.check_in || "—"} />
                    <InfoCard icon={Calendar} label="Bitiş" value={data.end_date || data.check_out || "—"} />
                    <InfoCard icon={User} label="Misafir" value={data.customer_name || data.guest_name} />
                    <InfoCard icon={Tag} label="Kanal" value={data.channel} />
                    {data.product_title && (
                      <InfoCard icon={Ticket} label="Ürün" value={data.product_title} className="col-span-2" />
                    )}
                  </div>
                </div>

                {/* ── Actions ── */}
                <div>
                  <div className="flex items-center gap-2 mb-2.5">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60">İşlemler</span>
                    <div className="flex-1 h-px bg-border/40" />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button onClick={confirm} variant="outline" size="sm" className="gap-1.5 text-xs font-medium h-8 border-emerald-200 text-emerald-700 hover:bg-emerald-50 hover:text-emerald-800" data-testid="res-confirm">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Onayla
                    </Button>
                    <Button onClick={cancel} variant="outline" size="sm" className="gap-1.5 text-xs font-medium h-8 border-rose-200 text-rose-600 hover:bg-rose-50 hover:text-rose-700" data-testid="res-cancel">
                      <XCircle className="h-3.5 w-3.5" />
                      İptal Et
                    </Button>
                    <Button onClick={openVoucher} variant="outline" size="sm" className="gap-1.5 text-xs font-medium h-8 border-primary/30 text-primary hover:bg-primary/5" data-testid="res-voucher">
                      <ExternalLink className="h-3.5 w-3.5" />
                      Voucher
                    </Button>
                    <Button onClick={sendWhatsApp} variant="outline" size="sm" className="gap-1.5 text-xs font-medium h-8 border-emerald-200 text-emerald-600 hover:bg-emerald-50" data-testid="res-whatsapp">
                      <MessageCircle className="h-3.5 w-3.5" />
                      WhatsApp
                    </Button>
                  </div>
                </div>

                {/* ── Payment Form ── */}
                <PaymentForm reservationId={reservationId} currency={data.currency} onSaved={load} />

                {/* ── Payment History ── */}
                <div className="rounded-xl border border-border/60 bg-gradient-to-br from-background to-muted/20 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/5">
                        <Receipt className="h-3.5 w-3.5 text-primary/60" />
                      </div>
                      <span className="text-[13px] font-semibold tracking-tight text-foreground">Tahsilatlar</span>
                    </div>
                    <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary/10 px-1.5 text-[10px] font-bold text-primary">
                      {(data.payments || []).length}
                    </span>
                  </div>

                  {(data.payments || []).length === 0 ? (
                    <div className="py-4 text-center text-xs text-muted-foreground/60">Henüz tahsilat kaydı bulunmuyor.</div>
                  ) : (
                    <div className="space-y-1.5">
                      {(data.payments || []).map((p) => (
                        <div key={p.id} className="flex items-center justify-between rounded-lg border border-border/40 bg-background/60 px-3 py-2.5 transition-colors hover:bg-muted/30">
                          <div>
                            <div className="text-xs font-medium text-foreground">{p.method === "cash" ? "Nakit" : p.method === "bank_transfer" ? "Havale" : p.method === "card" ? "Kredi Kartı" : p.method}</div>
                            <div className="text-[10px] text-muted-foreground/60 mt-0.5">
                              {p.reference || "—"} · {p.created_at ? new Date(p.created_at).toLocaleDateString("tr-TR") : ""}
                            </div>
                          </div>
                          <div className="text-xs font-bold text-emerald-600">
                            +{formatMoney(p.amount, p.currency)}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* ── Footer ── */}
        <div className="sticky bottom-0 border-t bg-background/95 backdrop-blur px-5 py-3">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} className="text-xs font-medium" data-testid="res-detail-close">
            Kapat
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

/* ═══════════════════════ MAIN PAGE ═══════════════════════ */
export default function ReservationsPage() {
  const [searchParams] = useSearchParams();
  const statusParam = searchParams.get("status") || "";

  const [status, setStatus] = useState(statusParam || "all");
  const [q, setQ] = useState("");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [openForm, setOpenForm] = useState(false);
  const [detailId, setDetailId] = useState(null);
  const [openDetail, setOpenDetail] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/reservations", {
        params: { status: status && status !== "all" ? status : undefined, q: q || undefined },
      });
      setRows(resp.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [q, status]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    setStatus(statusParam || "all");
  }, [statusParam]);

  const badges = useMemo(
    () =>
      rows.reduce((acc, r) => {
        acc[r.status] = (acc[r.status] || 0) + 1;
        return acc;
      }, {}),
    [rows]
  );

  return (
    <div className="space-y-5">
      {/* ── Page Header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">Rezervasyonlar</h2>
          <p className="mt-0.5 text-xs text-muted-foreground/70 font-medium">Durum akışı, voucher ve tahsilat yönetimi</p>
        </div>
        <Button onClick={() => setOpenForm(true)} size="sm" className="gap-1.5 text-xs font-medium h-9" data-testid="res-new">
          <Plus className="h-3.5 w-3.5" />
          Yeni Rezervasyon
        </Button>
      </div>

      {/* ── Status Badges ── */}
      {Object.keys(badges).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(badges).map(([k, v]) => {
            const cfg = statusConfig(k);
            return (
              <div key={k} className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 ${cfg.bg} ${cfg.border}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
                <span className={`text-[11px] font-medium ${cfg.color}`}>{cfg.label}</span>
                <span className={`text-[11px] font-bold ${cfg.color}`}>{v}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Filters + Table ── */}
      <Card className="rounded-xl shadow-sm border-border/60">
        <CardHeader className="pb-3 px-5 pt-5">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5">
            <div className="relative md:col-span-5">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground/50" />
              <Input
                placeholder="PNR veya müşteri ara..."
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="pl-9 h-9 text-xs"
                data-testid="res-search"
              />
            </div>
            <div className="md:col-span-4">
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger data-testid="res-filter-status" className="h-9 text-xs">
                  <SelectValue placeholder="Tüm durumlar" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tüm Durumlar</SelectItem>
                  <SelectItem value="pending">Beklemede</SelectItem>
                  <SelectItem value="confirmed">Onaylandı</SelectItem>
                  <SelectItem value="paid">Ödendi</SelectItem>
                  <SelectItem value="cancelled">İptal</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-3">
              <Button variant="outline" onClick={load} className="w-full h-9 gap-1.5 text-xs font-medium" data-testid="res-filter-apply">
                <Search className="h-3 w-3" />
                Filtrele
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-5 pb-5">
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600 mb-3" data-testid="res-list-error">
              {error}
            </div>
          )}

          <div className="overflow-x-auto rounded-lg border border-border/40">
            <Table data-testid="res-table">
              <TableHeader>
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">PNR</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Durum</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Toplam</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Ödenen</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Kanal</TableHead>
                  <TableHead className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/70 h-9 text-right">İşlem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-12 text-center">
                      <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        Yükleniyor...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-8">
                      <EmptyState
                        title="Henüz rezervasyon yok"
                        description="İlk manuel rezervasyonu oluşturarak satış akışını uçtan uca test edebilirsiniz."
                        action={
                          <Button onClick={() => setOpenForm(true)} size="sm" className="text-xs">
                            İlk rezervasyonu oluştur
                          </Button>
                        }
                      />
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((r) => (
                    <TableRow key={r.id} className="group cursor-pointer hover:bg-muted/20 transition-colors" onClick={() => { setDetailId(r.id); setOpenDetail(true); }}>
                      <TableCell className="text-[13px] font-semibold tracking-tight text-foreground py-3">{r.pnr}</TableCell>
                      <TableCell className="py-3">
                        <div className="flex items-center gap-1.5">
                          <StatusPill status={r.status} />
                          {r.has_open_case && (
                            <button
                              type="button"
                              className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[9px] font-bold text-amber-800 tracking-wide"
                              onClick={(e) => { e.stopPropagation(); window.location.href = `/ops/cases?booking_id=${r.id}&status=open,waiting,in_progress`; }}
                              data-testid={`badge-open-case-${r.id}`}
                            >
                              OPEN CASE
                            </button>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-[13px] font-medium text-foreground/80 py-3">{formatMoney(r.total_price, r.currency)}</TableCell>
                      <TableCell className="text-[13px] font-medium text-foreground/80 py-3">{formatMoney(r.paid_amount, r.currency)}</TableCell>
                      <TableCell className="text-[12px] text-muted-foreground py-3">{r.channel}</TableCell>
                      <TableCell className="text-right py-3">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-1 text-[11px] font-medium h-7 text-primary hover:text-primary opacity-60 group-hover:opacity-100 transition-opacity"
                          onClick={(e) => { e.stopPropagation(); setDetailId(r.id); setOpenDetail(true); }}
                          data-testid={`res-open-${r.id}`}
                        >
                          Detay
                          <ArrowRight className="h-3 w-3" />
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

      <ReservationForm open={openForm} onOpenChange={setOpenForm} onSaved={load} />
      <ReservationDetails open={openDetail} onOpenChange={setOpenDetail} reservationId={detailId} />
    </div>
  );
}
