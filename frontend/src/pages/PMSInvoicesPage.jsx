import React, { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { FileText, Search, X, Building2, CalendarCheck, Printer, CheckCircle, XCircle, Eye } from "lucide-react";

const INVOICE_STATUS_MAP = {
  draft: { label: "Taslak", color: "bg-slate-100 text-slate-700" },
  issued: { label: "Kesildi", color: "bg-blue-100 text-blue-700" },
  paid: { label: "Odendi", color: "bg-green-100 text-green-700" },
  cancelled: { label: "Iptal", color: "bg-red-100 text-red-600" },
};

function InvoiceDetailPanel({ invoiceId, onClose, onUpdate }) {
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get(`/agency/pms/accounting/invoices/${invoiceId}`);
        setInvoice(res.data);
      } catch {
        toast.error("Fatura yuklenemedi");
      } finally { setLoading(false); }
    })();
  }, [invoiceId]);

  const handleStatusChange = async (newStatus) => {
    try {
      await api.put(`/agency/pms/accounting/invoices/${invoiceId}`, { status: newStatus });
      toast.success(`Fatura durumu guncellendi: ${INVOICE_STATUS_MAP[newStatus]?.label}`);
      onUpdate();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Guncelleme basarisiz");
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!invoice) return null;
  const statusInfo = INVOICE_STATUS_MAP[invoice.status] || INVOICE_STATUS_MAP.draft;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4" onClick={(e) => e.stopPropagation()} data-testid="invoice-detail-panel">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b">
          <div>
            <h2 className="text-lg font-bold">{invoice.invoice_no}</h2>
            <Badge className={`text-xs mt-1 ${statusInfo.color}`} variant="outline">{statusInfo.label}</Badge>
          </div>
          <div className="flex items-center gap-2">
            {invoice.status === "draft" && (
              <Button size="sm" onClick={() => handleStatusChange("issued")} data-testid="issue-invoice-btn">
                <Printer className="h-3.5 w-3.5 mr-1" /> Fatura Kes
              </Button>
            )}
            {invoice.status === "issued" && (
              <Button size="sm" variant="default" onClick={() => handleStatusChange("paid")} data-testid="mark-paid-btn">
                <CheckCircle className="h-3.5 w-3.5 mr-1" /> Odendi Isaretle
              </Button>
            )}
            {(invoice.status === "draft" || invoice.status === "issued") && (
              <Button size="sm" variant="destructive" onClick={() => handleStatusChange("cancelled")} data-testid="cancel-invoice-btn">
                <XCircle className="h-3.5 w-3.5 mr-1" /> Iptal
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={onClose}><X className="h-4 w-4" /></Button>
          </div>
        </div>

        {/* Invoice Info */}
        <div className="p-5 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Fatura Kesen</p>
              <p className="font-medium text-sm">{invoice.invoice_to}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Misafir</p>
              <p className="font-medium text-sm">{invoice.guest_name}</p>
            </div>
            {invoice.tax_id && (
              <div>
                <p className="text-xs text-muted-foreground">Vergi No</p>
                <p className="font-medium text-sm">{invoice.tax_id}</p>
              </div>
            )}
            {invoice.tax_office && (
              <div>
                <p className="text-xs text-muted-foreground">Vergi Dairesi</p>
                <p className="font-medium text-sm">{invoice.tax_office}</p>
              </div>
            )}
            {invoice.address && (
              <div className="col-span-2">
                <p className="text-xs text-muted-foreground">Adres</p>
                <p className="font-medium text-sm">{invoice.address}</p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Otel</p>
              <p className="font-medium text-sm">{invoice.hotel_name}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Konaklama</p>
              <p className="font-medium text-sm">{invoice.check_in} - {invoice.check_out}</p>
            </div>
            {invoice.room_number && (
              <div>
                <p className="text-xs text-muted-foreground">Oda</p>
                <p className="font-medium text-sm">{invoice.room_number}</p>
              </div>
            )}
          </div>

          {/* Items */}
          <div>
            <h3 className="text-sm font-semibold mb-2">Kalemler</h3>
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="text-left p-3 text-xs font-medium text-muted-foreground">Aciklama</th>
                    <th className="text-right p-3 text-xs font-medium text-muted-foreground">Tutar</th>
                  </tr>
                </thead>
                <tbody>
                  {invoice.items?.map((item, i) => (
                    <tr key={i} className="border-t">
                      <td className="p-3">{item.description}</td>
                      <td className="p-3 text-right font-medium">{item.amount?.toLocaleString("tr-TR")} TRY</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Totals */}
          <div className="border-t pt-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Ara Toplam</span>
              <span className="font-medium">{invoice.subtotal?.toLocaleString("tr-TR")} TRY</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">KDV (%{(invoice.tax_rate * 100).toFixed(0)})</span>
              <span className="font-medium">{invoice.tax_amount?.toLocaleString("tr-TR")} TRY</span>
            </div>
            <div className="flex justify-between text-base font-bold border-t pt-2">
              <span>Toplam</span>
              <span className="text-primary">{invoice.total?.toLocaleString("tr-TR")} TRY</span>
            </div>
          </div>

          {invoice.notes && (
            <div>
              <p className="text-xs text-muted-foreground">Notlar</p>
              <p className="text-sm mt-1">{invoice.notes}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PMSInvoicesPage() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedInvoice, setSelectedInvoice] = useState(null);

  const loadInvoices = useCallback(async () => {
    try {
      const params = [];
      if (searchQuery) params.push(`search=${encodeURIComponent(searchQuery)}`);
      if (statusFilter !== "all") params.push(`status=${statusFilter}`);
      const qs = params.length ? `?${params.join("&")}` : "";
      const res = await api.get(`/agency/pms/accounting/invoices${qs}`);
      setInvoices(res.data.items || []);
    } catch {
      toast.error("Faturalar yuklenemedi");
    } finally { setLoading(false); }
  }, [searchQuery, statusFilter]);

  useEffect(() => { loadInvoices(); }, [loadInvoices]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="pms-invoices-page">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Faturalar</h1>
        <p className="text-sm text-muted-foreground mt-1">Tum faturaları goruntule ve yonet</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="Fatura no, misafir adi ile ara..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} data-testid="invoice-search" />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px]" data-testid="invoice-status-filter">
            <SelectValue placeholder="Durum" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tumu</SelectItem>
            {Object.entries(INVOICE_STATUS_MAP).map(([k, v]) => <SelectItem key={k} value={k}>{v.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Invoice List */}
      <Card className="border-0 shadow-sm">
        <CardContent className="p-0">
          {invoices.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <FileText className="h-10 w-10 mb-3 opacity-40" />
              <p className="text-sm font-medium">Fatura bulunamadi</p>
              <p className="text-xs mt-1">Muhasebe sayfasindan fatura olusturabilirsiniz</p>
            </div>
          ) : (
            invoices.map((inv) => {
              const statusInfo = INVOICE_STATUS_MAP[inv.status] || INVOICE_STATUS_MAP.draft;
              return (
                <div
                  key={inv.id}
                  className="flex items-center gap-4 p-4 border-b last:border-b-0 hover:bg-muted/30 transition-colors cursor-pointer"
                  onClick={() => setSelectedInvoice(inv.id)}
                  data-testid={`invoice-row-${inv.id}`}
                >
                  <FileText className="h-5 w-5 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-sm">{inv.invoice_no}</p>
                      <Badge className={`text-[10px] px-1.5 py-0 ${statusInfo.color}`} variant="outline">{statusInfo.label}</Badge>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                      <span>{inv.invoice_to || inv.guest_name}</span>
                      {inv.hotel_name && <span className="flex items-center gap-1"><Building2 className="h-3 w-3" />{inv.hotel_name}</span>}
                      <span className="flex items-center gap-1"><CalendarCheck className="h-3 w-3" />{inv.check_in} - {inv.check_out}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-bold text-primary">{inv.total?.toLocaleString("tr-TR")} TRY</p>
                    <p className="text-xs text-muted-foreground">{new Date(inv.created_at).toLocaleDateString("tr-TR")}</p>
                  </div>
                </div>
              );
            })
          )}
        </CardContent>
      </Card>

      {selectedInvoice && (
        <InvoiceDetailPanel
          invoiceId={selectedInvoice}
          onClose={() => setSelectedInvoice(null)}
          onUpdate={loadInvoices}
        />
      )}
    </div>
  );
}
