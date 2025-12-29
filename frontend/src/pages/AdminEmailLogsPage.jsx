import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, RefreshCw, Search } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";

import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

const STATUS_OPTIONS = [
  { value: "", label: "Tümü" },
  { value: "pending", label: "Pending" },
  { value: "sent", label: "Sent" },
  { value: "failed", label: "Failed" },
];

const EVENT_LABELS = {
  "booking.confirmed": "Rezervasyon Onayı",
  "booking.cancelled": "Rezervasyon İptali",
};

function statusVariant(status) {
  switch (status) {
    case "pending":
      return "secondary"; // sarımsı (Tailwind theme'de genelde warning için secondary veya outline kullanılıyor)
    case "sent":
      return "default"; // yeşil tonu
    case "failed":
      return "destructive"; // kırmızı
    default:
      return "outline";
  }
}

function statusLabel(status) {
  if (!status) return "-";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function eventLabel(ev) {
  return EVENT_LABELS[ev] || ev || "-";
}

function formatDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("tr-TR");
}

export default function AdminEmailLogsPage() {
  const [status, setStatus] = useState("");
  const [eventType, setEventType] = useState("");
  const [query, setQuery] = useState("");

  const [items, setItems] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [retryingId, setRetryingId] = useState(null);

  async function load(cursor) {
    setLoading(true);
    setError("");
    try {
      const params = { limit: 50 };
      if (status) params.status = status;
      if (eventType) params.event_type = eventType;
      if (query) params.q = query;
      if (cursor) params.cursor = cursor;

      const resp = await api.get("/admin/email-outbox", { params });
      const data = resp.data || { items: [], next_cursor: null };
      setItems(data.items || []);
      setNextCursor(data.next_cursor || null);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line
  }, []);

  const sorted = useMemo(() => {
    return [...(items || [])].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );
  }, [items]);

  async function handleRetry(job) {
    if (!job || job.status === "sent") return;
    setRetryingId(job.id);
    try {
      await api.post(`/admin/email-outbox/${job.id}/retry`);
      // optimistic: reload list
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setRetryingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Email Aktiviteleri</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Otomatik rezervasyon emaillerinin durumunu takip edin ve gerektiğinde yeniden deneyin.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => load()} disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Yenile
          </Button>
        </div>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm p-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div className="grid gap-1 md:col-span-1">
            <div className="text-xs text-muted-foreground">Status</div>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value || "all"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-1 md:col-span-1">
            <div className="text-xs text-muted-foreground">Event</div>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
            >
              <option value="">Tümü</option>
              <option value="booking.confirmed">Rezervasyon Onayı</option>
              <option value="booking.cancelled">Rezervasyon İptali</option>
            </select>
          </div>

          <div className="grid gap-1 md:col-span-2">
            <div className="text-xs text-muted-foreground">Arama</div>
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Booking ID, PNR veya email ara"
            />
          </div>

          <div className="grid gap-1 md:col-span-1">
            <div className="text-xs text-muted-foreground">&nbsp;</div>
            <div className="flex gap-2">
              <Button onClick={() => load()} disabled={loading}>
                <Search className="h-4 w-4 mr-2" />
                Filtrele
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setStatus("");
                  setEventType("");
                  setQuery("");
                  setTimeout(() => load(), 0);
                }}
                disabled={loading}
              >
                Sıfırla
              </Button>
            </div>
          </div>
        </div>

        {error ? (
          <div className="mt-3 rounded-xl border border-destructive/50 bg-destructive/5 p-3 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
            <div className="text-sm text-foreground">{error}</div>
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tarih</TableHead>
              <TableHead>Event</TableHead>
              <TableHead>Booking</TableHead>
              <TableHead>To</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Attempts</TableHead>
              <TableHead className="text-right">Aksiyon</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="py-10 text-center text-sm text-muted-foreground"
                >
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : sorted.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="py-10 text-center text-sm text-muted-foreground"
                >
                  Kayıt yok.
                </TableCell>
              </TableRow>
            ) : (
              sorted.map((job) => {
                const emails = job.to || [];
                const first = emails[0] || "-";
                const extra = emails.length > 1 ? emails.length - 1 : 0;

                return (
                  <TableRow key={job.id} className="hover:bg-accent/40">
                    <TableCell className="font-mono text-xs">
                      {formatDate(job.created_at)}
                    </TableCell>
                    <TableCell className="text-sm">
                      <div className="font-medium">{eventLabel(job.event_type)}</div>
                      <div className="text-xs text-muted-foreground font-mono">
                        {job.event_type}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">
                      <div className="font-mono text-xs">{job.booking_id || "-"}</div>
                    </TableCell>
                    <TableCell className="text-sm">
                      <div>{first}</div>
                      {extra > 0 ? (
                        <div className="text-xs text-muted-foreground">+{extra} alıcı daha</div>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(job.status)}>
                        {statusLabel(job.status)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      {job.attempt_count ?? 0}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRetry(job)}
                        disabled={job.status === "sent" || retryingId === job.id}
                      >
                        {retryingId === job.id ? "Retry ediliyor..." : "Retry now"}
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {nextCursor && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => load(nextCursor)} disabled={loading}>
            Daha fazla yükle
          </Button>
        </div>
      )}
    </div>
  );
}
