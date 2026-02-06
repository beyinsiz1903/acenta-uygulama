import React, { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { DollarSign, ArrowDownLeft, ArrowUpRight, Calendar, RefreshCcw, Plus, X, Loader2 } from "lucide-react";

function formatMoney(amount) {
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY" }).format(amount || 0);
}

/* ─── Payment Modal ───────────────────────────────────────────── */
function PaymentModal({ open, onClose, onSuccess }) {
  const [form, setForm] = useState({ amount: "", method: "cash", description: "", customer_id: "", reservation_id: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading || submitted) return; // Double-click guard
    setError("");
    setLoading(true);
    setSubmitted(true);
    try {
      const idempotencyKey = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const payload = { ...form, amount: parseFloat(form.amount), idempotency_key: idempotencyKey };
      if (!payload.customer_id) delete payload.customer_id;
      if (!payload.reservation_id) delete payload.reservation_id;
      await api.post("/webpos/payments", payload);
      onSuccess();
      onClose();
      setForm({ amount: "", method: "cash", description: "", customer_id: "", reservation_id: "" });
      setSubmitted(false);
    } catch (err) {
      setError(err?.response?.data?.error?.message || "Ödeme kaydedilemedi.");
      setSubmitted(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="payment-modal">
      <div className="bg-white dark:bg-slate-900 rounded-2xl border shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold flex items-center gap-2"><Plus className="h-5 w-5" /> Ödeme Kaydet</h3>
          <button onClick={onClose}><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm px-3 py-2 mb-3">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div><Label>Tutar (TRY)</Label><Input type="number" step="0.01" min="0.01" required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="0.00" data-testid="payment-amount" /></div>
          <div><Label>Yöntem</Label>
            <select className="w-full h-10 rounded-lg border px-3 text-sm bg-background" value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })} data-testid="payment-method">
              <option value="cash">Nakit</option>
              <option value="bank_transfer">Banka Transferi</option>
              <option value="manual_card">Kart (Manuel)</option>
              <option value="other">Diğer</option>
            </select>
          </div>
          <div><Label>Açıklama</Label><Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Ödeme notu" /></div>
          <Button type="submit" className="w-full" disabled={loading} data-testid="payment-submit">
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <DollarSign className="h-4 w-4 mr-2" />}
            Ödeme Kaydet
          </Button>
        </form>
      </div>
    </div>
  );
}

/* ─── Refund Modal ────────────────────────────────────────────── */
function RefundModal({ open, onClose, onSuccess, payment }) {
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { if (payment) setAmount(String(payment.amount)); }, [payment]);

  if (!open || !payment) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/webpos/refunds", { payment_id: payment.id, amount: parseFloat(amount), reason });
      onSuccess();
      onClose();
    } catch (err) {
      setError(err?.response?.data?.error?.message || "İade yapılamadı.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" data-testid="refund-modal">
      <div className="bg-white dark:bg-slate-900 rounded-2xl border shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold">İade</h3>
          <button onClick={onClose}><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm px-3 py-2 mb-3">{error}</div>}
        <p className="text-sm text-muted-foreground mb-3">Orijinal ödeme: {formatMoney(payment.amount)}</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div><Label>İade Tutarı</Label><Input type="number" step="0.01" min="0.01" max={payment.amount} value={amount} onChange={(e) => setAmount(e.target.value)} data-testid="refund-amount" /></div>
          <div><Label>Sebep</Label><Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="İade sebebi" /></div>
          <Button type="submit" className="w-full" variant="destructive" disabled={loading} data-testid="refund-submit">
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            İade Et
          </Button>
        </form>
      </div>
    </div>
  );
}

