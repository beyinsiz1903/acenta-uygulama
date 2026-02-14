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
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 11,
        border: "1px solid " + (isDone ? "#16a34a" : "#eab308"),
        background: isDone ? "#dcfce7" : "#fef9c3",
        color: isDone ? "#166534" : "#854d0e",
      }}
    >
      {isDone ? "Tamamland\u0131" : "A\u00e7\u0131k"}
    </span>
  );
}

function PriorityBadge({ priority }) {
  const map = {
    low: { label: "D\u00fc\u015f\u00fck", color: "#4b5563", bg: "#e5e7eb" },
    normal: { label: "Normal", color: "#1d4ed8", bg: "#dbeafe" },
    high: { label: "Y\u00fcksek", color: "#b91c1c", bg: "#fee2e2" },
  };
  const conf = map[priority || "normal"];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 11,
        border: "1px solid transparent",
        background: conf.bg,
        color: conf.color,
      }}
    >
      {conf.label}
    </span>
  );
}

export default function CrmTasksPage() {
  const [activeTab, setActiveTab] = useState("today"); // "today" | "overdue" | "week"
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 50 });
  const [updatingId, setUpdatingId] = useState("");

  const tabConfig = useMemo(
    () => ({
      today: { label: "Bug\u00fcn", due: "today" },
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
      setErrMsg(e.message || "G\u00f6revler y\u00fcklenemedi.");
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
      setErrMsg(e.message || "G\u00f6rev g\u00fcncellenemedi.");
    } finally {
      setUpdatingId("");
    }
  }

  const items = data.items || [];

  return (
    <div style={{ padding: 16 }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>CRM • Görevler</h1>
          <div style={{ color: "#666", marginTop: 4, fontSize: 13 }}>
            Bugün, geciken ve bu hafta içindeki açık görevlerinizi izleyin.
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div
        style={{
          marginTop: 14,
          padding: 8,
          borderRadius: 999,
          border: "1px solid #eee",
          display: "inline-flex",
          gap: 6,
          background: "#fafafa",
        }}
      >
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
        <div
          style={{
            marginTop: 12,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #f2caca",
            background: "#fff5f5",
            color: "#8a1f1f",
          }}
        >
          {errMsg}
        </div>
      ) : null}

      {/* List */}
      <div style={{ marginTop: 12, border: "1px solid #eee", borderRadius: 12, overflow: "hidden" }}>
        <div
          style={{
            padding: 10,
            borderBottom: "1px solid #eee",
            background: "#fafafa",
            fontSize: 13,
            color: "#666",
            display: "flex",
            justifyContent: "space-between",
          }}
        >
          <span>
            {loading ? "Yükleniyor…" : "Görevler"} ({data.total || 0})
          </span>
        </div>

        {!loading && !items.length ? (
          <div style={{ padding: 18 }}>
            <div style={{ fontSize: 16, fontWeight: 600 }}>Bu filtrede görev yok.</div>
            <div style={{ marginTop: 6, color: "#666" }}>
              Farklı bir sekme deneyebilir veya yeni görevler oluşturabilirsiniz.
            </div>
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#fff" }}>
                <th
                  style={{
                    textAlign: "left",
                    padding: 12,
                    fontSize: 12,
                    color: "#666",
                    borderBottom: "1px solid #eee",
                    width: "45%",
                  }}
                >
                  Ba\u015fl\u0131k
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: 12,
                    fontSize: 12,
                    color: "#666",
                    borderBottom: "1px solid #eee",
                    width: "20%",
                  }}
                >
                  Durum / \u00d6ncelik
                </th>
                <th
                  style={{
                    textAlign: "left",
                    padding: 12,
                    fontSize: 12,
                    color: "#666",
                    borderBottom: "1px solid #eee",
                    width: "25%",
                  }}
                >
                  Biti\u015f Tarihi
                </th>
                <th
                  style={{
                    textAlign: "right",
                    padding: 12,
                    fontSize: 12,
                    color: "#666",
                    borderBottom: "1px solid #eee",
                    width: "10%",
                  }}
                >
                  \u0130\u015flemler
                </th>
              </tr>
            </thead>

            <tbody>
              {items.map((t) => (
                <tr key={t.id} style={{ cursor: "default" }}>
                  <td style={{ padding: 12, borderBottom: "1px solid #f3f3f3" }}>
                    <div style={{ fontWeight: 600 }}>{t.title}</div>
                    <div style={{ fontSize: 12, color: "#666", marginTop: 2 }}>
                      {t.related_type && t.related_id ? (
                        <span>
                          {t.related_type}: {t.related_id}
                        </span>
                      ) : (
                        <span>Ba\u011flant\u0131 yok</span>
                      )}
                    </div>
                  </td>

                  <td style={{ padding: 12, borderBottom: "1px solid #f3f3f3" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <StatusBadge status={t.status} />
                      <PriorityBadge priority={t.priority} />
                    </div>
                  </td>

                  <td style={{ padding: 12, borderBottom: "1px solid #f3f3f3" }}>
                    <div style={{ fontSize: 13 }}>{formatDateTime(t.due_date)}</div>
                    <div style={{ fontSize: 11, color: "#666", marginTop: 2 }}>{formatRelative(t.due_date)}</div>
                  </td>

                  <td style={{ padding: 12, borderBottom: "1px solid #f3f3f3", textAlign: "right" }}>
                    <button
                      type="button"
                      disabled={updatingId === t.id || t.status === "done"}
                      onClick={() => markDone(t.id)}
                      style={{
                        padding: "6px 10px",
                        borderRadius: 999,
                        border: "1px solid #16a34a",
                        background: t.status === "done" ? "#e5e7eb" : "#16a34a",
                        color: t.status === "done" ? "#4b5563" : "#ecfdf3",
                        cursor: t.status === "done" ? "not-allowed" : "pointer",
                        fontSize: 12,
                      }}
                    >
                      {updatingId === t.id
                        ? `\u0130\u015faretleniyor${"\\u2026"}`
                        : t.status === "done"
                        ? "Tamamland\u0131"
                        : "Tamamland\u0131 olarak i\u015faretle"}
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
