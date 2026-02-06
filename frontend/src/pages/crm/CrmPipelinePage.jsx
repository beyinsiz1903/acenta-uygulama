// frontend/src/pages/crm/CrmPipelinePage.jsx
import React, { useEffect, useMemo, useState } from "react";
import { listDeals, patchDeal, createDeal, moveDealStage } from "../../lib/crm";
import { getUser, apiErrorMessage } from "../../lib/api";

function ColumnHeader({ title, count, tone }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <div
          style={{
            padding: "4px 8px",
            borderRadius: 999,
            fontSize: 11,
            fontWeight: 600,
            border: "1px solid #e5e7eb",
            background: tone?.bg || "#f9fafb",
            color: tone?.color || "#111827",
          }}
        >
          {title}
        </div>
        <div style={{ fontSize: 11, color: "#6b7280" }}>{count} kayıt</div>
      </div>
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: tone?.dot || "#9ca3af",
        }}
      />
    </div>
  );
}

function DealCard({ deal, stages, onChangeStage, disabled }) {
  const safeStage = stages.find((s) => s.value === deal.stage)?.value || "lead";
  const [currentStage, setCurrentStage] = useState(safeStage);

  function handleStageChange(e) {
    const value = e.target.value;
    setCurrentStage(value);
    onChangeStage(deal, value);
  }

  return (
    <div
      style={{
        borderRadius: 12,
        border: "1px solid #e5e7eb",
        padding: 10,
        background: "#ffffff",
        boxShadow: "0 1px 2px rgba(15,23,42,0.05)",
        marginBottom: 8,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "#111827",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={deal.title || deal.id}
          >
            {deal.title || deal.id}
          </div>
          <div style={{ marginTop: 4, fontSize: 11, color: "#6b7280" }}>
            {deal.customer_id
              ? `M\u00fc\u015fteri: ${deal.customer_id}`
              : "M\u00fc\u015fteri yok"}
          </div>
          <div style={{ marginTop: 4, fontSize: 11, color: "#6b7280" }}>
            {deal.owner_user_id
              ? `Sahip: ${deal.owner_user_id}`
              : "Sahip atanmad\u0131"}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#111827" }}>
            {deal.amount != null ? `${deal.amount} ${deal.currency || ""}` : "Tutar yok"}
          </div>
          <div style={{ marginTop: 6 }}>
            <select
              value={currentStage}
              onChange={handleStageChange}
              disabled={disabled}
              style={{
                fontSize: 11,
                padding: "4px 8px",
                borderRadius: 999,
                border: "1px solid #d1d5db",
                background: disabled ? "#e5e7eb" : "#f9fafb",
                cursor: disabled ? "not-allowed" : "pointer",
              }}
            >
              {stages.map((st) => (
                <option key={st.value} value={st.value}>
                  {st.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}

function NewDealModal({ open, onClose, onCreated }) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("TRY");
  const [customerId, setCustomerId] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  if (!open) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const payload = {
        title: title.trim() || undefined,
        amount: amount ? Number(amount) : undefined,
        currency: currency || undefined,
        customer_id: customerId.trim() || undefined,
      };
      await createDeal(payload);
      onCreated?.();
      onClose();
      setTitle("");
      setAmount("");
      setCurrency("TRY");
      setCustomerId("");
    } catch (e2) {
      setErr(apiErrorMessage(e2));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15,23,42,0.35)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        zIndex: 1000,
      }}
      onMouseDown={onClose}
    >
      <div
        style={{
          width: "min(480px, 100%)",
          background: "#ffffff",
          borderRadius: 12,
          padding: 16,
          boxShadow: "0 20px 40px rgba(15,23,42,0.3)",
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Yeni F\u0131rsat</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            style={{
              border: "none",
              background: "transparent",
              fontSize: 18,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.5 : 1,
            }}
            aria-label="Kapat"
          >
            {"\u00d7"}
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ marginTop: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={{ fontSize: 12, color: "#6b7280" }}>Ba\u015fl\u0131k *</label>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                minLength={2}
                style={{
                  marginTop: 6,
                  width: "100%",
                  padding: 10,
                  borderRadius: 10,
                  border: "1px solid #d1d5db",
                }}
                placeholder={"\u00d6rn: Yaz sezonu kontrat"}
              />
            </div>

            <div>
              <label style={{ fontSize: 12, color: "#6b7280" }}>Tutar</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                style={{
                  marginTop: 6,
                  width: "100%",
                  padding: 10,
                  borderRadius: 10,
                  border: "1px solid #d1d5db",
                }}
                placeholder={"\u00d6rn: 50000"}
              />
            </div>

            <div>
              <label style={{ fontSize: 12, color: "#6b7280" }}>Para Birimi</label>
              <input
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                style={{
                  marginTop: 6,
                  width: "100%",
                  padding: 10,
                  borderRadius: 10,
                  border: "1px solid #d1d5db",
                }}
                placeholder="TRY"
              />
            </div>

            <div style={{ gridColumn: "1 / -1" }}>
              <label style={{ fontSize: 12, color: "#6b7280" }}>M\u00fc\u015fteri ID (opsiyonel)</label>
              <input
                value={customerId}
                onChange={(e) => setCustomerId(e.target.value)}
                style={{
                  marginTop: 6,
                  width: "100%",
                  padding: 10,
                  borderRadius: 10,
                  border: "1px solid #d1d5db",
                }}
                placeholder={"\u00d6rn: cust_..."}
              />
            </div>
          </div>

          {err ? (
            <div
              style={{
                marginTop: 10,
                padding: 10,
                borderRadius: 10,
                border: "1px solid #fecaca",
                background: "#fef2f2",
                color: "#b91c1c",
                fontSize: 13,
              }}
            >
              {err}
            </div>
          ) : null}

          <div style={{ marginTop: 14, display: "flex", justifyContent: "flex-end", gap: 10 }}>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid #d1d5db",
                background: "#ffffff",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              {"\u0130ptal"}
            </button>
            <button
              type="submit"
              disabled={loading || !title.trim()}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid #111827",
                background: "#111827",
                color: "#ffffff",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              {loading ? "Olu\u015fturuluyor\u2026" : "Olu\u015ftur"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function CrmPipelinePage() {
  const user = getUser();

  const [onlyMine, setOnlyMine] = useState(true);
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [dealsByStage, setDealsByStage] = useState({
    new: [],
    qualified: [],
    quoted: [],
    won: [],
    lost: [],
  });
  const [optimistic, setOptimistic] = useState({});
  const [newDealOpen, setNewDealOpen] = useState(false);

  const stages = useMemo(
    () => [
      { value: "lead", label: "Lead" },
      { value: "contacted", label: "Iletisimde" },
      { value: "proposal", label: "Teklif" },
      { value: "won", label: "Kazanildi" },
      { value: "lost", label: "Kaybedildi" },
    ],
    []
  );

  const columnConfig = useMemo(
    () => ({
      lead: {
        key: "lead",
        title: "Lead",
        tone: { bg: "#eff6ff", color: "#1d4ed8", dot: "#3b82f6" },
      },
      contacted: {
        key: "contacted",
        title: "Iletisimde",
        tone: { bg: "#ecfdf3", color: "#15803d", dot: "#22c55e" },
      },
      proposal: {
        key: "proposal",
        title: "Teklif",
        tone: { bg: "#fefce8", color: "#a16207", dot: "#eab308" },
      },
      won: {
        key: "won",
        title: "Kazanildi",
        tone: { bg: "#e0f2fe", color: "#0369a1", dot: "#0ea5e9" },
      },
      lost: {
        key: "lost",
        title: "Kaybedildi",
        tone: { bg: "#fef2f2", color: "#b91c1c", dot: "#ef4444" },
      },
    }),
    []
  );

  function distributeDeals(allDeals) {
    const next = {
      lead: [],
      contacted: [],
      proposal: [],
      won: [],
      lost: [],
    };

    allDeals.forEach((deal) => {
      let stage = deal.stage || "lead";
      // Map old stages to new
      if (stage === "new") stage = "lead";
      if (stage === "qualified") stage = "contacted";
      if (stage === "quoted") stage = "proposal";
      if (!["lead", "contacted", "proposal", "won", "lost"].includes(stage)) {
        stage = "lead";
      }
      if (deal.status === "won") stage = "won";
      if (deal.status === "lost") stage = "lost";
      next[stage].push(deal);
    });

    setDealsByStage(next);
  }

  async function refresh() {
    setLoading(true);
    setErrMsg("");
    const ownerId = onlyMine ? user?.id : undefined;
    try {
      const baseParams = ownerId ? { owner: ownerId } : {};
      const [openRes, wonRes, lostRes] = await Promise.all([
        listDeals({ ...baseParams, status: "open" }),
        listDeals({ ...baseParams, status: "won" }),
        listDeals({ ...baseParams, status: "lost" }),
      ]);

      const allItems = [
        ...(openRes?.items || []),
        ...(wonRes?.items || []),
        ...(lostRes?.items || []),
      ];

      distributeDeals(allItems);
    } catch (e) {
      setErrMsg(e.message || "Pipeline y\u00fcklenemedi.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyMine]);

  function handleStageChange(deal, newStage) {
    const prevStage = deal.stage || "lead";
    if (prevStage === newStage) return;

    setOptimistic((prev) => ({ ...prev, [deal.id]: true }));

    // optimistic move
    setDealsByStage((current) => {
      const next = {
        lead: [],
        contacted: [],
        proposal: [],
        won: [],
        lost: [],
      };
      const all = [
        ...current.lead,
        ...current.contacted,
        ...current.proposal,
        ...current.won,
        ...current.lost,
      ].filter((d) => d.id !== deal.id);
      const updated = { ...deal, stage: newStage };
      const safeStage = ["lead", "contacted", "proposal", "won", "lost"].includes(newStage)
        ? newStage
        : "lead";
      all.push(updated);
      all.forEach((d) => {
        let st = d.stage || "lead";
        if (!["lead", "contacted", "proposal", "won", "lost"].includes(st)) {
          st = "lead";
        }
        if (d.status === "won") st = "won";
        if (d.status === "lost") st = "lost";
        if (d.id === deal.id) {
          st = safeStage;
        }
        next[st].push(d);
      });
      return next;
    });

    (async () => {
      try {
        const { moveDealStage } = await import("../../lib/crm");
        await moveDealStage(deal.id, newStage);
      } catch (e) {
        setErrMsg(e.message || "Asama guncellenemedi.");
        await refresh();
      } finally {
        setOptimistic((prev) => {
          const copy = { ...prev };
          delete copy[deal.id];
          return copy;
        });
      }
    })();
  }

  const totalOpen =
    (dealsByStage.new?.length || 0) +
    (dealsByStage.qualified?.length || 0) +
    (dealsByStage.quoted?.length || 0);

  return (
    <div style={{ padding: 16 }}>
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
          <h1 style={{ margin: 0, fontSize: 22 }}>CRM • Pipeline</h1>
          <div style={{ marginTop: 4, fontSize: 13, color: "#6b7280" }}>
            Satış fırsatlarınızı aşamalara göre izleyin, kazanılan ve kaybedilenleri ayrı görün.
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 13,
              color: "#4b5563",
            }}
          >
            <input
              type="checkbox"
              checked={onlyMine}
              onChange={(e) => setOnlyMine(e.target.checked)}
            />
            {"Sadece benim f\u0131rsatlar\u0131m"}
          </label>

          <button
            type="button"
            onClick={() => setNewDealOpen(true)}
            style={{
              padding: "8px 12px",
              borderRadius: 10,
              border: "1px solid #111827",
              background: "#111827",
              color: "#ffffff",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            {"Yeni F\u0131rsat"}
          </button>
        </div>
      </div>

      {errMsg ? (
        <div
          style={{
            marginTop: 12,
            padding: 12,
            borderRadius: 12,
            border: "1px solid #fecaca",
            background: "#fef2f2",
            color: "#b91c1c",
            fontSize: 13,
          }}
        >
          {errMsg}
        </div>
      ) : null}

      <div style={{ marginTop: 12, fontSize: 13, color: "#6b7280" }}>
        {"Toplam a\u00e7\u0131k f\u0131rsat: "}
        <b>{totalOpen}</b>
      </div>

      <div
        style={{
          marginTop: 12,
          display: "grid",
          gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
          gap: 12,
        }}
      >
        {(["lead", "contacted", "proposal", "won", "lost"]).map((key) => {
          const col = columnConfig[key];
          const items = dealsByStage[key] || [];
          return (
            <div
              key={key}
              style={{
                borderRadius: 16,
                border: "1px solid #e5e7eb",
                padding: 10,
                background: "#f9fafb",
                minHeight: 120,
              }}
            >
              <ColumnHeader title={col.title} count={items.length} tone={col.tone} />
              <div style={{ maxHeight: 520, overflowY: "auto", paddingRight: 4 }}>
                {items.length === 0 ? (
                  <div
                    style={{
                      borderRadius: 12,
                      border: "1px dashed #e5e7eb",
                      padding: 12,
                      fontSize: 11,
                      color: "#9ca3af",
                      textAlign: "center",
                    }}
                  >
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>Henüz fırsat yok</div>
                    <div style={{ marginBottom: 8 }}>
                      İlk fırsatı oluşturarak pipeline akışını başlatabilirsiniz.
                    </div>
                    <button
                      type="button"
                      onClick={() => setNewDealOpen(true)}
                      style={{
                        padding: "6px 10px",
                        borderRadius: 999,
                        border: "1px solid #111827",
                        background: "#111827",
                        color: "#ffffff",
                        fontSize: 11,
                        cursor: "pointer",
                      }}
                    >
                      İlk fırsatı oluştur
                    </button>
                  </div>
                ) : (
                  items.map((deal) => (
                    <DealCard
                      key={deal.id}
                      deal={deal}
                      stages={stages}
                      onChangeStage={handleStageChange}
                      disabled={!!optimistic[deal.id]}
                    />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      <NewDealModal open={newDealOpen} onClose={() => setNewDealOpen(false)} onCreated={refresh} />

      {loading ? (
        <div style={{ marginTop: 8, fontSize: 12, color: "#6b7280" }}>
          {"Y\u00fckleniyor\u2026"}
        </div>
      ) : null}
    </div>
  );
}
