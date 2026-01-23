import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Ticket, Search, CheckCircle2, XCircle, ExternalLink, Plus } from "lucide-react";

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
          <DialogTitle>Yeni Rezervasyon</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>Ürün</Label>
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
            <Label>Müşteri</Label>
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
            <Label>Başlangıç</Label>
            <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} data-testid="res-form-start" />
          </div>
          <div className="space-y-2">
            <Label>Bitiş (opsiyonel)</Label>
            <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} data-testid="res-form-end" />
          </div>
          <div className="space-y-2">
            <Label>Pax</Label>
            <Input type="number" value={pax} onChange={(e) => setPax(e.target.value)} data-testid="res-form-pax" />
          </div>
        </div>

        {error ? (
          <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="res-form-error">
            {error}
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Vazgeç
          </Button>
          <Button onClick={save} disabled={loading} data-testid="res-form-save">
            {loading ? "Oluşturuluyor..." : "Rezervasyon Oluştur"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

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

  return (
    <div className="rounded-2xl border bg-card p-4">
      <div className="text-sm font-semibold text-foreground">Tahsilat Ekle</div>
      <div className="mt-3 grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="space-y-2">
          <Label>Tutar</Label>
          <Input value={amount} onChange={(e) => setAmount(e.target.value)} type="number" data-testid="pay-amount" />
        </div>
        <div className="space-y-2">
          <Label>Yöntem</Label>
          <Select value={method} onValueChange={setMethod}>
            <SelectTrigger data-testid="pay-method">
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
        <div className="space-y-2 md:col-span-2">
          <Label>Referans</Label>
          <Input value={reference} onChange={(e) => setReference(e.target.value)} data-testid="pay-ref" />
        </div>
      </div>
      <div className="mt-3">
        <Button onClick={addPayment} disabled={loading} className="gap-2" data-testid="pay-save">
          {loading ? "Ekleniyor..." : "Tahsilatı Kaydet"}
        </Button>
      </div>
    </div>
  );
}

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
    if (!window.confirm("Rezervasyonu iptal etmek istiyor musun?")) return;
    await api.post(`/reservations/${reservationId}/cancel`);
    await load();
  }

  const badge = statusBadge(data?.status);

  const openVoucher = useCallback(() => {
    if (!reservationId) return;
    // REACT_APP_BACKEND_URL kullanılmalı, hardcode yok.
    window.open(`${process.env.REACT_APP_BACKEND_URL}/api/reservations/${reservationId}/voucher`, "_blank");
  }, [reservationId]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="p-0">
        <div className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-5 py-4">
          <SheetHeader>
            <SheetTitle>Rezervasyon Detayı</SheetTitle>
          </SheetHeader>
        </div>

        <div className="max-h-[calc(100vh-64px)] overflow-y-auto px-5 py-4">
          {loading ? <div className="text-sm text-muted-foreground">Yükleniyor...</div> : null}
          {error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="res-detail-error">
            {error}
          </div>
        ) : null}

          {data ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <div className="rounded-2xl border bg-accent/40 p-3">
                  <div className="text-xs text-muted-foreground">PNR</div>
                  <div className="text-sm font-semibold text-foreground">{data.pnr}</div>
                </div>
                <div className="rounded-2xl border bg-accent/40 p-3">
                <div className="text-xs text-muted-foreground">Voucher</div>
                <div className="text-sm font-semibold text-foreground">{data.voucher_no}</div>
              </div>
              <div className="rounded-2xl border bg-accent/40 p-3">
                <div className="text-xs text-muted-foreground">Durum</div>
                <div className="text-sm font-semibold text-foreground">{badge.label}</div>
              </div>
            </div>

              <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                <div className="rounded-2xl border bg-card p-4">
                  <div className="text-xs text-muted-foreground">Aksiyonlar</div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button onClick={confirm} variant="outline" className="gap-2" data-testid="res-confirm">
                      <CheckCircle2 className="h-4 w-4" />
                      Onayla
                    </Button>
                    <Button onClick={cancel} variant="destructive" className="gap-2" data-testid="res-cancel">
                      <XCircle className="h-4 w-4" />
                      İptal
                    </Button>
                    <Button
                      onClick={openVoucher}
                      variant="outline"
                      className="gap-2"
                      data-testid="res-voucher"
                    >
                      <ExternalLink className="h-4 w-4" />
                      Voucher
                    </Button>
                  </div>
                  <div className="mt-3 text-xs text-muted-foreground">
                    Not: Aksiyonlar status’e göre backend’de doğrulanır.
                  </div>
                </div>

                <div className="rounded-2xl border bg-card p-4 md:col-span-2">
                  <div className="text-xs text-muted-foreground">Özet</div>
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-xs text-muted-foreground">Toplam</div>
                      <div className="text-sm font-semibold text-foreground">{formatMoney(data.total_price, data.currency)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Ödenen</div>
                      <div className="text-sm font-semibold text-foreground">{formatMoney(data.paid_amount, data.currency)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Kalan</div>
                      <div className="text-sm font-semibold text-foreground">{formatMoney(data.due_amount, data.currency)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Kanal</div>
                      <div className="text-sm font-semibold text-foreground">{data.channel}</div>
                    </div>
                  </div>
                </div>
              </div>



            <PaymentForm reservationId={reservationId} currency={data.currency} onSaved={load} />

            <div className="rounded-2xl border bg-card p-4">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold text-foreground">Tahsilatlar</div>
                <span className="rounded-full border bg-accent px-2 py-1 text-xs font-medium text-foreground/80">
                  {(data.payments || []).length}
                </span>
              </div>
              <div className="mt-2 text-sm text-muted-foreground">
                {(data.payments || []).length === 0 ? "Kayıt yok." : null}
              </div>
              <div className="mt-2 space-y-2">
                {(data.payments || []).map((p) => (
                  <div key={p.id} className="flex items-center justify-between rounded-xl border bg-accent/40 px-3 py-2">
                    <div className="text-sm text-foreground/80">
                      {p.method} — {p.reference || "-"}
                      <div className="text-xs text-muted-foreground">{p.created_at}</div>
                    </div>
                    <div className="text-sm font-semibold text-foreground">
                      {formatMoney(p.amount, p.currency)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            </div>
          ) : null}
        </div>

        <SheetFooter className="gap-2 border-t px-5 py-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="res-detail-close">
            Kapat
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

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
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Rezervasyonlar</h2>
          <p className="text-sm text-muted-foreground">Durum akışı + voucher + tahsilat.</p>
        </div>
        <Button onClick={() => setOpenForm(true)} className="gap-2" data-testid="res-new">
          <Plus className="h-4 w-4" />
          Yeni Rezervasyon
        </Button>
      </div>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Ticket className="h-4 w-4 text-muted-foreground" />
            Liste
          </CardTitle>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="relative md:col-span-2">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Ara (PNR)"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="pl-9"
                data-testid="res-search"
              />
            </div>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger data-testid="res-filter-status">
                <SelectValue placeholder="Tüm durumlar" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tümü</SelectItem>
                <SelectItem value="pending">Beklemede</SelectItem>
                <SelectItem value="confirmed">Onaylı</SelectItem>
                <SelectItem value="paid">Ödendi</SelectItem>
                <SelectItem value="cancelled">İptal</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={load} data-testid="res-filter-apply">
              Filtrele
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="res-list-error">
              {error}
            </div>
          ) : null}

          <div className="overflow-x-auto">
            <Table data-testid="res-table">
              <TableHeader>
                <TableRow>
                  <TableHead>PNR</TableHead>
                  <TableHead>Durum</TableHead>
                  <TableHead>Toplam</TableHead>
                  <TableHead>Ödenen</TableHead>
                  <TableHead>Kanal</TableHead>
                  <TableHead className="text-right">İşlem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-6 text-muted-foreground">Yükleniyor...</TableCell>
                  </TableRow>
                ) : rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-6">
                      <EmptyState
                        title="Henüz rezervasyon yok"
                        description="İlk manuel rezervasyonu oluşturarak satış akışını uçtan uca test edebilirsiniz."
                        action={
                          <Button onClick={() => setOpenForm(true)} size="sm">
                            İlk rezervasyonu oluştur
                          </Button>
                        }
                      />
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((r) => {
                    const b = statusBadge(r.status);
                    return (
                      <TableRow key={r.id}>
                        <TableCell className="font-medium text-foreground">{r.pnr}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="rounded-full border bg-accent px-2 py-1 text-xs font-medium text-foreground/80">
                              {b.label}
                            </span>
                            {r.has_open_case ? (
                              <button
                                type="button"
                                className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-800"
                                onClick={() => {
                                  window.location.href = `/ops/cases?booking_id=${r.id}&status=open,waiting,in_progress`;
                                }}
                                data-testid={`badge-open-case-${r.id}`}
                              >
                                OPEN CASE
                              </button>
                            ) : null}
                          </div>
                        </TableCell>
                        <TableCell className="text-foreground/80">{formatMoney(r.total_price, r.currency)}</TableCell>
                        <TableCell className="text-foreground/80">{formatMoney(r.paid_amount, r.currency)}</TableCell>
                        <TableCell className="text-muted-foreground">{r.channel}</TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setDetailId(r.id);
                              setOpenDetail(true);
                            }}
                            data-testid={`res-open-${r.id}`}
                          >
                            Aç
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>

          <div className="mt-3 text-xs text-muted-foreground space-y-1">
            <div className="font-medium text-[11px] text-foreground/80">Durum sayaçları</div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(badges).length === 0 ? (
                <span className="text-muted-foreground">Henüz rezervasyon yok.</span>
              ) : (
                Object.entries(badges).map(([k, v]) => (
                  <span
                    key={k}
                    className="inline-flex items-center gap-1 rounded-full border bg-accent px-2 py-0.5 text-[11px] font-medium text-foreground/80"
                  >
                    <span>
                      {k === "pending"
                        ? "Beklemede"
                        : k === "confirmed"
                        ? "Onaylı"
                        : k === "paid"
                        ? "Ödendi"
                        : k === "cancelled"
                        ? "İptal"
                        : k}
                    </span>
                    <span className="text-foreground">{v}</span>
                  </span>
                ))
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <ReservationForm open={openForm} onOpenChange={setOpenForm} onSaved={load} />
      <ReservationDetails open={openDetail} onOpenChange={setOpenDetail} reservationId={detailId} />
    </div>
  );
}
