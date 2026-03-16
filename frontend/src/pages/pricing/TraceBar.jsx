import React from "react";
import { Fingerprint, Database, Clock, Copy } from "lucide-react";
import { toast } from "sonner";

export function TraceBar({ result }) {
  if (!result) return null;
  const traceId = result.pricing_trace_id || "";
  const cacheHit = result.cache_hit || false;
  const latency = result.latency_ms || 0;
  const cacheKey = result.cache_key || "";

  const copyTrace = () => {
    navigator.clipboard.writeText(traceId);
    toast.success("Trace ID kopyalandi");
  };

  return (
    <div className="flex flex-wrap items-center gap-3 px-3 py-2 rounded-lg bg-slate-900 text-white text-xs font-mono" data-testid="pricing-trace-bar">
      <div className="flex items-center gap-1.5">
        <Fingerprint className="w-3.5 h-3.5 text-amber-400" />
        <span className="text-slate-400">trace:</span>
        <span className="text-amber-300 font-semibold" data-testid="trace-id-value">{traceId}</span>
        <button onClick={copyTrace} className="hover:text-amber-200 transition-colors" data-testid="copy-trace-btn" title="Kopyala">
          <Copy className="w-3 h-3" />
        </button>
      </div>
      <div className="w-px h-4 bg-slate-700" />
      <div className="flex items-center gap-1.5">
        <Database className="w-3.5 h-3.5 text-teal-400" />
        <span className="text-slate-400">cache:</span>
        <span className={`font-semibold ${cacheHit ? "text-emerald-400" : "text-slate-500"}`} data-testid="cache-status">
          {cacheHit ? "HIT" : "MISS"}
        </span>
      </div>
      <div className="w-px h-4 bg-slate-700" />
      <div className="flex items-center gap-1.5">
        <Clock className="w-3.5 h-3.5 text-blue-400" />
        <span className="text-slate-400">latency:</span>
        <span className="text-blue-300" data-testid="latency-value">{latency}ms</span>
      </div>
      {cacheKey && (
        <>
          <div className="w-px h-4 bg-slate-700" />
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">key:</span>
            <span className="text-slate-400">{cacheKey}</span>
          </div>
        </>
      )}
    </div>
  );
}
