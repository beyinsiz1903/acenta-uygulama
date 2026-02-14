import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Card } from "../components/ui/card";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
      {text}
    </div>
  );
}

export default function AdminFunnelPage() {
  const [correlationId, setCorrelationId] = useState("");
  const [entityId, setEntityId] = useState("");
  const [channel, setChannel] = useState("");
  const [events, setEvents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [days, setDays] = useState(7);
  const emptySummary = {
    days: 7,
    quote_count: 0,
    checkout_started_count: 0,
    booking_created_count: 0,
    payment_succeeded_count: 0,
    payment_failed_count: 0,
    conversion: 0,
  };

  const [summary, setSummary] = useState(emptySummary);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");
  const [summaryChannel, setSummaryChannel] = useState("all");
  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alertsError, setAlertsError] = useState("");

  const loadSummary = async (nextDays) => {
    const d = nextDays ?? days;
    setSummaryLoading(true);
    setSummaryError("");
    try {
      const res = await api.get("/admin/funnel/summary", { params: { days: d } });
      setSummary(res.data || { ...emptySummary, days: d });
    } catch (e) {
      setSummaryError(apiErrorMessage(e));
    } finally {
      setSummaryLoading(false);
    }
  };

  const loadAlerts = async (nextDays) => {
    const d = nextDays ?? days;
    setAlertsLoading(true);
    setAlertsError("");
    try {
      const res = await api.get("/admin/funnel/alerts", { params: { days: d } });
      setAlerts((res.data && res.data.alerts) || []);
    } catch (e) {
      setAlertsError(apiErrorMessage(e));
    } finally {
      setAlertsLoading(false);
    }
  };

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const params = {};
      if (correlationId) params.correlation_id = correlationId;
      if (entityId) params.entity_id = entityId;
      if (channel) params.channel = channel;
      const res = await api.get("/admin/funnel/events", { params });
      setEvents(res.data || []);
      setSelected(null);
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSummary(days);
    void loadAlerts(days);
    // Initial empty load (no filters) is noisy; wait for user input
  }, [days]);

  const formatPercent = (v) => {
    if (!v || Number.isNaN(v)) return "0.0%";
    const num = Number(v) || 0;
    const pct = Math.round(num * 1000) / 10; // 12.3%
    return `${pct.toFixed(1)}%`;
  };

  const currentSummary =
    summaryChannel === "all"
      ? summary
      : (summary?.by_channel?.[summaryChannel] || { ...emptySummary, days: summary.days });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Funnel Events</h1>
        <p className="text-xs text-muted-foreground">
          quote → checkout → booking → payment zincirini correlation_id bazlı inceleyin.
        </p>
      </div>

      <Card className="p-3 space-y-3 text-xs">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Label htmlFor="funnel-days" className="text-xs">
                Son
              </Label>
              <select
                id="funnel-days"
                data-testid="funnel-kpi-days-select"
                className="h-7 rounded-md border bg-background px-2 text-xs"
                value={days}
                onChange={(e) => setDays(Number(e.target.value) || 7)}
              >
                <option value={7}>7 gün</option>
                <option value={14}>14 gün</option>
                <option value={30}>30 gün</option>
              </select>
            </div>
            <div className="flex items-center gap-1 border rounded-md bg-background p-0.5 text-2xs">
              <button
                type="button"
                data-testid="funnel-kpi-channel-all"
                onClick={() => setSummaryChannel("all")}
                className={`px-2 py-1 rounded ${
                  summaryChannel === "all" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                }`}
              >
                All
              </button>
              <button
                type="button"
                data-testid="funnel-kpi-channel-public"
                onClick={() => setSummaryChannel("public")}
                className={`px-2 py-1 rounded ${
                  summaryChannel === "public" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                }`}
              >
                Public
              </button>
              <button
                type="button"
                data-testid="funnel-kpi-channel-b2b"
                onClick={() => setSummaryChannel("b2b")}
                className={`px-2 py-1 rounded ${
                  summaryChannel === "b2b" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                }`}
              >
                B2B
              </button>
            </div>
          </div>
          {summaryLoading && <div className="text-xs text-muted-foreground">Ykleniyor...</div>}
        </div>

        {summaryError && <FieldError text={summaryError} />}

        <div className="grid grid-cols-2 md:grid-cols-6 gap-2 mt-2">
          <div className="rounded-md border px-2 py-2" data-testid="funnel-kpi-quotes">
            <div className="text-2xs text-muted-foreground">Teklifler</div>
            <div className="text-sm font-semibold">{currentSummary.quote_count}</div>
          </div>
          <div className="rounded-md border px-2 py-2" data-testid="funnel-kpi-checkout-started">
            <div className="text-2xs text-muted-foreground">Checkout Başlatıldı</div>
            <div className="text-sm font-semibold">{currentSummary.checkout_started_count}</div>
          </div>
          <div className="rounded-md border px-2 py-2" data-testid="funnel-kpi-bookings">
            <div className="text-2xs text-muted-foreground">Rezervasyonlar</div>
            <div className="text-sm font-semibold">{currentSummary.booking_created_count}</div>
          </div>
          <div className="rounded-md border px-2 py-2" data-testid="funnel-kpi-pay-succeeded">
            <div className="text-2xs text-muted-foreground">Başarılı Ödemeler</div>
            <div className="text-sm font-semibold">{currentSummary.payment_succeeded_count}</div>
          </div>
          <div className="rounded-md border px-2 py-2" data-testid="funnel-kpi-pay-failed">
            <div className="text-2xs text-muted-foreground">Başarısız Ödemeler</div>
            <div className="text-sm font-semibold">{currentSummary.payment_failed_count}</div>
          </div>
          <div className="rounded-md border px-2 py-2" data-testid="funnel-kpi-conversion">
            <div className="text-2xs text-muted-foreground">Dönüşüm</div>
            <div className="text-sm font-semibold">{formatPercent(currentSummary.conversion)}</div>
          </div>
        </div>
      </Card>

      {/* Alerts Panel */}
      <Card className="p-3 space-y-3 text-xs" data-testid="funnel-alerts-panel">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Funnel Alerts</div>
          {alertsLoading && <div className="text-xs text-muted-foreground">Yükleniyor...</div>}
        </div>

        {alertsError && <FieldError text={alertsError} />}

        {!alertsLoading && !alertsError && (
          <div className="space-y-2">
            {alerts.length === 0 ? (
              <div className="text-xs text-muted-foreground p-2 bg-green-50 border border-green-200 rounded-md">
                ✅ Sağlıklı - {days} günde alert bulunamadı
              </div>
            ) : (
              <div className="space-y-1">
                {alerts.map((alert, index) => (
                  <div
                    key={index}
                    className="p-2 bg-red-50 border border-red-200 rounded-md text-xs"
                    data-testid={`funnel-alert-item-${alert.code}-${alert.channel}`}
                  >
                    <div className="font-semibold text-red-700">{alert.code}</div>
                    <div className="text-red-600">{alert.message}</div>
                    <div className="text-red-500 text-2xs">Channel: {alert.channel}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      <Card className="p-3 space-y-3 text-xs">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <div className="space-y-1">
            <Label className="text-xs">Correlation ID</Label>
            <Input
              className="h-8 text-xs font-mono"
              value={correlationId}
              onChange={(e) => setCorrelationId(e.target.value)}
              placeholder="fc_..."
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Entity ID (booking/quote)</Label>
            <Input
              className="h-8 text-xs font-mono"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="booking_id / quote_id"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Channel</Label>
            <select
              className="h-8 w-full rounded-md border bg-background px-2 text-xs"
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
            >
              <option value="">Tümü</option>
              <option value="public">public</option>
              <option value="b2b">b2b</option>
            </select>
          </div>
          <div className="flex items-end justify-end">
            <Button size="sm" className="h-8 text-xs" onClick={load} disabled={loading}>
              Yükle
            </Button>
          </div>
        </div>

        <FieldError text={err} />
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Card className="p-3 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">Event Listesi</div>
            <div className="text-xs text-muted-foreground">Sonuç: {events.length}</div>
          </div>

          <div className="mt-2 rounded-md border overflow-hidden">
            <div className="grid grid-cols-5 bg-muted/40 px-2 py-2 font-semibold">
              <div>Zaman</div>
              <div>Event</div>
              <div>Entity</div>
              <div>Channel</div>
              <div>Correlation</div>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {events.map((ev) => (
                <button
                  key={ev.id}
                  type="button"
                  onClick={() => setSelected(ev)}
                  className="grid grid-cols-5 w-full border-t px-2 py-1 text-left hover:bg-muted/60"
                >
                  <div className="truncate" title={ev.created_at}>{String(ev.created_at).slice(0, 19)}</div>
                  <div className="truncate" title={ev.event_name}>{ev.event_name}</div>
                  <div className="truncate" title={`${ev.entity_type}:${ev.entity_id}`}>
                    {ev.entity_type}:{ev.entity_id}
                  </div>
                  <div>{ev.channel}</div>
                  <div className="truncate font-mono" title={ev.correlation_id}>{ev.correlation_id}</div>
                </button>
              ))}
              {!events.length && (
                <div className="px-2 py-3 text-xs text-muted-foreground">
                  Henüz event yok veya filtre boş sonuç döndürdü.
                </div>
              )}
            </div>
          </div>
        </Card>

        <Card className="p-3 space-y-2 text-xs">
          <div className="text-sm font-semibold">Detay</div>
          {!selected && (
            <div className="text-xs text-muted-foreground mt-2">
              Soldan bir event seçin.
            </div>
          )}
          {selected && (
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="font-semibold">Event</div>
                  <div>{selected.event_name}</div>
                </div>
                <div>
                  <div className="font-semibold">Zaman</div>
                  <div>{String(selected.created_at).slice(0, 19)}</div>
                </div>
              </div>

              <div className="space-y-1">
                <div className="font-semibold">Context</div>
                <Textarea
                  readOnly
                  className="font-mono text-xs min-h-[120px]"
                  value={JSON.stringify(selected.context || {}, null, 2)}
                />
              </div>

              <div className="space-y-1">
                <div className="font-semibold">Trace</div>
                <Textarea
                  readOnly
                  className="font-mono text-xs min-h-[120px]"
                  value={JSON.stringify(selected.trace || {}, null, 2)}
                />
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
