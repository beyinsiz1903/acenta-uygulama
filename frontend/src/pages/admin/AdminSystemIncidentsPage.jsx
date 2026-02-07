import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { AlertOctagon, RefreshCw, Plus, CheckCircle, Clock, X } from "lucide-react";

const SEVERITY_MAP = {
  critical: { label: "Kritik", className: "bg-red-100 text-red-700" },
  high: { label: "Yüksek", className: "bg-orange-100 text-orange-700" },
  medium: { label: "Orta", className: "bg-amber-100 text-amber-700" },
  low: { label: "Düşük", className: "bg-blue-100 text-blue-700" },
};

export default function AdminSystemIncidentsPage() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [resolveId, setResolveId] = useState(null);
  const [resolveNotes, setResolveNotes] = useState("");
  const [form, setForm] = useState({
    severity: "medium",
    title: "",
    affected_tenants: [],
    root_cause: "",
  });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/system/incidents");
      setIncidents(res.data?.items || []);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    try {
      setCreating(true);
      await api.post("/admin/system/incidents", form);
      setShowCreate(false);
      setForm({ severity: "medium", title: "", affected_tenants: [], root_cause: "" });
      await load();
    } catch (e) { console.error(e); } finally { setCreating(false); }
  };

  const handleResolve = async () => {
    if (!resolveId) return;
    try {
      await api.patch(`/admin/system/incidents/${resolveId}/resolve`, {
        resolution_notes: resolveNotes,
      });
      setResolveId(null);
      setResolveNotes("");
      await load();
    } catch (e) { console.error(e); }
  };

  return (
    <div className="space-y-6" data-testid="system-incidents-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertOctagon className="h-6 w-6 text-orange-600" />
          <h1 className="text-2xl font-bold text-gray-900">Olay Yönetimi</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Yenile
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)} data-testid="create-incident-btn">
            <Plus className="h-4 w-4 mr-1" />
            Yeni Olay
          </Button>
        </div>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-white border rounded-lg p-4 space-y-3" data-testid="create-incident-form">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">Yeni Olay Oluştur</h3>
            <Button variant="ghost" size="sm" onClick={() => setShowCreate(false)}><X className="h-4 w-4" /></Button>
          </div>
          <input
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="Başlık"
            value={form.title}
            onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))}
            data-testid="incident-title-input"
          />
          <select
            className="w-full border rounded px-3 py-2 text-sm bg-white"
            value={form.severity}
            onChange={(e) => setForm(f => ({ ...f, severity: e.target.value }))}
          >
            <option value="low">Düşük</option>
            <option value="medium">Orta</option>
            <option value="high">Yüksek</option>
            <option value="critical">Kritik</option>
          </select>
          <textarea
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="Kök neden"
            value={form.root_cause}
            onChange={(e) => setForm(f => ({ ...f, root_cause: e.target.value }))}
            rows={2}
            data-testid="incident-root-cause-input"
          />
          <Button size="sm" onClick={handleCreate} disabled={creating || !form.title} data-testid="submit-incident-btn">
            {creating ? "Oluşturuluyor..." : "Oluştur"}
          </Button>
        </div>
      )}

      {/* Resolve Modal */}
      {resolveId && (
        <div className="bg-white border rounded-lg p-4 space-y-3 border-green-200" data-testid="resolve-form">
          <h3 className="font-medium text-green-700">Olay Çöz</h3>
          <textarea
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="Çözüm notları"
            value={resolveNotes}
            onChange={(e) => setResolveNotes(e.target.value)}
            rows={2}
            data-testid="resolve-notes-input"
          />
          <div className="flex gap-2">
            <Button size="sm" onClick={handleResolve} disabled={!resolveNotes} data-testid="submit-resolve-btn">
              <CheckCircle className="h-4 w-4 mr-1" /> Çöz
            </Button>
            <Button variant="ghost" size="sm" onClick={() => { setResolveId(null); setResolveNotes(""); }}>İptal</Button>
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      ) : incidents.length === 0 ? (
        <div className="text-center py-12 text-gray-500" data-testid="empty-state">
          <AlertOctagon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p>Olay bulunamadı</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="incidents-list">
          {incidents.map((inc) => {
            const sv = SEVERITY_MAP[inc.severity] || { label: inc.severity, className: "bg-gray-100 text-gray-600" };
            const resolved = !!inc.end_time;
            return (
              <div key={inc.incident_id || inc._id} className={`bg-white border rounded-lg p-4 ${resolved ? "opacity-70" : ""}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Badge className={sv.className}>{sv.label}</Badge>
                    <span className="font-medium text-gray-900">{inc.title}</span>
                    {resolved && <Badge className="bg-green-100 text-green-700">Çözüldü</Badge>}
                  </div>
                  {!resolved && (
                    <Button variant="outline" size="sm" onClick={() => setResolveId(inc.incident_id || inc._id)} data-testid="resolve-btn">
                      <CheckCircle className="h-4 w-4 mr-1" /> Çöz
                    </Button>
                  )}
                </div>
                {inc.root_cause && <p className="text-sm text-gray-600 mb-1">Neden: {inc.root_cause}</p>}
                {inc.resolution_notes && <p className="text-sm text-green-700 mb-1">Çözüm: {inc.resolution_notes}</p>}
                <div className="flex gap-4 text-xs text-gray-400">
                  <span><Clock className="h-3 w-3 inline mr-1" />Başlangıç: {inc.start_time ? new Date(inc.start_time).toLocaleString("tr-TR") : "-"}</span>
                  {resolved && <span><Clock className="h-3 w-3 inline mr-1" />Bitiş: {new Date(inc.end_time).toLocaleString("tr-TR")}</span>}
                  {inc.affected_tenants?.length > 0 && <span>Etkilenen: {inc.affected_tenants.join(", ")}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
