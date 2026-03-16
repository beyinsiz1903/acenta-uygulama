import React from "react";
import { Clock, Flame, RefreshCw } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";

export function GlobalDiagnosticsPanel({ diagnostics, onRefresh }) {
  if (!diagnostics) return null;

  return (
    <div className="border-t bg-white px-4 py-3 space-y-3" data-testid="diagnostics-panel">
      <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Global Cache Diagnostics</div>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="rounded-md border p-2.5 text-center bg-slate-50" data-testid="diag-hit-rate">
          <div className="text-[10px] text-slate-500 font-medium">Global Hit Rate</div>
          <div className={`text-lg font-bold font-mono ${diagnostics.global_hit_rate >= 70 ? "text-emerald-600" : diagnostics.global_hit_rate >= 50 ? "text-amber-600" : "text-red-600"}`}>
            %{diagnostics.global_hit_rate}
          </div>
        </div>
        <div className="rounded-md border p-2.5 text-center bg-slate-50" data-testid="diag-entries">
          <div className="text-[10px] text-slate-500 font-medium">Total Entries</div>
          <div className="text-lg font-bold font-mono text-slate-700">{diagnostics.total_entries}</div>
          <div className="text-[9px] text-slate-400">/ {diagnostics.max_size} (%{diagnostics.utilization_pct})</div>
        </div>
        <div className="rounded-md border p-2.5 text-center bg-slate-50" data-testid="diag-memory">
          <div className="text-[10px] text-slate-500 font-medium">Memory Usage</div>
          <div className="text-lg font-bold font-mono text-blue-600">{diagnostics.memory_usage_mb}MB</div>
        </div>
        <div className="rounded-md border p-2.5 text-center bg-slate-50" data-testid="diag-evictions">
          <div className="text-[10px] text-slate-500 font-medium">Evictions</div>
          <div className="text-lg font-bold font-mono text-amber-600">{diagnostics.evictions}</div>
        </div>
        <div className="rounded-md border p-2.5 text-center bg-slate-50" data-testid="diag-uptime">
          <div className="text-[10px] text-slate-500 font-medium">Uptime</div>
          <div className="text-lg font-bold font-mono text-slate-700">{Math.floor(diagnostics.uptime_seconds / 60)}dk</div>
        </div>
        <div className="rounded-md border p-2.5 text-center bg-slate-50" data-testid="diag-suppliers">
          <div className="text-[10px] text-slate-500 font-medium">Suppliers</div>
          <div className="text-lg font-bold font-mono text-violet-600">{diagnostics.supplier_count}</div>
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3 h-3 text-emerald-500" />
          <span className="text-slate-500">HIT Latency:</span>
          <strong className="text-emerald-600">{diagnostics.avg_hit_latency_ms}ms</strong>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-3 h-3 text-amber-500" />
          <span className="text-slate-500">MISS Latency:</span>
          <strong className="text-amber-600">{diagnostics.avg_miss_latency_ms}ms</strong>
        </div>
        {diagnostics.warming_status && (
          <div className="flex items-center gap-1.5">
            <Flame className="w-3 h-3 text-orange-500" />
            <span className="text-slate-500">Tracked Routes:</span>
            <strong className="text-orange-600">{diagnostics.warming_status.tracked_queries}</strong>
          </div>
        )}
        {diagnostics.active_alerts?.length > 0 && (
          <Badge variant="destructive" className="text-[10px] h-4 px-1.5">
            {diagnostics.active_alerts.length} aktif alert
          </Badge>
        )}
        <Button variant="ghost" size="sm" onClick={onRefresh} className="h-5 px-1.5 text-[10px] ml-auto">
          <RefreshCw className="w-2.5 h-2.5 mr-0.5" /> Yenile
        </Button>
      </div>
    </div>
  );
}
