import React from "react";
import { Database, BarChart3, Cpu, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { GlobalDiagnosticsPanel } from "./GlobalDiagnosticsPanel";
import { CacheTelemetryPanel } from "./CacheTelemetryPanel";

export function CacheStatsBar({
  cacheStats,
  hasActiveAlerts,
  showDiagnostics,
  showTelemetry,
  diagnostics,
  telemetry,
  warmingLoading,
  onToggleDiagnostics,
  onToggleTelemetry,
  onRefreshCache,
  onClearCache,
  onRefreshDiagnostics,
  onWarmSupplier,
  onInvalidateSupplier,
}) {
  if (!cacheStats) return null;

  return (
    <div className="rounded-lg border bg-slate-50 overflow-hidden" data-testid="cache-stats-bar">
      <div className="flex items-center gap-4 px-4 py-2.5 text-xs">
        <div className="flex items-center gap-1.5 text-slate-600">
          <Database className="w-3.5 h-3.5 text-teal-600" />
          <span className="font-medium">Pricing Cache</span>
        </div>
        <div className="flex items-center gap-3 text-slate-500 font-mono">
          <span>Entries: <strong className="text-slate-700">{cacheStats.active_entries}</strong></span>
          <span>Hits: <strong className="text-emerald-600">{cacheStats.hits}</strong></span>
          <span>Misses: <strong className="text-amber-600">{cacheStats.misses}</strong></span>
          <span>Hit Rate: <strong className={cacheStats.hit_rate_pct >= 70 ? "text-emerald-600" : cacheStats.hit_rate_pct >= 50 ? "text-amber-600" : "text-red-600"}>{cacheStats.hit_rate_pct}%</strong></span>
          <span>Evictions: <strong className="text-slate-600">{cacheStats.evictions || 0}</strong></span>
          <span>Mem: <strong className="text-slate-600">{cacheStats.memory_usage_mb || 0}MB</strong></span>
        </div>
        {hasActiveAlerts && (
          <Badge variant="destructive" className="text-[10px] h-4 px-1.5 animate-pulse" data-testid="alert-badge">
            ALERT
          </Badge>
        )}
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onToggleDiagnostics} className="h-6 px-2 text-xs" data-testid="toggle-diagnostics-btn">
            <Cpu className="w-3 h-3 mr-1" /> {showDiagnostics ? "Gizle" : "Diagnostics"}
          </Button>
          <Button variant="ghost" size="sm" onClick={onToggleTelemetry} className="h-6 px-2 text-xs" data-testid="toggle-telemetry-btn">
            <BarChart3 className="w-3 h-3 mr-1" /> {showTelemetry ? "Gizle" : "Telemetry"}
          </Button>
          <Button variant="ghost" size="sm" onClick={onRefreshCache} className="h-6 px-2 text-xs" data-testid="refresh-cache-btn">
            <RefreshCw className="w-3 h-3 mr-1" /> Yenile
          </Button>
          <Button variant="ghost" size="sm" onClick={onClearCache} className="h-6 px-2 text-xs text-red-500 hover:text-red-600" data-testid="clear-cache-btn">
            <Trash2 className="w-3 h-3 mr-1" /> Temizle
          </Button>
        </div>
      </div>

      {showDiagnostics && (
        <GlobalDiagnosticsPanel diagnostics={diagnostics} onRefresh={onRefreshDiagnostics} />
      )}

      {showTelemetry && (
        <CacheTelemetryPanel
          telemetry={telemetry}
          warmingLoading={warmingLoading}
          onWarmSupplier={onWarmSupplier}
          onInvalidateSupplier={onInvalidateSupplier}
        />
      )}
    </div>
  );
}
