import React from "react";

import { SYROCE_COMPARISON_ROWS, formatComparisonValue } from "../../lib/syrocePricingContent";

export const SyrocePricingComparison = ({ packages, testIdPrefix = "pricing-comparison" }) => {
  return (
    <section className="space-y-8" data-testid={testIdPrefix}>
      <div className="max-w-4xl">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#2563EB]" data-testid={`${testIdPrefix}-eyebrow`}>
          Paket Karşılaştırma
        </p>
        <h2 className="mt-3 text-3xl font-extrabold leading-[1.08] tracking-[-0.04em] text-slate-950 sm:text-4xl lg:text-5xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`${testIdPrefix}-title`}>
          Paketleri aynı tabloda karşılaştırın
        </h2>
        <p className="mt-4 text-sm leading-7 text-slate-600 sm:text-base md:text-lg" data-testid={`${testIdPrefix}-description`}>
          Syroce paketleri rezervasyon sınırı ile değil; entegrasyon seviyesi, ekip yapısı, destek modeli ve operasyon kapsamı ile ayrışır.
        </p>
      </div>

      <div className="overflow-hidden rounded-[2rem] border border-white/80 bg-white/95 shadow-[0_24px_80px_rgba(15,23,42,0.05)]" data-testid={`${testIdPrefix}-table-wrap`}>
        <div className="grid grid-cols-[1.2fr_repeat(4,minmax(0,1fr))] gap-px bg-slate-200 text-sm" data-testid={`${testIdPrefix}-table`}>
          <div className="bg-slate-950 px-4 py-4 text-xs font-semibold uppercase tracking-[0.18em] text-white" data-testid={`${testIdPrefix}-header-feature`}>
            Özellik
          </div>
          {packages.map((pkg) => (
            <div key={pkg.key} className="bg-slate-950 px-4 py-4 text-center text-xs font-semibold uppercase tracking-[0.18em] text-white" data-testid={`${testIdPrefix}-header-${pkg.key}`}>
              {pkg.label}
            </div>
          ))}

          {SYROCE_COMPARISON_ROWS.map((row) => (
            <React.Fragment key={row.key}>
              <div className="bg-white px-4 py-4 text-sm font-semibold text-slate-900" data-testid={`${testIdPrefix}-row-label-${row.key}`}>
                {row.label}
              </div>
              {packages.map((pkg) => (
                <div key={`${pkg.key}-${row.key}`} className="bg-white px-4 py-4 text-center text-sm text-slate-600" data-testid={`${testIdPrefix}-cell-${pkg.key}-${row.key}`}>
                  {formatComparisonValue(pkg.compare?.[row.key])}
                </div>
              ))}
            </React.Fragment>
          ))}
        </div>
      </div>
    </section>
  );
};