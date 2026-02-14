import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Bug, RefreshCw, Clock } from "lucide-react";

const SEVERITY_MAP = {
  critical: { label: "Kritik", className: "bg-red-100 text-red-700" },
  error: { label: "Hata", className: "bg-orange-100 text-orange-700" },
  warning: { label: "Uyarı", className: "bg-amber-100 text-amber-700" },
  info: { label: "Bilgi", className: "bg-blue-100 text-blue-700" },
};

export default function AdminSystemErrorsPage() {
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const params = filter ? `?severity=${filter}` : "";
      const res = await api.get(`/admin/system/errors${params}`);
      setErrors(res.data?.items || []);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6" data-testid="system-errors-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bug className="h-6 w-6 text-red-600" />
          <h1 className="text-2xl font-bold text-foreground">Sistem Hataları</h1>
        </div>
        <div className="flex gap-2">
          <select
            className="border rounded px-3 py-1.5 text-sm bg-white"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="">Tüm Seviyeler</option>
            <option value="critical">Kritik</option>
            <option value="error">Hata</option>
            <option value="warning">Uyarı</option>
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
      ) : errors.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="empty-state">
          <Bug className="h-12 w-12 mx-auto mb-3 text-muted-foreground/40" />
          <p>Hata bulunamadı</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="errors-list">
          {errors.map((err, i) => {
            const sv = SEVERITY_MAP[err.severity] || { label: err.severity, className: "bg-gray-100 text-muted-foreground" };
            return (
              <div key={err._id || i} className="bg-white border rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge className={sv.className}>{sv.label}</Badge>
                    <span className="text-sm font-medium text-foreground">{err.message}</span>
                  </div>
                  <Badge variant="outline">{err.count || 1}x</Badge>
                </div>
                {err.stack_trace && (
                  <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto max-h-24 text-muted-foreground">
                    {err.stack_trace}
                  </pre>
                )}
                <div className="flex gap-4 text-xs text-muted-foreground/60">
                  <span><Clock className="h-3 w-3 inline mr-1" />İlk: {err.first_seen ? new Date(err.first_seen).toLocaleString("tr-TR") : "-"}</span>
                  <span><Clock className="h-3 w-3 inline mr-1" />Son: {err.last_seen ? new Date(err.last_seen).toLocaleString("tr-TR") : "-"}</span>
                  {err.request_id && <span>Request: {err.request_id}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
