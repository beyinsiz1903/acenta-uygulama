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
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";

const OPEN_SET = new Set(["open", "unpaid"]);
const SETTLED_SET = new Set(["settled", "paid", "closed"]);

function normalizeStatus(v) {
  return String(v || "").trim().toLowerCase();
}

function settlementBadge(status) {
  const s = normalizeStatus(status);
  switch (s) {
    case "confirmed_by_agency":
      return { label: "Acenta Onayladı", variant: "outline" };
    case "confirmed_by_hotel":
      return { label: "Otel Onayladı", variant: "outline" };
    case "closed":
      return { label: "Kapandı", variant: "default" };
    case "disputed":
      return { label: "İtiraz", variant: "destructive" };
    case "open":
    default:
      return { label: "Açık", variant: "secondary" };
  }
}

function summarizeEntriesByCurrency(entries, amountKey) {
  const byCur = new Map(); // cur -> { total, open, settled, other }
  for (const e of entries || []) {
    const cur = e.currency || "TRY";
    const existing = byCur.get(cur) || { total: 0, open: 0, settled: 0, other: 0 };
    const amount = Number(e?.[amountKey] || 0);

    existing.total += amount;
    const st = normalizeStatus(e.settlement_status);
    if (OPEN_SET.has(st)) existing.open += amount;
    else if (SETTLED_SET.has(st)) existing.settled += amount;
    else existing.other += amount;

    byCur.set(cur, existing);
  }
  return byCur;
}


function currentMonth() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

