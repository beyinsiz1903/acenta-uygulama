import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2 } from "lucide-react";

import { Button } from "../ui/button";
import { getPricingForCycle } from "../../lib/syrocePricingContent";

export const SyrocePricingCard = ({ pkg, billingCycle, testIdPrefix = "marketing-pricing" }) => {
  const pricing = getPricingForCycle(pkg, billingCycle);

  return (
    <article
      className={`relative flex h-full flex-col overflow-hidden rounded-[2rem] border p-7 shadow-[0_26px_90px_rgba(15,23,42,0.06)] ${pkg.accent}`}
      data-testid={`${testIdPrefix}-card-${pkg.key}`}
    >
      {pkg.featuredLabel ? (
        <div className="absolute right-5 top-5 rounded-full bg-white/90 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-900" data-testid={`${testIdPrefix}-badge-${pkg.key}`}>
          {pkg.featuredLabel}
        </div>
      ) : null}

      <div className="space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#2a9d8f]" data-testid={`${testIdPrefix}-audience-${pkg.key}`}>
            {pkg.audience}
          </p>
          <h3 className="mt-3 text-3xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`${testIdPrefix}-title-${pkg.key}`}>
            {pkg.label}
          </h3>
          <p className="mt-3 text-sm leading-7 opacity-85" data-testid={`${testIdPrefix}-description-${pkg.key}`}>
            {pkg.description}
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-2" data-testid={`${testIdPrefix}-price-wrap-${pkg.key}`}>
          <span className="text-4xl font-extrabold tracking-[-0.05em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`${testIdPrefix}-price-${pkg.key}`}>
            {pricing.label}
          </span>
          <span className="pb-1 text-sm opacity-70" data-testid={`${testIdPrefix}-period-${pkg.key}`}>
            {pricing.period}
          </span>
          {pricing.badge ? (
            <span className="rounded-full bg-[#fff1e8] px-3 py-1 text-xs font-semibold text-[#d16024]" data-testid={`${testIdPrefix}-price-badge-${pkg.key}`}>
              {pricing.badge}
            </span>
          ) : null}
        </div>

        <div className="rounded-[1.4rem] border border-white/60 bg-white/55 px-4 py-4 text-sm font-medium text-slate-700" data-testid={`${testIdPrefix}-offer-${pkg.key}`}>
          {pkg.specialOffer}
        </div>

        <div className="grid gap-3" data-testid={`${testIdPrefix}-feature-list-${pkg.key}`}>
          {pkg.highlights.map((feature, index) => (
            <div key={feature} className={`flex items-start gap-3 rounded-2xl px-4 py-3 text-sm ${pkg.bulletTone}`} data-testid={`${testIdPrefix}-feature-${pkg.key}-${index + 1}`}>
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#f3722c]" />
              <span>{feature}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8 pt-2">
        <Button asChild className="h-12 w-full rounded-full bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] text-sm font-semibold text-white hover:brightness-110" data-testid={`${testIdPrefix}-cta-${pkg.key}`}>
          <Link to={pkg.ctaHref}>
            {pkg.ctaLabel}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </div>
    </article>
  );
};