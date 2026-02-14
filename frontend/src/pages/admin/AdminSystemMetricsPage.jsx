import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Activity, RefreshCw, Users, FileText, MessageSquare, Ticket, Clock, HardDrive, AlertTriangle } from "lucide-react";

export default function AdminSystemMetricsPage() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/system/metrics");
      setMetrics(res.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const MetricCard = ({ icon: Icon, label, value, suffix, color = "text-foreground" }) => (
    <div className="bg-white border rounded-lg p-4 flex items-start gap-3">
      <div className="p-2 bg-gray-50 rounded-lg">
        <Icon className="h-5 w-5 text-muted-foreground" />
      </div>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className={`text-2xl font-bold ${color}`}>{value !== undefined && value !== null ? value : "-"}{suffix && <span className="text-sm font-normal text-muted-foreground/60 ml-1">{suffix}</span>}</p>
      </div>
    </div>
  );

  return (
    <div className="space-y-6" data-testid="system-metrics-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-6 w-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-foreground">Sistem Metrikleri</h1>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
          Yenile
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground/60" />
        </div>
      ) : !metrics ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="empty-state">
          <p>Metrikler yüklenemedi</p>
        </div>
      ) : (
        <div className="space-y-6" data-testid="metrics-data">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard icon={Users} label="Aktif Tenant" value={metrics.active_tenants} />
            <MetricCard icon={Users} label="Toplam Kullanıcı" value={metrics.total_users} />
            <MetricCard icon={FileText} label="Bugünkü Faturalar" value={metrics.invoices_today} />
            <MetricCard icon={MessageSquare} label="Bugünkü SMS" value={metrics.sms_sent_today} />
            <MetricCard icon={Ticket} label="Bugünkü Check-in" value={metrics.tickets_checked_in_today} />
            <MetricCard icon={Clock} label="Ort. Gecikme" value={metrics.avg_request_latency_ms} suffix="ms" />
            <MetricCard 
              icon={AlertTriangle} 
              label="Hata Oranı" 
              value={metrics.error_rate_percent} 
              suffix="%"
              color={metrics.error_rate_percent > 5 ? "text-red-600" : "text-green-600"}
            />
            <MetricCard 
              icon={HardDrive} 
              label="Disk Kullanımı" 
              value={metrics.disk_usage_percent} 
              suffix="%"
              color={metrics.disk_usage_percent > 85 ? "text-red-600" : "text-foreground"}
            />
          </div>
          <p className="text-xs text-muted-foreground/60">Son güncelleme: {metrics.computed_at ? new Date(metrics.computed_at).toLocaleString("tr-TR") : "-"}</p>
        </div>
      )}
    </div>
  );
}
