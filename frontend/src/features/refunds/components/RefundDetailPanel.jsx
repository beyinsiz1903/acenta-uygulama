import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { Loader2, AlertCircle } from "lucide-react";
import { RefundStatusBadge } from "./RefundBadges";
import { RefundDocumentsSection } from "./RefundDocuments";
import { RefundTasksSection } from "./RefundTasks";
import { MiniRefundHistory } from "./MiniRefundHistory";

export function RefundDetailPanel({
  caseData,
  bookingFinancials,
  loading,
  onRefresh,
  onOpenApproveStep1,
  onOpenApproveStep2,
  onOpenReject,
  onOpenMarkPaid,
  onCloseCase,
}) {
  if (loading) {
    return (
      <Card className="h-full flex items-center justify-center" data-testid="refund-detail-loading">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </Card>
    );
  }

  if (!caseData) {
    return (
      <Card className="h-full flex items-center justify-center" data-testid="refund-detail-empty">
        <p className="text-sm text-muted-foreground">Soldan bir refund case secin.</p>
      </Card>
    );
  }

  const status = caseData.status;
  const isOpen = status === "open" || status === "pending_approval" || status === "pending_approval_1";
  const isPendingStep2 = status === "pending_approval_2";
  const isApproved = status === "approved";
  const isPaid = status === "paid";
  const isRejected = status === "rejected";
  const isClosed = status === "closed";
  const computed = caseData.computed || {};
  const requested = caseData.requested || {};

  return (
    <Card className="h-full flex flex-col" data-testid="refund-detail-panel">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardTitle className="text-sm font-medium">Refund Detail</CardTitle>
          <p className="text-xs text-muted-foreground">
            Case ID: <span className="font-mono">{caseData.case_id}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Booking: <span className="font-mono">{caseData.booking_id}</span>  Agency: <span className="font-mono">{caseData.agency_id}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Status: <RefundStatusBadge status={caseData.status} />
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Button size="sm" variant="outline" onClick={onRefresh} data-testid="refresh-detail-btn">Yenile</Button>
          <div className="flex flex-wrap items-center gap-2 mt-2 text-xs">
            <Button size="sm" onClick={onOpenApproveStep1} disabled={!isOpen || isClosed} data-testid="open-approve-step1">1. Onay</Button>
            <Button size="sm" variant="outline" onClick={onOpenApproveStep2} disabled={!isPendingStep2 || isClosed} data-testid="open-approve-step2">2. Onay</Button>
            <Button size="sm" variant="secondary" onClick={onOpenMarkPaid} disabled={!isApproved || isClosed} data-testid="open-mark-paid">Odendi</Button>
            <Button size="sm" variant="outline" onClick={onOpenReject} disabled={isClosed} data-testid="open-reject">Reddet</Button>
            <Button size="sm" variant="ghost" onClick={onCloseCase} disabled={!(isPaid || isRejected) || isClosed} data-testid="close-case-btn">Kapat</Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-4 text-sm">
        {/* Request */}
        <div className="rounded-lg border bg-muted/40 p-3 space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Request</div>
          <div className="flex flex-wrap gap-4 text-xs">
            <div><div className="text-muted-foreground">Requested</div><div>{requested.amount != null ? requested.amount.toFixed(2) : "-"}</div></div>
            <div><div className="text-muted-foreground">Currency</div><div>{caseData.currency}</div></div>
            <div className="min-w-[200px]"><div className="text-muted-foreground">Message</div><div className="truncate" title={requested.message || "-"}>{requested.message || "-"}</div></div>
          </div>
        </div>

        {/* Computed */}
        <div className="rounded-lg border bg-muted/40 p-3 space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Computed</div>
          <div className="flex flex-wrap gap-4 text-xs">
            <div><div className="text-muted-foreground">Iade Edilebilir</div><div>{computed.refundable != null ? computed.refundable.toFixed(2) : "-"}</div></div>
            <div><div className="text-muted-foreground">Penalty</div><div>{computed.penalty != null ? computed.penalty.toFixed(2) : "-"}</div></div>
            <div><div className="text-muted-foreground">Basis</div><div>{computed.basis || "-"}</div></div>
          </div>
        </div>

        {/* Booking financials */}
        <div className="rounded-lg border bg-muted/40 p-3 space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Booking financials</div>
          {bookingFinancials ? (
            <div className="flex flex-wrap gap-4 text-xs">
              <div><div className="text-muted-foreground">Sell total</div><div>{bookingFinancials.sell_total != null ? bookingFinancials.sell_total.toFixed(2) : "-"}</div></div>
              <div><div className="text-muted-foreground">Refunded total</div><div>{bookingFinancials.refunded_total != null ? bookingFinancials.refunded_total.toFixed(2) : "-"}</div></div>
              <div><div className="text-muted-foreground">Penalty total</div><div>{bookingFinancials.penalty_total != null ? bookingFinancials.penalty_total.toFixed(2) : "-"}</div></div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <AlertCircle className="h-3 w-3" /><span>Booking icin finansal ozet bulunamadi.</span>
            </div>
          )}
        </div>

        {/* Decision (when closed) */}
        {isClosed && (
          <div className="rounded-lg border bg-muted/20 p-3 space-y-1">
            <div className="text-xs font-semibold text-muted-foreground">Decision</div>
            <div className="flex flex-wrap gap-4 text-xs">
              <div><div className="text-muted-foreground">Decision</div><div>{caseData.decision || "-"}</div></div>
              <div><div className="text-muted-foreground">Approved amount</div><div>{caseData.approved?.amount != null ? caseData.approved.amount.toFixed(2) : "-"}</div></div>
              <div><div className="text-muted-foreground">By</div><div>{caseData.decision_by_email || "-"}</div></div>
              <div><div className="text-muted-foreground">At</div><div>{caseData.decision_at ? new Date(caseData.decision_at).toLocaleString() : "-"}</div></div>
            </div>
          </div>
        )}

        <RefundDocumentsSection caseData={caseData} />
        <RefundTasksSection caseData={caseData} />

        <div className="rounded-lg border bg-muted/10 p-3 space-y-2">
          <div className="text-xs font-semibold text-muted-foreground">Bu booking icin son 5 kapali refund</div>
          <MiniRefundHistory bookingId={caseData.booking_id} />
        </div>
      </CardContent>
    </Card>
  );
}
