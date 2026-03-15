import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  FileText, Send, Plus, X, Eye, RefreshCw, AlertTriangle,
  CheckCircle, Clock, Ban, ArrowRight, Building2, User,
  Receipt, TrendingUp, ChevronDown, ChevronUp
} from "lucide-react";
import { cn } from "../lib/utils";
import { toast } from "sonner";

const STATUS_MAP = {
  draft: { label: "Taslak", icon: Clock, color: "bg-slate-100 text-slate-700 border-slate-200" },
  ready_for_issue: { label: "Kesilmeye Hazir", icon: ArrowRight, color: "bg-amber-50 text-amber-700 border-amber-200" },
  issuing: { label: "Kesiliyor", icon: RefreshCw, color: "bg-blue-50 text-blue-700 border-blue-200" },
  issued: { label: "Kesildi", icon: CheckCircle, color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  failed: { label: "Basarisiz", icon: AlertTriangle, color: "bg-red-50 text-red-700 border-red-200" },
  cancelled: { label: "Iptal", icon: Ban, color: "bg-gray-100 text-gray-500 border-gray-200" },
  refunded: { label: "Iade", icon: ArrowRight, color: "bg-orange-50 text-orange-700 border-orange-200" },
  sync_pending: { label: "Sync Bekliyor", icon: Clock, color: "bg-indigo-50 text-indigo-700 border-indigo-200" },
  synced: { label: "Senkronize", icon: CheckCircle, color: "bg-teal-50 text-teal-700 border-teal-200" },
  sync_failed: { label: "Sync Hatali", icon: AlertTriangle, color: "bg-rose-50 text-rose-700 border-rose-200" },
};

const TYPE_MAP = {
  e_fatura: { label: "e-Fatura", color: "text-blue-700 bg-blue-50" },
  e_arsiv: { label: "e-Arsiv", color: "text-purple-700 bg-purple-50" },
  draft_only: { label: "Taslak", color: "text-gray-600 bg-gray-50" },
  accounting_only: { label: "Muhasebe", color: "text-teal-700 bg-teal-50" },
};

function StatusBadge({ status }) {
  const s = STATUS_MAP[status] || { label: status, icon: Clock, color: "" };
  const Icon = s.icon;
  return (
    <Badge variant="outline" className={cn("gap-1 font-medium", s.color)} data-testid={`status-badge-${status}`}>
      <Icon className="h-3 w-3" /> {s.label}
    </Badge>
  );
}

function StatCard({ label, value, icon: Icon, color, sub }) {
  return (
    <div className={cn("rounded-xl border p-4 flex items-start gap-3", color)} data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="rounded-lg bg-background/80 p-2.5 shadow-sm">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <div className="text-xs font-medium text-muted-foreground">{label}</div>
        <div className="text-2xl font-bold tracking-tight">{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

function CreateInvoiceWizard({ onCreated, onClose }) {
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState("manual");
  const [creating, setCreating] = useState(false);
  const [customer, setCustomer] = useState({
    name: "", tax_id: "", tax_office: "", id_number: "",
    customer_type: "b2c", address: "", city: "", country: "TR", email: "", phone: "",
  });
  const [lines, setLines] = useState([{ description: "", quantity: 1, unit_price: 0, tax_rate: 20 }]);
  const [currency, setCurrency] = useState("TRY");
  const [bookingId, setBookingId] = useState("");

  const addLine = () => setLines(l => [...l, { description: "", quantity: 1, unit_price: 0, tax_rate: 20 }]);
  const removeLine = (i) => setLines(l => l.filter((_, idx) => idx !== i));
  const updateLine = (i, field, val) => {
    setLines(l => l.map((ln, idx) => idx === i ? { ...ln, [field]: val } : ln));
  };

  const subtotal = lines.reduce((s, ln) => s + ln.quantity * ln.unit_price, 0);
  const taxTotal = lines.reduce((s, ln) => s + (ln.quantity * ln.unit_price * ln.tax_rate / 100), 0);

  const handleSubmit = async () => {
    setCreating(true);
    try {
      if (mode === "booking") {
        if (!bookingId.trim()) { toast.error("Booking ID gerekli"); return; }
        const res = await api.post("/invoices/create-from-booking", {
          booking_id: bookingId,
          customer: customer.name ? customer : undefined,
        });
        toast.success(`Fatura olusturuldu: ${res.data.invoice_id}`);
        onCreated?.();
      } else {
        if (lines.length === 0 || !lines[0].description) { toast.error("En az bir kalem gerekli"); return; }
        const res = await api.post("/invoices/create-manual", {
          lines, customer: customer.name ? customer : undefined, currency,
        });
        toast.success(`Fatura olusturuldu: ${res.data.invoice_id}`);
        onCreated?.();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="rounded-xl border bg-card shadow-sm p-5 mb-6" data-testid="invoice-wizard">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold flex items-center gap-2"><Receipt className="h-4 w-4" /> Yeni Fatura Olustur</h3>
        <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
      </div>

      {/* Step indicator */}
      <div className="flex gap-2 mb-5">
        {[1, 2, 3].map(s => (
          <div key={s} className={cn("h-1.5 flex-1 rounded-full transition-colors", step >= s ? "bg-primary" : "bg-muted")} />
        ))}
      </div>

      {step === 1 && (
        <div data-testid="wizard-step-1">
          <p className="text-sm text-muted-foreground mb-3">Fatura tipini secin</p>
          <div className="grid grid-cols-2 gap-3">
            <button onClick={() => { setMode("booking"); setStep(2); }}
              className={cn("rounded-lg border-2 p-4 text-left transition-all hover:border-primary", mode === "booking" ? "border-primary bg-primary/5" : "")}
              data-testid="mode-booking">
              <Building2 className="h-5 w-5 mb-2 text-primary" />
              <div className="font-medium text-sm">Rezervasyondan Fatura</div>
              <div className="text-xs text-muted-foreground mt-1">Mevcut rezervasyondan otomatik fatura olustur</div>
            </button>
            <button onClick={() => { setMode("manual"); setStep(2); }}
              className={cn("rounded-lg border-2 p-4 text-left transition-all hover:border-primary", mode === "manual" ? "border-primary bg-primary/5" : "")}
              data-testid="mode-manual">
              <FileText className="h-5 w-5 mb-2 text-primary" />
              <div className="font-medium text-sm">Manuel Fatura</div>
              <div className="text-xs text-muted-foreground mt-1">Serbest kalem girisi ile fatura olustur</div>
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div data-testid="wizard-step-2">
          <p className="text-sm text-muted-foreground mb-3">Musteri bilgileri</p>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs font-medium block mb-1">Musteri Tipi</label>
              <select value={customer.customer_type} onChange={e => setCustomer(c => ({ ...c, customer_type: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm bg-background" data-testid="customer-type-select">
                <option value="b2c">Bireysel (B2C)</option>
                <option value="b2b">Kurumsal (B2B)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Ad / Unvan</label>
              <input value={customer.name} onChange={e => setCustomer(c => ({ ...c, name: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm bg-background" placeholder="Musteri adi veya firma unvani"
                data-testid="customer-name-input" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            {customer.customer_type === "b2b" ? (
              <>
                <div>
                  <label className="text-xs font-medium block mb-1">VKN (Vergi Kimlik No)</label>
                  <input value={customer.tax_id} onChange={e => setCustomer(c => ({ ...c, tax_id: e.target.value }))}
                    className="w-full rounded-lg border px-3 py-2 text-sm bg-background" placeholder="10 haneli" data-testid="vkn-input" />
                </div>
                <div>
                  <label className="text-xs font-medium block mb-1">Vergi Dairesi</label>
                  <input value={customer.tax_office} onChange={e => setCustomer(c => ({ ...c, tax_office: e.target.value }))}
                    className="w-full rounded-lg border px-3 py-2 text-sm bg-background" placeholder="Ornek: Kadikoy" />
                </div>
              </>
            ) : (
              <div>
                <label className="text-xs font-medium block mb-1">TC Kimlik No</label>
                <input value={customer.id_number} onChange={e => setCustomer(c => ({ ...c, id_number: e.target.value }))}
                  className="w-full rounded-lg border px-3 py-2 text-sm bg-background" placeholder="11 haneli" data-testid="tckn-input" />
              </div>
            )}
          </div>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div>
              <label className="text-xs font-medium block mb-1">Sehir</label>
              <input value={customer.city} onChange={e => setCustomer(c => ({ ...c, city: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm bg-background" />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">E-posta</label>
              <input value={customer.email} onChange={e => setCustomer(c => ({ ...c, email: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm bg-background" />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Telefon</label>
              <input value={customer.phone} onChange={e => setCustomer(c => ({ ...c, phone: e.target.value }))}
                className="w-full rounded-lg border px-3 py-2 text-sm bg-background" />
            </div>
          </div>
          <div className="flex justify-between mt-4">
            <Button variant="outline" size="sm" onClick={() => setStep(1)}>Geri</Button>
            <Button size="sm" onClick={() => setStep(3)} data-testid="wizard-next-btn">Devam</Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div data-testid="wizard-step-3">
          {mode === "booking" ? (
            <div>
              <p className="text-sm text-muted-foreground mb-3">Rezervasyon ID girin</p>
              <input value={bookingId} onChange={e => setBookingId(e.target.value)}
                className="w-full rounded-lg border px-3 py-2 text-sm bg-background mb-3" placeholder="Booking ID"
                data-testid="booking-id-input" />
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm text-muted-foreground">Fatura kalemleri</p>
                <div className="flex gap-2 items-center">
                  <label className="text-xs font-medium">Para Birimi:</label>
                  <select value={currency} onChange={e => setCurrency(e.target.value)}
                    className="rounded-lg border px-2 py-1 text-xs bg-background" data-testid="currency-select">
                    <option value="TRY">TRY</option><option value="EUR">EUR</option><option value="USD">USD</option><option value="GBP">GBP</option>
                  </select>
                </div>
              </div>
              <div className="space-y-2 mb-3">
                {lines.map((ln, i) => (
                  <div key={i} className="grid grid-cols-[1fr_80px_100px_80px_32px] gap-2 items-center" data-testid={`invoice-line-${i}`}>
                    <input placeholder="Aciklama" value={ln.description} onChange={e => updateLine(i, "description", e.target.value)}
                      className="rounded-lg border px-2 py-1.5 text-xs bg-background" />
                    <input type="number" placeholder="Adet" value={ln.quantity} onChange={e => updateLine(i, "quantity", +e.target.value)}
                      className="rounded-lg border px-2 py-1.5 text-xs bg-background text-center" />
                    <input type="number" placeholder="Birim Fiyat" value={ln.unit_price} onChange={e => updateLine(i, "unit_price", +e.target.value)}
                      className="rounded-lg border px-2 py-1.5 text-xs bg-background text-right" />
                    <input type="number" placeholder="KDV%" value={ln.tax_rate} onChange={e => updateLine(i, "tax_rate", +e.target.value)}
                      className="rounded-lg border px-2 py-1.5 text-xs bg-background text-center" />
                    {lines.length > 1 && (
                      <button onClick={() => removeLine(i)} className="text-destructive hover:bg-destructive/10 rounded p-1">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <Button variant="ghost" size="sm" onClick={addLine} className="text-xs gap-1 mb-3"><Plus className="h-3 w-3" /> Kalem Ekle</Button>
              <div className="rounded-lg bg-muted/50 p-3 text-sm space-y-1">
                <div className="flex justify-between"><span className="text-muted-foreground">Ara Toplam:</span><span className="font-mono">{subtotal.toFixed(2)} {currency}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">KDV:</span><span className="font-mono">{taxTotal.toFixed(2)} {currency}</span></div>
                <div className="flex justify-between font-semibold border-t pt-1"><span>Genel Toplam:</span><span className="font-mono">{(subtotal + taxTotal).toFixed(2)} {currency}</span></div>
              </div>
            </div>
          )}
          <div className="flex justify-between mt-4">
            <Button variant="outline" size="sm" onClick={() => setStep(2)}>Geri</Button>
            <Button size="sm" onClick={handleSubmit} disabled={creating} data-testid="submit-invoice-btn">
              {creating ? "Olusturuluyor..." : "Faturayi Olustur"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function InvoiceDetail({ invoice, onClose, onRefresh }) {
  const [events, setEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [issuing, setIssuing] = useState(false);

  useEffect(() => {
    if (!invoice?.invoice_id) return;
    setLoadingEvents(true);
    api.get(`/invoices/${invoice.invoice_id}/events`).then(r => setEvents(r.data?.events || [])).catch(() => {}).finally(() => setLoadingEvents(false));
  }, [invoice?.invoice_id]);

  const handleIssue = async () => {
    setIssuing(true);
    try {
      await api.post(`/invoices/${invoice.invoice_id}/issue`);
      toast.success("Fatura kesildi");
      onRefresh?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setIssuing(false); }
  };

  const handleCancel = async () => {
    if (!window.confirm("Faturayi iptal etmek istediginize emin misiniz?")) return;
    try {
      await api.post(`/invoices/${invoice.invoice_id}/cancel`);
      toast.success("Fatura iptal edildi");
      onRefresh?.();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  if (!invoice) return null;
  const typeInfo = TYPE_MAP[invoice.invoice_type] || { label: invoice.invoice_type, color: "" };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center pt-[10vh] p-4" onClick={onClose} data-testid="invoice-detail-modal">
      <div className="bg-card rounded-xl shadow-xl border w-full max-w-2xl max-h-[75vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="sticky top-0 bg-card border-b px-5 py-4 flex items-center justify-between z-10">
          <div>
            <div className="font-semibold text-lg">{invoice.invoice_id}</div>
            <div className="flex gap-2 mt-1">
              <StatusBadge status={invoice.status} />
              <Badge variant="outline" className={cn("text-xs", typeInfo.color)}>{typeInfo.label}</Badge>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
        </div>

        <div className="p-5 space-y-5">
          {/* Customer */}
          {invoice.customer?.name && (
            <div className="rounded-lg bg-muted/30 p-3">
              <div className="text-xs font-medium text-muted-foreground mb-1">Musteri</div>
              <div className="font-medium">{invoice.customer.name}</div>
              {invoice.customer.tax_id && <div className="text-xs text-muted-foreground">VKN: {invoice.customer.tax_id} {invoice.customer.tax_office && `- ${invoice.customer.tax_office}`}</div>}
              {invoice.customer.id_number && <div className="text-xs text-muted-foreground">TCKN: {invoice.customer.id_number}</div>}
              {invoice.customer.city && <div className="text-xs text-muted-foreground">{invoice.customer.city}, {invoice.customer.country}</div>}
            </div>
          )}

          {/* Booking info */}
          {invoice.booking_id && (
            <div className="rounded-lg bg-muted/30 p-3">
              <div className="text-xs font-medium text-muted-foreground mb-1">Rezervasyon</div>
              <div className="text-sm">
                <span className="font-mono">{invoice.booking_ref || invoice.booking_id}</span>
                {invoice.hotel_name && <span className="ml-2 text-muted-foreground">- {invoice.hotel_name}</span>}
              </div>
              {invoice.stay?.check_in && (
                <div className="text-xs text-muted-foreground mt-1">{invoice.stay.check_in} → {invoice.stay.check_out}</div>
              )}
            </div>
          )}

          {/* Lines */}
          <div>
            <div className="text-xs font-medium text-muted-foreground mb-2">Kalemler</div>
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead><tr className="bg-muted/50">
                  <th className="text-left px-3 py-2">Aciklama</th>
                  <th className="text-center px-3 py-2 w-16">Adet</th>
                  <th className="text-right px-3 py-2 w-24">Birim</th>
                  <th className="text-center px-3 py-2 w-16">KDV%</th>
                  <th className="text-right px-3 py-2 w-24">Toplam</th>
                </tr></thead>
                <tbody>
                  {(invoice.lines || []).map((ln, i) => (
                    <tr key={i} className="border-t">
                      <td className="px-3 py-2">{ln.description}</td>
                      <td className="px-3 py-2 text-center">{ln.quantity}</td>
                      <td className="px-3 py-2 text-right font-mono">{ln.unit_price?.toFixed(2)}</td>
                      <td className="px-3 py-2 text-center">%{ln.tax_rate}</td>
                      <td className="px-3 py-2 text-right font-mono">{ln.gross_total?.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Totals */}
          <div className="rounded-lg bg-muted/30 p-3 text-sm space-y-1">
            <div className="flex justify-between"><span className="text-muted-foreground">Ara Toplam:</span><span className="font-mono">{invoice.totals?.subtotal?.toFixed(2)} {invoice.totals?.currency}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Vergi:</span><span className="font-mono">{invoice.totals?.tax_total?.toFixed(2)} {invoice.totals?.currency}</span></div>
            <div className="flex justify-between font-semibold border-t pt-1 mt-1"><span>Genel Toplam:</span><span className="font-mono">{invoice.totals?.grand_total?.toFixed(2)} {invoice.totals?.currency}</span></div>
          </div>

          {/* Events */}
          {events.length > 0 && (
            <div>
              <div className="text-xs font-medium text-muted-foreground mb-2">Gecmis</div>
              <div className="space-y-1">
                {events.map((ev, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                    <span className="text-muted-foreground">{ev.created_at ? new Date(ev.created_at).toLocaleString("tr-TR") : ""}</span>
                    <span className="font-medium">{ev.type}</span>
                    {ev.actor && <span className="text-muted-foreground">({ev.actor})</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-2 border-t">
            {["draft", "ready_for_issue", "failed"].includes(invoice.status) && (
              <Button size="sm" onClick={handleIssue} disabled={issuing} className="gap-1" data-testid="issue-invoice-btn">
                <Send className="h-3.5 w-3.5" /> {issuing ? "Kesiliyor..." : "Faturayi Kes"}
              </Button>
            )}
            {["draft", "ready_for_issue", "issued"].includes(invoice.status) && (
              <Button size="sm" variant="destructive" onClick={handleCancel} className="gap-1" data-testid="cancel-invoice-btn">
                <Ban className="h-3.5 w-3.5" /> Iptal Et
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminEFaturaPage() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [filter, setFilter] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [invRes, statsRes] = await Promise.all([
        api.get("/invoices", { params: { limit: 100, ...(filter ? { status: filter } : {}) } }),
        api.get("/invoices/dashboard"),
      ]);
      setInvoices(invRes.data?.items || []);
      setStats(statsRes.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const handleIssue = async (invoiceId) => {
    try {
      await api.post(`/invoices/${invoiceId}/issue`);
      toast.success("Fatura kesildi");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  const handleCancel = async (invoiceId) => {
    if (!window.confirm("Faturayi iptal etmek istediginize emin misiniz?")) return;
    try {
      await api.post(`/invoices/${invoiceId}/cancel`);
      toast.success("Fatura iptal edildi");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
  };

  const fmt = (v) => typeof v === "number" ? v.toLocaleString("tr-TR", { minimumFractionDigits: 2 }) : "0";

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="invoice-engine-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2" data-testid="page-title">
            <Receipt className="h-6 w-6 text-primary" /> Fatura Motoru
          </h1>
          <p className="text-sm text-muted-foreground mt-1">Fatura olusturun, kesin, takip edin.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} data-testid="refresh-btn"><RefreshCw className="h-4 w-4 mr-1" /> Yenile</Button>
          <Button size="sm" onClick={() => setShowCreate(!showCreate)} data-testid="new-invoice-btn">
            <Plus className="h-4 w-4 mr-1" /> Yeni Fatura
          </Button>
        </div>
      </div>

      {/* Dashboard Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6" data-testid="invoice-dashboard">
          <StatCard label="Toplam Fatura" value={stats.total} icon={FileText} />
          <StatCard label="Kesildi" value={stats.issued} icon={CheckCircle} color="bg-emerald-50/50" />
          <StatCard label="Basarisiz" value={stats.failed} icon={AlertTriangle} color="bg-red-50/50" />
          <StatCard label="Gelir" value={`${fmt(stats.financials?.total_revenue)} TL`} icon={TrendingUp} sub={`Vergi: ${fmt(stats.financials?.total_tax)} TL`} />
        </div>
      )}

      {/* Create Wizard */}
      {showCreate && (
        <CreateInvoiceWizard
          onCreated={() => { setShowCreate(false); load(); }}
          onClose={() => setShowCreate(false)}
        />
      )}

      {/* Filters */}
      <div className="flex gap-2 mb-4 flex-wrap" data-testid="invoice-filters">
        {[
          { value: "", label: "Tumu" },
          { value: "draft", label: "Taslak" },
          { value: "issued", label: "Kesildi" },
          { value: "failed", label: "Basarisiz" },
          { value: "cancelled", label: "Iptal" },
        ].map(f => (
          <Button key={f.value} variant={filter === f.value ? "default" : "outline"} size="sm"
            onClick={() => setFilter(f.value)} className="text-xs" data-testid={`filter-${f.value || 'all'}`}>
            {f.label}
          </Button>
        ))}
      </div>

      {/* Invoice Table */}
      {loading ? (
        <div className="space-y-3">{[1,2,3].map(i => <div key={i} className="animate-pulse h-14 bg-muted rounded-lg" />)}</div>
      ) : invoices.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground" data-testid="no-invoices">
          <Receipt className="h-16 w-16 mx-auto mb-4 opacity-20" />
          <p className="text-lg font-medium">Henuz fatura yok</p>
          <p className="text-sm mt-1">Yeni fatura olusturmak icin yukardaki butonu kullanin.</p>
        </div>
      ) : (
        <div className="border rounded-xl overflow-hidden shadow-sm" data-testid="invoice-table">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/40 border-b">
                <th className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider">Fatura No</th>
                <th className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider">Tip</th>
                <th className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider">Musteri</th>
                <th className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider">Durum</th>
                <th className="text-right px-4 py-3 font-medium text-xs uppercase tracking-wider">Tutar</th>
                <th className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider">Tarih</th>
                <th className="text-right px-4 py-3 font-medium text-xs uppercase tracking-wider">Aksiyonlar</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map(inv => {
                const typeInfo = TYPE_MAP[inv.invoice_type] || { label: inv.invoice_type || "-", color: "" };
                return (
                  <tr key={inv.invoice_id} className="border-b last:border-0 hover:bg-muted/20 transition-colors cursor-pointer"
                    onClick={() => setSelectedInvoice(inv)} data-testid={`invoice-row-${inv.invoice_id}`}>
                    <td className="px-4 py-3 font-mono text-xs font-medium">{inv.invoice_id}</td>
                    <td className="px-4 py-3">
                      <Badge variant="outline" className={cn("text-xs", typeInfo.color)}>{typeInfo.label}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm">{inv.customer?.name || inv.guest_name || "-"}</div>
                      {inv.hotel_name && <div className="text-xs text-muted-foreground">{inv.hotel_name}</div>}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                    <td className="px-4 py-3 text-right font-mono font-medium">{inv.totals?.grand_total?.toFixed(2)} {inv.totals?.currency}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{inv.created_at ? new Date(inv.created_at).toLocaleDateString("tr-TR") : "-"}</td>
                    <td className="px-4 py-3 text-right" onClick={e => e.stopPropagation()}>
                      <div className="flex justify-end gap-1">
                        {["draft", "ready_for_issue", "failed"].includes(inv.status) && (
                          <Button size="sm" className="h-7 text-xs gap-1" onClick={() => handleIssue(inv.invoice_id)} data-testid={`issue-btn-${inv.invoice_id}`}>
                            <Send className="h-3 w-3" /> Kes
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setSelectedInvoice(inv)} data-testid={`detail-btn-${inv.invoice_id}`}>
                          <Eye className="h-3 w-3" />
                        </Button>
                        {["draft", "ready_for_issue", "issued"].includes(inv.status) && (
                          <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive" onClick={() => handleCancel(inv.invoice_id)}>
                            <X className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Modal */}
      {selectedInvoice && (
        <InvoiceDetail
          invoice={selectedInvoice}
          onClose={() => setSelectedInvoice(null)}
          onRefresh={() => { load(); setSelectedInvoice(null); }}
        />
      )}
    </div>
  );
}
