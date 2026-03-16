import React from "react";
import { STEP_COLORS, fmtCurrency } from "./lib/pricingConstants";

export function PipelineExplainer({ steps, sellPrice, sellCurrency, supplierPrice }) {
  if (!steps?.length) return null;
  return (
    <div className="space-y-1" data-testid="pipeline-explainer">
      {steps.map((s, i) => {
        const colors = STEP_COLORS[s.step] || STEP_COLORS.supplier_price;
        const isLast = i === steps.length - 1;
        const showAdjustment = s.step !== "supplier_price" && s.step !== "currency_conversion";
        return (
          <React.Fragment key={i}>
            <div className={`rounded-lg border ${colors.border} ${colors.bg} p-3 transition-all duration-200 hover:shadow-sm`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-1.5 h-8 rounded-full ${colors.accent}`} />
                  <div>
                    <p className={`text-sm font-medium ${colors.text}`}>{s.label}</p>
                    {s.rule_name && <p className="text-[10px] text-muted-foreground">Kural: {s.rule_name} ({s.rule_id})</p>}
                    {!s.rule_name && s.detail && <p className="text-[10px] text-muted-foreground">{s.detail}</p>}
                  </div>
                </div>
                <div className="text-right">
                  {showAdjustment && s.adjustment_amount !== 0 && (
                    <p className={`text-xs font-mono ${s.adjustment_amount > 0 ? "text-emerald-600" : s.adjustment_amount < 0 ? "text-red-500" : "text-muted-foreground"}`}>
                      {s.adjustment_amount > 0 ? "+" : ""}{s.adjustment_amount.toFixed(2)}
                      {s.adjustment_pct !== 0 && ` (%${s.adjustment_pct > 0 ? "+" : ""}${s.adjustment_pct})`}
                    </p>
                  )}
                  <p className={`text-sm font-bold font-mono ${colors.text}`}>{s.output_price.toFixed(2)}</p>
                </div>
              </div>
            </div>
            {!isLast && (
              <div className="flex justify-center">
                <div className="w-px h-3 bg-slate-300" />
              </div>
            )}
          </React.Fragment>
        );
      })}
      <div className="bg-slate-900 text-white rounded-lg p-4 flex justify-between items-center mt-2">
        <div>
          <span className="font-semibold text-sm">Satis Fiyati</span>
          <p className="text-[10px] text-slate-400">supplier_price: {supplierPrice} -&gt; final: {sellPrice}</p>
        </div>
        <span className="text-xl font-bold font-mono" data-testid="sim-sell-price">{fmtCurrency(sellPrice, sellCurrency)}</span>
      </div>
    </div>
  );
}
