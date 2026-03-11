import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, ChevronDown, ChevronUp, Check, X } from "lucide-react";

import { Button } from "../ui/button";
import { getPricingForCycle } from "../../lib/syrocePricingContent";

export const SyrocePricingCard = ({ pkg, billingCycle, testIdPrefix = "marketing-pricing" }) => {
  const pricing = getPricingForCycle(pkg, billingCycle);
  const [expanded, setExpanded] = useState(false);
  const detailedFeatures = pkg.detailedFeatures || [];

  return (
    <article
      className={`relative flex h-full flex-col overflow-hidden rounded-[2rem] border p-7 shadow-[0_26px_90px_rgba(15,23,42,0.06)] transition-shadow duration-300 hover:shadow-[0_32px_100px_rgba(15,23,42,0.12)] ${pkg.accent}`}
      data-testid={`${testIdPrefix}-card-${pkg.key}`}
    >
      {pkg.featuredLabel ? (
        <div className="absolute right-5 top-5 rounded-full bg-white/90 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-900" data-testid={`${testIdPrefix}-badge-${pkg.key}`}>
          {pkg.featuredLabel}
        </div>
      ) : null}

      <div className="space-y-5 flex-1">
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

        <div className="space-y-1" data-testid={`${testIdPrefix}-price-wrap-${pkg.key}`}>
          {pricing.oldPrice && billingCycle === "yearly" && (
            <div className="text-sm line-through opacity-50" data-testid={`${testIdPrefix}-old-price-${pkg.key}`}>
              {pricing.oldPrice}
            </div>
          )}
          <div className="flex flex-wrap items-end gap-2">
            <span className="text-4xl font-extrabold tracking-[-0.05em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`${testIdPrefix}-price-${pkg.key}`}>
              {pricing.label}
            </span>
            <span className="pb-1 text-sm opacity-70" data-testid={`${testIdPrefix}-period-${pkg.key}`}>
              {pricing.period}
            </span>
          </div>
          {pricing.badge ? (
            <span className="inline-block mt-1 rounded-full bg-[#fff1e8] px-3 py-1 text-xs font-semibold text-[#d16024]" data-testid={`${testIdPrefix}-price-badge-${pkg.key}`}>
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

        {detailedFeatures.length > 0 && (
          <div data-testid={`${testIdPrefix}-details-${pkg.key}`}>
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1.5 text-xs font-semibold text-[#2563EB] hover:underline transition-colors duration-200"
              data-testid={`${testIdPrefix}-details-toggle-${pkg.key}`}
            >
              {expanded ? "Detayları gizle" : "Tüm özellikleri gör"}
              {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
            {expanded && (
              <div className="mt-3 space-y-2 animate-in fade-in-0 slide-in-from-top-2 duration-200" data-testid={`${testIdPrefix}-details-list-${pkg.key}`}>
                {detailedFeatures.map((feat, i) => (
                  <div key={i} className="flex items-center gap-2.5 text-xs">
                    {feat.included ? (
                      <Check className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                    ) : (
                      <X className="h-3.5 w-3.5 shrink-0 text-slate-300" />
                    )}
                    <span className={feat.included ? "opacity-90" : "opacity-50 line-through"}>
                      {feat.label}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
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
