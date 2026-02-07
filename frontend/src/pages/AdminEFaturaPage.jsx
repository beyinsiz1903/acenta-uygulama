import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { FileText, Send, Plus, X, Eye, RefreshCw } from "lucide-react";
import { cn } from "../lib/utils";

const STATUS_MAP = {
  draft: { label: "Taslak", className: "bg-gray-100 text-gray-700" },
  queued: { label: "Kuyrukta", className: "bg-blue-100 text-blue-700" },
  sent: { label: "Gonderildi", className: "bg-indigo-100 text-indigo-700" },
  accepted: { label: "Kabul Edildi", className: "bg-green-100 text-green-700" },
  rejected: { label: "Reddedildi", className: "bg-red-100 text-red-700" },
  canceled: { label: "Iptal", className: "bg-gray-200 text-gray-500" },
};

export default function AdminEFaturaPage() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    source_type: "manual", source_id: "", customer_id: "", currency: "TRY",
    lines: [{ description: "", quantity: 1, unit_price: 0, tax_rate: 18, line_total: 0 }],
  });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/efatura/invoices");
      setInvoices(res.data?.items || []);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const addLine = () => setForm(f => ({ ...f, lines: [...f.lines, { description: "", quantity: 1, unit_price: 0, tax_rate: 18, line_total: 0 }] }));

  const updateLine = (i, field, value) => {
    const lines = [...form.lines];
    lines[i] = { ...lines[i], [field]: value };
    lines[i].line_total = lines[i].quantity * lines[i].unit_price;
    setForm(f => ({ ...f, lines }));
  };

  const handleCreate = async () => {
    try {
      setCreating(true);
      await api.post("/efatura/invoices", form);
      setShowCreate(false);
      await load();
    } catch (e) { alert(e.response?.data?.error?.message || e.message); } finally { setCreating(false); }
  };

  const handleSend = async (invoiceId) => {
    try {
      await api.post(`/efatura/invoices/${invoiceId}/send`);
      await load();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const handleCancel = async (invoiceId) => {
    if (!window.confirm("Fatura iptal edilsin mi?")) return;
    try {
      await api.post(`/efatura/invoices/${invoiceId}/cancel`);
      await load();
    } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const getStatus = (s) => STATUS_MAP[s] || { label: s, className: "" };

  return (
    <div className="p-6" data-testid="efatura-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><FileText className="h-6 w-6" /> E-Fatura</h1>
          <p className="text-sm text-muted-foreground mt-1">Fatura olusturun, gonderin ve takip edin.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className="h-4 w-4 mr-1" /> Yenile</Button>
          <Button size="sm" onClick={() => setShowCreate(!showCreate)} data-testid="create-invoice-btn"><Plus className="h-4 w-4 mr-1" /> Yeni Fatura</Button>
        </div>
      </div>

      {showCreate && (
        <div className="rounded-lg border p-4 mb-6 bg-muted/20" data-testid="create-invoice-form">
          <h3 className="text-sm font-semibold mb-3">Yeni Fatura</h3>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div>
              <label className="text-xs font-medium block mb-1">Kaynak Tipi</label>
              <select value={form.source_type} onChange={e => setForm(f => ({ ...f, source_type: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" data-testid="source-type-select">
                <option value="manual">Manuel</option>
                <option value="reservation">Rezervasyon</option>
                <option value="payment">Odeme</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Kaynak ID</label>
              <input value={form.source_id} onChange={e => setForm(f => ({ ...f, source_id: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" placeholder="Opsiyonel" />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Musteri ID</label>
              <input value={form.customer_id} onChange={e => setForm(f => ({ ...f, customer_id: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" placeholder="Opsiyonel" />
            </div>
          </div>
          <div className="space-y-2 mb-3">
            <div className="text-xs font-medium">Kalemler</div>
            {form.lines.map((line, i) => (
              <div key={i} className="grid grid-cols-5 gap-2">
                <input placeholder="Aciklama" value={line.description} onChange={e => updateLine(i, "description", e.target.value)} className="rounded-md border px-2 py-1.5 text-xs bg-background" />
                <input type="number" placeholder="Adet" value={line.quantity} onChange={e => updateLine(i, "quantity", +e.target.value)} className="rounded-md border px-2 py-1.5 text-xs bg-background" />
                <input type="number" placeholder="Birim Fiyat" value={line.unit_price} onChange={e => updateLine(i, "unit_price", +e.target.value)} className="rounded-md border px-2 py-1.5 text-xs bg-background" />
                <input type="number" placeholder="KDV %" value={line.tax_rate} onChange={e => updateLine(i, "tax_rate", +e.target.value)} className="rounded-md border px-2 py-1.5 text-xs bg-background" />
                <div className="text-xs py-2 text-right font-mono">{(line.quantity * line.unit_price).toFixed(2)} TL</div>
              </div>
            ))}
            <Button variant="ghost" size="sm" onClick={addLine} className="text-xs"><Plus className="h-3 w-3 mr-1" /> Kalem Ekle</Button>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowCreate(false)}>Iptal</Button>
            <Button size="sm" onClick={handleCreate} disabled={creating} data-testid="submit-invoice-btn">{creating ? "Olusturuluyor..." : "Olustur"}</Button>
          </div>
        </div>
      )}

      {loading ? <div className="animate-pulse h-20 bg-muted rounded-lg" /> : invoices.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="no-invoices"><FileText className="h-12 w-12 mx-auto mb-3 opacity-30" /><p>Henuz fatura yok.</p></div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-muted/50 border-b">
              <th className="text-left px-4 py-2.5 font-medium">Fatura No</th>
              <th className="text-left px-4 py-2.5 font-medium">Kaynak</th>
              <th className="text-left px-4 py-2.5 font-medium">Durum</th>
              <th className="text-right px-4 py-2.5 font-medium">Tutar</th>
              <th className="text-left px-4 py-2.5 font-medium">Tarih</th>
              <th className="text-right px-4 py-2.5 font-medium">Aksiyonlar</th>
            </tr></thead>
            <tbody>
              {invoices.map(inv => (
                <tr key={inv.id} className="border-b last:border-0 hover:bg-muted/30" data-testid={`invoice-row-${inv.invoice_id}`}>
                  <td className="px-4 py-3 font-mono text-xs">{inv.invoice_id}</td>
                  <td className="px-4 py-3">{inv.source_type}{inv.source_id ? ` / ${inv.source_id}` : ""}</td>
                  <td className="px-4 py-3"><Badge variant="outline" className={getStatus(inv.status).className}>{getStatus(inv.status).label}</Badge></td>
                  <td className="px-4 py-3 text-right font-mono">{inv.totals?.grand_total?.toFixed(2)} {inv.totals?.currency}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{inv.created_at ? new Date(inv.created_at).toLocaleDateString("tr-TR") : "-"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      {inv.status === "draft" && <Button size="sm" className="h-7 text-xs gap-1" onClick={() => handleSend(inv.invoice_id)} data-testid={`send-btn-${inv.invoice_id}`}><Send className="h-3 w-3" /> Gonder</Button>}
                      {["draft","sent","accepted"].includes(inv.status) && <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive" onClick={() => handleCancel(inv.invoice_id)}><X className="h-3 w-3" /></Button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
