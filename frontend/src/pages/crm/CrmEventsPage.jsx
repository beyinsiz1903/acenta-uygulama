// frontend/src/pages/crm/CrmEventsPage.jsx
import React, { useEffect, useMemo, useState } from "react";
import { listCrmEvents } from "../../lib/crm";
import { getUser } from "../../lib/api";
import { toast } from "sonner";

function formatDateTimeTr(dateIso) {
  if (!dateIso) return "-";
  const d = new Date(dateIso);
  return d.toLocaleString("tr-TR");
}

function getEntityLink(event) {
  const id = event.entity_id;
  if (!id) return null;
  switch (event.entity_type) {
    case "customer":
      return `/app/crm/customers/${id}`;
    case "booking":
      return `/app/ops/bookings/${id}`;
    case "customer_merge":
      return `/app/crm/customers/${id}`;
    default:
      return null;
  }
}

async function copyTextToClipboard(text) {
  if (!text) return { ok: false, method: "empty" };

  // 1) Modern API
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return { ok: true, method: "clipboard" };
    }
  } catch (e) {
    // fall through to fallback
  }

  // 2) execCommand fallback
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-9999px";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, ta.value.length);

    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return { ok, method: "execCommand" };
  } catch (e) {
    return { ok: false, method: "failed" };
  }
}

