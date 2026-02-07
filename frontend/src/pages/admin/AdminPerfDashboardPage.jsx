import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Gauge, RefreshCw, Zap, AlertTriangle, Database } from "lucide-react";

const latencyColor = (ms) => {
  if (ms < 100) return "text-green-600";
  if (ms < 500) return "text-amber-600";
  return "text-red-600";
};

const errorColor = (pct) => {
  if (pct < 1) return "text-green-600";
  if (pct < 5) return "text-amber-600";
  return "text-red-600";
};

export default function AdminPerfDashboardPage() {
  const [topEndpoints, setTopEndpoints] = useState([]);
  const [slowEndpoints, setSlowEndpoints] = useState([]);
  const [cacheStats, setCacheStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [window, setWindow] = useState(24);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [topRes, slowRes, cacheRes] = await Promise.all([
        api.get(`/admin/system/perf/top-endpoints?window=${window}`),
        api.get(`/admin/system/perf/slow-endpoints?window=${window}&threshold=200`),
        api.get("/admin/system/perf/cache-stats"),
      ]);
      setTopEndpoints(topRes.data?.endpoints || []);
      setSlowEndpoints(slowRes.data?.endpoints || []);
      setCacheStats(cacheRes.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, [window]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6" data-testid="perf-dashboard-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Gauge className="h-6 w-6 text-violet-600" />
          <h1 className="text-2xl font-bold text-gray-900">Performans Paneli</h1>
        </div>
        <div className="flex gap-2">
          <select
            className="border rounded px-3 py-1.5 text-sm bg-white"
            value={window}
            onChange={(e) => setWindow(Number(e.target.value))}
          >
            <option value={1}>Son 1 saat</option>
            <option value={6}>Son 6 saat</option>
            <option value={24}>Son 24 saat</option>
            <option value={72}>Son 3 gün</option>
          </select>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Yenile
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : (
        <div className="space-y-6" data-testid="perf-data">
          {/* Cache Stats */}
          {cacheStats && (
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white border rounded-lg p-4 flex items-center gap-3">
                <Database className="h-5 w-5 text-indigo-500" />
                <div>
                  <p className="text-sm text-gray-500">Cache Toplam</p>
                  <p className="text-xl font-bold">{cacheStats.total_entries}</p>
                </div>
              </div>
              <div className="bg-white border rounded-lg p-4 flex items-center gap-3">
                <Zap className="h-5 w-5 text-green-500" />
                <div>
                  <p className="text-sm text-gray-500">Aktif</p>
                  <p className="text-xl font-bold text-green-600">{cacheStats.active_entries}</p>
                </div>
              </div>
              <div className="bg-white border rounded-lg p-4 flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-sm text-gray-500">Süresi Dolmuş</p>
                  <p className="text-xl font-bold text-gray-400">{cacheStats.expired_entries}</p>
                </div>
              </div>
            </div>
          )}

          {/* Slow Endpoints Alert */}
          {slowEndpoints.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
                <h3 className="font-semibold text-amber-800">Yavaş Endpoint'ler (p95 &gt; 200ms)</h3>
                <Badge className="bg-amber-100 text-amber-700">{slowEndpoints.length}</Badge>
              </div>
              <div className="space-y-1">
                {slowEndpoints.slice(0, 5).map((ep, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-gray-700">{ep.method} {ep.path}</span>
                    <span className={`font-bold ${latencyColor(ep.p95_ms)}`}>p95: {ep.p95_ms}ms</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top Endpoints Table */}
          <div className="bg-white border rounded-lg overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b">
              <h3 className="font-semibold text-gray-800">Top Endpoint'ler (İstek Hacmi)</h3>
            </div>
            {topEndpoints.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                Henüz yeterli perf sample yok. Trafik arttıkça dolacak.
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200" data-testid="top-endpoints-table">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Endpoint</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">İstek</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Hata%</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Ort.</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">p50</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">p95</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">p99</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Max</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {topEndpoints.map((ep, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-sm">
                        <span className="inline-block w-12 text-xs font-mono bg-gray-100 text-gray-600 text-center rounded px-1">{ep.method}</span>
                        <span className="ml-2 font-mono text-gray-700 text-xs">{ep.path}</span>
                      </td>
                      <td className="px-3 py-2 text-sm text-right font-bold">{ep.count}</td>
                      <td className={`px-3 py-2 text-sm text-right font-bold ${errorColor(ep.error_rate)}`}>{ep.error_rate}%</td>
                      <td className={`px-3 py-2 text-sm text-right ${latencyColor(ep.avg_ms)}`}>{ep.avg_ms}</td>
                      <td className={`px-3 py-2 text-sm text-right ${latencyColor(ep.p50_ms)}`}>{ep.p50_ms}</td>
                      <td className={`px-3 py-2 text-sm text-right font-bold ${latencyColor(ep.p95_ms)}`}>{ep.p95_ms}</td>
                      <td className={`px-3 py-2 text-sm text-right ${latencyColor(ep.p99_ms)}`}>{ep.p99_ms}</td>
                      <td className={`px-3 py-2 text-sm text-right ${latencyColor(ep.max_ms)}`}>{ep.max_ms}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
