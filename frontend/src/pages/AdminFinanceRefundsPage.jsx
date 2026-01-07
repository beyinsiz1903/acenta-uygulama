import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { toast } from "../components/ui/sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
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
import { Loader2, AlertCircle } from "lucide-react";

function StatusBadge({ status }) {
  if (status === "closed") {
    return <Badge variant="secondary">Closed</Badge>;
  }
  if (status === "pending_approval") {
    return <Badge variant="outline">Pending</Badge>;
  }
  return <Badge variant="default">Open</Badge>;
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
            <CardTitle className="text-sm font-medium">Refund Queue</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Ops i50 ak151 i5in a51k refund case listesi.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Status</div>
              <select
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={statusFilter}
                onChange={(e) => onChangeStatus(e.target.value)}
              >
                <option value="all">All</option>
                <option value="open">Open</option>
                <option value="closed">Closed</option>
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
          <p className="text-sm text-muted-foreground">
            Bu filtrelerle refund case bulunamad1.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Created</TableHead>
                  <TableHead className="text-xs">Case</TableHead>
                  <TableHead className="text-xs">Booking</TableHead>
                  <TableHead className="text-xs">Agency</TableHead>
                  <TableHead className="text-xs text-right">Requested</TableHead>
                  <TableHead className="text-xs text-right">Refundable</TableHead>
                  <TableHead className="text-xs">Status</TableHead>
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
                    <TableCell className="text-xs">
                      {it.created_at ? new Date(it.created_at).toLocaleString() : "-"}
                    </TableCell>
                    <TableCell className="text-xs font-mono truncate max-w-[120px]">
                      {it.case_id}
                    </TableCell>
                    <TableCell className="text-xs font-mono truncate max-w-[120px]">
                      {it.booking_id}
                    </TableCell>
                    <TableCell className="text-xs font-mono truncate max-w-[120px]">
                      {it.agency_id}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {it.requested_amount != null ? it.requested_amount.toFixed(2) : "-"}
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      {it.refundable != null ? it.refundable.toFixed(2) : "-"}
                    </TableCell>
                    <TableCell className="text-xs">
                      <StatusBadge status={it.status} />
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
        title: "Approved amount invalid",
        description: `Amount must be > 0 and <= refundable (${refundable.toFixed(2)})`,
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
      toast({ title: "Refund approved" });
      onApproved();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Approve failed", description: apiErrorMessage(e), variant: "destructive" });
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
            <div className="text-xs text-muted-foreground">Approved amount</div>
            <Input
              type="number"
              min={0}
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Payment reference (optional)</div>
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
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Approve
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
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
      </CardContent>
    </Card>
  );
}

export default function AdminFinanceRefundsPage() {
  // NOTE: keep hooks simple; eslint exhaustive-deps is noisy here.
  // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const loadList = async () => {
    try {
      setLoadingList(true);
      setListError("");
      const params = {};
      if (statusFilter === "open") {
        // open bucket (backend will treat open + pending_approval)
        params.status = "open";
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
  };

  const loadDetail = async (caseId) => {
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
  };

  useEffect(() => {
    loadList();
  }, [statusFilter, limit]);

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
      <div>
        <h1 className="text-2xl font-bold text-foreground">Finance  b7 Refunds</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Refund case kuyru1 ve booking finansal snapshot g f6r fcn fcm fc.
        </p>
      </div>

      {listError && !loadingList && (
        <div className="flex items-center gap-2 text-destructive text-sm">
          <AlertCircle className="h-4 w-4" />
          <span>{listError}</span>
        </div>
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
