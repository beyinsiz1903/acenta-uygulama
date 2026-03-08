import React from "react";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";

import { Button } from "../ui/button";

export const BillingPlanCard = ({
  plan,
  billingCycle,
  isCurrent,
  loading,
  disabled,
  onSelect,
}) => {
  const pricing = plan.pricing?.[billingCycle] || plan.pricing?.monthly;
  const isEnterprise = plan.key === "enterprise";

  return (
    <article
      className={`relative flex h-full flex-col rounded-[1.9rem] border p-6 shadow-sm ${plan.isPopular ? "border-[#f3722c] bg-[#fff8f2]" : "border-border/60 bg-card/85"}`}
      data-testid={`billing-plan-card-${plan.key}`}
    >
      {plan.isPopular ? (
        <div className="absolute right-5 top-5 rounded-full bg-[#f3722c] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-white" data-testid={`billing-plan-card-badge-${plan.key}`}>
          Önerilen
        </div>
      ) : null}

      <div className="space-y-4">
        <div>
          <h3 className="text-2xl font-bold tracking-tight text-foreground" data-testid={`billing-plan-card-title-${plan.key}`}>
            {plan.label}
          </h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground" data-testid={`billing-plan-card-description-${plan.key}`}>
            {plan.description}
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-2" data-testid={`billing-plan-card-price-wrap-${plan.key}`}>
          <span className="text-4xl font-bold tracking-tight text-foreground" data-testid={`billing-plan-card-price-${plan.key}`}>
            {pricing?.label}
          </span>
          <span className="pb-1 text-sm text-muted-foreground" data-testid={`billing-plan-card-period-${plan.key}`}>
            {pricing?.period}
          </span>
          {pricing?.badge ? (
            <span className="rounded-full bg-[#fff1e8] px-3 py-1 text-xs font-semibold text-[#d16024]" data-testid={`billing-plan-card-badge-saving-${plan.key}`}>
              {pricing.badge}
            </span>
          ) : null}
        </div>

        <ul className="grid gap-2" data-testid={`billing-plan-card-features-${plan.key}`}>
          {plan.features.map((feature, index) => (
            <li key={feature} className="flex items-start gap-2 rounded-2xl bg-muted/30 px-3 py-3 text-sm text-foreground/85" data-testid={`billing-plan-card-feature-${plan.key}-${index + 1}`}>
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <span>{feature}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6 space-y-3">
        {isEnterprise ? (
          <Button asChild className="h-11 w-full rounded-xl bg-[#264653] text-sm font-semibold text-white hover:bg-[#1f3742]" data-testid="billing-plan-enterprise-contact-button">
            <Link to="/demo">Satış ile Görüş</Link>
          </Button>
        ) : (
          <Button
            onClick={onSelect}
            disabled={isCurrent || disabled || loading}
            className={`h-11 w-full rounded-xl text-sm font-semibold ${plan.isPopular ? "bg-[#f3722c] text-white hover:bg-[#e05d1b]" : "bg-[#264653] text-white hover:bg-[#1f3742]"}`}
            data-testid={`billing-plan-card-action-${plan.key}`}
          >
            {isCurrent ? "Mevcut Plan" : loading ? "İşleniyor..." : "Planı Değiştir"}
          </Button>
        )}
        <p className="text-xs text-muted-foreground" data-testid={`billing-plan-card-note-${plan.key}`}>
          {isEnterprise
            ? "Enterprise planı satış görüşmesi ile ilerler."
            : isCurrent
              ? "Bu periyotta aktif kullandığınız plan budur."
              : "Upgrade hemen, downgrade bir sonraki dönemde uygulanır."}
        </p>
      </div>
    </article>
  );
};