/* ═══ MAIN PAGE ═══════════════════════════════════════════════ */
export default function WebPOSPage() {
  const [payments, setPayments] = useState([]);
  const [ledger, setLedger] = useState([]);
  const [balance, setBalance] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showPayment, setShowPayment] = useState(false);
  const [showRefund, setShowRefund] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState(null);
  const [dailySummary, setDailySummary] = useState(null);
  const [tab, setTab] = useState("payments");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [payRes, ledRes, balRes] = await Promise.all([
        api.get("/webpos/payments?limit=50"),
        api.get("/webpos/ledger?limit=50"),
        api.get("/webpos/balance"),
      ]);
      setPayments(payRes.data.items || []);
      setLedger(ledRes.data.items || []);
      setBalance(balRes.data.balance || 0);

      // Daily summary
      const today = new Date().toISOString().slice(0, 10);
      try {
        const ds = await api.get(`/webpos/daily-summary?date=${today}`);
        setDailySummary(ds.data);
      } catch {}
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRefundClick = (p) => { setSelectedPayment(p); setShowRefund(true); };

  const methodLabel = { cash: "Nakit", bank_transfer: "Banka", manual_card: "Kart", other: "Diğer" };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6" data-testid="webpos-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">WebPOS</h1>
          <p className="text-sm text-muted-foreground">Ödeme kayıtları ve mali defter</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCcw className="h-4 w-4 mr-1" /> Yenile</Button>
          <Button size="sm" onClick={() => setShowPayment(true)} data-testid="new-payment-btn"><Plus className="h-4 w-4 mr-1" /> Ödeme Kaydet</Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
          <div className="text-sm text-muted-foreground">Bakiye</div>
          <div className="text-2xl font-bold text-green-600" data-testid="balance">{formatMoney(balance)}</div>
        </div>
        {dailySummary && (
          <>
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
              <div className="text-sm text-muted-foreground">Bugün Gelen</div>
              <div className="text-xl font-bold text-blue-600">{formatMoney(dailySummary.debit_total)}</div>
              <div className="text-xs text-muted-foreground">{dailySummary.debit_count} işlem</div>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
              <div className="text-sm text-muted-foreground">Bugün İade</div>
              <div className="text-xl font-bold text-rose-600">{formatMoney(dailySummary.credit_total)}</div>
              <div className="text-xs text-muted-foreground">{dailySummary.credit_count} işlem</div>
            </div>
            <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
              <div className="text-sm text-muted-foreground">Bugün Net</div>
              <div className="text-xl font-bold">{formatMoney(dailySummary.net)}</div>
            </div>
          </>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        {["payments", "ledger"].map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 text-sm font-medium border-b-2 transition-all ${tab === t ? "border-blue-500 text-blue-600" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t === "payments" ? "Ödemeler" : "Defter"}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-blue-500" /></div>
      ) : tab === "payments" ? (
        <div className="bg-white dark:bg-slate-900 rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Tarih</th>
                <th className="px-4 py-3 text-left font-medium">Tutar</th>
                <th className="px-4 py-3 text-left font-medium">Yöntem</th>
                <th className="px-4 py-3 text-left font-medium">Açıklama</th>
                <th className="px-4 py-3 text-left font-medium">Durum</th>
                <th className="px-4 py-3 text-right font-medium">İşlem</th>
              </tr>
            </thead>
            <tbody>
              {payments.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">Henüz ödeme kaydı yok.</td></tr>
              )}
              {payments.map((p) => (
                <tr key={p.id} className="border-t hover:bg-muted/20">
                  <td className="px-4 py-3">{p.created_at ? new Date(p.created_at).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "-"}</td>
                  <td className="px-4 py-3 font-medium">{formatMoney(p.amount)}</td>
                  <td className="px-4 py-3">{methodLabel[p.method] || p.method}</td>
                  <td className="px-4 py-3 text-muted-foreground">{p.description || "-"}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${p.status === "recorded" ? "bg-green-100 text-green-700" : p.status === "refunded" ? "bg-rose-100 text-rose-700" : "bg-yellow-100 text-yellow-700"}`}>
                      {p.status === "recorded" ? "Kayıtlı" : p.status === "refunded" ? "İade" : p.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {p.status === "recorded" && (
                      <Button variant="ghost" size="sm" onClick={() => handleRefundClick(p)} data-testid="refund-btn">İade</Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-900 rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Zaman</th>
                <th className="px-4 py-3 text-left font-medium">Tür</th>
                <th className="px-4 py-3 text-left font-medium">Kategori</th>
                <th className="px-4 py-3 text-left font-medium">Tutar</th>
                <th className="px-4 py-3 text-left font-medium">Bakiye</th>
                <th className="px-4 py-3 text-left font-medium">Açıklama</th>
              </tr>
            </thead>
            <tbody>
              {ledger.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">Defter kaydı yok.</td></tr>
              )}
              {ledger.map((e) => (
                <tr key={e.id} className="border-t hover:bg-muted/20">
                  <td className="px-4 py-3">{e.timestamp ? new Date(e.timestamp).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" }) : "-"}</td>
                  <td className="px-4 py-3">
                    {e.type === "debit" ? <span className="flex items-center gap-1 text-green-600"><ArrowDownLeft className="h-3.5 w-3.5" /> Borç</span> : <span className="flex items-center gap-1 text-rose-600"><ArrowUpRight className="h-3.5 w-3.5" /> Alacak</span>}
                  </td>
                  <td className="px-4 py-3 capitalize">{e.category}</td>
                  <td className="px-4 py-3 font-medium">{formatMoney(e.amount)}</td>
                  <td className="px-4 py-3 font-mono text-xs">{formatMoney(e.balance_after)}</td>
                  <td className="px-4 py-3 text-muted-foreground">{e.description || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <PaymentModal open={showPayment} onClose={() => setShowPayment(false)} onSuccess={load} />
      <RefundModal open={showRefund} onClose={() => { setShowRefund(false); setSelectedPayment(null); }} onSuccess={load} payment={selectedPayment} />
    </div>
  );
}
