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
    <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive">
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
    // Initial empty load (no filters) is noisy; wait for user input
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Funnel Events</h1>
        <p className="text-xs text-muted-foreground">
          quote → checkout → booking → payment zincirini correlation_id bazlı inceleyin.
        </p>
      </div>

      <Card className="p-3 space-y-3 text-[11px]">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Correlation ID</Label>
            <Input
              className="h-8 text-xs font-mono"
              value={correlationId}
              onChange={(e) => setCorrelationId(e.target.value)}
              placeholder="fc_..."
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Entity ID (booking/quote)</Label>
            <Input
              className="h-8 text-xs font-mono"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="booking_id / quote_id"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Channel</Label>
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
        <Card className="p-3 space-y-2 text-[11px]">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">Event Listesi</div>
            <div className="text-[11px] text-muted-foreground">Sonuç: {events.length}</div>
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
                <div className="px-2 py-3 text-[11px] text-muted-foreground">
                  Henüz event yok veya filtre boş sonuç döndürdü.
                </div>
              )}
            </div>
          </div>
        </Card>

        <Card className="p-3 space-y-2 text-[11px]">
          <div className="text-sm font-semibold">Detay</div>
          {!selected && (
            <div className="text-[11px] text-muted-foreground mt-2">
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
                  className="font-mono text-[11px] min-h-[120px]"
                  value={JSON.stringify(selected.context || {}, null, 2)}
                />
              </div>

              <div className="space-y-1">
                <div className="font-semibold">Trace</div>
                <Textarea
                  readOnly
                  className="font-mono text-[11px] min-h-[120px]"
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
