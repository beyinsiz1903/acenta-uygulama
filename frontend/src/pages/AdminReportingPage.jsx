import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive">
      {text}
    </div>
  );
}

export default function AdminReportingPage() {
  const [days, setDays] = useState(7);

  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const [topProducts, setTopProducts] = useState([]);
  const [topLoading, setTopLoading] = useState(false);
  const [topError, setTopError] = useState("");

  const [funnel, setFunnel] = useState(null);
  const [funnelLoading, setFunnelLoading] = useState(false);
  const [funnelError, setFunnelError] = useState("");

  const loadSummary = async (d) => {
    const v = d ?? days;
    setSummaryLoading(true);
    setSummaryError("");
    try {
      const res = await api.get("/admin/reporting/summary", { params: { days: v } });
      setSummary(res.data || null);
    } catch (e) {
      setSummaryError(apiErrorMessage(e));
    } finally {
      setSummaryLoading(false);
    }
  };

  const loadTopProducts = async (d) => {
    const v = d ?? days;
    setTopLoading(true);
    setTopError("");
    try {
      const res = await api.get("/admin/reporting/top-products", {
        params: { days: v, limit: 10, by: "sell" },
      });
      setTopProducts((res.data && res.data.items) || []);
    } catch (e) {
      setTopError(apiErrorMessage(e));
    } finally {
      setTopLoading(false);
    }
  };

  const loadFunnel = async (d) => {
    const v = d ?? days;
    setFunnelLoading(true);
    setFunnelError("");
    try {
      const res = await api.get("/admin/funnel/summary", { params: { days: v } });
      setFunnel(res.data || null);
    } catch (e) {
      setFunnelError(apiErrorMessage(e));
    } finally {
      setFunnelLoading(false);
    }
  };

  useEffect(() => {
    void loadSummary(days);
    void loadTopProducts(days);
    void loadFunnel(days);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const formatMoney = (v) => {
    if (v == null) return "0.00";
    const num = Number(v) || 0;
    return num.toFixed(2);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold">Raporlama</h1>
            <Badge
              variant="outline"
              data-testid="payments-e2e-proof-pending-badge"
              className="border-amber-300 bg-amber-50 text-[10px] font-medium text-amber-800"
            >
              Payments e2e: proof pending (env)
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Son X gün için ciro özeti, en çok satan ürünler ve funnel KPI&apos;larını görüntüleyin.
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px]">
          <Label htmlFor="reporting-days" className="text-[11px]">
            Son
          </Label>
          <select
            id="reporting-days"
            className="h-7 rounded-md border bg-background px-2 text-xs"
            value={days}
            onChange={(e) => setDays(Number(e.target.value) || 7)}
          >
            <option value={7}>7 gün</option>
            <option value={14}>14 gün</option>
            <option value={30}>30 gün</option>
          </select>
        </div>
      </div>

      <Card className="p-3 text-[11px] space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Ciro Özeti</div>
          {summaryLoading && <div className="text-[11px] text-muted-foreground">Yükleniyor...</div>}
        </div>
        <FieldError text={summaryError} />
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-6 gap-2 mt-2">
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Rezervasyonlar</div>
              <div className="text-sm font-semibold">{summary.bookings.count}</div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Sell Total</div>
              <div className="text-sm font-semibold">
                {formatMoney(summary.bookings.sell_total)} {summary.bookings.currency}
              </div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Net Total</div>
              <div className="text-sm font-semibold">
                {formatMoney(summary.bookings.net_total)} {summary.bookings.currency}
              </div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Markup Total</div>
              <div className="text-sm font-semibold">
                {formatMoney(summary.bookings.markup_total)} {summary.bookings.currency}
              </div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Avg Sell</div>
              <div className="text-sm font-semibold">
                {formatMoney(summary.bookings.avg_sell)} {summary.bookings.currency}
              </div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Paid / Unpaid</div>
              <div className="text-sm font-semibold">
                {summary.payments.paid_count} / {summary.payments.unpaid_count}
              </div>
            </div>
          </div>
        )}
      </Card>

      <Card className="p-3 text-[11px] space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">En Çok Satan Ürünler (ciroya göre)</div>
          {topLoading && <div className="text-[11px] text-muted-foreground">Yükleniyor...</div>}
        </div>
        <FieldError text={topError} />
        <div className="mt-2 rounded-md border overflow-hidden">
          <div className="grid grid-cols-4 bg-muted/40 px-2 py-2 font-semibold">
            <div>Ürün ID</div>
            <div>Rezervasyon</div>
            <div>Ciro</div>
            <div>Net</div>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {topProducts.map((p) => (
              <div key={p.product_id} className="grid grid-cols-4 border-t px-2 py-2">
                <div className="font-mono truncate" title={p.product_id}>{p.product_id}</div>
                <div>{p.bookings}</div>
                <div>{formatMoney(p.sell_total)}</div>
                <div>{formatMoney(p.net_total)}</div>
              </div>
            ))}
            {!topProducts.length && !topLoading && (
              <div className="px-2 py-3 text-[11px] text-muted-foreground">Son {days} günde ürün bulunamadı.</div>
            )}
          </div>
        </div>
      </Card>

      <Card className="p-3 text-[11px] space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Funnel Özeti</div>
          {funnelLoading && <div className="text-[11px] text-muted-foreground">Yükleniyor...</div>}
        </div>
        <FieldError text={funnelError} />
        {funnel && (
          <div className="grid grid-cols-2 md:grid-cols-6 gap-2 mt-2">
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Teklifler</div>
              <div className="text-sm font-semibold">{funnel.quote_count}</div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Checkout Başlatıldı</div>
              <div className="text-sm font-semibold">{funnel.checkout_started_count}</div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Rezervasyonlar</div>
              <div className="text-sm font-semibold">{funnel.booking_created_count}</div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Başarılı Ödemeler</div>
              <div className="text-sm font-semibold">{funnel.payment_succeeded_count}</div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Başarısız Ödemeler</div>
              <div className="text-sm font-semibold">{funnel.payment_failed_count}</div>
            </div>
            <div className="rounded-md border px-2 py-2">
              <div className="text-[10px] text-muted-foreground">Dönüşüm</div>
              <div className="text-sm font-semibold">{(Number(funnel.conversion || 0) * 100).toFixed(1)}%</div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
