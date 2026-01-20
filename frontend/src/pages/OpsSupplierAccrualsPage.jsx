import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { RefreshCw, AlertCircle, Filter, Link as LinkIcon } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";

function formatDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString();
  } catch (e) {
    return String(value);
  }
}

function formatMoney(value, currency) {
  const v = Number(value || 0);
  const cur = currency || "EUR";
  return `${v.toFixed(2)} ${cur}`;
}

const STATUS_LABELS = {
  accrued: { label: "Accrued", variant: "outline" },
  adjusted: { label: "Adjusted", variant: "secondary" },
  in_settlement: { label: "In settlement", variant: "default" },
  settled: { label: "Settled", variant: "outline" },
  reversed: { label: "Reversed", variant: "destructive" },
};

function StatusBadge({ status }) {
  if (!status) return null;
  const cfg = STATUS_LABELS[status] || { label: status, variant: "outline" };
  return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
}

export default function OpsSupplierAccrualsPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [supplierId, setSupplierId] = useState(searchParams.get("supplier_id") || "");
  const [status, setStatus] = useState(searchParams.get("status") || "");

  const totalNet = useMemo(
    () => items.reduce((sum, it) => sum + Number(it.net_payable || 0), 0),
    [items],
  );

  async function load() {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (supplierId) params.supplier_id = supplierId;
      if (status) params.status = status;

      const resp = await api.get("/ops/finance/supplier-accruals", { params });
      setItems(resp.data?.items || []);
    } catch (e) {
      setError(apiErrorMessage(e));
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleApplyFilters = () => {
    const next = {};
    if (supplierId) next.supplier_id = supplierId;
    if (status) next.status = status;
    setSearchParams(next);
    load();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Supplier accruals (Ops)"
        subtitle="Bu ekran, tedarikçi bazlı accrual satırlarını ve settlement run’lar ile ilişkisini görmeniz için tasarlanmıştır."
      />

      {error && !loading && (
        <ErrorState
          title="Accrual listesi yüklenemedi"
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
                <CardTitle className="text-sm flex items-center gap-2">
                  <Filter className="h-4 w-4" /> Filtreler
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  Tedarikçi ID ve durum filtresiyle accrual listesini daraltın. Bu liste hanya ops/debug amaçlıdır ve
                  settlement run’larınızı besleyen ham veriyi gösterir.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={load} disabled={loading}>
                  <RefreshCw className="h-3 w-3 mr-1" /> Yenile
                </Button>
                <Button size="sm" onClick={handleApplyFilters} disabled={loading}>
                  Filtreyi uygula
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Tedarikçi ID</div>
                  <Input
                    value={supplierId}
                    onChange={(e) => setSupplierId(e.target.value)}
                    placeholder="supplier uuid"
                    className="h-9 text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Durum</div>
                  <select
                    className="h-9 rounded-md border bg-background px-3 text-xs"
                    value={status}
                    onChange={(e) => setStatus(e.target.value)}
                  >
                    <option value="">Tümü</option>
                    <option value="accrued">Accrued</option>
                    <option value="adjusted">Adjusted</option>
                    <option value="in_settlement">In settlement</option>
                    <option value="settled">Settled</option>
                    <option value="reversed">Reversed</option>
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="min-h-[320px]">
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-sm">Accrual listesi</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Her satır, belirli bir booking için hesaplanan supplier accrual kaydını temsil eder.
                </p>
              </div>
              <div className="text-[11px] text-muted-foreground flex flex-col items-end">
                <span>{items.length} accrual</span>
                <span>Toplam net ödenecek: {formatMoney(totalNet, items[0]?.currency || "EUR")}</span>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto border-t">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Accrual</TableHead>
                      <TableHead className="text-xs">Booking</TableHead>
                      <TableHead className="text-xs">Tedarikçi</TableHead>
                      <TableHead className="text-xs">Para birimi</TableHead>
                      <TableHead className="text-xs text-right">Net ödenecek</TableHead>
                      <TableHead className="text-xs">Durum</TableHead>
                      <TableHead className="text-xs">Accrued at</TableHead>
                      <TableHead className="text-xs">Settlement run</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      <TableRow>
                        <TableCell colSpan={8} className="py-10 text-center text-sm text-muted-foreground">
                          Yükleniyor...
                        </TableCell>
                      </TableRow>
                    ) : items.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="py-10">
                          <EmptyState
                            title="Kayıt yok"
                            description="Filtrelere göre supplier accrual bulunamadı."
                          />
                        </TableCell>
                      </TableRow>
                    ) : (
                      items.map((it) => (
                        <TableRow key={it.accrual_id} className="hover:bg-accent/40">
                          <TableCell className="text-[11px] font-mono truncate max-w-[160px]">
                            {it.accrual_id}
                          </TableCell>
                          <TableCell className="text-[11px] font-mono truncate max-w-[140px]">
                            {it.booking_id || "-"}
                          </TableCell>
                          <TableCell className="text-[11px] font-mono truncate max-w-[140px]">
                            {it.supplier_id || "-"}
                          </TableCell>
                          <TableCell className="text-[11px]">{it.currency || "EUR"}</TableCell>
                          <TableCell className="text-[11px] text-right">
                            {formatMoney(it.net_payable, it.currency)}
                          </TableCell>
                          <TableCell className="text-[11px]">
                            <StatusBadge status={it.status} />
                          </TableCell>
                          <TableCell className="text-[11px]">{formatDate(it.accrued_at)}</TableCell>
                          <TableCell className="text-[11px]">
                            {it.settlement_id ? (
                              <button
                                type="button"
                                className="inline-flex items-center gap-1 text-[11px] text-primary underline-offset-2 hover:underline"
                                onClick={() =>
                                  window.location.assign(
                                    `/app/admin/finance/settlement-runs/${it.settlement_id}`,
                                  )
                                }
                              >
                                <LinkIcon className="h-3 w-3" />
                                {String(it.settlement_id).slice(0, 8)}...
                              </button>
                            ) : (
                              <span className="text-muted-foreground text-[11px]">-</span>
                            )}
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
                Bu ekran, Agentis seviyesinde bir finans omurgasında beklenen supplier accrual görünürlüğünü sağlar:
                settlement run’larınızı besleyen ham kayıtlara şeffaf erişim.
              </p>
              <ul className="list-disc list-inside space-y-1">
                <li>
                  Ops ekipleri, belirli bir tedarikçi için hangi booking’lerin hangi net ödenecek tutarı ürettiğini
                  görebilir.
                </li>
                <li>
                  <strong>Durum</strong> ve <strong>settlement_id</strong> sayesinde accrual → run → ödeme zinciri takip
                  edilebilir.
                </li>
                <li>
                  "In settlement" durumundaki accrual’lar, ilgili settlement run detayı ekranına bağlanarak incelenebilir.
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
