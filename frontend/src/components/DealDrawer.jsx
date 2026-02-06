import React, { useState, useEffect, useCallback } from "react";
import { X, ChevronRight, Trophy, XCircle, Plus, CheckCircle, Circle, Clock, FileText, Activity, ListChecks, MessageSquare, Loader2 } from "lucide-react";
import { getDeal, patchDeal, moveDealStage, listTasks, createTask, completeTask, listNotes, createNote, getActivity } from "../lib/crm";

const STAGE_LABELS = { lead: "Lead", contacted: "Iletisimde", proposal: "Teklif", won: "Kazanildi", lost: "Kaybedildi" };
const STAGE_COLORS = { lead: "bg-blue-100 text-blue-700", contacted: "bg-green-100 text-green-700", proposal: "bg-yellow-100 text-yellow-700", won: "bg-sky-100 text-sky-700", lost: "bg-red-100 text-red-700" };

function Skeleton({ className = "" }) {
  return <div className={`animate-pulse bg-gray-200 rounded ${className}`} />;
}

function Badge({ stage }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STAGE_COLORS[stage] || "bg-gray-100 text-gray-600"}`}>
      {STAGE_LABELS[stage] || stage}
    </span>
  );
}

function TabButton({ active, label, icon: Icon, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors ${active ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-700"}`}
    >
      <Icon size={14} /> {label}
    </button>
  );
}

