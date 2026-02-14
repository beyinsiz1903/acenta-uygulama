// frontend/src/pages/crm/CrmPipelinePage.jsx
import React, { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { listDeals, createDeal, moveDealStage } from "../../lib/crm";
import { getUser, apiErrorMessage } from "../../lib/api";
import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, closestCenter } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import DealDrawer from "../../components/DealDrawer";
import { Lock, Plus, GripVertical } from "lucide-react";

/* ─── Stage config ──────────────────────────────────────────────── */
const STAGES = ["lead", "contacted", "proposal", "won", "lost"];
const STAGE_META = {
  lead:      { title: "Lead",        bg: "#eff6ff", color: "#1d4ed8", dot: "#3b82f6" },
  contacted: { title: "Iletisimde",  bg: "#ecfdf3", color: "#15803d", dot: "#22c55e" },
  proposal:  { title: "Teklif",      bg: "#fefce8", color: "#a16207", dot: "#eab308" },
  won:       { title: "Kazanildi",   bg: "#e0f2fe", color: "#0369a1", dot: "#0ea5e9" },
  lost:      { title: "Kaybedildi",  bg: "#fef2f2", color: "#b91c1c", dot: "#ef4444" },
};

function mapStage(s) {
  if (s === "new") return "lead";
  if (s === "qualified") return "contacted";
  if (s === "quoted") return "proposal";
  if (STAGES.includes(s)) return s;
  return "lead";
}

/* ─── Column header ─────────────────────────────────────────────── */
function ColHeader({ stage, count }) {
  const m = STAGE_META[stage];
  return (
    <div className="flex items-center justify-between mb-2 px-1">
      <div className="flex items-center gap-1.5">
        <span className="px-2 py-0.5 rounded-full text-xs font-semibold border" style={{ background: m.bg, color: m.color, borderColor: m.color + "33" }}>{m.title}</span>
        <span className="text-xs text-muted-foreground/60">{count}</span>
      </div>
      <div className="w-2 h-2 rounded-full" style={{ background: m.dot }} />
    </div>
  );
}

