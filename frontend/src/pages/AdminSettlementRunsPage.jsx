import React, { useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw, AlertCircle, CheckCircle2, XCircle, Clock } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";

function StatusBadge({ status }) {
  if (!status) return null;
  const tone = String(status).toLowerCase();
  if (tone === "draft") {
    return <Badge variant="outline">Taslak</Badge>;
  }
  if (tone === "approved") {
    return (
      <Badge variant="secondary" className="flex items-center gap-1">
        <CheckCircle2 className="h-3 w-3" /> Onaylı
      </Badge>
    );
  }
  if (tone === "paid") {
    return (
      <Badge variant="default" className="flex items-center gap-1">
        <CheckCircle2 className="h-3 w-3" /> Ödendi
      </Badge>
    );
  }
  if (tone === "cancelled") {
    return (
      <Badge variant="destructive" className="flex items-center gap-1">
        <XCircle className="h-3 w-3" /> İptal
      </Badge>
    );
  }
  return <Badge variant="outline">{status}</Badge>;
}

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

function CreateSettlementDialog({ open, onOpenChange, onCreated }) {
  const [supplierId, setSupplierId] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!supplierId || !currency) {
      setError("Tedarikçi ve para birimi zorunlu.");
      return;
    }
    try {
      setSubmitting(true);
      setError("");
      await api.post("/ops/finance/settlements", {
        supplier_id: supplierId,
        currency,
        period: null,
      });
      onOpenChange(false);
      onCreated?.();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Yeni settlement run</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Tedarikçi ID</div>
            <Input
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              placeholder="supplier uuid"
            />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Para birimi</div>
            <Input
              value={currency}
              onChange={(e) => setCurrency(e.target.value.toUpperCase())}
              placeholder="EUR"
            />
          </div>
          {error && (
            <div className="flex items-center gap-2 text-xs text-destructive">
              <AlertCircle className="h-3 w-3" />
              <span>{error}</span>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            İptal
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting && <Clock className="h-4 w-4 mr-2 animate-spin" />}
            Oluştur
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminSettlementRunsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [supplierId, setSupplierId] = useState("");
  const [currency, setCurrency] = useState("");
  const [status, setStatus] = useState("");

  const [createOpen, setCreateOpen] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (supplierId) params.supplier_id = supplierId;
      if (currency) params.currency = currency;
      if (status) params.status = status;

      const resp = await api.get("/ops/finance/settlements", { params });
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

  const totals = useMemo(() => {
    let totalNet = 0;
    for (const it of items || []) {
      const net = Number(it.totals?.total_net_payable || 0);
      totalNet += net;
    }
    return {
      count: items.length,
      totalNet,
    };
  }, [items]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tedarikçi settlement runları"
        subtitle="Supplier accruals üzerinden oluşturulan settlement run listesi. Taslak → onaylı → ödenmiş yaşam döngüsünü yönetmek için kullanılır."
      />

      {error && !loading && (
        <ErrorState
          title="Settlement run listesi yüklenemedi"
          description={error}
          onRetry={load}
          className="max-w-xl"
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)] gap-4">
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <div className="space-y-1">
                <CardTitle className="text-sm">Filtreler</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Tedarikçi, para birimi ve durum filtresiyle settlement run listesini daraltın.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={load} disabled={loading}>
                  <RefreshCw className="h-3 w-3 mr-1" /> Yenile
                </Button>
                <Button size="sm" onClick={() => setCreateOpen(true)}>
                  <Plus className="h-3 w-3 mr-1" /> Yeni run
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
                  <div className="text-xs text-muted-foreground">Para birimi</div>
                  <Input
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                    placeholder="EUR"
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
                    <option value="draft">Taslak</option>
                    <option value="approved">Onaylı</option>
                    <option value="paid">Ödendi</option>
                    <option value="cancelled">İptal</option>
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="min-h-[320px]">
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-sm">Settlement run listesi</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Her satır, belirli bir tedarikçi ve para birimi için oluşturulmuş settlement run’ı temsil eder.
                </p>
              </div>
              <div className="text-xs text-muted-foreground flex flex-col items-end">
                <span>{totals.count} run</span>
                <span>Toplam net ödenecek: {formatMoney(totals.totalNet, items[0]?.currency || "EUR")}</span>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto border-t">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Tedarikçi</TableHead>
                      <TableHead className="text-xs">Para Birimi</TableHead>
                      <TableHead className="text-xs">Durum</TableHead>
                      <TableHead className="text-xs text-right">Net ödenecek</TableHead>
                      <TableHead className="text-xs">Oluşturulma</TableHead>
                      <TableHead className="text-xs">Onay</TableHead>
                      <TableHead className="text-xs">Ödeme</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      <TableRow>
                        <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                          Yükleniyor...
                        </TableCell>
                      </TableRow>
                    ) : items.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="py-10">
                          <EmptyState
                            title="Kayıt yok"
                            description="Filtrelere göre settlement run bulunamadı."
                          />
                        </TableCell>
                      </TableRow>
                    ) : (
                      items.map((it) => {
                        const net = Number(it.totals?.total_net_payable || 0);
                        return (
                          <TableRow
                            key={it.settlement_id}
                            className="hover:bg-accent/40 cursor-pointer"
                            onClick={() => window.location.assign(`/app/admin/finance/settlement-runs/${it.settlement_id}`)}
                          >
                            <TableCell className="text-xs font-mono truncate max-w-[160px]">
                              {it.supplier_id}
                            </TableCell>
                            <TableCell className="text-xs">{it.currency}</TableCell>
                            <TableCell className="text-xs">
                              <StatusBadge status={it.status} />
                            </TableCell>
                            <TableCell className="text-xs text-right">
                              {formatMoney(net, it.currency)}
                            </TableCell>
                            <TableCell className="text-xs">{formatDate(it.created_at)}</TableCell>
                            <TableCell className="text-xs">{formatDate(it.approved_at)}</TableCell>
                            <TableCell className="text-xs">{formatDate(it.paid_at)}</TableCell>
                          </TableRow>
                        );
                      })
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
                Supplier accruals üzerinden oluşturulan settlement run’lar, tedarikçilere yapılacak toplu ödemelerin
                kaydını ve onay sürecini yönetmek için kullanılır.
              </p>
              <ul className="list-disc list-inside space-y-1">
                <li>
                  <strong>Taslak</strong>: Accrual ekleme/çıkarma yapılabilen çalışma aşaması.
                </li>
                <li>
                  <strong>Onaylı</strong>: Artık içerik kilitlidir, sadece ödeme beklenir.
                </li>
                <li>
                  <strong>Ödendi</strong>: Gerçek ödeme yapıldı, payment_reference ve paid_at alanları dolar.
                </li>
                <li>
                  <strong>İptal</strong>: Hatalı/iptal edilen run’lar için kullanılır.
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>

      <CreateSettlementDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={load}
      />
    </div>
  );
}
