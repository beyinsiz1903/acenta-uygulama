import React, { useState, useEffect, useCallback } from "react";
import { BarChart3, TrendingUp, AlertTriangle, Users, CreditCard, Loader2, RefreshCw, ArrowUpRight, Activity } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { fetchRevenueSummary, fetchUsageOverview, fetchPushStatus } from "../../lib/analytics";

function StatCard({ icon: Icon, label, value, sub, variant }) {
  const colors = {
    default: "border-border",
    success: "border-emerald-500/30 bg-emerald-500/5",
    warning: "border-amber-500/30 bg-amber-500/5",
    danger: "border-destructive/30 bg-destructive/5",
  };
  return (
    <div className={`rounded-lg border p-4 ${colors[variant] || colors.default}`} data-testid={`stat-${label.toLowerCase().replace(/\s/g, "-")}`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-semibold text-foreground">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  );
}

function PlanBar({ plan, count, total, color }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-20 font-medium capitalize">{plan}</span>
      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-16 text-right text-muted-foreground">{count} ({pct}%)</span>
    </div>
  );
}

function QuotaBucketBar({ bucket, count, maxCount }) {
  const pct = maxCount > 0 ? Math.round((count / maxCount) * 100) : 0;
  const isHigh = bucket === "80-100%" || bucket === "100%+";
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className={`w-16 ${isHigh ? "font-medium text-foreground" : "text-muted-foreground"}`}>{bucket}</span>
      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${bucket === "100%+" ? "bg-destructive" : isHigh ? "bg-amber-500" : "bg-primary"}`} style={{ width: `${Math.max(pct, count > 0 ? 5 : 0)}%` }} />
      </div>
      <span className="w-8 text-right text-muted-foreground">{count}</span>
    </div>
  );
}

function formatTRY(amount) {
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 0 }).format(amount);
}

export default function AdminAnalyticsPage() {
  const [revenue, setRevenue] = useState(null);
  const [usage, setUsage] = useState(null);
  const [pushStatus, setPushStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [rev, usg, ps] = await Promise.all([
        fetchRevenueSummary({ lookback: 3 }),
        fetchUsageOverview(),
        fetchPushStatus().catch(() => null),
      ]);
      setRevenue(rev);
      setUsage(usg);
      setPushStatus(ps);
    } catch {
      // partial load ok
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const planColors = { starter: "bg-blue-500", pro: "bg-emerald-500", enterprise: "bg-purple-500" };
  const totalSubs = revenue?.active_subscriptions_count || 0;
  const maxBucket = usage ? Math.max(...(usage.quota_buckets || []).map((b) => b.tenant_count), 1) : 1;

  return (
    <div className="space-y-6" data-testid="admin-analytics-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight" data-testid="analytics-title">Revenue Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">SaaS gelir metrikleri ve kullanım analizi.</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
          {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : <RefreshCw className="h-4 w-4 mr-1.5" />}
          Yenile
        </Button>
      </div>

      {loading && !revenue ? (
        <div className="flex items-center justify-center py-20 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin mr-2" /> Yükleniyor...
        </div>
      ) : (
        <>
          {/* Revenue Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard icon={Users} label="Aktif Subscription" value={totalSubs} variant="default" />
            <StatCard icon={TrendingUp} label="MRR (Gross)" value={formatTRY(revenue?.mrr_gross_active || 0)} variant="success" />
            <StatCard icon={AlertTriangle} label="MRR At Risk" value={formatTRY(revenue?.mrr_at_risk || 0)} variant={revenue?.mrr_at_risk > 0 ? "warning" : "default"} />
            <StatCard icon={CreditCard} label="Past Due" value={revenue?.past_due_count || 0} sub={`Grace: ${revenue?.grace_count || 0} | Canceling: ${revenue?.canceling_count || 0}`} variant={revenue?.past_due_count > 0 ? "danger" : "default"} />
          </div>

          {/* MRR Trend */}
          {(revenue?.trend || []).length > 0 && (
            <div className="border rounded-lg p-4 space-y-3" data-testid="mrr-trend">
              <h3 className="text-sm font-medium text-foreground">MRR Trendi (Son 3 Ay)</h3>
              <div className="flex items-end gap-2 h-24">
                {revenue.trend.map((t, i) => {
                  const maxMRR = Math.max(...revenue.trend.map((x) => x.mrr_gross_active), 1);
                  const pct = Math.max(5, Math.round((t.mrr_gross_active / maxMRR) * 100));
                  return (
                    <div key={t.period} className="flex-1 flex flex-col items-center gap-1">
                      <span className="text-[10px] text-muted-foreground">{formatTRY(t.mrr_gross_active)}</span>
                      <div className="w-full rounded-t bg-primary/80 transition-all" style={{ height: `${pct}%` }} />
                      <span className="text-[10px] text-muted-foreground">{t.period}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Plan Distribution */}
            <div className="border rounded-lg p-4 space-y-3">
              <h3 className="text-sm font-medium text-foreground">Plan Dağılımı</h3>
              {Object.keys(revenue?.plan_distribution || {}).length === 0 ? (
                <p className="text-xs text-muted-foreground">Henüz aktif subscription yok.</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(revenue?.plan_distribution || {}).map(([plan, count]) => (
                    <PlanBar key={plan} plan={plan} count={count} total={totalSubs} color={planColors[plan] || "bg-muted-foreground"} />
                  ))}
                </div>
              )}
            </div>

            {/* Quota Buckets */}
            <div className="border rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-foreground">Quota Kullanımı (B2B Talep)</h3>
                {(usage?.exceeded_count || 0) > 0 && (
                  <Badge variant="destructive" className="text-[10px]">{usage.exceeded_count} aşım</Badge>
                )}
              </div>
              <div className="space-y-1.5">
                {(usage?.quota_buckets || []).map((b) => (
                  <QuotaBucketBar key={b.bucket} bucket={b.bucket} count={b.tenant_count} maxCount={maxBucket} />
                ))}
              </div>
              {(usage?.over_80_count || 0) > 0 && (
                <p className="text-xs text-amber-600">Quota'nın %80'inin üstünde: {usage.over_80_count} tenant</p>
              )}
            </div>
          </div>

          {/* Enterprise Candidates */}
          {(usage?.enterprise_candidates_count || 0) > 0 && (
            <div className="border rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2">
                <ArrowUpRight className="h-4 w-4 text-purple-500" />
                <h3 className="text-sm font-medium text-foreground">Enterprise Adayları</h3>
                <Badge className="bg-purple-500/10 text-purple-700 border-purple-500/20 text-[10px]">
                  {usage.enterprise_candidates_count} tenant
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">Pro planda olup quota'nın %80'ini aşan tenant'lar.</p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-1.5 px-2 text-muted-foreground font-medium">Tenant ID</th>
                      <th className="text-right py-1.5 px-2 text-muted-foreground font-medium">Kullanım</th>
                      <th className="text-right py-1.5 px-2 text-muted-foreground font-medium">Quota</th>
                      <th className="text-right py-1.5 px-2 text-muted-foreground font-medium">Oran</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(usage?.top_candidates || []).map((c) => (
                      <tr key={c.tenant_id} className="border-b hover:bg-muted/30">
                        <td className="py-1.5 px-2 font-mono">{c.tenant_id.slice(0, 16)}...</td>
                        <td className="py-1.5 px-2 text-right">{c.used}</td>
                        <td className="py-1.5 px-2 text-right">{c.quota}</td>
                        <td className="py-1.5 px-2 text-right font-medium">{Math.round(c.usage_ratio * 100)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {revenue?.generated_at && (
            <p className="text-[10px] text-muted-foreground text-right">
              Oluşturulma: {new Date(revenue.generated_at).toLocaleString("tr-TR")}
            </p>
          )}
        </>
      )}
    </div>
  );
}