/* ─── Draggable deal card ───────────────────────────────────────── */
function DealCard({ deal, onClick, isDragging }) {
  const locked = deal.stage === "won" || deal.stage === "lost";
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: deal.id,
    disabled: locked,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rounded-xl border bg-white p-2.5 mb-2 shadow-sm hover:shadow-md transition-shadow cursor-pointer group ${locked ? "opacity-70" : ""}`}
      data-testid="deal-card"
      onClick={() => onClick(deal.id)}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-foreground truncate">{deal.title || deal.id}</div>
          <div className="text-xs text-muted-foreground mt-1">{deal.amount != null ? `${deal.amount} ${deal.currency || "TRY"}` : ""}</div>
          {deal.next_action_at && (
            <div className="text-2xs text-muted-foreground/60 mt-0.5">Aksiyon: {new Date(deal.next_action_at).toLocaleDateString("tr-TR")}</div>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {locked ? (
            <Lock size={12} className="text-muted-foreground/60" />
          ) : (
            <div {...attributes} {...listeners} className="cursor-grab active:cursor-grabbing p-0.5 rounded hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-opacity">
              <GripVertical size={14} className="text-muted-foreground/60" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Droppable column ──────────────────────────────────────────── */
function KanbanColumn({ stage, deals, onCardClick }) {
  return (
    <div className="rounded-2xl border bg-gray-50/80 p-2.5 min-h-[140px] flex flex-col" data-testid={`kanban-column-${stage}`}>
      <ColHeader stage={stage} count={deals.length} />
      <div className="flex-1 overflow-y-auto max-h-[520px] pr-1">
        {deals.length === 0 ? (
          <div className="text-center py-6 text-xs text-muted-foreground/60 border border-dashed rounded-xl p-3">Henuz firsat yok</div>
        ) : (
          deals.map((d) => <DealCard key={d.id} deal={d} onClick={onCardClick} />)
        )}
      </div>
    </div>
  );
}

/* ─── Drag overlay card ─────────────────────────────────────────── */
function DragOverlayCard({ deal }) {
  if (!deal) return null;
  return (
    <div className="rounded-xl border-2 border-blue-400 bg-white p-2.5 shadow-xl w-[200px]">
      <div className="text-sm font-semibold text-foreground truncate">{deal.title || deal.id}</div>
      <div className="text-xs text-muted-foreground mt-1">{deal.amount != null ? `${deal.amount} ${deal.currency || "TRY"}` : ""}</div>
    </div>
  );
}

/* ─── New deal modal ────────────────────────────────────────────── */
function NewDealModal({ open, onClose, onCreated }) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("TRY");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  if (!open) return null;

  async function handleSubmit(e) {
    e.preventDefault(); setErr(""); setLoading(true);
    try {
      await createDeal({ title: title.trim() || undefined, amount: amount ? Number(amount) : undefined, currency: currency || undefined });
      onCreated?.(); onClose(); setTitle(""); setAmount("");
    } catch (e2) { setErr(apiErrorMessage(e2)); } finally { setLoading(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-4">Yeni Firsat</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div><label className="text-sm font-medium">Baslik</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm mt-1" placeholder="Deal basligi" /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-sm font-medium">Tutar</label>
              <input value={amount} onChange={(e) => setAmount(e.target.value)} type="number" className="w-full border rounded-lg px-3 py-2 text-sm mt-1" /></div>
            <div><label className="text-sm font-medium">Para Birimi</label>
              <select value={currency} onChange={(e) => setCurrency(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm mt-1">
                <option value="TRY">TRY</option><option value="USD">USD</option><option value="EUR">EUR</option>
              </select></div>
          </div>
          {err && <p className="text-sm text-red-600">{err}</p>}
          <div className="flex gap-2 justify-end pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm border rounded-lg">Iptal</button>
            <button type="submit" disabled={loading} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg disabled:opacity-50">
              {loading ? "Olusturuluyor..." : "Olustur"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN PIPELINE PAGE
   ═══════════════════════════════════════════════════════════════════ */
export default function CrmPipelinePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [user] = useState(() => getUser());
  const [allDeals, setAllDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errMsg, setErrMsg] = useState("");
  const [newDealOpen, setNewDealOpen] = useState(false);
  const [activeDragId, setActiveDragId] = useState(null);

  // Drawer
  const drawerDealId = searchParams.get("deal") || null;
  function openDrawer(id) { setSearchParams({ deal: id }); }
  function closeDrawer() { const p = new URLSearchParams(searchParams); p.delete("deal"); setSearchParams(p); }

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  // Fetch deals
  const refresh = useCallback(async () => {
    setLoading(true); setErrMsg("");
    try {
      const res = await listDeals({ status: "", page_size: 200 });
      setAllDeals(res.items || []);
    } catch (e) { setErrMsg(e.message || "Yuklenemedi"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Distribute deals by stage
  const columns = useMemo(() => {
    const cols = {};
    STAGES.forEach((s) => { cols[s] = []; });
    allDeals.forEach((d) => {
      let s = mapStage(d.stage);
      if (d.status === "won") s = "won";
      if (d.status === "lost") s = "lost";
      cols[s].push(d);
    });
    return cols;
  }, [allDeals]);

  const totalOpen = useMemo(() => allDeals.filter((d) => d.status === "open").length, [allDeals]);

  // Find deal by id (for drag overlay)
  const activeDeal = activeDragId ? allDeals.find((d) => d.id === activeDragId) : null;

  // DnD handlers
  function findStageForDeal(dealId) {
    for (const stage of STAGES) {
      if (columns[stage].some((d) => d.id === dealId)) return stage;
    }
    return null;
  }

  function handleDragStart(event) { setActiveDragId(event.active.id); }

  function handleDragEnd(event) {
    setActiveDragId(null);
    const { active, over } = event;
    if (!over) return;

    const dealId = active.id;
    // Find target stage: over.id could be a deal card or column
    let targetStage = null;
    if (STAGES.includes(over.id)) {
      targetStage = over.id;
    } else {
      // Dropped on a deal card - find which column it's in
      targetStage = findStageForDeal(over.id);
    }

    if (!targetStage) return;
    const sourceStage = findStageForDeal(dealId);
    if (sourceStage === targetStage) return;

    // Optimistic update
    const prevDeals = [...allDeals];
    setAllDeals((prev) =>
      prev.map((d) => d.id === dealId ? { ...d, stage: targetStage, status: targetStage === "won" ? "won" : targetStage === "lost" ? "lost" : "open" } : d)
    );

    // API call
    (async () => {
      try {
        await moveDealStage(dealId, targetStage);
      } catch (e) {
        setErrMsg(e.message || "Stage degistirilemedi");
        setAllDeals(prevDeals); // Rollback
      }
    })();
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto" }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h1 className="text-xl font-bold text-foreground">CRM Pipeline</h1>
          <div className="text-sm text-muted-foreground mt-0.5">Toplam acik firsat: <b>{totalOpen}</b></div>
        </div>
        <button onClick={() => setNewDealOpen(true)} className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700" data-testid="new-deal-btn">
          <Plus size={16} /> Yeni Firsat
        </button>
      </div>

      {errMsg && <div className="bg-red-50 text-red-700 px-4 py-2 rounded-lg text-sm mb-3">{errMsg}</div>}

      {/* Kanban board with DnD */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-5 gap-3" data-testid="kanban-board">
          {STAGES.map((stage) => (
            <KanbanColumn key={stage} stage={stage} deals={columns[stage]} onCardClick={openDrawer} />
          ))}
        </div>
        <DragOverlay>{activeDeal ? <DragOverlayCard deal={activeDeal} /> : null}</DragOverlay>
      </DndContext>

      {loading && <div className="text-center text-sm text-muted-foreground/60 mt-3">Yukleniyor...</div>}

      {/* New deal modal */}
      <NewDealModal open={newDealOpen} onClose={() => setNewDealOpen(false)} onCreated={refresh} />

      {/* Deal drawer (deep-linkable) */}
      {drawerDealId && (
        <DealDrawer dealId={drawerDealId} onClose={closeDrawer} onStageChanged={refresh} />
      )}
    </div>
  );
}
