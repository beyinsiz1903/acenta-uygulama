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
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return { ok: true, method: "clipboard" };
    }
  } catch (e) {
    // fall through to fallback
  }
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

function RangeButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-2.5 py-2 rounded-full border text-xs cursor-pointer transition-colors ${
        active
          ? "border-foreground bg-foreground text-primary-foreground"
          : "border-border bg-card text-foreground hover:bg-muted"
      }`}
    >
      {children}
    </button>
  );
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
    <div className="border-b border-border/50 px-3 py-2.5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-[1_1_200px]">
          <div className="text-sm text-foreground font-semibold">
            {event.entity_type} {event.action}{" "}
            {entityLink ? (
              <a href={entityLink} className="text-primary underline">
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
                        toast.success("ID kopyalandı.");
                      } else {
                        toast.error("ID kopyalanamadı. Kopyalamak için ID'yi seçip Ctrl+C yapın.");
                      }
                    }}
                    className="ml-2 text-xs px-1.5 py-0.5 rounded-full border border-border bg-muted cursor-pointer hover:bg-accent transition-colors"
                    aria-label="ID kopyala"
                    title="ID kopyala"
                  >
                    📋
                  </button>
                ) : null}
              </>
            )}
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground">{createdAtLabel}</div>
        </div>

        <div className="min-w-0 flex-[1_1_160px] text-xs text-muted-foreground">{actorLabel}</div>

        <div className="flex gap-2 items-center">
          <span className="text-xs px-2 py-0.5 rounded-full border border-border bg-muted text-muted-foreground">
            {event.source || "api"}
          </span>

          <button
            type="button"
            onClick={toggle}
            className={`px-2.5 py-1.5 rounded-full border text-xs cursor-pointer transition-colors ${
              open
                ? "border-foreground bg-foreground text-primary-foreground"
                : "border-foreground bg-card text-foreground hover:bg-muted"
            }`}
          >
            {open ? "Detayı kapat" : "Detay"}
          </button>
        </div>
      </div>

      {open ? (
        <div className="mt-2 p-2.5 rounded-lg border border-border bg-muted text-xs">
          {(() => {
            const p = event.payload || {};
            const chips = [];
            if (p.customer_id) {
              chips.push({
                label: `Müşteri: ${p.customer_id}`,
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
                label: `Primary müşteri: ${p.primary_id}`,
                href: `/app/crm/customers/${p.primary_id}`,
              });
            }
            if (Array.isArray(p.merged_ids)) {
              p.merged_ids.forEach((id) => {
                chips.push({
                  label: `Birleşen: ${id}`,
                  href: `/app/crm/customers/${id}`,
                });
              });
            }

            const hasPayload = p && Object.keys(p).length > 0;

            return (
              <>
                {chips.length ? (
                  <div className="mb-2 flex flex-wrap gap-1.5">
                    {chips.map((chip, idx) => (
                      <a
                        key={idx}
                        href={chip.href}
                        className="text-xs px-2 py-1 rounded-full border border-border bg-card text-foreground hover:bg-accent transition-colors"
                      >
                        {chip.label}
                      </a>
                    ))}
                  </div>
                ) : null}

                {hasPayload ? (
                  <pre className="m-0 whitespace-pre-wrap break-words text-xs font-mono">
                    {JSON.stringify(p, null, 2)}
                  </pre>
                ) : (
                  <div className="text-xs text-muted-foreground">Payload yok.</div>
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
  const [range, setRange] = useState("7d");
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
      setErrMsg(e.message || "Olaylar yüklenemedi.");
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
      <div className="p-4">
        <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive">
          <h1 className="m-0 text-xl font-bold">Erişim kısıtlı</h1>
          <p className="mt-2 text-sm">
            Bu sayfaya yalnızca admin kullanıcılar erişebilir.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="m-0 text-xl font-bold text-foreground">CRM Olaylar</h1>
          <div className="mt-1 text-sm text-muted-foreground">
            Kritik CRM işlemlerinin kim tarafından, ne zaman yapıldığını izleyin.
          </div>
        </div>
      </div>

      {/* Filters */}
      <form
        onSubmit={applyFilters}
        className="mt-3.5 p-3 rounded-xl border border-border flex flex-wrap gap-2.5 items-center"
      >
        <select
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          className="p-2.5 rounded-lg border border-border min-w-[180px] text-sm bg-card text-foreground"
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
          className="p-2.5 rounded-lg border border-border min-w-[220px] flex-[1_1_220px] text-sm bg-card text-foreground placeholder:text-muted-foreground"
        />

        <input
          value={action}
          onChange={(e) => setAction(e.target.value)}
          placeholder="Aksiyon (created/updated/...)"
          className="p-2.5 rounded-lg border border-border min-w-[200px] text-sm bg-card text-foreground placeholder:text-muted-foreground"
        />

        <div className="flex gap-1.5 flex-wrap">
          <RangeButton active={range === "24h"} onClick={() => { setRange("24h"); setFromOverride(""); setToOverride(""); }}>
            Son 24 saat
          </RangeButton>
          <RangeButton active={range === "7d"} onClick={() => { setRange("7d"); setFromOverride(""); setToOverride(""); }}>
            Son 7 gün
          </RangeButton>
          <RangeButton active={range === "30d"} onClick={() => { setRange("30d"); setFromOverride(""); setToOverride(""); }}>
            Son 30 gün
          </RangeButton>
        </div>

        <div className="flex flex-col gap-1.5 min-w-[220px]">
          <label className="text-xs text-muted-foreground">Gelişmiş tarih aralığı (opsiyonel)</label>
          <div className="flex gap-1.5">
            <input
              type="datetime-local"
              value={fromOverride}
              onChange={(e) => setFromOverride(e.target.value)}
              className="flex-1 p-2 rounded-lg border border-border text-sm bg-card text-foreground"
            />
            <input
              type="datetime-local"
              value={toOverride}
              onChange={(e) => setToOverride(e.target.value)}
              className="flex-1 p-2 rounded-lg border border-border text-sm bg-card text-foreground"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="ml-auto px-3 py-2.5 rounded-lg border border-foreground bg-foreground text-primary-foreground text-sm cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
        >
          {loading ? "Yükleniyor..." : "Filtrele"}
        </button>
      </form>

      {/* Error */}
      {errMsg ? (
        <div className="mt-3 p-3 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive text-sm">
          {errMsg}
        </div>
      ) : null}

      {/* List */}
      <div className="mt-3 rounded-xl border border-border overflow-hidden">
        <div className="p-2.5 border-b border-border bg-muted/50 text-sm text-muted-foreground flex justify-between">
          <span>{loading ? "Yükleniyor..." : "Olaylar"}</span>
          <span>
            Toplam: <b>{total}</b>
          </span>
        </div>

        {!loading && items.length === 0 ? (
          <div className="p-5">
            <div className="text-base font-semibold text-foreground">Bu filtreler için kayıt yok.</div>
            <div className="mt-1.5 text-sm text-muted-foreground">
              Farklı bir tarih aralığı veya entity filtresi deneyebilirsiniz.
            </div>
          </div>
        ) : (
          <div className="max-h-[520px] overflow-y-auto">
            {items.map((ev) => (
              <EventRow key={ev.id} event={ev} />
            ))}
          </div>
        )}
      </div>

      {/* Load more */}
      <div className="mt-3 flex justify-center">
        <button
          type="button"
          disabled={!hasNext || loading}
          onClick={loadMore}
          className={`px-3 py-2 rounded-full border text-sm cursor-pointer transition-colors ${
            hasNext
              ? "border-border bg-card text-foreground hover:bg-muted"
              : "border-border bg-muted text-muted-foreground cursor-not-allowed"
          }`}
        >
          {hasNext ? "Daha fazla yükle" : "Kayıt kalmadı"}
        </button>
      </div>
    </div>
  );
}
