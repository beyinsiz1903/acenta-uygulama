import React, { useEffect, useMemo, useState } from "react";

import { api, apiErrorMessage } from "../lib/api";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { RefreshCw } from "lucide-react";

function formatMoney(value, currency) {
  const v = Number(value || 0);
  const cur = currency || "EUR";
  return `${v.toFixed(2)} ${cur}`;
}

export default function AdminSupplierSettlementBridgePage() {
  const [currency, setCurrency] = useState("EUR");
  const [supplierFilter, setSupplierFilter] = useState("");

  const [payableSummary, setPayableSummary] = useState(null);
  const [settlementRuns, setSettlementRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [payableRes, runsRes] = await Promise.all([
        api.get("/ops/finance/suppliers/payable-summary", { params: { currency } }),
        api.get("/ops/finance/settlements", { params: { currency } }),
      ]);

      setPayableSummary(payableRes.data || null);
      setSettlementRuns(runsRes.data?.items || []);
    } catch (e) {
      setError(apiErrorMessage(e));
      setPayableSummary(null);
      setSettlementRuns([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const merged = useMemo(() => {
    if (!payableSummary) return [];
    const map = new Map();

    for (const item of payableSummary.items || []) {
      if (supplierFilter && !String(item.supplier_id).includes(supplierFilter)) continue;
      map.set(item.supplier_id, {
        supplier_id: item.supplier_id,
        supplier_name: item.supplier_name,
        currency: item.currency,
        payable_balance: Number(item.balance || 0),
        open_settlements_total: 0,
        paid_total: 0,
      });
    }

    for (const run of settlementRuns || []) {
      if (run.currency !== currency) continue;
      if (supplierFilter && !String(run.supplier_id).includes(supplierFilter)) continue;

      const key = run.supplier_id;
      if (!map.has(key)) {
        map.set(key, {
          supplier_id: run.supplier_id,
          supplier_name: "Unknown",
          currency: run.currency,
          payable_balance: 0,
          open_settlements_total: 0,
          paid_total: 0,
        });
      }

      const row = map.get(key);
      const totalNet = Number(run.totals?.total_net_payable || 0);
      if (run.status === "draft" || run.status === "approved") {
        row.open_settlements_total += totalNet;
      } else if (run.status === "paid") {
        row.paid_total += totalNet;
      }
    }

    return Array.from(map.values()).sort((a, b) => b.payable_balance - a.payable_balance);
  }, [payableSummary, settlementRuns, currency, supplierFilter]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Supplier Settlement Bridge"
        subtitle="Supplier payable bakiyeleri, açık settlement run'lar ve ödenmiş tutarların tek ekranda özetlendiği mini-dashboard."
      />

      {error && !loading && (
        <ErrorState
          title="Veriler yüklenemedi"
          description={error}
          onRetry={load}
          className="max-w-xl"
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] gap-4">
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <div className="space-y-1">
                <CardTitle className="text-sm">Filtreler</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Para birimi ve tedarikçi ID filtresiyle supplier settlement köprüsünü daraltın.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={load}
                  disabled={loading}
                >
                  <RefreshCw className="h-3 w-3 mr-1" /> Yenile
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Para birimi</div>
                  <Input
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                    className="h-9 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Tedarikçi ID (opsiyonel)</div>
                  <Input
                    value={supplierFilter}
                    onChange={(e) => setSupplierFilter(e.target.value)}
                    placeholder="supplier uuid"
                    className="h-9 text-xs"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="min-h-[320px]">
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-sm">Supplier settlement köprüsü</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Her satır, bir tedarikçi için ledger bakiyesi, açık settlement run toplamı ve ödenmiş settlement
                  toplamını gösterir.
                </p>
              </div>
              <div className="text-[11px] text-muted-foreground flex flex-col items-end">
                <span>{merged.length} tedarikçi</span>
                {payableSummary && (
                  <span>Toplam payable: {formatMoney(payableSummary.total_payable, payableSummary.currency)}</span>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto border-t">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Tedarikçi</TableHead>
                      <TableHead className="text-xs">Para birimi</TableHead>
                      <TableHead className="text-xs text-right">Ledger payable</TableHead>
                      <TableHead className="text-xs text-right">Açık settlement toplamı</TableHead>
                      <TableHead className="text-xs text-right">Ödenmiş settlement toplamı</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      <TableRow>
                        <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                          Yükleniyor...
                        </TableCell>
                      </TableRow>
                    ) : merged.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                          Görüntülenecek tedarikçi bulunamadı.
                        </TableCell>
                      </TableRow>
                    ) : (
                      merged.map((row) => (
                        <TableRow key={row.supplier_id} className="hover:bg-accent/40">
                          <TableCell className="text-[11px]">
                            <div className="flex flex-col">
                              <span className="font-mono truncate max-w-[160px]">{row.supplier_id}</span>
                              <span className="text-[11px] text-muted-foreground truncate max-w-[200px]">
                                {row.supplier_name}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell className="text-[11px]">{row.currency}</TableCell>
                          <TableCell className="text-[11px] text-right">
                            {formatMoney(row.payable_balance, row.currency)}
                          </TableCell>
                          <TableCell className="text-[11px] text-right">
                            {formatMoney(row.open_settlements_total, row.currency)}
                          </TableCell>
                          <TableCell className="text-[11px] text-right">
                            {formatMoney(row.paid_total, row.currency)}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Ne için kullanılır?</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground space-y-2">
              <p>
                Bu mini-dashboard, Agentis seviyesinde bir supplier settlement görünürlüğü sağlar: ledger üzerindeki
                payable bakiyesi ile settlement run yaşam döngüsünü tek ekranda birleştirir.
              </p>
              <ul className="list-disc list-inside space-y-1">
                <li>
                  Ledger payable bakiyesi, supplier hesabının güncel borcunu gösterir (account_balances üzerinden).
                </li>
                <li>
                  Açık settlement toplamı (taslak + onaylı), henüz ödemesi yapılmamış settlement run tutarlarını özetler.
                </li>
                <li>
                  Ödenmiş settlement toplamı, SETTLEMENT_PAID eventleri üzerinden kapatılmış tutarları gösterir.
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
