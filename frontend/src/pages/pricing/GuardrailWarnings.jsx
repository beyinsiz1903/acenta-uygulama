import React from "react";
import { ShieldCheck, ShieldAlert, AlertTriangle, Info } from "lucide-react";
import { GUARDRAIL_LABELS } from "./lib/pricingConstants";

export function GuardrailWarnings({ warnings, passed }) {
  if (!warnings?.length) return null;
  return (
    <div className={`rounded-lg border p-3 space-y-2 ${passed ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"}`} data-testid="guardrail-warnings">
      <div className="flex items-center gap-2">
        {passed
          ? <ShieldCheck className="w-4 h-4 text-emerald-600" />
          : <ShieldAlert className="w-4 h-4 text-red-600" />
        }
        <span className={`text-sm font-semibold ${passed ? "text-emerald-700" : "text-red-700"}`}>
          {passed ? "Tum guardrail'lar gecti" : "Guardrail ihlali tespit edildi"}
        </span>
      </div>
      {warnings.map((w, i) => (
        <div key={i} className={`flex items-start gap-2 text-xs p-2 rounded ${w.severity === "error" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"}`}>
          {w.severity === "error" ? <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" /> : <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />}
          <div>
            <p className="font-medium">{GUARDRAIL_LABELS[w.guardrail] || w.guardrail}</p>
            <p>{w.message}</p>
            <p className="text-[10px] opacity-75">Beklenen: {w.expected} | Gercek: {w.actual}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
