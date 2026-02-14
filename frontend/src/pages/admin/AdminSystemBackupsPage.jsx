import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Database, Trash2, Play, RefreshCw, Clock } from "lucide-react";

const STATUS_MAP = {
  completed: { label: "Tamamlandı", className: "bg-green-100 text-green-700" },
  failed: { label: "Başarısız", className: "bg-red-100 text-red-700" },
  running: { label: "Çalışıyor", className: "bg-blue-100 text-blue-700" },
};

export default function AdminSystemBackupsPage() {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/system/backups");
      setBackups(res.data?.items || []);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runBackup = async () => {
    try {
      setRunning(true);
      await api.post("/admin/system/backups/run");
      await load();
    } catch (e) { console.error(e); } finally { setRunning(false); }
  };

  const deleteBackup = async (id) => {
    if (!window.confirm("Bu yedeği silmek istediğinize emin misiniz?")) return;
    try {
      await api.delete(`/admin/system/backups/${id}`);
      await load();
    } catch (e) { console.error(e); }
  };

  const formatSize = (bytes) => {
    if (!bytes) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="space-y-6" data-testid="system-backups-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Database className="h-6 w-6 text-indigo-600" />
          <h1 className="text-2xl font-bold text-foreground">Sistem Yedekleri</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Yenile
          </Button>
          <Button size="sm" onClick={runBackup} disabled={running} data-testid="run-backup-btn">
            <Play className="h-4 w-4 mr-1" />
            {running ? "Çalışıyor..." : "Yedek Al"}
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground/60" />
        </div>
      ) : backups.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="empty-state">
          <Database className="h-12 w-12 mx-auto mb-3 text-muted-foreground/40" />
          <p>Henüz yedek bulunmuyor</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200" data-testid="backups-table">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Dosya</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Tür</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Boyut</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Durum</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Tarih</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {backups.map((b) => {
                const st = STATUS_MAP[b.status] || { label: b.status, className: "bg-gray-100 text-muted-foreground" };
                return (
                  <tr key={b.backup_id || b._id}>
                    <td className="px-4 py-3 text-sm font-mono text-foreground">{b.filename}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground capitalize">{b.type}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{formatSize(b.size_bytes)}</td>
                    <td className="px-4 py-3">
                      <Badge className={st.className}>{st.label}</Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      <Clock className="h-3 w-3 inline mr-1" />
                      {b.created_at ? new Date(b.created_at).toLocaleString("tr-TR") : "-"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button variant="ghost" size="sm" onClick={() => deleteBackup(b.backup_id || b._id)}>
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
