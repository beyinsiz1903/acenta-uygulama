import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AlertCircle, CheckCircle2, XCircle, ArrowLeft, Loader2 } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";

function StatusBadge({ status }) {
  if (!status) return null;
  const tone = String(status).toLowerCase();
  if (tone === "draft") return <Badge variant="outline">Taslak</Badge>;
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

export default function AdminSettlementRunDetailPage() {
  const { settlementId } = useParams();
  const navigate = useNavigate();

  const [run, setRun] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [cancelReason, setCancelReason] = useState("");
  const [paymentRef, setPaymentRef] = useState("");
  const [accrualToAdd, setAccrualToAdd] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const totals = useMemo(() => {
    if (!run) return { totalItems: 0, totalNet: 0 };
    const t = run.totals || {};
    return {
      totalItems: t.total_items || 0,
      totalNet: Number(t.total_net_payable || 0),
    };
  }, [run]);

  async function load() {
    if (!settlementId) return;
    setLoading(true);
    setError("");
    try {
      const resp = await api.get(`/ops/finance/settlements/${settlementId}`);
      setRun(resp.data || null);
    } catch (e) {
      setError(apiErrorMessage(e));
      setRun(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settlementId]);

  async function handleApprove() {
    if (!run) return;
    setActionLoading(true);
    try {
      await api.post(`/ops/finance/settlements/${run.settlement_id}/approve`, {});
      await load();
    } catch (e) {
      alert(apiErrorMessage(e));
    } finally {
      setActionLoading(false);
    }
  }

  async function handleCancel() {
    if (!run) return;
    if (!cancelReason.trim()) {
      alert("Lütfen iptal sebebi girin.");
      return;
    }
    setActionLoading(true);
    try {
      await api.post(`/ops/finance/settlements/${run.settlement_id}/cancel`, {
        reason: cancelReason,
      });
      await load();
    } catch (e) {
      alert(apiErrorMessage(e));
    } finally {
      setActionLoading(false);
    }
  }

  async function handleMarkPaid() {
    if (!run) return;
    setActionLoading(true);
    try {
      await api.post(`/ops/finance/settlements/${run.settlement_id}/mark-paid`, {
        payment_reference: paymentRef || null,
      });
      await load();
    } catch (e) {
      alert(apiErrorMessage(e));
    } finally {
      setActionLoading(false);
    }
  }

  if (loading && !run) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Settlement run yükleniyor...
        </div>
      </div>
    );
  }

  if (error && !run) {
    return (
      <div className="p-6">
        <ErrorState
          title="Settlement run yüklenemedi"
          description={error}
          onRetry={load}
        />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-6">
        <ErrorState
          title="Settlement run bulunamadı"
          description="Belirtilen settlement_id için sonuç alınamadı."
          onRetry={load}
        />
      </div>
    );
  }

  const canApprove = run.status === "draft";
  const canCancel = run.status === "draft" || run.status === "approved";
  const canMarkPaid = run.status === "approved";
  const canEditItems = run.status === "draft";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settlement run detayı"
        subtitle="Bu ekran, seçili settlement run’ın satırlarını ve durum aksiyonlarını yönetmek için kullanılır."
        backButton={{
          label: "Tüm run’lara geri dön",
          onClick: () => navigate("/app/admin/finance/settlement-runs"),
          icon: ArrowLeft,
        }}
      />

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] gap-4">
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <div className="space-y-1">
                <CardTitle className="text-sm">Run özeti</CardTitle>
                <div className="text-xs text-muted-foreground flex flex-wrap gap-2">
                  <span className="font-mono">{run.settlement_id}</span>
                  <span>Supplier: {run.supplier_id}</span>
                  <span>Currency: {run.currency}</span>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1 text-right">
                <StatusBadge status={run.status} />
                <div className="text-[11px] text-muted-foreground">
                  Toplam {totals.totalItems} satır, net ödenecek {formatMoney(totals.totalNet, run.currency)}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <div>
                  <div className="font-medium text-[11px]">Oluşturulma</div>
                  <div>{formatDate(run.created_at)}</div>
                </div>
                <div>
                  <div className="font-medium text-[11px]">Onay</div>
                  <div>{formatDate(run.approved_at)}</div>
                </div>
                <div>
                  <div className="font-medium text-[11px]">Ödeme</div>
                  <div>{formatDate(run.paid_at)}</div>
                </div>
                <div>
                  <div className="font-medium text-[11px]">Durum</div>
                  <div>{run.status}</div>
                </div>
              </div>
              {run.cancel_reason && (
                <div className="mt-2 p-2 rounded-md bg-red-50 text-red-700 flex items-start gap-2">
                  <AlertCircle className="h-3 w-3 mt-0.5" />
                  <div>
                    <div className="text-[11px] font-semibold">İptal sebebi</div>
                    <div className="text-[11px] whitespace-pre-line">{run.cancel_reason}</div>
                  </div>
                </div>
              )}
              {run.payment_reference && (
                <div className="mt-1">
                  <div className="text-[11px] font-semibold">Payment reference</div>
                  <div className="text-[11px] font-mono break-all">{run.payment_reference}</div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="min-h-[260px]">
            <CardHeader>
              <CardTitle className="text-sm">Satır detayları</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto border-t">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Accrual</TableHead>
                      <TableHead className="text-xs">Booking</TableHead>
                      <TableHead className="text-xs text-right">Net ödenecek</TableHead>
                      <TableHead className="text-xs">Durum (onay anı)</TableHead>
                      <TableHead className="text-xs">Accrued at</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {!run.line_items || run.line_items.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                          Bu run için henüz satır bulunmuyor. Taslak aşamasında accrual eklenmesi gerekir.
                        </TableCell>
                      </TableRow>
                    ) : (
                      run.line_items.map((li) => (
                        <TableRow key={li.accrual_id}>
                          <TableCell className="text-[11px] font-mono truncate max-w-[160px]">
                            {li.accrual_id}
                          </TableCell>
                          <TableCell className="text-[11px] font-mono truncate max-w-[160px]">
                            {li.booking_id || "-"}
                          </TableCell>
                          <TableCell className="text-[11px] text-right">
                            {formatMoney(li.net_payable, run.currency)}
                          </TableCell>
                          <TableCell className="text-[11px]">
                            {li.status_at_approval || "-"}
                          </TableCell>
                          <TableCell className="text-[11px]">{formatDate(li.accrued_at)}</TableCell>
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
              <CardTitle className="text-sm">Durum aksiyonları</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-muted-foreground">
              <p>
                Settlement run, aşağıdaki yaşam döngüsüne sahiptir: <strong>Taslak → Onaylı → Ödendi</strong>. Taslak ve
                onaylı run’lar iptal edilebilir.
              </p>

              <div className="space-y-2">
                <div className="font-semibold text-[11px]">Taslak → Onaylı</div>
                <p>
                  Run taslak durumdayken, içindeki accrual’lar kilitlidir. Onayladığınızda, satır snapshot’ı alınır ve
                  toplamlar dondurulur.
                </p>
                <Button
                  size="sm"
                  disabled={!canApprove || actionLoading}
                  onClick={handleApprove}
                >
                  Run’u onayla
                </Button>
              </div>

              <div className="space-y-2 pt-3 border-t">
                <div className="font-semibold text-[11px]">Taslak / Onaylı → İptal</div>
                <p>
                  İptal edilen run, kilitlediği accrual’ları eski durumuna geri döndürür. Lütfen iptal sebebini ayrıntılı
                  yazın.
                </p>
                <Textarea
                  rows={3}
                  placeholder="İptal sebebi"
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  className="text-xs"
                />
                <Button
                  size="sm"
                  variant="destructive"
                  disabled={!canCancel || actionLoading}
                  onClick={handleCancel}
                >
                  Run’u iptal et
                </Button>
              </div>

              <div className="space-y-2 pt-3 border-t">
                <div className="font-semibold text-[11px]">Onaylı → Ödendi</div>
                <p>
                  Ödendi olarak işaretlediğinizde, supplier payable hesabı ile platform cash hesabı arasında
                  <strong>SETTLEMENT_PAID</strong> ledger postingi oluşturulur ve accrual’lar <strong>settled</strong>
                  durumuna geçer.
                </p>
                <Input
                  value={paymentRef}
                  onChange={(e) => setPaymentRef(e.target.value)}
                  placeholder="Ödeme referansı (örn. banka dekont no)"
                  className="text-xs"
                />
                <Button
                  size="sm"
                  disabled={!canMarkPaid || actionLoading}
                  onClick={handleMarkPaid}
                >
                  Ödendi olarak işaretle
                </Button>
              </div>

              <div className="pt-3 border-t text-[11px]">
                <p className="font-semibold mb-1">Notlar</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>Taslak durumdayken accrual ekleme/çıkarma yalnızca API üzerinden yapılabilir.</li>
                  <li>
                    Ödendi işlemi idempotenttir; aynı run için tekrar çağrıldığında yeni posting yaratılmaz, mevcut posting
                    döner.
                  </li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
