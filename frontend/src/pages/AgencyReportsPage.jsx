import React, { useEffect, useMemo, useState } from "react";
import { BarChart3, AlertCircle, RefreshCw, Calendar as CalendarIcon } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { formatMoney } from "../lib/format";
import { Button } from "../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function addDaysISO(base, days) {
  const d = base ? new Date(base) : new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function AgencyReportsPage() {
  const [preset, setPreset] = useState("30");
  const [dateFrom, setDateFrom] = useState(addDaysISO(todayISO(), -30));
  const [dateTo, setDateTo] = useState(todayISO());

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  function applyPreset(nextPreset) {
    setPreset(nextPreset);
    if (nextPreset === "custom") return;
    const days = Number(nextPreset || 30);
    const to = todayISO();
    const from = addDaysISO(to, -days);
    setDateFrom(from);
    setDateTo(to);
  }

  async function load() {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const resp = await api.get("/reports/agency-financial", { params });
      setData(resp.data || null);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const kpi = useMemo(() => {
    if (!data) {
      return {
        totalBookings: 0,
        totalGross: 0,
        totalCommission: 0,
        totalPaid: 0,
        totalUnpaid: 0,
      };
    }
    return {
      totalBookings: data.total_bookings || 0,
      totalGross: data.total_gross || 0,
      totalCommission: data.total_commission || 0,
      totalPaid: data.total_paid || 0,
      totalUnpaid: data.total_unpaid || 0,
    };
  }, [data]);

  const statusRows = useMemo(() => data?.by_status || [], [data]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Finansal Raporlar
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Seçilen tarih aralığında acenta bazlı finansal özet.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={load}
            disabled={loading}
            data-testid="agency-finance-refresh-button"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Yenile
          </Button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="rounded-2xl border bg-card shadow-sm p-4 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Preset</div>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={preset}
              onChange={(e) => applyPreset(e.target.value)}
              data-testid="reports-preset-select"
            >
              <option value="7">Son 7 gün</option>
              <option value="14">Son 14 gün</option>
              <option value="30">Son 30 gün</option>
              <option value="custom">Özel</option>
            </select>
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Başlangıç</div>
            <div className="relative flex items-center">
              <CalendarIcon className="h-4 w-4 text-muted-foreground absolute left-2" />
              <input
                type="date"
                className="h-10 w-full rounded-md border bg-background pl-8 pr-3 text-sm"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                data-testid="reports-date-from"
              />
            </div>
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">Bitiş</div>
            <div className="relative flex items-center">
              <CalendarIcon className="h-4 w-4 text-muted-foreground absolute left-2" />
              <input
                type="date"
                className="h-10 w-full rounded-md border bg-background pl-8 pr-3 text-sm"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                data-testid="reports-date-to"
              />
            </div>
          </div>
          <div className="grid gap-1">
            <div className="text-xs text-muted-foreground">&nbsp;</div>
            <Button onClick={load} disabled={loading} data-testid="reports-apply-button">
              Filtrele
            </Button>
          </div>
        </div>

        {error ? (
          <div className="mt-3 rounded-xl border border-destructive/50 bg-destructive/5 p-3 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
            <div className="text-sm text-foreground">{error}</div>
          </div>
        ) : null}
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border bg-card p-4 shadow-sm" data-testid="kpi-total-bookings">
          <div className="text-xs text-muted-foreground">Toplam Rezervasyon</div>
          <div className="mt-2 text-2xl font-semibold">{kpi.totalBookings}</div>
        </div>
        <div className="rounded-2xl border bg-card p-4 shadow-sm" data-testid="kpi-total-gross">
          <div className="text-xs text-muted-foreground">Toplam Brüt Satış</div>
          <div className="mt-2 text-2xl font-semibold">
            {formatMoney(kpi.totalGross || 0, "TRY")}
          </div>
        </div>
        <div className="rounded-2xl border bg-card p-4 shadow-sm" data-testid="kpi-total-commission">
          <div className="text-xs text-muted-foreground">Toplam Komisyon</div>
          <div className="mt-2 text-2xl font-semibold">
            {formatMoney(kpi.totalCommission || 0, "TRY")}
          </div>
        </div>
        <div className="rounded-2xl border bg-card p-4 shadow-sm" data-testid="kpi-paid-unpaid">
          <div className="text-xs text-muted-foreground">Tahsilat Durumu</div>
          <div className="mt-2 text-sm flex items-center justify-between">
            <span className="text-emerald-600 dark:text-emerald-400">
              Paid: {formatMoney(kpi.totalPaid || 0, "TRY")}
            </span>
            <span className="text-amber-600 dark:text-amber-400">
              Unpaid: {formatMoney(kpi.totalUnpaid || 0, "TRY")}
            </span>
          </div>
        </div>
      </div>

      {/* Breakdown table */}
      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Ödeme Durumu</TableHead>
              <TableHead className="text-right">Adet</TableHead>
              <TableHead className="text-right">Brüt</TableHead>
              <TableHead className="text-right">Komisyon</TableHead>
              <TableHead className="text-right">Net</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : statusRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Kayıt yok.
                </TableCell>
              </TableRow>
            ) : (
              statusRows.map((r) => (
                <TableRow key={r.status || "-"} className="hover:bg-accent/40">
                  <TableCell className="capitalize">{r.status || "-"}</TableCell>
                  <TableCell className="text-right">{r.count || 0}</TableCell>
                  <TableCell className="text-right">
                    {formatMoney(r.gross_total || 0, r.currency || "TRY")}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(r.commission_total || 0, r.currency || "TRY")}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(r.net_total || 0, r.currency || "TRY")}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
