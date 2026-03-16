import React from "react";
import { Activity, Bell, AlertTriangle, Trash2, Flame, Loader2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "../../components/ui/tooltip";

export function CacheTelemetryPanel({ telemetry, warmingLoading, onWarmSupplier, onInvalidateSupplier }) {
  if (!telemetry) return null;

  return (
    <div className="border-t bg-white px-4 py-3 space-y-3" data-testid="telemetry-panel">
      {/* Summary Row */}
      <div className="flex items-center gap-6 text-xs">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-blue-500" />
          <span className="text-slate-500">Toplam Istek:</span>
          <strong className="text-slate-700">{telemetry.total_requests}</strong>
        </div>
        <div>
          <span className="text-slate-500">Ort. HIT Latency:</span>
          <strong className="text-emerald-600 ml-1">{telemetry.avg_hit_latency_ms}ms</strong>
        </div>
        <div>
          <span className="text-slate-500">Ort. MISS Latency:</span>
          <strong className="text-amber-600 ml-1">{telemetry.avg_miss_latency_ms}ms</strong>
        </div>
        <div>
          <span className="text-slate-500">Uptime:</span>
          <strong className="text-slate-700 ml-1">{Math.floor(telemetry.uptime_seconds / 60)}dk</strong>
        </div>
        <div>
          <span className="text-slate-500">Evictions:</span>
          <strong className="text-amber-600 ml-1">{telemetry.evictions || 0}</strong>
        </div>
        <div>
          <span className="text-slate-500">Mem:</span>
          <strong className="text-blue-600 ml-1">{telemetry.memory_usage_mb || 0}MB</strong>
        </div>
      </div>

      {/* Per-Supplier Breakdown */}
      {telemetry.supplier_breakdown && Object.keys(telemetry.supplier_breakdown).length > 0 && (
        <div>
          <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-1.5">Supplier Bazli</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(telemetry.supplier_breakdown).map(([supplier, data]) => (
              <div key={supplier} className="flex items-center justify-between rounded-md border px-2.5 py-1.5 text-xs bg-slate-50" data-testid={`supplier-telemetry-${supplier}`}>
                <div>
                  <div className="font-medium text-slate-700">{supplier}</div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    {data.hits}H / {data.misses}M / {data.hit_rate_pct}%
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <Badge variant="outline" className="text-[10px] h-4 px-1">
                    {data.active_entries}
                  </Badge>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-5 w-5 p-0 text-orange-400 hover:text-orange-600"
                        onClick={() => onWarmSupplier(supplier)}
                        disabled={warmingLoading[supplier]}
                        data-testid={`warm-${supplier}-btn`}
                      >
                        {warmingLoading[supplier]
                          ? <Loader2 className="w-3 h-3 animate-spin" />
                          : <Flame className="w-3 h-3" />
                        }
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Cache Warming: Populer rotalari onbellekle</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-5 w-5 p-0 text-red-400 hover:text-red-600"
                        onClick={() => onInvalidateSupplier(supplier)}
                        data-testid={`invalidate-${supplier}-btn`}
                      >
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Supplier cache temizle</TooltipContent>
                  </Tooltip>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alert History */}
      {telemetry.alert_history && telemetry.alert_history.length > 0 && (
        <div>
          <div className="text-[11px] font-medium text-amber-600 uppercase tracking-wider mb-1.5 flex items-center gap-1">
            <Bell className="w-3 h-3" /> Alert Gecmisi
          </div>
          <div className="space-y-1">
            {telemetry.alert_history.slice(-5).reverse().map((alert, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px] text-amber-700 font-mono bg-amber-50 rounded px-2 py-1" data-testid={`alert-history-${i}`}>
                <AlertTriangle className="w-3 h-3 shrink-0" />
                <span className="text-amber-500">{alert.timestamp?.split("T")[1]?.split(".")[0]}</span>
                <span>hit_rate: %{alert.hit_rate_pct}</span>
                <Badge variant="outline" className="text-[10px] h-4 px-1.5 border-amber-300">{alert.type}</Badge>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Invalidations */}
      {telemetry.recent_invalidations && telemetry.recent_invalidations.length > 0 && (
        <div>
          <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-1.5">Son Invalidation'lar</div>
          <div className="space-y-1">
            {telemetry.recent_invalidations.slice(-5).reverse().map((inv, i) => (
              <div key={i} className="flex items-center gap-2 text-[11px] text-slate-500 font-mono" data-testid={`invalidation-log-${i}`}>
                <span className="text-slate-400">{inv.timestamp?.split("T")[1]?.split(".")[0]}</span>
                <Badge variant="outline" className="text-[10px] h-4 px-1.5">{inv.reason}</Badge>
                <span className="text-red-500">{inv.cleared} temizlendi</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
