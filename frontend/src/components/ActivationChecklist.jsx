import React, { useState, useEffect } from "react";
import { getChecklist, completeChecklistItem } from "../lib/gtm";

export default function ActivationChecklist() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [completing, setCompleting] = useState(null);

  useEffect(() => { loadChecklist(); }, []);

  async function loadChecklist() {
    try { const res = await getChecklist(); setData(res); }
    catch { setData(null); }
    finally { setLoading(false); }
  }

  async function handleComplete(key) {
    setCompleting(key);
    try { await completeChecklistItem(key); await loadChecklist(); }
    catch (e) { console.error(e); }
    finally { setCompleting(null); }
  }

  if (loading || !data || dismissed || data.all_completed) return null;
  const items = data.items || [];
  const completedCount = data.completed_count || 0;
  const total = data.total || items.length;
  const pct = total > 0 ? Math.round((completedCount / total) * 100) : 0;

  return (
    <div className="bg-white border border-blue-200 rounded-xl shadow-sm mb-4" data-testid="activation-checklist">
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-50 rounded-full flex items-center justify-center">
            <span className="text-blue-600 font-bold text-sm">{pct}%</span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Aktivasyon Kontrol Listesi</h3>
            <p className="text-xs text-gray-500">{completedCount}/{total} tamamlandi</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setCollapsed(!collapsed)} className="p-1 hover:bg-gray-100 rounded text-gray-500">
            {collapsed ? "\u25BC" : "\u25B2"}
          </button>
          <button onClick={() => setDismissed(true)} className="p-1 hover:bg-gray-100 rounded text-gray-400" title="Kapat">\u2715</button>
        </div>
      </div>
      <div className="px-4 pb-2"><div className="w-full bg-gray-200 rounded-full h-1.5"><div className="bg-blue-600 h-1.5 rounded-full transition-all" style={{ width: `${pct}%` }} /></div></div>
      {!collapsed && (
        <div className="px-4 pb-4 space-y-2">
          {items.map((item) => {
            const done = !!item.completed_at;
            return (
              <div key={item.key} className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${done ? "bg-green-50" : "hover:bg-gray-50 cursor-pointer"}`} onClick={() => !done && handleComplete(item.key)} data-testid={`checklist-item-${item.key}`}>
                {done ? <span className="text-green-500">\u2713</span> : completing === item.key ? <span className="animate-spin">\u25CB</span> : <span className="text-gray-300">\u25CB</span>}
                <span className={`text-sm ${done ? "text-green-700 line-through" : "text-gray-700"}`}>{item.label}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
