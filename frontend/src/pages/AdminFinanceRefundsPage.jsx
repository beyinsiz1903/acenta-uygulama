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
              Ops ie akf1 iin af1k refund case listesi.
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
          Soldan bir refund case see7in.
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
        <div>
          <CardTitle className="text-sm font-medium">Refund Detail</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Case ID: <span className="font-mono">{caseData.case_id}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Booking: <span className="font-mono">{caseData.booking_id}</span>  b7 Agency:{