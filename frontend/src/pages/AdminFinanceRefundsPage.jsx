import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { toast } from "../components/ui/sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";

import { Loader2, AlertCircle, Clipboard } from "lucide-react";

function StatusBadge({ status }) {
  if (!status) return <Badge variant="outline">-</Badge>;

  switch (status) {
    case "open":
      return <Badge variant="outline">Açık</Badge>;
    case "pending_approval_1":
    case "pending_approval":
      return <Badge variant="outline">1. onay bekliyor</Badge>;
    case "pending_approval_2":
      return <Badge variant="outline">2. onay bekliyor</Badge>;
    case "approved":
      return <Badge variant="secondary">Onaylandı</Badge>;
    case "paid":
      return <Badge variant="secondary">Ödendi</Badge>;
    case "rejected":
      return (
        <Badge variant="destructive" className="gap-1">
          Reddedildi
        </Badge>
      );
    case "closed":
      return <Badge variant="secondary">Kapalı</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function RefundQueueList({
  items,
  statusFilter,
  limit,
  onChangeStatus,
  onChangeLimit,
  selectedCaseId,
  onSelectCase,
}) {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-medium">İade Kuyruğu</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Ops ekibi için açık iade case listesi.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Durum</div>
              <select
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={statusFilter}
                onChange={(e) => onChangeStatus(e.target.value)}
              >
                <option value="all">Tümü</option>
                <option value="open">Açık / Beklemede</option>
                <option value="closed">Kapalı</option>
              </select>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Limit</div>
              <Input
                className="h-8 w-20 text-xs"
                type="number"
                min={1}
                max={200}
                value={limit}
                onChange={(e) => onChangeLimit(Number(e.target.value) || 50)}
              />
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <EmptyState
            title="Henüz refund case yok"
            description="Bu ortamda refund akışı henüz veri üretmemiş olabilir."
          />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Case</TableHead>
                  <TableHead className="text-xs">Agency</TableHead>
                  <TableHead className="text-xs">Booking</TableHead>
                  <TableHead className="text-xs">Booking Status</TableHead>
                  <TableHead className="text-xs text-right">Requested</TableHead>
                  <TableHead className="text-xs text-right">Refundable</TableHead>
                  <TableHead className="text-xs text-right">Penalty</TableHead>
                  <TableHead className="text-xs">Status</TableHead>
                  <TableHead className="text-xs">Decision</TableHead>
                  <TableHead className="text-xs">Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((it) => (
                  <TableRow
                    key={it.case_id}
                    className={
                      "cursor-pointer hover:bg-muted/40 " +
                      (selectedCaseId === it.case_id ? "bg-muted" : "")
                    }
                    onClick={() => onSelectCase(it.case_id)}
                  >
                    <TableCell className="text-xs font-mono truncate max-w-[120px]">
                      {it.case_id}
                    </TableCell>
                    <TableCell className="text-xs truncate max-w-[140px]">
                      {it.agency_name || it.agency_id}
                    </TableCell>
                    <TableCell className="text-xs font-mono truncate max-w-[120px]">
                      {it.booking_id}
                    </TableCell>
                    <TableCell className="text-xs">
                      {it.booking_status ? (
                        <Badge variant="outline">{it.booking_status}</Badge>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {it.requested_amount != null ? it.requested_amount.toFixed(2) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {it.computed_refundable != null ? it.computed_refundable.toFixed(2) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {it.computed_penalty != null ? it.computed_penalty.toFixed(2) : "-"}
                    </TableCell>
                    <TableCell className="text-xs">
                      <StatusBadge status={it.status} />
                    </TableCell>
                    <TableCell className="text-xs">
                      {it.decision || "-"}
                    </TableCell>
                    <TableCell className="text-xs">
                      {it.updated_at
                        ? new Date(it.updated_at).toLocaleString()
                        : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RefundApproveDialog({ open, onOpenChange, caseData, onApproved }) {
  const [amount, setAmount] = useState("");
  const [paymentRef, setPaymentRef] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const refundable = caseData?.computed?.refundable ?? 0;

  useEffect(() => {
    if (open && refundable) {
      setAmount(String(refundable));
    }
  }, [open, refundable]);

  const onSubmit = async () => {
    const parsed = parseFloat(amount);
    if (!parsed || parsed <= 0 || parsed > refundable + 1e-6) {
      toast({
        title: "Onaylanan tutar geçersiz",
        description: `Tutar 0'dan büyük ve iade edilebilir tutardan ( ${refundable.toFixed(2)} ) küçük veya eşit olmalıdır.`,
        variant: "destructive",
      });
      return;
    }
    try {
      setSubmitting(true);
      await api.post(`/ops/finance/refunds/${caseData.case_id}/approve`, {
        approved_amount: parsed,
        payment_reference: paymentRef || null,
      });
      toast({ title: "İade onaylandı" });
      onApproved();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Onaylama başarısız", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Approve refund</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="text-xs text-muted-foreground">
            Refundable (computed): <strong>{refundable.toFixed(2)}</strong>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Onaylanan tutar</div>
            <Input
              type="number"
              min={0}
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Ödeme referansı (opsiyonel)</div>
            <Input
              type="text"
              value={paymentRef}
              onChange={(e) => setPaymentRef(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            İptal
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Onayla
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MiniRefundHistory({ bookingId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!bookingId) {
      setItems([]);
      setError("");
      return;
    }
    let cancelled = false;
    const run = async () => {
      try {
        setLoading(true);
        setError("");
        const resp = await api.get("/ops/finance/refunds", {
          params: { booking_id: bookingId, status: "closed", limit: 5 },
        });
        if (cancelled) return;
        setItems(resp.data?.items || []);
      } catch (e) {
        if (cancelled) return;
        setError("Liste yfklenemedi");
        setItems([]);
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [bookingId]);

  if (!bookingId) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Yfkleniyor...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-destructive">
        <AlertCircle className="h-3 w-3" />
        <span>{error}</span>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="text-xs text-muted-foreground">
        Bu booking icin kapal refund yok.
      </div>
    );
  }

  return (
    <div className="space-y-1 text-xs">
      {items.map((it) => (
        <div
          key={it.case_id}
          className="flex flex-wrap items-center justify-between gap-2 border-b last:border-0 py-1"
        >
          <div className="flex flex-col gap-0.5">
            <div className="text-[11px] text-muted-foreground">
              {it.updated_at
                ? new Date(it.updated_at).toLocaleString()
                : "-"}
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant={
                  it.decision === "approved"
                    ? "default"
                    : it.decision === "rejected"
                    ? "destructive"
                    : "secondary"
                }
                className="text-[10px] px-1 py-0"
              >
                {it.decision || "-"}
              </Badge>
              {(() => {
                const amount =
                  it.approved_amount ?? it.requested_amount ?? null;
                if (amount == null) return null;
                return (
                  <span>
                    {Number(amount).toFixed(2)} {it.currency || ""}
                  </span>
                );
              })()}
            </div>
          </div>
          <button
            type="button"
            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(it.case_id);
              } catch (e) {
                console.error("copy case_id failed", e);
              }
            }}
          >
            <Clipboard className="h-3 w-3" />
            <span className="font-mono truncate max-w-[120px]">{it.case_id}</span>
          </button>
        </div>
      ))}
    </div>
  );
}

function RefundRejectDialog({ open, onOpenChange, caseData, onRejected }) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) setReason("");
  }, [open]);

  const onSubmit = async () => {
    try {
      setSubmitting(true);
      await api.post(`/ops/finance/refunds/${caseData.case_id}/reject`, {
        reason: reason || null,
      });
      toast({ title: "Refund rejected" });
      onRejected();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Reject failed", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reject refund</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Reason</div>
            <Input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Ops reason (optional)"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Reject
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RefundDetailPanel({
  caseData,
  bookingFinancials,
  loading,
  onRefresh,
  onOpenApprove,
  onOpenReject,
}) {
  if (loading) {
    return (
      <Card className="h-full flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </Card>
    );
  }

  if (!caseData) {
    return (
      <Card className="h-full flex items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Soldan bir refund case se1n.
        </p>
      </Card>
    );
  }

  const isOpen = caseData.status === "open" || caseData.status === "pending_approval";
  const computed = caseData.computed || {};
  const requested = caseData.requested || {};

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardTitle className="text-sm font-medium">Refund Detail</CardTitle>
          <p className="text-xs text-muted-foreground">
            Case ID: <span className="font-mono">{caseData.case_id}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Booking: <span className="font-mono">{caseData.booking_id}</span>  b7 Agency: <span className="font-mono">{caseData.agency_id}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Status: <StatusBadge status={caseData.status} />
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={onRefresh}
            >
              Refresh
            </Button>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <Button
              size="sm"
              onClick={onOpenApprove}
              disabled={!isOpen}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={onOpenReject}
              disabled={!isOpen}
            >
              Reject
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-4 text-sm">
        <div className="rounded-lg border bg-muted/40 p-3 space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Request</div>
          <div className="flex flex-wrap gap-4 text-xs">
            <div>
              <div className="text-muted-foreground">Requested</div>
              <div>{requested.amount != null ? requested.amount.toFixed(2) : "-"}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Currency</div>
              <div>{caseData.currency}</div>
            </div>
            <div className="min-w-[200px]">
              <div className="text-muted-foreground">Message</div>
              <div className="truncate" title={requested.message || "-"}>
                {requested.message || "-"}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-muted/40 p-3 space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Computed</div>
          <div className="flex flex-wrap gap-4 text-xs">
            <div>
              <div className="text-muted-foreground">Refundable</div>
              <div>{computed.refundable != null ? computed.refundable.toFixed(2) : "-"}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Penalty</div>
              <div>{computed.penalty != null ? computed.penalty.toFixed(2) : "-"}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Basis</div>
              <div>{computed.basis || "-"}</div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-muted/40 p-3 space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Booking financials</div>
          {bookingFinancials ? (
            <div className="flex flex-wrap gap-4 text-xs">
              <div>
                <div className="text-muted-foreground">Sell total</div>
                <div>{bookingFinancials.sell_total != null ? bookingFinancials.sell_total.toFixed(2) : "-"}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Refunded total</div>
                <div>{bookingFinancials.refunded_total != null ? bookingFinancials.refunded_total.toFixed(2) : "-"}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Penalty total</div>
                <div>{bookingFinancials.penalty_total != null ? bookingFinancials.penalty_total.toFixed(2) : "-"}</div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <AlertCircle className="h-3 w-3" />
              <span>Financials bulunamad1.</span>
            </div>
          )}
        </div>

        {caseData.status === "closed" && (
          <div className="rounded-lg border bg-muted/20 p-3 space-y-1">
            <div className="text-xs font-semibold text-muted-foreground">Decision</div>
            <div className="flex flex-wrap gap-4 text-xs">
              <div>
                <div className="text-muted-foreground">Decision</div>
                <div>{caseData.decision || "-"}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Approved amount</div>
                <div>
                  {caseData.approved?.amount != null
                    ? caseData.approved.amount.toFixed(2)
                    : "-"}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">By</div>
                <div>{caseData.decision_by_email || "-"}</div>
              </div>
              <div>
                <div className="text-muted-foreground">At</div>
                <div>
                  {caseData.decision_at
                    ? new Date(caseData.decision_at).toLocaleString()
                    : "-"}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Last 5 closed refunds for this booking */}
        <div className="rounded-lg border bg-muted/10 p-3 space-y-2">
          <div className="text-xs font-semibold text-muted-foreground">
            Bu booking i e7in son 5 kapal31 refund
          </div>
          <MiniRefundHistory bookingId={caseData.booking_id} />
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminFinanceRefundsPage() {
  const [list, setList] = useState([]);
  const [statusFilter, setStatusFilter] = useState("open");
  const [limit, setLimit] = useState(50);

  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState("");

  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [bookingFinancials, setBookingFinancials] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);

  const loadList = React.useCallback(async () => {
    try {
      setLoadingList(true);
      setListError("");
      const params = {};
      if (statusFilter === "open") {
        // Open bucket = open + pending_approval
        params.status = "open,pending_approval";
      } else if (statusFilter === "closed") {
        params.status = "closed";
      }
      if (limit) params.limit = limit;
      const resp = await api.get("/ops/finance/refunds", { params });
      setList(resp.data?.items || []);
    } catch (e) {
      setListError(apiErrorMessage(e));
    } finally {
      setLoadingList(false);
    }
  }, [limit, statusFilter]);

  const loadDetail = React.useCallback(async (caseId) => {
    if (!caseId) return;
    try {
      setDetailLoading(true);
      setCaseData(null);
      setBookingFinancials(null);
      const resp = await api.get(`/ops/finance/refunds/${caseId}`);
      const data = resp.data;
      setCaseData(data);

      if (data.booking_id) {
        try {
          const finResp = await api.get(
            `/ops/finance/bookings/${data.booking_id}/financials`
          );
          setBookingFinancials(finResp.data || null);
        } catch (e) {
          console.error("booking_financials fetch failed", e);
          setBookingFinancials(null);
        }
      }
    } catch (e) {
      toast({
        title: "Refund case load failed",
        description: apiErrorMessage(e),
        variant: "destructive",
      });
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    // load list when filters change
    loadList();
  }, [statusFilter, limit, loadList]);

  useEffect(() => {
    if (list && list.length > 0) {
      const first = list[0];
      setSelectedCaseId(first.case_id);
      loadDetail(first.case_id);
    } else {
      setSelectedCaseId(null);
      setCaseData(null);
      setBookingFinancials(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [list]);

  const onSelectCase = (caseId) => {
    setSelectedCaseId(caseId);
    loadDetail(caseId);
  };

  const onAfterDecision = async () => {
    await loadList();
    if (selectedCaseId) {
      await loadDetail(selectedCaseId);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Refund Kuyruğu"
        subtitle="Refund case kuyruğu ve ilgili booking finansal özeti."
      />

      {listError && !loadingList && (
        <ErrorState
          title="Refund listesi yüklenemedi"
          description={listError}
          onRetry={loadList}
          className="max-w-xl"
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1.8fr)] gap-4 h-[560px]">
        <div className="min-h-0">
          {loadingList ? (
            <Card className="h-full flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </Card>
          ) : (
            <RefundQueueList
              items={list}
              statusFilter={statusFilter}
              limit={limit}
              onChangeStatus={setStatusFilter}
              onChangeLimit={setLimit}
              selectedCaseId={selectedCaseId}
              onSelectCase={onSelectCase}
            />
          )}
        </div>
        <div className="min-h-0">
          <RefundDetailPanel
            caseData={caseData}
            bookingFinancials={bookingFinancials}
            loading={detailLoading}
            onRefresh={() => {
              if (selectedCaseId) loadDetail(selectedCaseId);
            }}
            onOpenApprove={() => setApproveOpen(true)}
            onOpenReject={() => setRejectOpen(true)}
          />
        </div>
      </div>

      <RefundApproveDialog
        open={approveOpen}
        onOpenChange={setApproveOpen}
        caseData={caseData}
        onApproved={onAfterDecision}
      />

      <RefundRejectDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        caseData={caseData}
        onRejected={onAfterDecision}
      />
    </div>
  );
}
