import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { QrCode, CheckCircle, Plus, Search, RefreshCw, XCircle, BarChart3, X, Download, Printer } from "lucide-react";
import { cn } from "../lib/utils";
import { QRCodeSVG } from "qrcode.react";

const STATUS_MAP = {
  active: { label: "Aktif", className: "bg-green-100 text-green-700" },
  checked_in: { label: "Giris Yapildi", className: "bg-blue-100 text-blue-700" },
  canceled: { label: "Iptal", className: "bg-red-100 text-red-700" },
  expired: { label: "Suresi Dolmus", className: "bg-gray-100 text-gray-500" },
};

export default function AdminTicketsPage() {
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showCheckin, setShowCheckin] = useState(false);
  const [creating, setCreating] = useState(false);
  const [checkinCode, setCheckinCode] = useState("");
  const [checkinResult, setCheckinResult] = useState(null);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [form, setForm] = useState({
    reservation_id: "", product_name: "", customer_name: "",
    customer_email: "", customer_phone: "", event_date: "", seat_info: "",
  });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [tkRes, stRes] = await Promise.all([
        api.get("/tickets"),
        api.get("/tickets/stats"),
      ]);
      setTickets(tkRes.data?.items || []);
      setStats(stRes.data || {});
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!form.reservation_id || !form.product_name || !form.customer_name) return;
    try {
      setCreating(true);
      await api.post("/tickets", form);
      setShowCreate(false);
      setForm({ reservation_id: "", product_name: "", customer_name: "", customer_email: "", customer_phone: "", event_date: "", seat_info: "" });
      await load();
    } catch (e) { alert(e.response?.data?.error?.message || e.message); } finally { setCreating(false); }
  };

  const handleCheckin = async () => {
    if (!checkinCode.trim()) return;
    try {
      setCheckinResult(null);
      const res = await api.post("/tickets/check-in", { ticket_code: checkinCode.trim() });
      setCheckinResult({ success: true, data: res.data });
      setCheckinCode("");
      await load();
    } catch (e) {
      setCheckinResult({ success: false, error: e.response?.data?.detail || e.response?.data?.error?.message || e.message });
    }
  };

  const handleCancel = async (code) => {
    if (!window.confirm("Bilet iptal edilsin mi?")) return;
    try { await api.post(`/tickets/${code}/cancel`); await load(); } catch (e) { alert(e.response?.data?.detail || e.message); }
  };

  const getStatus = (s) => STATUS_MAP[s] || { label: s, className: "" };

  return (
    <div className="p-6" data-testid="tickets-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2"><QrCode className="h-6 w-6" /> QR Bilet & Check-in</h1>
          <p className="text-sm text-muted-foreground mt-1">Bilet olusturun, QR kodu ile check-in yapin.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className="h-4 w-4 mr-1" /> Yenile</Button>
          <Button variant="outline" size="sm" onClick={() => { setShowCheckin(!showCheckin); setShowCreate(false); }} data-testid="checkin-toggle-btn"><Search className="h-4 w-4 mr-1" /> Check-in</Button>
          <Button size="sm" onClick={() => { setShowCreate(!showCreate); setShowCheckin(false); }} data-testid="create-ticket-btn"><Plus className="h-4 w-4 mr-1" /> Yeni Bilet</Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-6" data-testid="ticket-stats">
        <div className="rounded-lg border p-3 text-center"><div className="text-2xl font-bold">{stats.total || 0}</div><div className="text-xs text-muted-foreground">Toplam</div></div>
        <div className="rounded-lg border p-3 text-center"><div className="text-2xl font-bold text-green-600">{stats.active || 0}</div><div className="text-xs text-muted-foreground">Aktif</div></div>
        <div className="rounded-lg border p-3 text-center"><div className="text-2xl font-bold text-blue-600">{stats.checked_in || 0}</div><div className="text-xs text-muted-foreground">Giris Yapan</div></div>
        <div className="rounded-lg border p-3 text-center"><div className="text-2xl font-bold text-red-600">{stats.canceled || 0}</div><div className="text-xs text-muted-foreground">Iptal</div></div>
      </div>

      {/* Check-in Panel */}
      {showCheckin && (
        <div className="rounded-lg border p-4 mb-6 bg-blue-50/50 dark:bg-blue-950/20" data-testid="checkin-panel">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><QrCode className="h-4 w-4" /> Bilet Check-in</h3>
          <div className="flex gap-2">
            <input value={checkinCode} onChange={e => setCheckinCode(e.target.value)} placeholder="Bilet kodu girin (TKT-XXXX-XXXX-XX)" className="flex-1 rounded-md border px-3 py-2 text-sm bg-background font-mono" data-testid="checkin-input" onKeyDown={e => e.key === "Enter" && handleCheckin()} />
            <Button onClick={handleCheckin} data-testid="checkin-submit-btn"><CheckCircle className="h-4 w-4 mr-1" /> Check-in</Button>
          </div>
          {checkinResult && (
            <div className={cn("mt-3 p-3 rounded-lg text-sm", checkinResult.success ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800")} data-testid="checkin-result">
              {checkinResult.success ? <span className="flex items-center gap-1"><CheckCircle className="h-4 w-4" /> Basarili! Check-in tamamlandi.</span> : <span className="flex items-center gap-1"><XCircle className="h-4 w-4" /> {checkinResult.error}</span>}
            </div>
          )}
        </div>
      )}

      {/* Create Ticket Form */}
      {showCreate && (
        <div className="rounded-lg border p-4 mb-6 bg-muted/20" data-testid="create-ticket-form">
          <h3 className="text-sm font-semibold mb-3">Yeni Bilet</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div><label className="text-xs font-medium block mb-1">Rezervasyon ID *</label><input value={form.reservation_id} onChange={e => setForm(f => ({ ...f, reservation_id: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" data-testid="ticket-reservation-input" /></div>
            <div><label className="text-xs font-medium block mb-1">Urun Adi *</label><input value={form.product_name} onChange={e => setForm(f => ({ ...f, product_name: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" data-testid="ticket-product-input" /></div>
            <div><label className="text-xs font-medium block mb-1">Musteri Adi *</label><input value={form.customer_name} onChange={e => setForm(f => ({ ...f, customer_name: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" data-testid="ticket-customer-input" /></div>
            <div><label className="text-xs font-medium block mb-1">Email</label><input value={form.customer_email} onChange={e => setForm(f => ({ ...f, customer_email: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" /></div>
            <div><label className="text-xs font-medium block mb-1">Telefon</label><input value={form.customer_phone} onChange={e => setForm(f => ({ ...f, customer_phone: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" /></div>
            <div><label className="text-xs font-medium block mb-1">Etkinlik Tarihi</label><input type="date" value={form.event_date} onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))} className="w-full rounded-md border px-3 py-2 text-sm bg-background" /></div>
          </div>
          <div className="flex justify-end gap-2 mt-3">
            <Button variant="outline" size="sm" onClick={() => setShowCreate(false)}>Iptal</Button>
            <Button size="sm" onClick={handleCreate} disabled={creating || !form.reservation_id} data-testid="submit-ticket-btn">{creating ? "Olusturuluyor..." : "Olustur"}</Button>
          </div>
        </div>
      )}

      {/* Tickets Table */}
      {loading ? <div className="animate-pulse h-20 bg-muted rounded-lg" /> : tickets.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="no-tickets"><QrCode className="h-12 w-12 mx-auto mb-3 opacity-30" /><p>Henuz bilet yok.</p></div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="bg-muted/50 border-b">
              <th className="text-left px-4 py-2.5 font-medium">Bilet Kodu</th>
              <th className="text-left px-4 py-2.5 font-medium">Urun</th>
              <th className="text-left px-4 py-2.5 font-medium">Musteri</th>
              <th className="text-left px-4 py-2.5 font-medium">Durum</th>
              <th className="text-left px-4 py-2.5 font-medium">Tarih</th>
              <th className="text-right px-4 py-2.5 font-medium">Aksiyonlar</th>
            </tr></thead>
            <tbody>
              {tickets.map(t => (
                <tr key={t.id} className="border-b last:border-0 hover:bg-muted/30" data-testid={`ticket-row-${t.ticket_code}`}>
                  <td className="px-4 py-3 font-mono text-xs">{t.ticket_code}</td>
                  <td className="px-4 py-3">{t.product_name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{t.customer_name}</td>
                  <td className="px-4 py-3"><Badge variant="outline" className={getStatus(t.status).className}>{getStatus(t.status).label}</Badge></td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{t.event_date || (t.created_at ? new Date(t.created_at).toLocaleDateString("tr-TR") : "-")}</td>
                  <td className="px-4 py-3 text-right">
                    {t.status === "active" && <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive" onClick={() => handleCancel(t.ticket_code)}><XCircle className="h-3 w-3 mr-1" /> Iptal</Button>}
                    {t.status === "checked_in" && <span className="text-xs text-blue-600">Giris: {t.checked_in_at ? new Date(t.checked_in_at).toLocaleTimeString("tr-TR") : ""}</span>}
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
