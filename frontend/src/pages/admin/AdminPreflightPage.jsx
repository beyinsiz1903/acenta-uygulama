import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import {
  ShieldCheck, RefreshCw, CheckCircle, XCircle, AlertTriangle,
  Rocket, Database, HardDrive, Lock, Activity, TestTube, Shield
} from "lucide-react";

const CATEGORY_META = {
  database: { label: "Veritabanı", icon: Database, color: "text-blue-600" },
  infrastructure: { label: "Altyapı", icon: HardDrive, color: "text-purple-600" },
  backup: { label: "Yedekleme", icon: Database, color: "text-indigo-600" },
  scheduler: { label: "Zamanlayıcı", icon: Activity, color: "text-teal-600" },
  integrity: { label: "Veri Bütünlüğü", icon: ShieldCheck, color: "text-emerald-600" },
  security: { label: "Güvenlik", icon: Lock, color: "text-red-600" },
  sla: { label: "SLA / Uptime", icon: Activity, color: "text-green-600" },
  testing: { label: "Test", icon: TestTube, color: "text-orange-600" },
};

const STATUS_ICON = {
  pass: { Icon: CheckCircle, color: "text-green-500", bg: "bg-green-50" },
  fail: { Icon: XCircle, color: "text-red-500", bg: "bg-red-50" },
  warn: { Icon: AlertTriangle, color: "text-amber-500", bg: "bg-amber-50" },
};

const VERDICT_STYLE = {
  GO: { bg: "bg-green-600", text: "text-white", label: "✅ GO — Production Ready" },
  "NO-GO": { bg: "bg-red-600", text: "text-white", label: "❌ NO-GO — Kritik Sorunlar" },
  CONDITIONAL: { bg: "bg-amber-500", text: "text-white", label: "⚠️ KOŞULLU — İnceleme Gerekli" },
};

export default function AdminPreflightPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/system/preflight");
      setData(res.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const vs = data ? VERDICT_STYLE[data.verdict] || VERDICT_STYLE["NO-GO"] : null;

  return (
    <div className="space-y-6" data-testid="preflight-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Rocket className="h-6 w-6 text-indigo-600" />
          <h1 className="text-2xl font-bold text-gray-900">Production Go-Live Kontrolü</h1>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
          Yeniden Çalıştır
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 animate-spin text-indigo-400 mx-auto mb-3" />
            <p className="text-gray-500">Preflight kontrolleri çalıştırılıyor...</p>
          </div>
        </div>
      ) : !data ? (
        <div className="text-center py-12 text-gray-500">Sonuç alınamadı</div>
      ) : (
        <div className="space-y-6" data-testid="preflight-results">
          {/* Verdict Banner */}
          <div className={`${vs.bg} ${vs.text} rounded-xl p-6 text-center shadow-lg`}>
            <p className="text-3xl font-bold mb-1">{vs.label}</p>
            <p className="text-sm opacity-90">{data.verdict_detail}</p>
            <div className="flex justify-center gap-6 mt-4 text-sm">
              <span className="flex items-center gap-1"><CheckCircle className="h-4 w-4" /> {data.summary.pass} Geçti</span>
              <span className="flex items-center gap-1"><AlertTriangle className="h-4 w-4" /> {data.summary.warn} Uyarı</span>
              <span className="flex items-center gap-1"><XCircle className="h-4 w-4" /> {data.summary.fail} Başarısız</span>
            </div>
          </div>

          {/* Category Groups */}
          {Object.entries(data.categories || {}).map(([catKey, checks]) => {
            const meta = CATEGORY_META[catKey] || { label: catKey, icon: Shield, color: "text-gray-600" };
            const CatIcon = meta.icon;
            return (
              <div key={catKey} className="bg-white border rounded-lg overflow-hidden">
                <div className="px-4 py-3 bg-gray-50 border-b flex items-center gap-2">
                  <CatIcon className={`h-4 w-4 ${meta.color}`} />
                  <h3 className="font-semibold text-gray-800">{meta.label}</h3>
                  <Badge variant="outline" className="ml-auto">{checks.length}</Badge>
                </div>
                <div className="divide-y divide-gray-100">
                  {checks.map((check, i) => {
                    const si = STATUS_ICON[check.status] || STATUS_ICON.warn;
                    const StatusIcon = si.Icon;
                    return (
                      <div key={i} className={`px-4 py-3 flex items-center gap-3 ${si.bg}`}>
                        <StatusIcon className={`h-5 w-5 flex-shrink-0 ${si.color}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900">{check.name}</p>
                          <p className="text-xs text-gray-500 truncate">{check.detail}</p>
                        </div>
                        {check.critical && check.status === "fail" && (
                          <Badge className="bg-red-100 text-red-700 text-xs">Kritik</Badge>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}

          <p className="text-xs text-gray-400 text-right">
            Kontrol zamanı: {data.checked_at ? new Date(data.checked_at).toLocaleString("tr-TR") : "-"}
          </p>
        </div>
      )}
    </div>
  );
}
