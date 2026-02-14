import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Signal, RefreshCw, ArrowUp, ArrowDown } from "lucide-react";

export default function AdminSystemUptimePage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get(`/admin/system/uptime?days=${days}`);
      setStats(res.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  const uptimeColor = (pct) => {
    if (pct >= 99.9) return "text-green-600";
    if (pct >= 99) return "text-amber-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-6" data-testid="system-uptime-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Signal className="h-6 w-6 text-green-600" />
          <h1 className="text-2xl font-bold text-foreground">Sistem Çalışma Süresi</h1>
        </div>
        <div className="flex gap-2">
          <select
            className="border rounded px-3 py-1.5 text-sm bg-white"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>Son 7 gün</option>
            <option value={30}>Son 30 gün</option>
            <option value={90}>Son 90 gün</option>
          </select>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Yenile
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground/60" />
        </div>
      ) : !stats ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="empty-state">
          <Signal className="h-12 w-12 mx-auto mb-3 text-muted-foreground/40" />
          <p>Veri bulunamadı</p>
        </div>
      ) : (
        <div className="space-y-6" data-testid="uptime-data">
          {/* Big uptime percentage */}
          <div className="bg-white border rounded-lg p-8 text-center">
            <p className="text-sm text-muted-foreground mb-2">Çalışma Süresi</p>
            <p className={`text-6xl font-bold ${uptimeColor(stats.uptime_percent)}`}>
              {stats.uptime_percent}%
            </p>
            <p className="text-sm text-muted-foreground/60 mt-2">Son {stats.period_days} gün</p>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white border rounded-lg p-4 flex items-center gap-3">
              <ArrowUp className="h-5 w-5 text-green-500" />
              <div>
                <p className="text-sm text-muted-foreground">Çalışma</p>
                <p className="text-xl font-bold text-foreground">{stats.up_minutes || 0} dk</p>
              </div>
            </div>
            <div className="bg-white border rounded-lg p-4 flex items-center gap-3">
              <ArrowDown className="h-5 w-5 text-red-500" />
              <div>
                <p className="text-sm text-muted-foreground">Kesinti</p>
                <p className="text-xl font-bold text-foreground">{stats.downtime_minutes || 0} dk</p>
              </div>
            </div>
            <div className="bg-white border rounded-lg p-4 flex items-center gap-3">
              <Signal className="h-5 w-5 text-blue-500" />
              <div>
                <p className="text-sm text-muted-foreground">Toplam Ölçüm</p>
                <p className="text-xl font-bold text-foreground">{stats.total_minutes || 0} dk</p>
              </div>
            </div>
          </div>

          <p className="text-xs text-muted-foreground/60">
            Son güncelleme: {stats.computed_at ? new Date(stats.computed_at).toLocaleString("tr-TR") : "-"}
          </p>
        </div>
      )}
    </div>
  );
}
