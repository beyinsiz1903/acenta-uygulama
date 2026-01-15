import React, { useEffect, useState } from "react";
import { Calendar, Loader2, Search } from "lucide-react";

import { api, apiErrorMessage } from "../../lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Badge } from "../../components/ui/badge";

function todayIso() {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

export default function B2BBookingsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");

  useEffect(() => {
    // Default: last 30 days
    const today = todayIso();
    const d = new Date();
    d.setDate(d.getDate() - 30);
    const last30 = d.toISOString().slice(0, 10);
    setFromDate(last30);
    setToDate(today);
  }, []);

  useEffect(() => {
    if (!fromDate || !toDate) return;
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fromDate, toDate, status]);

  async function load(paramsOverride) {
    setLoading(true);
    setError("");
    try {
      const params = {
        from: fromDate ? `${fromDate}T00:00:00Z` : undefined,
        to: toDate ? `${toDate}T23:59:59Z` : undefined,
        status: status || undefined,
        q: (paramsOverride && paramsOverride.q) || (q.trim() || undefined),
        limit: 20,
      };
      const resp = await api.get("/b2b/bookings", { params });
      setItems(resp.data?.items || []);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    load({ q });
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-semibold">Rezervasyonlarım</h1>
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Rezervasyonlar yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-semibold">Rezervasyonlarım</h1>
        <div className="rounded-2xl border bg-card shadow-sm p-6 text-sm text-red-600">
          Rezervasyonlar yüklenemedi. Lütfen tekrar deneyin.
          <div className="mt-2 text-xs text-muted-foreground">{error}</div>
        </div>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-semibold">Rezervasyonlarım</h1>

        <Filters
          fromDate={fromDate}
          toDate={toDate}
          status={status}
          q={q}
          setFromDate={setFromDate}
          setToDate={setToDate}
          setStatus={setStatus}
          setQ={setQ}
          onSearch={handleSearchSubmit}
        />

        <div className="rounded-2xl border bg-card shadow-sm p-10 text-center space-y-2">
          <p className="text-sm font-medium">Bu filtrelerle rezervasyon bulunamadı.</p>
          <p className="text-xs text-muted-foreground">
            Tarih aralığını veya arama terimini değiştirerek tekrar deneyin.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Rezervasyonlarım</h1>

      <Filters
        fromDate={fromDate}
        toDate={toDate}
        status={status}
        q={q}
        setFromDate={setFromDate}
        setToDate={setToDate}
        setStatus={setStatus}
        setQ={setQ}
        onSearch={handleSearchSubmit}
      />

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-semibold">Rez ID</TableHead>
              <TableHead className="font-semibold">Misafir</TableHead>
              <TableHead className="font-semibold">Ürün/Otel</TableHead>
              <TableHead className="font-semibold">Tarih</TableHead>
              <TableHead className="font-semibold">Durum</TableHead>
              <TableHead className="font-semibold">Tutar</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((b) => (
              <TableRow
                key={b.booking_id}
                className="cursor-pointer hover:bg-accent/50"
                onClick={() => {
                  // P0-1.3'te /b2b/bookings/:id detayına gidecek
                  window.location.href = `/b2b/bookings/${b.booking_id}`;
                }}
              >
                <TableCell className="font-mono text-xs">
                  {b.booking_id.slice(0, 8)}
                </TableCell>
                <TableCell className="text-sm">{b.primary_guest_name || "-"}</TableCell>
                <TableCell className="text-sm">{b.product_name || "B2B Booking"}</TableCell>
                <TableCell className="text-sm flex items-center gap-1">
                  <Calendar className="h-3 w-3 text-muted-foreground" />
                  {b.check_in} - {b.check_out}
                </TableCell>
                <TableCell>
                  <StatusBadge status={b.status} />
                </TableCell>
                <TableCell className="text-sm">
                  {b.amount_sell != null ? (
                    <span>
                      {b.amount_sell.toFixed(2)} {b.currency || ""}
                    </span>
                  ) : (
                    "-"
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function Filters({
  fromDate,
  toDate,
  status,
  q,
  setFromDate,
  setToDate,
  setStatus,
  setQ,
  onSearch,
}) {
  return (
    <div className="rounded-2xl border bg-card shadow-sm p-4 space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="grid gap-1">
          <div className="text-xs text-muted-foreground">Başlangıç tarihi</div>
          <input
            type="date"
            className="h-9 rounded-md border bg-background px-3 text-sm"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
          />
        </div>
        <div className="grid gap-1">
          <div className="text-xs text-muted-foreground">Bitiş tarihi</div>
          <input
            type="date"
            className="h-9 rounded-md border bg-background px-3 text-sm"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
          />
        </div>
        <div className="grid gap-1">
          <div className="text-xs text-muted-foreground">Durum</div>
          <select
            className="h-9 rounded-md border bg-background px-3 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">Tümü</option>
            <option value="CONFIRMED">Onaylı</option>
            <option value="PENDING">Beklemede</option>
            <option value="CANCELLED">İptal</option>
          </select>
        </div>
        <form className="grid gap-1" onSubmit={onSearch}>
          <div className="text-xs text-muted-foreground">Arama</div>
          <div className="flex gap-2">
            <input
              className="h-9 flex-1 rounded-md border bg-background px-3 text-sm"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Rez ID / Misafir / Ürün"
            />
            <button
              type="submit"
              className="inline-flex h-9 items-center justify-center rounded-md border bg-primary text-primary-foreground px-3 text-xs gap-1"
            >
              <Search className="h-3 w-3" />
              Filtrele
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const s = String(status || "").toUpperCase();
  if (s === "CONFIRMED") {
    return <Badge className="bg-emerald-500 text-white hover:bg-emerald-500">Onaylı</Badge>;
  }
  if (s === "PENDING") {
    return <Badge className="bg-amber-500 text-white hover:bg-amber-500">Beklemede</Badge>;
  }
  if (s === "CANCELLED") {
    return <Badge className="bg-rose-500 text-white hover:bg-rose-500">İptal</Badge>;
  }
  return <Badge variant="outline">{s || "-"}</Badge>;
}