function EventRow({ event, onToggle }) {
  const [open, setOpen] = useState(false);

  function toggle() {
    const next = !open;
    setOpen(next);
    onToggle?.(event, next);
  }

  const createdAtLabel = formatDateTimeTr(event.created_at);
  const rolesLabel = (event.actor_roles || []).join(", ");
  const actorLabel = event.actor_user_id
    ? rolesLabel
      ? `${event.actor_user_id} (${rolesLabel})`
      : event.actor_user_id
    : "Sistem";

  const entityLink = getEntityLink(event);

  return (
    <div
      style={{
        borderBottom: "1px solid #f3f3f3",
        padding: "10px 12px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <div style={{ minWidth: 0, flex: "1 1 200px" }}>
          <div style={{ fontSize: 13, color: "#111", fontWeight: 600 }}>
            {event.entity_type} {event.action}{" "}
            {entityLink ? (
              <a
                href={entityLink}
                style={{ color: "#2563eb", textDecoration: "underline" }}
              >
                {event.entity_id}
              </a>
            ) : (
              <>
                <span>{event.entity_id}</span>
                {event.entity_type === "deal" ||
                event.entity_type === "task" ||
                event.entity_type === "activity" ? (
                  <button
                    type="button"
                    onClick={async () => {
                      if (!event.entity_id) return;
                      const res = await copyTextToClipboard(event.entity_id);
                      if (res.ok) {
                        toast.success("ID kopyaland\u0131.");
                      } else {
                        toast.error(
                          "ID kopyalanamad\u0131. Kopyalamak i\u00e7in ID'yi se\u00e7ip Ctrl+C yap\u0131n."
                        );
                      }
                    }}
                    style={{
                      marginLeft: 8,
                      fontSize: 11,
                      padding: "2px 6px",
                      borderRadius: 999,
                      border: "1px solid #e5e7eb",
                      background: "#f9fafb",
                      cursor: "pointer",
                    }}
                    aria-label="ID kopyala"
                    title="ID kopyala"
                  >
                    📋
                  </button>
                ) : null}
              </>
            )}
          </div>
          <div style={{ marginTop: 2, fontSize: 12, color: "#4b5563" }}>{createdAtLabel}</div>
        </div>

        <div style={{ minWidth: 0, flex: "1 1 160px", fontSize: 12, color: "#4b5563" }}>{actorLabel}</div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span
            style={{
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 999,
              border: "1px solid #e5e7eb",
              background: "#f9fafb",
              color: "#4b5563",
            }}
          >
            {event.source || "api"}
          </span>

          <button
            type="button"
            onClick={toggle}
            style={{
              padding: "6px 10px",
              borderRadius: 999,
              border: "1px solid #111827",
              background: open ? "#111827" : "#ffffff",
              color: open ? "#ffffff" : "#111827",
              cursor: "pointer",
              fontSize: 12,
            }}
          >
            {open ? "Detayı kapat" : "Detay"}
          </button>
        </div>
      </div>

      {open ? (
        <div
          style={{
            marginTop: 8,
            padding: 10,
            borderRadius: 10,
            border: "1px solid #e5e7eb",
            background: "#f9fafb",
            fontSize: 12,
          }}
        >
          {(() => {
            const p = event.payload || {};
            const chips = [];
            if (p.customer_id) {
              chips.push({
                label: `Mffteri: ${p.customer_id}`,
                href: `/app/crm/customers/${p.customer_id}`,
              });
            }
            if (p.booking_id) {
              chips.push({
                label: `Rezervasyon: ${p.booking_id}`,
                href: `/app/ops/bookings/${p.booking_id}`,
              });
            }
            if (p.primary_id) {
              chips.push({
                label: `Primary mffteri: ${p.primary_id}`,
                href: `/app/crm/customers/${p.primary_id}`,
              });
            }
            if (Array.isArray(p.merged_ids)) {
              p.merged_ids.forEach((id) => {
                chips.push({
                  label: `Birlefen: ${id}`,
                  href: `/app/crm/customers/${id}`,
                });
              });
            }

            const hasPayload = p && Object.keys(p).length > 0;

            return (
              <>
                {chips.length ? (
                  <div
                    style={{
                      marginBottom: 8,
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 6,
                    }}
                  >
                    {chips.map((chip, idx) => (
                      <a
                        key={idx}
                        href={chip.href}
                        style={{
                          fontSize: 11,
                          padding: "4px 8px",
                          borderRadius: 999,
                          border: "1px solid #e5e7eb",
                          background: "#f9fafb",
                          color: "#111827",
                        }}
                      >
                        {chip.label}
                      </a>
                    ))}
                  </div>
                ) : null}

                {hasPayload ? (
                  <pre
                    style={{
                      margin: 0,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontSize: 12,
                      fontFamily:
                        "SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
                    }}
                  >
                    {JSON.stringify(p, null, 2)}
                  </pre>
                ) : (
                  <div style={{ fontSize: 12, color: "#6b7280" }}>Payload yok.</div>
                )}
              </>
            );
          })()}
        </div>
      ) : null}
    </div>
  );
}

export default function CrmEventsPage() {
  const user = getUser();

  const [entityType, setEntityType] = useState("");
  const [entityId, setEntityId] = useState("");
  const [action, setAction] = useState("");
  const [range, setRange] = useState("7d"); // 24h | 7d | 30d
  const [fromOverride, setFromOverride] = useState("");
  const [toOverride, setToOverride] = useState("");

  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");

  const isAdmin = useMemo(() => {
    const roles = (user && user.roles) || [];
    return roles.includes("admin") || roles.includes("super_admin");
  }, [user]);

  const hasNext = total > items.length;

  function computeRange() {
    // If manual from/to provided, use them
    if (fromOverride || toOverride) {
      return {
        from: fromOverride || undefined,
        to: toOverride || undefined,
      };
    }

    const now = new Date();
    let from = null;
    if (range === "24h") {
      from = new Date(Date.now() - 24 * 60 * 60 * 1000);
    } else if (range === "7d") {
      from = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    } else if (range === "30d") {
      from = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    }

    return {
      from: from ? from.toISOString() : undefined,
      to: now.toISOString(),
    };
  }

  const queryParams = useMemo(() => {
    const qp = {
      page,
      page_size: pageSize,
    };
    if (entityType) qp.entity_type = entityType;
    if (entityId) qp.entity_id = entityId.trim();
    if (action) qp.action = action.trim();

    const r = computeRange();
    if (r.from) qp.from = r.from;
    if (r.to) qp.to = r.to;

    return qp;
  }, [page, pageSize, entityType, entityId, action, range, fromOverride, toOverride]);

  async function load(reset) {
    if (!isAdmin || loading) return;
    const start = Date.now();
    setLoading(true);
    setErrMsg("");
    try {
      const nextPage = reset ? 1 : page;
      const baseParams = { ...queryParams, page: nextPage };
      const res = await listCrmEvents(baseParams);
      if (reset) {
        setItems(res.items || []);
      } else {
        setItems((prev) => [...prev, ...(res.items || [])]);
      }
      setTotal(res.total || 0);
      setPage(res.page || nextPage);
    } catch (e) {
      setErrMsg(e.message || "Olaylar ycklenemedi.");
    } finally {
      const elapsed = Date.now() - start;
      const minMs = 300;
      const waitMs = Math.max(0, minMs - elapsed);
      if (waitMs) {
        await new Promise((resolve) => setTimeout(resolve, waitMs));
      }
      setLoading(false);
    }
  }

  useEffect(() => {
    // initial load with default 7d range
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyFilters(e) {
    e?.preventDefault?.();
    if (loading) return;
    setPage(1);
    load(true);
  }

  function loadMore() {
    if (loading || !hasNext) return;
    const nextPage = page + 1;
    setPage(nextPage);
    load(false);
  }

  if (!isAdmin) {
    return (
      <div style={{ padding: 16 }}>
        <div
          style={{
            padding: 16,
            borderRadius: 12,
            border: "1px solid #fee2e2",
            background: "#fef2f2",
            color: "#b91c1c",
          }}
        >
          <h1 style={{ margin: 0, fontSize: 20 }}>Erişim kısıtlı</h1>
          <p style={{ marginTop: 8, fontSize: 14 }}>
            Bu sayfaya yalnızca admin kullanıcılar erişebilir.
          </p>
        </div>
      </div>
    );
  }

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
          <h1 style={{ margin: 0, fontSize: 22 }}>CRM Olaylar</h1>
          <div style={{ marginTop: 4, fontSize: 13, color: "#6b7280" }}>
            Kritik CRM işlemlerinin kim tarafından, ne zaman yapıldığını izleyin.
          </div>
        </div>
      </div>

      {/* Filters */}
      <form
        onSubmit={applyFilters}
        style={{
          marginTop: 14,
          padding: 12,
          borderRadius: 12,
          border: "1px solid #eee",
          display: "flex",
          flexWrap: "wrap",
          gap: 10,
          alignItems: "center",
        }}
      >
        <select
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          style={{ padding: 10, borderRadius: 10, border: "1px solid #ddd", minWidth: 180 }}
        >
          <option value="">Tüm tipler</option>
          <option value="customer">Müşteri</option>
          <option value="deal">Fırsat</option>
          <option value="task">Görev</option>
          <option value="activity">Aktivite</option>
          <option value="customer_merge">Müşteri Birleştirme</option>
          <option value="booking">Rezervasyon</option>
        </select>

        <input
          value={entityId}
          onChange={(e) => setEntityId(e.target.value)}
          placeholder="Entity ID (opsiyonel)"
          style={{
            padding: 10,
            borderRadius: 10,
            border: "1px solid #ddd",
            minWidth: 220,
            flex: "1 1 220px",
          }}
        />

        <input
          value={action}
          onChange={(e) => setAction(e.target.value)}
          placeholder="Aksiyon (created/updated/...)"
          style={{
            padding: 10,
            borderRadius: 10,
            border: "1px solid #ddd",
            minWidth: 200,
          }}
        />

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => {
              setRange("24h");
              setFromOverride("");
              setToOverride("");
            }}
            style={{
              padding: "8px 10px",
              borderRadius: 999,
              border: range === "24h" ? "1px solid #111" : "1px solid #ddd",
              background: range === "24h" ? "#111" : "#fff",
              color: range === "24h" ? "#fff" : "#333",
              cursor: "pointer",
              fontSize: 12,
            }}
>
            Son 24 saat
          </button>
          <button
            type="button"
            onClick={() => {
              setRange("7d");
              setFromOverride("");
              setToOverride("");
            }}
            style={{
              padding: "8px 10px",
              borderRadius: 999,
              border: range === "7d" ? "1px solid #111" : "1px solid #ddd",
              background: range === "7d" ? "#111" : "#fff",
              color: range === "7d" ? "#fff" : "#333",
              cursor: "pointer",
              fontSize: 12,
            }}
>
            Son 7 gün
          </button>
          <button
            type="button"
            onClick={() => {
              setRange("30d");
              setFromOverride("");
              setToOverride("");
            }}
            style={{
              padding: "8px 10px",
              borderRadius: 999,
              border: range === "30d" ? "1px solid #111" : "1px solid #ddd",
              background: range === "30d" ? "#111" : "#fff",
              color: range === "30d" ? "#fff" : "#333",
              cursor: "pointer",
              fontSize: 12,
            }}
>
            Son 30 gün
          </button>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 6,
            minWidth: 220,
          }}
        >
          <label style={{ fontSize: 11, color: "#6b7280" }}>Gelişmiş tarih aralığı (opsiyonel)</label>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              type="datetime-local"
              value={fromOverride}
              onChange={(e) => setFromOverride(e.target.value)}
              style={{
                flex: 1,
                padding: 8,
                borderRadius: 10,
                border: "1px solid #ddd",
              }}
            />
            <input
              type="datetime-local"
              value={toOverride}
              onChange={(e) => setToOverride(e.target.value)}
              style={{
                flex: 1,
                padding: 8,
                borderRadius: 10,
                border: "1px solid #ddd",
              }}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            marginLeft: "auto",
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid #111827",
            background: loading ? "#4b5563" : "#111827",
            color: "#ffffff",
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: 13,
          }}
        >
          {loading ? "Y\u00fckleniyor..." : "Filtrele"}
        </button>
      </form>

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
            fontSize: 13,
          }}
        >
          {errMsg}
        </div>
      ) : null}

      {/* List */}
      <div style={{ marginTop: 12, borderRadius: 12, border: "1px solid #eee", overflow: "hidden" }}>
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
          <span>{loading ? "Y\u00fckleniyor..." : "Olaylar"}</span>
          <span>
            Toplam: <b>{total}</b>
          </span>
        </div>

        {!loading && items.length === 0 ? (
          <div style={{ padding: 18 }}>
            <div style={{ fontSize: 16, fontWeight: 600 }}>Bu filtreler için kayıt yok.</div>
            <div style={{ marginTop: 6, color: "#666" }}>
              Farklı bir tarih aralığı veya entity filtresi deneyebilirsiniz.
            </div>
          </div>
        ) : (
          <div style={{ maxHeight: 520, overflowY: "auto" }}>
            {items.map((ev) => (
              <EventRow key={ev.id} event={ev} />
            ))}
          </div>
        )}
      </div>

      {/* Load more */}
      <div
        style={{
          marginTop: 12,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <button
          type="button"
          disabled={!hasNext || loading}
          onClick={loadMore}
          style={{
            padding: "8px 12px",
            borderRadius: 999,
            border: "1px solid #ddd",
            background: !hasNext ? "#f3f4f6" : "#ffffff",
            color: "#111827",
            cursor: !hasNext ? "not-allowed" : "pointer",
            fontSize: 13,
          }}
        >
          {hasNext ? "Daha fazla yükle" : "Kayıt kalmadı"}
        </button>
      </div>
    </div>
  );
}
