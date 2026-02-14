// frontend/src/pages/crm/CrmTasksPage.jsx
import React, { useEffect, useMemo, useState } from "react";
import { listTasks, patchTask } from "../../lib/crm";

function formatDateTime(dateIso) {
  if (!dateIso) return "-";
  const d = new Date(dateIso);
  return d.toLocaleString("tr-TR");
}

function formatRelative(dateIso) {
  if (!dateIso) return "-";
  const d = new Date(dateIso);
  const diffMs = d.getTime() - Date.now();
  const diffSec = Math.round(diffMs / 1000);
  const rtf = new Intl.RelativeTimeFormat("tr", { numeric: "auto" });

  const abs = Math.abs(diffSec);
  if (abs < 60) return rtf.format(diffSec, "second");

  const diffMin = Math.round(diffSec / 60);
  if (Math.abs(diffMin) < 60) return rtf.format(diffMin, "minute");

  const diffHour = Math.round(diffMin / 60);
  if (Math.abs(diffHour) < 24) return rtf.format(diffHour, "hour");

  const diffDay = Math.round(diffHour / 24);
  return rtf.format(diffDay, "day");
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-2.5 py-2 rounded-full border text-sm cursor-pointer transition-colors ${
        active
          ? "border-foreground bg-foreground text-primary-foreground font-semibold"
          : "border-border bg-card text-foreground font-medium hover:bg-muted"
      }`}
    >
      {children}
    </button>
  );
}

function StatusBadge({ status }) {
  const isDone = status === "done";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border ${
        isDone
          ? "border-green-500 bg-green-50 text-green-800"
          : "border-yellow-500 bg-yellow-50 text-yellow-800"
      }`}
    >
      {isDone ? "Tamamlandı" : "Açık"}
    </span>
  );
}

function PriorityBadge({ priority }) {
  const map = {
    low: { label: "Düşük", classes: "text-muted-foreground bg-gray-100" },
    normal: { label: "Normal", classes: "text-blue-700 bg-blue-50" },
    high: { label: "Yüksek", classes: "text-red-700 bg-red-50" },
  };
  const conf = map[priority || "normal"];
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border border-transparent ${conf.classes}`}>
      {conf.label}
    </span>
  );
}

export default function CrmTasksPage() {
  const [activeTab, setActiveTab] = useState("today");
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 50 });
  const [updatingId, setUpdatingId] = useState("");

  const tabConfig = useMemo(
    () => ({
      today: { label: "Bugün", due: "today" },
      overdue: { label: "Gecikenler", due: "overdue" },
      week: { label: "Bu Hafta", due: "week" },
    }),
    []
  );

  async function refresh() {
    setLoading(true);
    setErrMsg("");
    try {
      const cfg = tabConfig[activeTab];
      const res = await listTasks({ due: cfg.due, status: "open" });
      setData(res || { items: [], total: 0, page: 1, page_size: 50 });
    } catch (e) {
      setErrMsg(e.message || "Görevler yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  async function markDone(taskId) {
    if (!taskId) return;
    setUpdatingId(taskId);
    try {
      await patchTask(taskId, { status: "done" });
      await refresh();
    } catch (e) {
      setErrMsg(e.message || "Görev güncellenemedi.");
    } finally {
      setUpdatingId("");
    }
  }

  const items = data.items || [];

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="m-0 text-xl font-bold text-foreground">CRM • Görevler</h1>
          <div className="text-sm text-muted-foreground mt-1">
            Bugün, geciken ve bu hafta içindeki açık görevlerinizi izleyin.
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-3.5 p-2 rounded-full border border-border inline-flex gap-1.5 bg-muted/50">
        <TabButton active={activeTab === "today"} onClick={() => setActiveTab("today")}>
          Bugün
        </TabButton>
        <TabButton active={activeTab === "overdue"} onClick={() => setActiveTab("overdue")}>
          Gecikenler
        </TabButton>
        <TabButton active={activeTab === "week"} onClick={() => setActiveTab("week")}>
          Bu Hafta
        </TabButton>
      </div>

      {/* Error */}
      {errMsg ? (
        <div className="mt-3 p-3 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive text-sm">
          {errMsg}
        </div>
      ) : null}

      {/* List */}
      <div className="mt-3 border border-border rounded-xl overflow-hidden">
        <div className="p-2.5 border-b border-border bg-muted/50 text-sm text-muted-foreground flex justify-between">
          <span>
            {loading ? "Yükleniyor…" : "Görevler"} ({data.total || 0})
          </span>
        </div>

        {!loading && !items.length ? (
          <div className="p-5">
            <div className="text-base font-semibold text-foreground">Bu filtrede görev yok.</div>
            <div className="mt-1.5 text-sm text-muted-foreground">
              Farklı bir sekme deneyebilir veya yeni görevler oluşturabilirsiniz.
            </div>
          </div>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-card">
                <th className="text-left p-3 text-xs text-muted-foreground border-b border-border w-[45%] font-medium">
                  Başlık
                </th>
                <th className="text-left p-3 text-xs text-muted-foreground border-b border-border w-[20%] font-medium">
                  Durum / Öncelik
                </th>
                <th className="text-left p-3 text-xs text-muted-foreground border-b border-border w-[25%] font-medium">
                  Bitiş Tarihi
                </th>
                <th className="text-right p-3 text-xs text-muted-foreground border-b border-border w-[10%] font-medium">
                  İşlemler
                </th>
              </tr>
            </thead>

            <tbody>
              {items.map((t) => (
                <tr key={t.id} className="cursor-default hover:bg-muted/30 transition-colors">
                  <td className="p-3 border-b border-border/50">
                    <div className="font-semibold text-sm text-foreground">{t.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {t.related_type && t.related_id ? (
                        <span>
                          {t.related_type}: {t.related_id}
                        </span>
                      ) : (
                        <span>Bağlantı yok</span>
                      )}
                    </div>
                  </td>

                  <td className="p-3 border-b border-border/50">
                    <div className="flex flex-col gap-1">
                      <StatusBadge status={t.status} />
                      <PriorityBadge priority={t.priority} />
                    </div>
                  </td>

                  <td className="p-3 border-b border-border/50">
                    <div className="text-sm text-foreground">{formatDateTime(t.due_date)}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{formatRelative(t.due_date)}</div>
                  </td>

                  <td className="p-3 border-b border-border/50 text-right">
                    <button
                      type="button"
                      disabled={updatingId === t.id || t.status === "done"}
                      onClick={() => markDone(t.id)}
                      className={`px-2.5 py-1.5 rounded-full border text-xs cursor-pointer transition-colors ${
                        t.status === "done"
                          ? "border-border bg-muted text-muted-foreground cursor-not-allowed"
                          : "border-green-600 bg-green-600 text-white hover:bg-green-700"
                      }`}
                    >
                      {updatingId === t.id
                        ? "İşaretleniyor…"
                        : t.status === "done"
                        ? "Tamamlandı"
                        : "Tamamlandı olarak işaretle"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
