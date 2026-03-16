import React, { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import {
  Wallet, CreditCard, Receipt, ArrowUpRight, ArrowDownLeft,
  Search, Plus, Trash2, FileText, Building2, Users, CalendarCheck,
  DoorOpen, Hash, ChevronRight, X, Banknote, CircleDollarSign
} from "lucide-react";

const CHARGE_TYPES = {
  room: "Oda Ucreti",
  extra_bed: "Ekstra Yatak",
  food: "Yiyecek/Icecek",
  minibar: "Minibar",
  laundry: "Camasir",
  transfer: "Transfer",
  tour: "Tur",
  tax: "Vergi",
  other: "Diger",
};

const PAYMENT_METHODS = {
  cash: "Nakit",
  credit_card: "Kredi Karti",
  bank_transfer: "Banka Havale",
  online: "Online",
  other: "Diger",
};

function SummaryCards({ summary }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card className="border-0 shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Toplam Tahsilat</p>
              <p className="text-2xl font-bold mt-1 text-green-600">{summary.total_charges?.toLocaleString("tr-TR")} TRY</p>
            </div>
            <div className="p-2.5 rounded-lg bg-green-50"><ArrowUpRight className="h-5 w-5 text-green-600" /></div>
          </div>
        </CardContent>
      </Card>
      <Card className="border-0 shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Toplam Odeme</p>
              <p className="text-2xl font-bold mt-1 text-blue-600">{summary.total_payments?.toLocaleString("tr-TR")} TRY</p>
            </div>
            <div className="p-2.5 rounded-lg bg-blue-50"><ArrowDownLeft className="h-5 w-5 text-blue-600" /></div>
          </div>
        </CardContent>
      </Card>
      <Card className="border-0 shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Bakiye</p>
              <p className={`text-2xl font-bold mt-1 ${summary.balance > 0 ? "text-amber-600" : "text-green-600"}`}>
                {summary.balance?.toLocaleString("tr-TR")} TRY
              </p>
            </div>
            <div className="p-2.5 rounded-lg bg-amber-50"><Wallet className="h-5 w-5 text-amber-600" /></div>
          </div>
        </CardContent>
      </Card>
      <Card className="border-0 shadow-sm">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Faturalar</p>
              <p className="text-2xl font-bold mt-1 text-primary">{summary.invoice_stats?.total || 0}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {summary.invoice_stats?.draft || 0} taslak, {summary.invoice_stats?.issued || 0} kesilmis
              </p>
            </div>
            <div className="p-2.5 rounded-lg bg-muted/50"><Receipt className="h-5 w-5 text-muted-foreground" /></div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ChargeDialog({ reservationId, onSave, onClose }) {
  const [form, setForm] = useState({ amount: "", description: "", charge_type: "room", notes: "" });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.amount || parseFloat(form.amount) <= 0) { toast.error("Gecerli bir tutar girin"); return; }
    if (!form.description.trim()) { toast.error("Aciklama girin"); return; }
    setSaving(true);
    try {
      await api.post(`/agency/pms/accounting/folios/${reservationId}/charge`, {
        amount: parseFloat(form.amount),
        description: form.description,
        charge_type: form.charge_type,
        notes: form.notes || null,
      });
      toast.success("Tahsilat eklendi");
      onSave();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Islem basarisiz");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="charge-dialog">
        <div className="p-5 border-b flex items-center justify-between">
          <h2 className="text-lg font-bold">Tahsilat Ekle</h2>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Tahsilat Tipi</label>
            <Select value={form.charge_type} onValueChange={(v) => setForm({...form, charge_type: v})}>
              <SelectTrigger data-testid="charge-type-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(CHARGE_TYPES).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Tutar (TRY)</label>
            <Input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({...form, amount: e.target.value})} placeholder="0.00" data-testid="charge-amount-input" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Aciklama</label>
            <Input value={form.description} onChange={(e) => setForm({...form, description: e.target.value})} placeholder="Oda ucreti, minibar vb." data-testid="charge-description-input" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Not</label>
            <Input value={form.notes} onChange={(e) => setForm({...form, notes: e.target.value})} placeholder="Opsiyonel" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>Vazgec</Button>
            <Button type="submit" disabled={saving} data-testid="save-charge-btn">{saving ? "Kaydediliyor..." : "Tahsilat Ekle"}</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function PaymentDialog({ reservationId, onSave, onClose }) {
  const [form, setForm] = useState({ amount: "", description: "Odeme", payment_method: "cash", reference: "", notes: "" });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.amount || parseFloat(form.amount) <= 0) { toast.error("Gecerli bir tutar girin"); return; }
    setSaving(true);
    try {
      await api.post(`/agency/pms/accounting/folios/${reservationId}/payment`, {
        amount: parseFloat(form.amount),
        description: form.description,
        payment_method: form.payment_method,
        reference: form.reference || null,
        notes: form.notes || null,
      });
      toast.success("Odeme kaydedildi");
      onSave();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Islem basarisiz");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-md m-4" onClick={(e) => e.stopPropagation()} data-testid="payment-dialog">
        <div className="p-5 border-b flex items-center justify-between">
          <h2 className="text-lg font-bold">Odeme Kaydet</h2>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Odeme Yontemi</label>
            <Select value={form.payment_method} onValueChange={(v) => setForm({...form, payment_method: v})}>
              <SelectTrigger data-testid="payment-method-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(PAYMENT_METHODS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Tutar (TRY)</label>
            <Input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({...form, amount: e.target.value})} placeholder="0.00" data-testid="payment-amount-input" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Aciklama</label>
            <Input value={form.description} onChange={(e) => setForm({...form, description: e.target.value})} placeholder="Odeme" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Referans No</label>
            <Input value={form.reference} onChange={(e) => setForm({...form, reference: e.target.value})} placeholder="Opsiyonel" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>Vazgec</Button>
            <Button type="submit" disabled={saving} data-testid="save-payment-btn">{saving ? "Kaydediliyor..." : "Odeme Kaydet"}</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function InvoiceDialog({ reservationId, guestName, onSave, onClose }) {
  const [form, setForm] = useState({ invoice_to: guestName || "", tax_id: "", tax_office: "", address: "", notes: "" });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post("/agency/pms/accounting/invoices", {
        reservation_id: reservationId,
        invoice_to: form.invoice_to,
        tax_id: form.tax_id,
        tax_office: form.tax_office,
        address: form.address,
        notes: form.notes,
      });
      toast.success("Fatura olusturuldu");
      onSave();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fatura olusturulamadi");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-lg m-4" onClick={(e) => e.stopPropagation()} data-testid="invoice-dialog">
        <div className="p-5 border-b flex items-center justify-between">
          <h2 className="text-lg font-bold">Fatura Olustur</h2>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Fatura Kesen</label>
            <Input value={form.invoice_to} onChange={(e) => setForm({...form, invoice_to: e.target.value})} placeholder="Ad Soyad / Firma" data-testid="invoice-to-input" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Vergi No</label>
              <Input value={form.tax_id} onChange={(e) => setForm({...form, tax_id: e.target.value})} placeholder="VKN / TCKN" data-testid="invoice-tax-id" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Vergi Dairesi</label>
              <Input value={form.tax_office} onChange={(e) => setForm({...form, tax_office: e.target.value})} placeholder="Vergi dairesi" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Adres</label>
            <Input value={form.address} onChange={(e) => setForm({...form, address: e.target.value})} placeholder="Fatura adresi" />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Not</label>
            <Input value={form.notes} onChange={(e) => setForm({...form, notes: e.target.value})} placeholder="Opsiyonel" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>Vazgec</Button>
            <Button type="submit" disabled={saving} data-testid="create-invoice-btn">{saving ? "Olusturuluyor..." : "Fatura Olustur"}</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function FolioDetailPanel({ reservationId, onClose }) {
  const queryClient = useQueryClient();
  const [showCharge, setShowCharge] = useState(false);
  const [showPayment, setShowPayment] = useState(false);
  const [showInvoice, setShowInvoice] = useState(false);

  const { data: folio, isLoading: loading, refetch: loadFolio } = useQuery({
    queryKey: ["pms", "folio", reservationId],
    queryFn: async () => {
      const res = await api.get(`/agency/pms/accounting/folios/${reservationId}`);
      return res.data;
    },
    staleTime: 15_000,
    onError: () => toast.error("Folio yuklenemedi"),
  });

  const deleteTxMutation = useMutation({
    mutationFn: (txId) => api.delete(`/agency/pms/accounting/transactions/${txId}`),
    onSuccess: () => {
      toast.success("Islem silindi");
      loadFolio();
    },
    onError: () => toast.error("Silme basarisiz"),
  });

  const handleDeleteTx = (txId) => {
    if (!window.confirm("Bu islem silinsin mi?")) return;
    deleteTxMutation.mutate(txId);
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!folio) return null;
  const r = folio.reservation;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto m-4" onClick={(e) => e.stopPropagation()} data-testid="folio-detail-panel">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b sticky top-0 bg-background z-10">
          <div>
            <h2 className="text-lg font-bold">{r.guest_name} - Cari Hesap</h2>
            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
              <span>{r.check_in} - {r.check_out}</span>
              {r.room_number && <span>Oda {r.room_number}</span>}
              {r.pnr && <span>PNR: {r.pnr}</span>}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setShowCharge(true)} data-testid="add-charge-btn">
              <ArrowUpRight className="h-3.5 w-3.5 mr-1" /> Tahsilat
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowPayment(true)} data-testid="add-payment-btn">
              <ArrowDownLeft className="h-3.5 w-3.5 mr-1" /> Odeme
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
          </div>
        </div>

        {/* Balance Summary */}
        <div className="grid grid-cols-3 gap-4 p-5 border-b">
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Tahsilat</p>
            <p className="text-xl font-bold text-green-600">{folio.total_charges?.toLocaleString("tr-TR")} TRY</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Odeme</p>
            <p className="text-xl font-bold text-blue-600">{folio.total_payments?.toLocaleString("tr-TR")} TRY</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Bakiye</p>
            <p className={`text-xl font-bold ${folio.balance > 0 ? "text-amber-600" : "text-green-600"}`}>
              {folio.balance?.toLocaleString("tr-TR")} TRY
            </p>
          </div>
        </div>

        {/* Transactions */}
        <div className="p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">Islemler</h3>
            {folio.total_charges > 0 && (
              <Button size="sm" variant="outline" onClick={() => setShowInvoice(true)} data-testid="create-invoice-from-folio-btn">
                <FileText className="h-3.5 w-3.5 mr-1" /> Fatura Kes
              </Button>
            )}
          </div>

          {folio.transactions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Wallet className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">Henuz islem yok</p>
              <p className="text-xs mt-1">Tahsilat veya odeme ekleyerek baslayabilirsiniz</p>
            </div>
          ) : (
            <div className="space-y-1">
              {folio.transactions.map((tx) => (
                <div key={tx.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/30 transition-colors group" data-testid={`transaction-row-${tx.id}`}>
                  <div className={`p-1.5 rounded-full ${tx.type === "charge" ? "bg-green-100" : "bg-blue-100"}`}>
                    {tx.type === "charge" ? <ArrowUpRight className="h-3.5 w-3.5 text-green-600" /> : <ArrowDownLeft className="h-3.5 w-3.5 text-blue-600" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{tx.description}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{tx.type === "charge" ? CHARGE_TYPES[tx.charge_type] || tx.charge_type : PAYMENT_METHODS[tx.payment_method] || tx.payment_method}</span>
                      {tx.reference && <span>Ref: {tx.reference}</span>}
                      <span>{new Date(tx.created_at).toLocaleString("tr-TR")}</span>
                    </div>
                  </div>
                  <p className={`text-sm font-bold ${tx.type === "charge" ? "text-green-600" : "text-blue-600"}`}>
                    {tx.type === "charge" ? "+" : "-"}{tx.amount?.toLocaleString("tr-TR")} TRY
                  </p>
                  <Button size="sm" variant="ghost" className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 text-destructive" onClick={() => handleDeleteTx(tx.id)} data-testid={`delete-tx-${tx.id}`}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Invoices */}
        {folio.invoices.length > 0 && (
          <div className="p-5 border-t">
            <h3 className="text-sm font-semibold mb-3">Faturalar</h3>
            {folio.invoices.map((inv) => (
              <div key={inv.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/30">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1">
                  <p className="text-sm font-medium">{inv.invoice_no}</p>
                  <p className="text-xs text-muted-foreground">{inv.invoice_to}</p>
                </div>
                <Badge variant="outline" className={`text-xs ${
                  inv.status === "paid" ? "bg-green-100 text-green-700" :
                  inv.status === "issued" ? "bg-blue-100 text-blue-700" :
                  inv.status === "cancelled" ? "bg-red-100 text-red-600" :
                  "bg-slate-100 text-slate-700"
                }`}>{inv.status === "draft" ? "Taslak" : inv.status === "issued" ? "Kesildi" : inv.status === "paid" ? "Odendi" : "Iptal"}</Badge>
                <p className="text-sm font-bold">{inv.total?.toLocaleString("tr-TR")} TRY</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {showCharge && <ChargeDialog reservationId={reservationId} onSave={() => { setShowCharge(false); loadFolio(); }} onClose={() => setShowCharge(false)} />}
      {showPayment && <PaymentDialog reservationId={reservationId} onSave={() => { setShowPayment(false); loadFolio(); }} onClose={() => setShowPayment(false)} />}
      {showInvoice && <InvoiceDialog reservationId={reservationId} guestName={r.guest_name} onSave={() => { setShowInvoice(false); loadFolio(); }} onClose={() => setShowInvoice(false)} />}
    </div>
  );
}

export default function PMSAccountingPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedFolio, setSelectedFolio] = useState(null);

  const { data: accountingData, isLoading: loading, refetch } = useQuery({
    queryKey: ["pms", "accounting", searchQuery, statusFilter],
    queryFn: async () => {
      const params = [];
      if (searchQuery) params.push(`search=${encodeURIComponent(searchQuery)}`);
      if (statusFilter !== "all") params.push(`status=${statusFilter}`);
      const qs = params.length ? `?${params.join("&")}` : "";
      const [summaryRes, foliosRes] = await Promise.all([
        api.get("/agency/pms/accounting/summary"),
        api.get(`/agency/pms/accounting/folios${qs}`),
      ]);
      return { summary: summaryRes.data, folios: foliosRes.data.items || [] };
    },
    staleTime: 30_000,
    onError: () => toast.error("Muhasebe verisi yuklenemedi"),
  });
  const summary = accountingData?.summary || {};
  const folios = accountingData?.folios || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="pms-accounting-page">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Muhasebe</h1>
          <p className="text-sm text-muted-foreground mt-1">Cari hesaplar, odemeler ve faturalama</p>
        </div>
      </div>

      <SummaryCards summary={summary} />

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="Misafir adi veya PNR ile ara..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} data-testid="accounting-search" />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]" data-testid="accounting-status-filter">
            <SelectValue placeholder="Durum" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tum Hesaplar</SelectItem>
            <SelectItem value="has_balance">Bakiyesi Var</SelectItem>
            <SelectItem value="settled">Kapanmis</SelectItem>
            <SelectItem value="no_transactions">Islem Yok</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Folio List */}
      <Card className="border-0 shadow-sm">
        <CardContent className="p-0">
          {folios.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <Wallet className="h-10 w-10 mb-3 opacity-40" />
              <p className="text-sm font-medium">Cari hesap bulunamadi</p>
              <p className="text-xs mt-1">Rezervasyon verisi mevcut oldugunda burada gorunecek</p>
            </div>
          ) : (
            folios.map((folio) => (
              <div
                key={folio.reservation_id}
                className="flex items-center gap-4 p-4 border-b last:border-b-0 hover:bg-muted/30 transition-colors cursor-pointer"
                onClick={() => setSelectedFolio(folio.reservation_id)}
                data-testid={`folio-row-${folio.reservation_id}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-sm">{folio.guest_name || "Misafir"}</p>
                    {folio.balance > 0 && <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700" variant="outline">Bakiye Var</Badge>}
                    {folio.balance <= 0 && folio.transaction_count > 0 && <Badge className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700" variant="outline">Kapali</Badge>}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><CalendarCheck className="h-3 w-3" />{folio.check_in} - {folio.check_out}</span>
                    {folio.room_number && <span className="flex items-center gap-1"><DoorOpen className="h-3 w-3" />Oda {folio.room_number}</span>}
                    {folio.hotel_name && <span className="flex items-center gap-1"><Building2 className="h-3 w-3" />{folio.hotel_name}</span>}
                    {folio.pnr && <span className="flex items-center gap-1"><Hash className="h-3 w-3" />{folio.pnr}</span>}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="flex items-center gap-4 text-sm">
                    <div>
                      <p className="text-xs text-muted-foreground">Tahsilat</p>
                      <p className="font-medium text-green-600">{folio.total_charges?.toLocaleString("tr-TR")}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Odeme</p>
                      <p className="font-medium text-blue-600">{folio.total_payments?.toLocaleString("tr-TR")}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Bakiye</p>
                      <p className={`font-bold ${folio.balance > 0 ? "text-amber-600" : "text-green-600"}`}>{folio.balance?.toLocaleString("tr-TR")}</p>
                    </div>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Folio Detail Panel */}
      {selectedFolio && (
        <FolioDetailPanel
          reservationId={selectedFolio}
          onClose={() => { setSelectedFolio(null); refetch(); }}
        />
      )}
    </div>
  );
}