function relativeTime(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "az once";
  if (diff < 3600) return `${Math.floor(diff / 60)}dk once`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}sa once`;
  return `${Math.floor(diff / 86400)}g once`;
}

// ─── OVERVIEW TAB ──────────────────────────────────────────────────
function OverviewTab({ deal, onUpdate }) {
  const [editing, setEditing] = useState(null);
  const [val, setVal] = useState("");
  const [saving, setSaving] = useState(false);

  async function save(field) {
    setSaving(true);
    try {
      let payload = {};
      if (field === "amount") payload[field] = Number(val) || 0;
      else payload[field] = val;
      await patchDeal(deal.id, payload);
      onUpdate();
    } catch {} finally { setSaving(false); setEditing(null); }
  }

  function startEdit(field, current) { setEditing(field); setVal(current || ""); }

  const fields = [
    { key: "title", label: "Baslik", value: deal.title },
    { key: "amount", label: "Tutar", value: deal.amount != null ? `${deal.amount} ${deal.currency || "TRY"}` : "-" },
    { key: "owner_user_id", label: "Sahip", value: deal.owner_user_id || "-" },
    { key: "next_action_at", label: "Sonraki Aksiyon", value: deal.next_action_at ? new Date(deal.next_action_at).toLocaleDateString("tr-TR") : "-" },
  ];

  return (
    <div className="space-y-3 py-3">
      {fields.map((f) => (
        <div key={f.key} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
          <div>
            <div className="text-xs text-gray-500">{f.label}</div>
            {editing === f.key ? (
              <div className="flex items-center gap-2 mt-1">
                <input value={val} onChange={(e) => setVal(e.target.value)} className="text-sm border rounded px-2 py-1 w-40" autoFocus
                  onKeyDown={(e) => e.key === "Enter" && save(f.key)} />
                <button onClick={() => save(f.key)} disabled={saving} className="text-blue-600 text-xs font-medium">
                  {saving ? "..." : "Kaydet"}
                </button>
                <button onClick={() => setEditing(null)} className="text-gray-400 text-xs">Iptal</button>
              </div>
            ) : (
              <div className="text-sm font-medium text-gray-900 cursor-pointer" onClick={() => startEdit(f.key, f.key === "amount" ? String(deal.amount || "") : (deal[f.key] || ""))}>
                {f.value}
              </div>
            )}
          </div>
          {editing !== f.key && <ChevronRight size={14} className="text-gray-300" />}
        </div>
      ))}
    </div>
  );
}

// ─── TASKS TAB ─────────────────────────────────────────────────────
function TasksTab({ dealId }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newTitle, setNewTitle] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await listTasks({ relatedType: "deal", relatedId: dealId, status: "" });
      setTasks(res.items || []);
    } catch {} finally { setLoading(false); }
  }, [dealId]);

  useEffect(() => { load(); }, [load]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      await createTask({ title: newTitle, related_type: "deal", related_id: dealId });
      setNewTitle("");
      load();
    } catch {} finally { setCreating(false); }
  }

  async function handleComplete(id) {
    try { await completeTask(id); load(); } catch {}
  }

  if (loading) return <div className="space-y-3 py-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}</div>;

  return (
    <div className="py-3 space-y-2">
      <form onSubmit={handleCreate} className="flex gap-2">
        <input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} placeholder="Yeni gorev..." className="flex-1 text-sm border rounded-lg px-3 py-2" data-testid="deal-task-input" />
        <button type="submit" disabled={creating || !newTitle.trim()} className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50" data-testid="deal-task-add">
          {creating ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
        </button>
      </form>
      {tasks.length === 0 ? (
        <div className="text-center py-8 text-gray-400 text-sm">Bu deal icin gorev yok</div>
      ) : (
        tasks.map((t) => (
          <div key={t.id} className={`flex items-center gap-3 p-2.5 border rounded-lg ${t.status === "done" ? "bg-green-50" : "hover:bg-gray-50"}`}>
            <button onClick={() => t.status !== "done" && handleComplete(t.id)} className="shrink-0">
              {t.status === "done" ? <CheckCircle size={18} className="text-green-500" /> : <Circle size={18} className="text-gray-300" />}
            </button>
            <div className="flex-1 min-w-0">
              <div className={`text-sm truncate ${t.status === "done" ? "line-through text-gray-400" : "text-gray-800"}`}>{t.title}</div>
              {t.due_date && <div className="text-xs text-gray-400">{new Date(t.due_date).toLocaleDateString("tr-TR")}</div>}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ─── NOTES TAB ─────────────────────────────────────────────────────
function NotesTab({ dealId }) {
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await listNotes({ entity_type: "deal", entity_id: dealId });
      setNotes(res.items || []);
    } catch {} finally { setLoading(false); }
  }, [dealId]);

  useEffect(() => { load(); }, [load]);

  async function handleAdd(e) {
    e.preventDefault();
    if (!text.trim()) return;
    setSaving(true);
    try {
      await createNote({ content: text, entity_type: "deal", entity_id: dealId });
      setText("");
      load();
    } catch {} finally { setSaving(false); }
  }

  if (loading) return <div className="space-y-3 py-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}</div>;

  return (
    <div className="py-3 space-y-3">
      <form onSubmit={handleAdd} className="space-y-2">
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Not ekle..." rows={3} className="w-full text-sm border rounded-lg px-3 py-2 resize-none" data-testid="deal-note-input" />
        <button type="submit" disabled={saving || !text.trim()} className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50" data-testid="deal-note-save">
          {saving ? "Kaydediliyor..." : "Not Ekle"}
        </button>
      </form>
      {notes.length === 0 ? (
        <div className="text-center py-8 text-gray-400 text-sm">Henuz not yok</div>
      ) : (
        notes.map((n, i) => (
          <div key={n.id || i} className="p-3 border rounded-lg bg-gray-50">
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{n.content}</p>
            <div className="mt-1 text-xs text-gray-400 flex items-center gap-2">
              <span>{n.created_by_email || ""}</span>
              <span>{relativeTime(n.created_at)}</span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ─── ACTIVITY TAB ──────────────────────────────────────────────────
function ActivityTab({ dealId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await getActivity({ entity_type: "deal", entity_id: dealId });
        setItems(res.items || []);
      } catch {} finally { setLoading(false); }
    })();
  }, [dealId]);

  if (loading) return <div className="space-y-3 py-3">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-8 w-full" />)}</div>;
  if (items.length === 0) return <div className="text-center py-8 text-gray-400 text-sm">Aktivite yok</div>;

  return (
    <div className="py-3 space-y-2">
      {items.map((item, i) => (
        <div key={item.id || i} className="flex items-start gap-3 p-2 border-b border-gray-100 last:border-0">
          <Activity size={14} className="text-gray-400 mt-0.5 shrink-0" />
          <div className="min-w-0">
            <div className="text-sm text-gray-700">{item.action || "Event"}</div>
            <div className="text-xs text-gray-400">{item.actor?.email || ""} &middot; {relativeTime(item.created_at)}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── MAIN DRAWER ───────────────────────────────────────────────────
export default function DealDrawer({ dealId, onClose, onStageChanged }) {
  const [deal, setDeal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("overview");
  const [acting, setActing] = useState(false);

  const load = useCallback(async () => {
    if (!dealId) return;
    setLoading(true);
    try {
      const d = await getDeal(dealId);
      setDeal(d);
    } catch {} finally { setLoading(false); }
  }, [dealId]);

  useEffect(() => { load(); }, [load]);

  async function quickAction(stage) {
    setActing(true);
    try {
      await moveDealStage(dealId, stage);
      load();
      onStageChanged?.();
    } catch {} finally { setActing(false); }
  }

  if (!dealId) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />
      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full sm:w-[460px] bg-white shadow-2xl z-50 flex flex-col" data-testid="deal-drawer">
        {/* Header */}
        <div className="p-4 border-b flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            {loading ? (
              <><Skeleton className="h-5 w-48 mb-2" /><Skeleton className="h-4 w-32" /></>
            ) : deal ? (
              <>
                <h2 className="text-lg font-bold text-gray-900 truncate">{deal.title || deal.id}</h2>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <Badge stage={deal.stage} />
                  <span className="text-sm text-gray-600">{deal.amount != null ? `${deal.amount} ${deal.currency || "TRY"}` : ""}</span>
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {deal.owner_user_id && <span>Sahip: {deal.owner_user_id}</span>}
                  {deal.next_action_at && <span className="ml-2">Aksiyon: {new Date(deal.next_action_at).toLocaleDateString("tr-TR")}</span>}
                </div>
                {/* Quick actions */}
                {deal.stage !== "won" && deal.stage !== "lost" && (
                  <div className="flex gap-2 mt-2">
                    <button onClick={() => quickAction("won")} disabled={acting} className="flex items-center gap-1 px-2.5 py-1 text-xs bg-green-50 text-green-700 border border-green-200 rounded-full hover:bg-green-100 disabled:opacity-50">
                      <Trophy size={12} /> Kazan
                    </button>
                    <button onClick={() => quickAction("lost")} disabled={acting} className="flex items-center gap-1 px-2.5 py-1 text-xs bg-red-50 text-red-700 border border-red-200 rounded-full hover:bg-red-100 disabled:opacity-50">
                      <XCircle size={12} /> Kaybet
                    </button>
                  </div>
                )}
              </>
            ) : <div className="text-sm text-red-500">Deal bulunamadi</div>}
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg shrink-0" data-testid="deal-drawer-close">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b px-2 overflow-x-auto">
          <TabButton active={tab === "overview"} label="Ozet" icon={FileText} onClick={() => setTab("overview")} />
          <TabButton active={tab === "tasks"} label="Gorevler" icon={ListChecks} onClick={() => setTab("tasks")} />
          <TabButton active={tab === "notes"} label="Notlar" icon={MessageSquare} onClick={() => setTab("notes")} />
          <TabButton active={tab === "activity"} label="Aktivite" icon={Activity} onClick={() => setTab("activity")} />
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4">
          {loading ? (
            <div className="space-y-3 py-4">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12 w-full" />)}</div>
          ) : deal ? (
            <>
              {tab === "overview" && <OverviewTab deal={deal} onUpdate={load} />}
              {tab === "tasks" && <TasksTab dealId={deal.id} />}
              {tab === "notes" && <NotesTab dealId={deal.id} />}
              {tab === "activity" && <ActivityTab dealId={deal.id} />}
            </>
          ) : null}
        </div>
      </div>
    </>
  );
}
