import React from "react";
import { AlertTriangle, ArrowUpRight, CreditCard } from "lucide-react";

import { Button } from "../ui/button";

function formatDateTime(value) {
  if (!value) {
    return "—";
  }

  try {
    return new Intl.DateTimeFormat("tr-TR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return String(value);
  }
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  try {
    return new Intl.DateTimeFormat("tr-TR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    }).format(new Date(value));
  } catch {
    return String(value);
  }
}

export const BillingPaymentIssueBanner = ({ paymentIssue, portalAvailable, actionKey, onPortalOpen }) => {
  if (!paymentIssue?.has_issue) {
    return null;
  }

  const severityLabel = paymentIssue.severity === "critical" ? "Kritik" : "Uyarı";

  return (
    <div
      className="rounded-3xl border border-amber-300 bg-amber-50 px-5 py-4 text-sm text-amber-950"
      data-testid="billing-payment-issue-banner"
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-start gap-3">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-amber-300 bg-white/80 text-amber-700"
            data-testid="billing-payment-issue-icon"
          >
            <AlertTriangle className="h-5 w-5" />
          </div>

          <div className="space-y-3">
            <div className="space-y-2">
              <span
                className="inline-flex rounded-full bg-amber-200/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-900"
                data-testid="billing-payment-issue-severity"
              >
                {severityLabel}
              </span>
              <p className="text-base font-semibold" data-testid="billing-payment-issue-title">
                {paymentIssue.title || "Ödeme yönteminizi güncelleyin"}
              </p>
              <p className="text-sm leading-6" data-testid="billing-payment-issue-text">
                {paymentIssue.message}
              </p>
            </div>

            <div className="flex flex-wrap gap-2" data-testid="billing-payment-issue-meta-list">
              {paymentIssue.last_failed_amount_label ? (
                <span
                  className="rounded-full border border-amber-300/70 bg-white/80 px-3 py-1 text-xs font-medium"
                  data-testid="billing-payment-issue-amount"
                >
                  Başarısız tutar: {paymentIssue.last_failed_amount_label}
                </span>
              ) : null}

              {paymentIssue.last_failed_at ? (
                <span
                  className="rounded-full border border-amber-300/70 bg-white/80 px-3 py-1 text-xs font-medium"
                  data-testid="billing-payment-issue-last-failed-at"
                >
                  Son deneme: {formatDateTime(paymentIssue.last_failed_at)}
                </span>
              ) : null}

              {paymentIssue.grace_period_until ? (
                <span
                  className="rounded-full border border-amber-300/70 bg-white/80 px-3 py-1 text-xs font-medium"
                  data-testid="billing-payment-issue-grace-until"
                >
                  Son gün: {formatDate(paymentIssue.grace_period_until)}
                </span>
              ) : null}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 lg:justify-end">
          <Button
            onClick={() => void onPortalOpen()}
            disabled={actionKey === "portal" || !portalAvailable}
            className="rounded-2xl bg-amber-900 text-white hover:bg-amber-950"
            data-testid="billing-payment-issue-cta"
          >
            <CreditCard className="mr-2 h-4 w-4" />
            {actionKey === "portal" ? "Yönlendiriliyor..." : paymentIssue.cta_label || "Ödeme Yöntemini Güncelle"}
          </Button>

          {paymentIssue.invoice_hosted_url ? (
            <a
              href={paymentIssue.invoice_hosted_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center justify-center rounded-2xl border border-amber-400 bg-white px-4 text-sm font-medium text-amber-950 transition-colors hover:bg-amber-100"
              data-testid="billing-payment-issue-invoice-link"
            >
              Son faturayı aç
              <ArrowUpRight className="ml-2 h-4 w-4" />
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
};