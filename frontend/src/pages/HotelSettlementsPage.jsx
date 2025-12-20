import React, { useEffect, useMemo, useState } from "react";
import { Download, RefreshCw, AlertCircle } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { formatMoney } from "../lib/format";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Button } from "../components/ui/button";

function currentMonth() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

export default function HotelSettlementsPage() {
  const [month, setMonth] = useState(currentMonth());
  const [status, setStatus] = useState("");
  const [agencyId, setAgencyId] = useState("");

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const params = { month };
      if (status) params.status = status;
      if (agencyId) params.agency_id = agencyId;
      const resp = await api.get("/hotel/settlements", { params });
      setData(resp.data);
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

  const rows = useMemo(() => data?.totals || [], [data]);

  const summary = useMemo(() => {
    const entries = data?.entries || [];
    if (!entries.length) {
      return {
        currency: "TRY",
        totalNet: 0,
        openNet: 0,
        settledNet: 0,
      };
    }

    let currency = entries[0].currency || "TRY";
    let totalNet = 0;
    let openNet = 0;
    let settledNet = 0;

    for (const e of entries) {
      if (e.currency) {
        currency = e.currency;
      }
      const n = Number(e.net_amount || 0);
      totalNet += n;
      if (e.settlement_status === "open") {
        openNet += n;
      } else if (e.settlement_status === "settled") {
        settledNet += n;
      }
    }

    return { currency, totalNet, openNet, settledNet };
  }, [data]);

  async function downloadCsv() {
    try {
      const params = { month, export: "csv" };
      if (status) params.status = status;
      if (agencyId) params.agency_id = agencyId;

      const resp = await api.get("/hotel/settlements", {
        params,
        responseType: "blob",
      });

      const blob = new Blob([resp.data], { type: "text/csv;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl border bg-card shadow-sm p-4 space-y-1">
          <div className="text-xs text-muted-foreground">Bu ay kazandığın</div>
          <div className="text-lg font-semibold">
            {formatMoney(summary.totalNet, summary.currency)}
          </div>
        </div>
        <div className="rounded-2xl border bg-card shadow-sm p-4 space-y-1">
          <div className="text-xs text-muted-foreground">Bu ay tahsil edilecek</div>
          <div className="text-lg font-semibold">
            {formatMoney(summary.openNet, summary.currency)}
          </div>
        </div>
        <div className="rounded-2xl border bg-card shadow-sm p-4 space-y-1">
          <div className="text-xs text-muted-foreground">Ödenen</div>
          <div className="text-lg font-semibold">
            {formatMoney(summary.settledNet, summary.currency)}
          </div>
        </div>
      </div>


      const a = document.createElement("a");
      a.href = url;
      a.download = `hotel-settlements-${month}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Mutabakat</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Seçtiğiniz ay için acenta bazında toplam satış / komisyon / net.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Yenile
          </Button>
          <Button onClick={downloadCsv} disabled={loading}>
            <Download className="h-4 w-4 mr-2" />
            CSV
          </Button>
        </div>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Ay (YYYY-MM)</div>
            <input
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              placeholder="2026-03"
            />
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Durum</div>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">Tümü</option>
              <option value="open">open</option>
              <option value="settled">settled</option>
            </select>
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Agency ID (opsiyonel)</div>
            <input
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={agencyId}
              onChange={(e) => setAgencyId(e.target.value)}
              placeholder="agency uuid"
            />
          </div>
        </div>

        <div className="mt-3">
          <Button onClick={load} disabled={loading}>
            Filtrele
          </Button>
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
              <TableHead>Acenta</TableHead>
              <TableHead>Para Birimi</TableHead>
              <TableHead className="text-right">Brüt</TableHead>
              <TableHead className="text-right">Komisyon</TableHead>
              <TableHead className="text-right">Net (Otel Alacağı)</TableHead>
              <TableHead className="text-right">Adet</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  Kayıt yok.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r) => (
                <TableRow key={r.agency_id} className="hover:bg-accent/40">
                  <TableCell className="font-medium">
                    <div>{r.agency_name || "-"}</div>
                    <div className="text-xs text-muted-foreground">{r.agency_id}</div>
                  </TableCell>
                  <TableCell>{r.currency || "TRY"}</TableCell>
                  <TableCell className="text-right font-semibold">
                    {formatMoney(r.gross_total || 0, r.currency || "TRY")}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(r.commission_total || 0, r.currency || "TRY")}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(r.net_total || 0, r.currency || "TRY")}
                  </TableCell>
                  <TableCell className="text-right">{r.count}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
