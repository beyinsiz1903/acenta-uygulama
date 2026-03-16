import React, { useState, useEffect, useCallback } from "react";
import { api } from "../../lib/api";
import {
  Activity, Database, Server, RefreshCw, AlertTriangle,
  CheckCircle, XCircle, Clock, Zap, Shield, BarChart3,
  Play, RotateCcw, ChevronDown, ChevronUp
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL;

/* ── Helpers ─────────────────────────────────────────────── */

function pct(val) { return val != null ? `${val}%` : "—"; }
function num(val) { return val != null ? val.toLocaleString() : "—"; }

function StatusBadge({ status }) {
  const map = {
    healthy: { cls: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: CheckCircle, label: "Healthy" },
    degraded: { cls: "bg-amber-50 text-amber-700 border-amber-200", icon: AlertTriangle, label: "Degraded" },
    error: { cls: "bg-red-50 text-red-700 border-red-200", icon: XCircle, label: "Error" },
    unavailable: { cls: "bg-gray-100 text-gray-500 border-gray-200", icon: XCircle, label: "Unavailable" },
    pass: { cls: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: CheckCircle, label: "Pass" },
    fail: { cls: "bg-red-50 text-red-700 border-red-200", icon: XCircle, label: "Fail" },
  };
  const s = map[status] || map.error;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${s.cls}`} data-testid={`status-badge-${status}`}>
      <Icon size={12} /> {s.label}
    </span>
  );
}

function MetricCard({ label, value, sub, icon: Icon, color = "text-blue-600" }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-1 shadow-sm hover:shadow-md transition-shadow" data-testid={`metric-card-${label.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 uppercase tracking-wider font-medium">{label}</span>
        {Icon && <Icon size={14} className={color} />}
      </div>
      <span className="text-2xl font-bold text-gray-900 tracking-tight">{value}</span>
      {sub && <span className="text-xs text-gray-400">{sub}</span>}
    </div>
  );
}

function SectionHeader({ title, icon: Icon, children }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        {Icon && <Icon size={18} className="text-gray-500" />}
        <h2 className="text-base font-semibold text-gray-800">{title}</h2>
      </div>
      {children}
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────── */

export default function CacheHealthDashboardPage() {
  const [overview, setOverview] = useState(null);
  const [ttlConfig, setTtlConfig] = useState(null);
  const [fallbackResult, setFallbackResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [testRunning, setTestRunning] = useState(false);
  const [error, setError] = useState("");
  const [ttlExpanded, setTtlExpanded] = useState(false);
  const [eventsExpanded, setEventsExpanded] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [ovRes, ttlRes] = await Promise.all([
        api.get(`${API}/api/admin/cache-health/overview`),
        api.get(`${API}/api/admin/cache-health/ttl-config`),
      ]);
      setOverview(ovRes.data);
      setTtlConfig(ttlRes.data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Veri yuklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function runFallbackTest(simulateDown = false) {
    setTestRunning(true);
    try {
      const res = await api.post(`${API}/api/admin/cache-health/test-fallback`, {
        test_key: `dashboard_test_${Date.now()}`,
        simulate_redis_down: simulateDown,
      });
      setFallbackResult(res.data);
    } catch (e) {
      setFallbackResult({ status: "fail", error: e?.message });
    } finally {
      setTestRunning(false);
    }
  }

  async function resetMetrics() {
    try {
      await api.post(`${API}/api/admin/cache-health/reset-metrics`);
      await fetchData();
    } catch (e) { /* ignore */ }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]" data-testid="cache-health-loading">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const s = overview?.summary || {};
  const redis = overview?.redis_l1 || {};
  const mongo = overview?.mongo_l2 || {};
  const latency = overview?.latency || {};
  const events = overview?.recent_events || [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6" data-testid="cache-health-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Cache Health Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Redis L1 + MongoDB L2 cache katmanlarinin saglik durumu ve metrikleri
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={overview?.status || "error"} />
          <button
            onClick={fetchData}
            className="p-2 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-500 transition-colors"
            data-testid="refresh-btn"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">{error}</div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="kpi-grid">
        <MetricCard label="Hit Rate" value={pct(s.hit_rate_pct)} sub={`${num(s.total_requests)} total`} icon={Zap} color="text-emerald-500" />
        <MetricCard label="Miss Rate" value={pct(s.miss_rate_pct)} icon={XCircle} color="text-amber-500" />
        <MetricCard label="Fallback" value={num(s.fallback_count)} sub="Redis->Mongo" icon={Database} color="text-blue-500" />
        <MetricCard label="Stale Serve" value={num(s.stale_serve_count)} icon={Clock} color="text-orange-500" />
        <MetricCard label="Inv. OK" value={num(s.invalidation_success)} sub={`${num(s.invalidation_keys_cleared)} keys`} icon={CheckCircle} color="text-emerald-500" />
        <MetricCard label="Inv. Fail" value={num(s.invalidation_failure)} icon={AlertTriangle} color="text-red-500" />
      </div>

      {/* Redis & Mongo Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Redis Health */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm" data-testid="redis-health-card">
          <SectionHeader title="Redis L1 (In-Memory)" icon={Server}>
            <StatusBadge status={redis.health?.status || "unavailable"} />
          </SectionHeader>
          {redis.health?.status === "healthy" ? (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="text-gray-500">Memory Used</div>
              <div className="text-gray-800 font-mono">{redis.health?.used_memory_human || "—"}</div>
              <div className="text-gray-500">Peak Memory</div>
              <div className="text-gray-800 font-mono">{redis.health?.used_memory_peak_human || "—"}</div>
              <div className="text-gray-500">Connected Clients</div>
              <div className="text-gray-800 font-mono">{redis.health?.connected_clients || 0}</div>
              <div className="text-gray-500">Cache Keys</div>
              <div className="text-gray-800 font-mono">{redis.stats?.cache_keys ?? "—"}</div>
              <div className="text-gray-500">Hit Rate</div>
              <div className="text-gray-800 font-mono">{redis.stats?.stats?.hit_rate ?? "—"}%</div>
              <div className="text-gray-500">Ops/sec</div>
              <div className="text-gray-800 font-mono">{redis.stats?.ops_per_sec ?? "—"}</div>
            </div>
          ) : (
            <div className="flex items-center gap-3 py-4 px-4 bg-amber-50 border border-amber-100 rounded-lg">
              <AlertTriangle size={20} className="text-amber-500 flex-shrink-0" />
              <div>
                <div className="text-gray-700 text-sm font-medium">Redis Baglantisi Yok</div>
                <div className="text-xs text-gray-500 mt-0.5">{redis.health?.reason || "Sistem MongoDB fallback modunda calisiyor"}</div>
              </div>
            </div>
          )}
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-2 text-xs text-gray-400">
            <Shield size={12} />
            Redis Down: {num(s.redis_down_events)} | Timeout: {num(s.redis_timeout_events)}
          </div>
        </div>

        {/* MongoDB Health */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm" data-testid="mongo-health-card">
          <SectionHeader title="MongoDB L2 (Persistent)" icon={Database}>
            <StatusBadge status="healthy" />
          </SectionHeader>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="text-gray-500">Total Entries</div>
            <div className="text-gray-800 font-mono">{num(mongo.total_entries)}</div>
            <div className="text-gray-500">Active Entries</div>
            <div className="text-gray-800 font-mono">{num(mongo.active_entries)}</div>
            <div className="text-gray-500">Expired Entries</div>
            <div className="text-gray-800 font-mono">{num(mongo.expired_entries)}</div>
            {mongo.stale_entries != null && (
              <>
                <div className="text-gray-500">Stale Entries</div>
                <div className="text-amber-600 font-mono font-medium">{num(mongo.stale_entries)}</div>
              </>
            )}
          </div>
          {mongo.by_category && Object.keys(mongo.by_category).length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-100">
              <div className="text-xs text-gray-400 mb-2">Kategoriye Gore</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(mongo.by_category).map(([cat, count]) => (
                  <span key={cat} className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600 font-mono">
                    {cat}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Latency Stats */}
      {Object.keys(latency).length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm" data-testid="latency-card">
          <SectionHeader title="Latency (ms)" icon={Activity} />
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="latency-table">
              <thead>
                <tr className="border-b border-gray-100 text-gray-400 text-xs uppercase">
                  <th className="text-left py-2 pr-4">Layer</th>
                  <th className="text-right py-2 px-4">Avg</th>
                  <th className="text-right py-2 px-4">Min</th>
                  <th className="text-right py-2 px-4">Max</th>
                  <th className="text-right py-2 px-4">P95</th>
                  <th className="text-right py-2 px-4">Samples</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {Object.entries(latency).map(([layer, stats]) => (
                  <tr key={layer}>
                    <td className="py-2 pr-4 text-gray-700 font-mono text-xs">{layer}</td>
                    <td className="py-2 px-4 text-right text-gray-800 font-mono">{stats.avg_ms}</td>
                    <td className="py-2 px-4 text-right text-emerald-600 font-mono">{stats.min_ms}</td>
                    <td className="py-2 px-4 text-right text-amber-600 font-mono">{stats.max_ms}</td>
                    <td className="py-2 px-4 text-right text-blue-600 font-mono">{stats.p95_ms}</td>
                    <td className="py-2 px-4 text-right text-gray-400 font-mono">{stats.samples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Fallback Test */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm" data-testid="fallback-test-card">
        <SectionHeader title="Fallback Testi" icon={Shield}>
          <div className="flex items-center gap-2">
            <button
              onClick={() => runFallbackTest(false)}
              disabled={testRunning}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors disabled:opacity-50"
              data-testid="run-fallback-test-btn"
            >
              <Play size={12} /> Normal Test
            </button>
            <button
              onClick={() => runFallbackTest(true)}
              disabled={testRunning}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-amber-500 hover:bg-amber-600 text-white transition-colors disabled:opacity-50"
              data-testid="run-fallback-test-redis-down-btn"
            >
              <AlertTriangle size={12} /> Redis Down
            </button>
          </div>
        </SectionHeader>

        {testRunning && (
          <div className="flex items-center gap-2 py-4 text-gray-500 text-sm">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            Test calisiyor...
          </div>
        )}

        {fallbackResult && !testRunning && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <StatusBadge status={fallbackResult.status} />
              <span className="text-sm text-gray-500">
                Fallback {fallbackResult.fallback_operational ? "calisiyor" : "basarisiz"}
              </span>
            </div>
            {fallbackResult.results && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(fallbackResult.results).map(([step, result]) => (
                  <div key={step} className="bg-gray-50 border border-gray-100 rounded-lg p-3">
                    <div className="text-xs text-gray-400 mb-1 capitalize">{step.replace(/_/g, " ")}</div>
                    <div className="flex items-center gap-1">
                      {typeof result === "object" ? (
                        <>
                          {result.success ? (
                            <CheckCircle size={14} className="text-emerald-500" />
                          ) : (
                            <XCircle size={14} className="text-red-500" />
                          )}
                          <span className="text-xs text-gray-700 font-mono">
                            {result.latency_ms ? `${result.latency_ms}ms` : result.simulated_down ? "simulated" : "—"}
                          </span>
                        </>
                      ) : (
                        <span className="text-xs text-emerald-600 font-medium">{result}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* TTL Configuration */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm" data-testid="ttl-config-card">
        <div
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setTtlExpanded(!ttlExpanded)}
        >
          <SectionHeader title="TTL Yapilandirmasi" icon={Clock} />
          {ttlExpanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
        </div>
        {ttlExpanded && ttlConfig && (
          <div className="mt-4 space-y-4">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="ttl-table">
                <thead>
                  <tr className="border-b border-gray-100 text-gray-400 text-xs uppercase">
                    <th className="text-left py-2">Kategori</th>
                    <th className="text-right py-2">Redis TTL</th>
                    <th className="text-right py-2">Mongo TTL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {Object.entries(ttlConfig.default_matrix || {}).map(([cat, ttls]) => (
                    <tr key={cat}>
                      <td className="py-2 text-gray-700 font-mono text-xs">{cat}</td>
                      <td className="py-2 text-right text-blue-600 font-mono text-xs">{ttls.redis}s</td>
                      <td className="py-2 text-right text-amber-600 font-mono text-xs">{ttls.mongo}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {ttlConfig.supplier_overrides && Object.keys(ttlConfig.supplier_overrides).length > 0 && (
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wider mb-2 font-medium">Supplier TTL Override</div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  {Object.entries(ttlConfig.supplier_overrides).map(([supplier, overrides]) => (
                    <div key={supplier} className="bg-gray-50 border border-gray-100 rounded-lg p-3">
                      <div className="text-xs font-medium text-gray-700 mb-2 uppercase">{supplier}</div>
                      {Object.entries(overrides).map(([cat, ttls]) => (
                        <div key={cat} className="flex items-center justify-between text-xs mb-1">
                          <span className="text-gray-400">{cat}</span>
                          <span className="font-mono text-gray-600">R:{ttls.redis}s / M:{ttls.mongo}s</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recent Events */}
      {events.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm" data-testid="events-card">
          <div
            className="flex items-center justify-between cursor-pointer"
            onClick={() => setEventsExpanded(!eventsExpanded)}
          >
            <SectionHeader title={`Son Olaylar (${events.length})`} icon={BarChart3} />
            {eventsExpanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
          </div>
          {eventsExpanded && (
            <div className="mt-3 space-y-1 max-h-64 overflow-y-auto">
              {events.map((evt, i) => (
                <div key={i} className="flex items-center gap-3 text-xs py-1.5 border-b border-gray-50">
                  <span className={`px-2 py-0.5 rounded font-mono ${
                    evt.type === "fallback" ? "bg-blue-50 text-blue-600" :
                    evt.type === "redis_down" ? "bg-red-50 text-red-600" :
                    evt.type === "stale_serve" ? "bg-amber-50 text-amber-600" :
                    "bg-gray-100 text-gray-500"
                  }`}>
                    {evt.type}
                  </span>
                  <span className="text-gray-400 font-mono">{evt.timestamp?.split("T")[1]?.split(".")[0] || "—"}</span>
                  <span className="text-gray-500 truncate">{JSON.stringify(evt.details)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={resetMetrics}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-gray-200 bg-white hover:bg-gray-50 text-gray-500 transition-colors"
          data-testid="reset-metrics-btn"
        >
          <RotateCcw size={12} /> Metrikleri Sifirla
        </button>
      </div>
    </div>
  );
}
