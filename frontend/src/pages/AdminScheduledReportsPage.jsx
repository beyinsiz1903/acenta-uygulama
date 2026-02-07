import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Calendar, Clock, Mail, Plus, Trash2, RefreshCw, FileText } from "lucide-react";
import { cn } from "../lib/utils";

const REPORT_TYPES = [
  { value: "sales_summary", label: "Satış Özeti" },
  { value: "revenue_report", label: "Gelir Raporu" },
  { value: "occupancy", label: "Doluluk Raporu" },
  { value: "crm_pipeline", label: "CRM Pipeline" },
  { value: "financial_summary", label: "Finansal Özet" },
];

const FREQUENCIES = [
  { value: "daily", label: "Günlük" },
  { value: "weekly", label: "Haftalık" },
  { value: "monthly", label: "Aylık" },
];

export default function AdminScheduledReportsPage() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newSchedule, setNewSchedule] = useState({
    report_type: "sales_summary",
    frequency: "daily",
    email: "",
  });

  const loadSchedules = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/report-schedules");
      setSchedules(res.data?.items || []);
    } catch (e) {
      console.error("Failed to load schedules:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSchedules(); }, [loadSchedules]);

  const handleCreate = async () => {
    if (!newSchedule.email) return;
    try {
      setCreating(true);
      await api.post("/admin/report-schedules", newSchedule);
      setShowCreate(false);
      setNewSchedule({ report_type: "sales_summary", frequency: "daily", email: "" });
      await loadSchedules();
    } catch (e) {
      alert("Oluşturma hatası: " + (e.response?.data?.error?.message || e.message));
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Bu zamanlanmış raporu silmek istediğinize emin misiniz?")) return;
    try {
      await api.delete(`/admin/report-schedules/${id}`);
      await loadSchedules();
    } catch (e) {
      alert("Silme hatası: " + (e.response?.data?.error?.message || e.message));
    }
  };

  const handleTrigger = async () => {
    try {
      const res = await api.post("/admin/report-schedules/execute-due");
      const count = res.data?.count || 0;
      alert(`${count} rapor çalıştırıldı (simülasyon).`);
      await loadSchedules();
    } catch (e) {
      alert("Tetikleme hatası: " + (e.response?.data?.error?.message || e.message));
    }
  };

  const getFreqBadge = (freq) => {
    const map = {
      daily: { label: "Günlük", className: "bg-blue-50 text-blue-700 border-blue-200" },
      weekly: { label: "Haftalık", className: "bg-purple-50 text-purple-700 border-purple-200" },
      monthly: { label: "Aylık", className: "bg-green-50 text-green-700 border-green-200" },
    };
    const s = map[freq] || { label: freq, className: "" };
    return <Badge variant="outline" className={s.className}>{s.label}</Badge>;
  };

  return (
    <div className="p-6" data-testid="scheduled-reports-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Calendar className="h-6 w-6" />
            Zamanlanmış Raporlar
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Otomatik rapor gönderimi zamanlamalarını yönetin.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleTrigger} data-testid="trigger-btn">
            <RefreshCw className="h-4 w-4 mr-1" /> Bekleyenleri Çalıştır
          </Button>
          <Button size="sm" onClick={() => setShowCreate(!showCreate)} data-testid="create-schedule-btn">
            <Plus className="h-4 w-4 mr-1" /> Yeni Zamanlama
          </Button>
        </div>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="rounded-lg border p-4 mb-6 bg-muted/20" data-testid="create-schedule-form">
          <h3 className="text-sm font-semibold mb-3">Yeni Rapor Zamanlaması</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium mb-1 block">Rapor Türü</label>
              <select
                value={newSchedule.report_type}
                onChange={(e) => setNewSchedule({ ...newSchedule, report_type: e.target.value })}
                className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                data-testid="report-type-select"
              >
                {REPORT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium mb-1 block">Sıklık</label>
              <select
                value={newSchedule.frequency}
                onChange={(e) => setNewSchedule({ ...newSchedule, frequency: e.target.value })}
                className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                data-testid="frequency-select"
              >
                {FREQUENCIES.map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium mb-1 block">E-posta</label>
              <input
                type="email"
                value={newSchedule.email}
                onChange={(e) => setNewSchedule({ ...newSchedule, email: e.target.value })}
                placeholder="rapor@sirket.com"
                className="w-full rounded-md border px-3 py-2 text-sm bg-background"
                data-testid="schedule-email-input"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-3">
            <Button variant="outline" size="sm" onClick={() => setShowCreate(false)}>İptal</Button>
            <Button size="sm" onClick={handleCreate} disabled={creating || !newSchedule.email} data-testid="submit-schedule-btn">
              {creating ? "Oluşturuluyor..." : "Oluştur"}
            </Button>
          </div>
        </div>
      )}

      {/* Schedules List */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      ) : schedules.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="no-schedules">
          <Calendar className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p>Henüz zamanlanmış rapor yok.</p>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 border-b">
                <th className="text-left px-4 py-2.5 font-medium">Rapor Türü</th>
                <th className="text-left px-4 py-2.5 font-medium">Sıklık</th>
                <th className="text-left px-4 py-2.5 font-medium">E-posta</th>
                <th className="text-left px-4 py-2.5 font-medium">Sonraki Çalıştırma</th>
                <th className="text-left px-4 py-2.5 font-medium">Çalıştırma Sayısı</th>
                <th className="text-right px-4 py-2.5 font-medium">Aksiyonlar</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => (
                <tr key={s.id} className="border-b last:border-0 hover:bg-muted/30" data-testid={`schedule-row-${s.id}`}>
                  <td className="px-4 py-3 font-medium flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    {REPORT_TYPES.find((t) => t.value === s.report_type)?.label || s.report_type}
                  </td>
                  <td className="px-4 py-3">{getFreqBadge(s.frequency)}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Mail className="h-3.5 w-3.5" />
                      {s.email}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5" />
                      {s.next_run ? new Date(s.next_run).toLocaleString("tr-TR") : "-"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge variant="outline">{s.run_count || 0}</Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(s.id)}
                      data-testid={`delete-schedule-${s.id}`}
                      className="h-7 text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
