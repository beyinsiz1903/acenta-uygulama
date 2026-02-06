import React, { useState, useEffect, useCallback } from "react";
import { Loader2, Search, ChevronDown } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { Badge } from "../../components/ui/badge";
import { fetchAuditLogs } from "../../lib/auditLogs";
import { fetchTenantList } from "../../lib/tenantFeaturesAdmin";

function DiffSummary({ before, after }) {
  if (!before?.features && !after?.features) return <span className="text-muted-foreground">-</span>;

  const bSet = new Set(before?.features || []);
  const aSet = new Set(after?.features || []);
  const added = [...aSet].filter((f) => !bSet.has(f));
  const removed = [...bSet].filter((f) => !aSet.has(f));

  return (
    <div className="flex flex-wrap gap-1">
      {added.map((f) => (
        <Badge key={`+${f}`} variant="default" className="text-[10px] px-1.5 py-0 bg-green-600">+{f}</Badge>
      ))}
      {removed.map((f) => (
        <Badge key={`-${f}`} variant="destructive" className="text-[10px] px-1.5 py-0">-{f}</Badge>
      ))}
      {added.length === 0 && removed.length === 0 && (
        <span className="text-xs text-muted-foreground">Değişiklik yok</span>
      )}
    </div>
  );
}

function formatDate(iso) {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("tr-TR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function AdminAuditLogPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [filterTenant, setFilterTenant] = useState("");
  const [filterAction, setFilterAction] = useState("");

  // Load tenants for filter dropdown
  useEffect(() => {
    fetchTenantList().then((d) => setTenants(d.items || [])).catch(() => {});
  }, []);

  const loadLogs = useCallback(async (cursor) => {
    const params = { limit: 50 };
    if (filterTenant) params.tenant_id = filterTenant;
    if (filterAction) params.action = filterAction;
    if (cursor) params.cursor = cursor;

    try {
      const data = await fetchAuditLogs(params);
      if (cursor) {
        setLogs((prev) => [...prev, ...(data.items || [])]);
      } else {
        setLogs(data.items || []);
      }
      setNextCursor(data.next_cursor);
    } catch {
      if (!cursor) setLogs([]);
    }
  }, [filterTenant, filterAction]);

  useEffect(() => {
    setLoading(true);
    loadLogs(null).finally(() => setLoading(false));
  }, [loadLogs]);

  const handleLoadMore = async () => {
    if (!nextCursor) return;
    setLoadingMore(true);
    await loadLogs(nextCursor);
    setLoadingMore(false);
  };

  const tenantNameMap = {};
  tenants.forEach((t) => { tenantNameMap[t.id] = t.name || t.slug || t.id; });

  return (
    <div className="space-y-6" data-testid="admin-audit-log-page">
      <div>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight" data-testid="audit-log-title">
          Audit Log
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Tenant feature değişiklikleri ve admin aksiyonları.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div className="w-56">
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Tenant</label>
          <Select value={filterTenant} onValueChange={setFilterTenant}>
            <SelectTrigger className="h-9" data-testid="audit-tenant-filter">
              <SelectValue placeholder="Tümü" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Tümü</SelectItem>
              {tenants.map((t) => (
                <SelectItem key={t.id} value={t.id}>{t.name || t.slug || t.id.slice(0, 12)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-56">
          <label className="text-xs font-medium text-muted-foreground mb-1 block">Aksiyon</label>
          <Select value={filterAction} onValueChange={setFilterAction}>
            <SelectTrigger className="h-9" data-testid="audit-action-filter">
              <SelectValue placeholder="Tümü" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Tümü</SelectItem>
              <SelectItem value="tenant_features.updated">Feature Güncelleme</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="audit-log-table">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Tarih</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Aksiyon</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Tenant</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Actor</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Değişiklik</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-muted-foreground">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
                    Yükleniyor...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-muted-foreground" data-testid="audit-empty">
                    Henüz kayıt yok.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="border-t hover:bg-muted/30">
                    <td className="px-4 py-2.5 whitespace-nowrap text-xs">{formatDate(log.created_at)}</td>
                    <td className="px-4 py-2.5">
                      <Badge variant="outline" className="text-[11px]">{log.action}</Badge>
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      {tenantNameMap[log.tenant_id] || log.tenant_id?.slice(0, 12) + "..."}
                    </td>
                    <td className="px-4 py-2.5 text-xs">{log.actor_email}</td>
                    <td className="px-4 py-2.5">
                      <DiffSummary before={log.before} after={log.after} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {nextCursor && logs.length > 0 && (
          <div className="border-t px-4 py-3 flex justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={handleLoadMore}
              disabled={loadingMore}
              data-testid="load-more-btn"
            >
              {loadingMore ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : <ChevronDown className="h-4 w-4 mr-1.5" />}
              Daha fazla yükle
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