export default function AgencySettlementsPage() {
  const [month, setMonth] = useState(currentMonth());
  const [status, setStatus] = useState("");
  const [hotelId, setHotelId] = useState("");

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [activeSettlement, setActiveSettlement] = useState(null);
  const [disputeOpen, setDisputeOpen] = useState(false);
  const [disputeReason, setDisputeReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const params = { month };
      if (status) params.status = status;
      if (hotelId) params.hotel_id = hotelId;
      const resp = await api.get("/agency/settlements", { params });
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
    const byCur = summarizeEntriesByCurrency(entries, "commission_amount");
    const currencies = Array.from(byCur.keys());

    if (!entries.length) {
      return {
        isMulti: false,
        currencies: [],
        byCur,
        single: { currency: "TRY", total: 0, open: 0, settled: 0, other: 0 },
      };
    }

    if (currencies.length === 1) {
      const cur = currencies[0];
      const row = byCur.get(cur) || { total: 0, open: 0, settled: 0, other: 0 };
      return {
        isMulti: false,
        currencies,
        byCur,
        single: { currency: cur, ...row },
      };
    }

    return {
      isMulti: true,
      currencies,
      byCur,
      single: null,
    };
  }, [data]);

  async function downloadCsv() {
    try {
      const params = { month, export: "csv" };
      if (status) params.status = status;
      if (hotelId) params.hotel_id = hotelId;

      const resp = await api.get("/agency/settlements", {
        params,
        responseType: "blob",
      });

      const blob = new Blob([resp.data], { type: "text/csv;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = `agency-settlements-${month}.csv`;
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
            Seçtiğiniz ay için toplam satış / komisyon / net.
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
            <div className="text-xs text-muted-foreground">Hotel ID (opsiyonel)</div>
            <input
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={hotelId}
              onChange={(e) => setHotelId(e.target.value)}
              placeholder="hotel uuid"
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
              <TableHead>Durum</TableHead>
              <TableHead>Otel</TableHead>
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
                <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                  Kayıt yok.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r) => (
                <TableRow key={r.hotel_id} className="hover:bg-accent/40">
                  <TableCell>
                    {(() => {
                      const b = settlementBadge(r.status);
                      return (
                        <Badge
                          data-testid="settlement-status-badge"
                          variant={b.variant}
                          className="text-xs"
                        >
                          {b.label}
                        </Badge>
                      );
                    })()}
                  </TableCell>
                  <TableCell className="font-medium">
                    <div>{r.hotel_name || "-"}</div>
                    <div className="text-xs text-muted-foreground">{r.hotel_id}</div>
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

      {/* Dispute Modal */}
      <Dialog open={disputeOpen} onOpenChange={setDisputeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>İtiraz Aç</DialogTitle>
          </DialogHeader>
          <div className="mt-2">
            <label className="text-xs text-muted-foreground" htmlFor="agency-dispute-reason">
              İtiraz nedeni
            </label>
            <textarea
              id="agency-dispute-reason"
              data-testid="agency-settlement-dispute-reason"
              className="mt-1 w-full min-h-[80px] rounded-md border bg-background px-3 py-2 text-sm"
              value={disputeReason}
              onChange={(e) => setDisputeReason(e.target.value)}
            />
          </div>
          <DialogFooter className="mt-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => setDisputeOpen(false)}
            >
              Vazgeç
            </Button>
            <Button
              type="button"
              data-testid="agency-settlement-dispute-submit"
              disabled={!disputeReason || actionLoading || !activeSettlement}
              onClick={async () => {
                if (!activeSettlement) return;
                try {
                  setActionLoading(true);
                  const id = activeSettlement.id || activeSettlement._id || activeSettlement.settlement_id;
                  await api.post(`/agency/settlements/${id}/dispute`, { reason: disputeReason });
                  setDisputeOpen(false);
                  await load();
                } catch (e) {
                  setError(apiErrorMessage(e));
                } finally {
                  setActionLoading(false);
                }
              }}
            >
              Gönder
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Entries (actionable) table */}
      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Durum</TableHead>
              <TableHead>Otel</TableHead>
              <TableHead>Para Birimi</TableHead>
              <TableHead className="text-right">Brüt</TableHead>
              <TableHead className="text-right">Komisyon</TableHead>
              <TableHead className="text-right">Net</TableHead>
              <TableHead className="text-right">İşlemler</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-sm text-muted-foreground">
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : (data?.entries || []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-sm text-muted-foreground">
                  Bu ay için mutabakat kaydı yok.
                </TableCell>
              </TableRow>
            ) : (
              (data?.entries || []).map((e) => {
                const id = e.id || e._id || e.settlement_id;
                const st = normalizeStatus(e.status);
                const disabled = st === "closed" || st === "disputed";
                const badge = settlementBadge(e.status);
                return (
                  <TableRow key={id} className="hover:bg-accent/40 align-top">
                    <TableCell>
                      <Badge
                        data-testid="settlement-status-badge"
                        variant={badge.variant}
                        className="text-xs"
                      >
                        {badge.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">
                      <div>{e.hotel_name || "-"}</div>
                      <div className="text-xs text-muted-foreground">{e.hotel_id}</div>
                    </TableCell>
                    <TableCell>{e.currency || "TRY"}</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(e.gross_amount || 0, e.currency || "TRY")}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatMoney(e.commission_amount || 0, e.currency || "TRY")}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatMoney(e.net_amount || 0, e.currency || "TRY")}
                    </TableCell>
                    <TableCell className="text-right space-x-2">
                      <Button
                        size="xs"
                        variant="outline"
                        data-testid="agency-settlement-confirm-button"
                        disabled={disabled}
                        title={st === "closed" ? "Mutabakat kapandı" : undefined}
                        onClick={async () => {
                          if (!id) return;
                          try {
                            setActionLoading(true);
                            await api.post(`/agency/settlements/${id}/confirm`);
                            await load();
                          } catch (err) {
                            setError(apiErrorMessage(err));
                          } finally {
                            setActionLoading(false);
                          }
                        }}
                      >
                        Onayla
                      </Button>
                      <Button
                        size="xs"
                        variant="outline"
                        data-testid="agency-settlement-dispute-button"
                        disabled={disabled}
                        title={st === "closed" ? "Mutabakat kapandı" : undefined}
                        onClick={() => {
                          setActiveSettlement(e);
                          setDisputeReason("");
                          setDisputeOpen(true);
                        }}
                      >
                        İtiraz
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
