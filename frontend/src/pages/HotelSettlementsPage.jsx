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

function currentMonth() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

function settlementBadge(status) {
  const s = String(status || "").trim().toLowerCase();
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

export default function HotelSettlementsPage() {
  const [month, setMonth] = useState(currentMonth());
  const [status, setStatus] = useState("");
  const [agencyId, setAgencyId] = useState("");

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

      {/* Agency Net Distribution Chart */}
      {rows.length > 0 && (
        <div className="rounded-2xl border bg-card shadow-sm p-4 space-y-2">
          <div className="text-sm font-medium">Acenta bazlı net dağılım (bu ay)</div>
          <div className="text-xs text-muted-foreground">
            Çubuk uzunluğu, seçili ay için her acentanın net tutarına (otelin alacağı) göre orantılıdır.
          </div>
          <div className="mt-2 space-y-2">
            {(() => {
              const maxNet = rows.reduce(
                (max, r) => Math.max(max, Number(r.net_total || 0)),
                0
              );
              return rows.map((r) => {
                const net = Number(r.net_total || 0);
                const ratio = maxNet > 0 ? net / maxNet : 0;
                const width = `${10 + ratio * 90}%`;
                return (
                  <div key={r.agency_id} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium truncate mr-2">
                        {r.agency_name || "-"}
                      </span>
                      <span className="text-muted-foreground">
                        {formatMoney(net, r.currency || "TRY")}
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary/70"
                        style={{ width }}
                      />
                    </div>
                  </div>
                );
              });
            })()}
          </div>
        </div>
      )}

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Durum</TableHead>
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
                <TableRow key={r.agency_id} className="hover:bg-accent/40">
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
                  <TableCell className="text-right space-x-2">
                    <Button
                      size="xs"
                      variant="outline"
                      data-testid="hotel-settlement-confirm-button"
                      disabled={r.status === "closed" || r.status === "disputed"}
                      title={r.status === "closed" ? "Mutabakat kapandı" : undefined}
                      onClick={async () => {
                        try {
                          setActionLoading(true);
                          await api.post(`/agency/settlements/${r.settlement_id || r.id || r._id}/confirm`);
                          await load();
                        } catch (e) {
                          setError(apiErrorMessage(e));
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
                      data-testid="hotel-settlement-dispute-button"
                      disabled={r.status === "closed" || r.status === "disputed"}
                      title={r.status === "closed" ? "Mutabakat kapandı" : undefined}
                      onClick={() => {
                        setActiveSettlement(r);
                        setDisputeReason("");
                        setDisputeOpen(true);
                      }}
                    >
                      İtiraz
                    </Button>
                  </TableCell>
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
            <label className="text-xs text-muted-foreground" htmlFor="hotel-dispute-reason">
              İtiraz nedeni
            </label>
            <textarea
              id="hotel-dispute-reason"
              data-testid="hotel-settlement-dispute-reason"
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
              data-testid="hotel-settlement-dispute-submit"
              disabled={!disputeReason || actionLoading || !activeSettlement}
              onClick={async () => {
                if (!activeSettlement) return;
                try {
                  setActionLoading(true);
                  const id = activeSettlement.settlement_id || activeSettlement.id || activeSettlement._id;
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
    </div>
  );
}
