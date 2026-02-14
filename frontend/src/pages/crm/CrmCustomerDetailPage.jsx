// frontend/src/pages/crm/CrmCustomerDetailPage.jsx
import React, { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getCustomer, patchCustomer, listActivities, createActivity, listCustomerInboxThreads, getCustomerTimeline } from "../../lib/crm";

function Badge({ children }) {
  return (
    <span className="inline-flex px-2 py-0.5 rounded-full border border-border text-xs leading-[18px] mr-1.5 mb-1.5">
      {children}
    </span>
  );
}

function PrimaryContactLine({ contacts }) {
  const primary = (contacts || []).filter((c) => c?.is_primary);
  if (!primary.length) return <span className="text-muted-foreground">Birincil iletişim yok</span>;

  return (
    <>
      {primary.map((c, idx) => (
        <span key={idx} className="mr-3">
          {c.type === "email" ? "✉️" : "📞"} {c.value}
        </span>
      ))}
    </>
  );
}

function Tabs({ value, onChange, items }) {
  return (
    <div className="flex gap-2 border-b border-border mt-3">
      {items.map((it) => {
        const active = it.value === value;
        return (
          <button
            key={it.value}
            onClick={() => onChange(it.value)}
            className={`px-2.5 py-2.5 border-none bg-transparent cursor-pointer text-sm transition-colors ${
              active
                ? "border-b-2 border-foreground font-bold text-foreground"
                : "border-b-2 border-transparent font-medium text-muted-foreground hover:text-foreground"
            }`}
          >
            {it.label}
          </button>
        );
      })}
    </div>
  );
}

function formatDateTime(value) {
  if (!value) return "\u2014";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) {
    return "\u2014";
  }
  return d.toLocaleString("tr-TR");
}

function relTime(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "az once";
  if (diff < 3600) return `${Math.floor(diff / 60)}dk once`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}sa once`;
  return `${Math.floor(diff / 86400)}g once`;
}

const TL_ICONS = { reservation: "\u{1F3E8}", payment: "\u{1F4B3}", note: "\u{1F4DD}", deal: "\u{1F4BC}", task: "\u2705" };
const TL_FILTERS = [
  { value: "", label: "Tumu" },
  { value: "reservations", label: "Rezervasyonlar" },
  { value: "payments", label: "Odemeler" },
  { value: "deals", label: "Deallar" },
  { value: "tasks", label: "Gorevler" },
  { value: "notes", label: "Notlar" },
];

function TimelineTab({ customerId }) {
  const [items, setItems] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [filter, setFilter] = React.useState("");

  React.useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await getCustomerTimeline(customerId, { filter_type: filter || undefined, limit: 50 });
        setItems(res.items || []);
      } catch { setItems([]); }
      finally { setLoading(false); }
    })();
  }, [customerId, filter]);

  return (
    <div className="mt-3 border border-border rounded-xl p-3" data-testid="customer-timeline">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="font-bold text-base text-foreground">Timeline</div>
        <div className="flex gap-1">
          {TL_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              data-testid={`timeline-filter-${f.value || "all"}`}
              className={`px-2.5 py-1 rounded-full text-xs border cursor-pointer transition-colors ${
                filter === f.value
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground hover:bg-muted"
              }`}
            >{f.label}</button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col gap-2">
          {[1,2,3].map((i) => <div key={i} className="h-12 bg-muted rounded-lg animate-pulse" />)}
        </div>
      ) : items.length === 0 ? (
        <div className="text-muted-foreground text-sm text-center p-6">Bu musteri icin aktivite yok</div>
      ) : (
        <div className="flex flex-col gap-0.5">
          {items.map((item, i) => (
            <div key={i} className="flex items-start gap-2.5 py-2 px-1 border-b border-border/30" data-testid="timeline-item">
              <span className="text-lg leading-none mt-0.5">{TL_ICONS[item.type] || "\u{1F4CC}"}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-foreground">{item.title}</div>
                {item.subtitle && <div className="text-xs text-muted-foreground mt-0.5">{item.subtitle}</div>}
              </div>
              <div className="text-xs text-muted-foreground whitespace-nowrap" title={item.ts ? new Date(item.ts).toLocaleString("tr-TR") : ""}>
                {relTime(item.ts)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CrmCustomerDetailPage() {
  const navigate = useNavigate();
  const { customerId } = useParams();

  const [loading, setLoading] = useState(true);
  const [errMsg, setErrMsg] = useState("");
  const [detail, setDetail] = useState(null);

  const customer = detail?.customer;

  const [activeTab, setActiveTab] = useState("overview");

  const [editingTags, setEditingTags] = useState(false);
  const [tagsText, setTagsText] = useState("");
  const [savingTags, setSavingTags] = useState(false);
  const [tagsErr, setTagsErr] = useState("");

  const [activities, setActivities] = useState([]);
  const [activitiesTotal, setActivitiesTotal] = useState(0);
  const [activitiesLoading, setActivitiesLoading] = useState(false);
  const [activitiesErr, setActivitiesErr] = useState("");
  const [newBody, setNewBody] = useState("");
  const [creating, setCreating] = useState(false);

  const [inboxThreads, setInboxThreads] = useState([]);
  const [inboxTotal, setInboxTotal] = useState(0);
  const [inboxLoading, setInboxLoading] = useState(false);
  const [inboxErr, setInboxErr] = useState("");

  const computedTagsText = useMemo(() => {
    const tags = customer?.tags || [];
    return tags.join(", ");
  }, [customer?.tags]);

  async function load() {
    setLoading(true);
    setErrMsg("");
    try {
      const res = await getCustomer(customerId);
      setDetail(res);
      setTagsText((res?.customer?.tags || []).join(", "));
    } catch (e) {
      setErrMsg(e.message || "Detay yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchAll() {
    setLoading(true);
    setErrMsg("");
    try {
      const [cust, acts, inbox] = await Promise.all([
        getCustomer(customerId),
        listActivities({
          relatedType: "customer",
          relatedId: customerId,
          page: 1,
          page_size: 50,
        }),
        listCustomerInboxThreads(customerId, { page: 1, pageSize: 20 }),
      ]);

      setDetail(cust);
      setTagsText((cust?.customer?.tags || []).join(", "));
      setActivities(acts?.items || []);
      setActivitiesTotal(acts?.total || 0);
      setInboxThreads(inbox?.items || []);
      setInboxTotal(inbox?.total || 0);
    } catch (e) {
      setErrMsg(e.message || "Veriler yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId]);

  useEffect(() => {
    if (activeTab === "activities") {
      loadActivities();
    }
    if (activeTab === "overview") {
      loadInboxThreads();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, customerId]);

  async function saveTags() {
    setTagsErr("");
    setSavingTags(true);
    try {
      const tags = tagsText
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      await patchCustomer(customerId, { tags });
      setEditingTags(false);
      await load();
    } catch (e) {
      setTagsErr(e.message || "Etiketler kaydedilemedi.");
    } finally {
      setSavingTags(false);
    }
  }

  async function loadActivities() {
    setActivitiesLoading(true);
    setActivitiesErr("");
    try {
      const res = await listActivities({
        relatedType: "customer",
        relatedId: customerId,
        page: 1,
        page_size: 20,
      });
      setActivities(res?.items || []);
      setActivitiesTotal(res?.total || 0);
    } catch (e) {
      setActivitiesErr(e.message || "Aktiviteler yüklenemedi.");
      setActivities([]);
    } finally {
      setActivitiesLoading(false);
    }
  }

  async function loadInboxThreads() {
    setInboxLoading(true);
    setInboxErr("");
    try {
      const res = await listCustomerInboxThreads(customerId, { page: 1, pageSize: 20 });
      setInboxThreads(res?.items || []);
      setInboxTotal(res?.total || 0);
    } catch (e) {
      setInboxErr(e.message || "Inbox yüklenemedi.");
      setInboxThreads([]);
    } finally {
      setInboxLoading(false);
    }
  }

  async function handleCreateActivity(e) {
    e.preventDefault();
    if (!newBody.trim()) return;
    setCreating(true);
    setActivitiesErr("");
    try {
      await createActivity({
        type: "note",
        body: newBody.trim(),
        related_type: "customer",
        related_id: customerId,
      });
      setNewBody("");
      await loadActivities();
    } catch (e) {
      setActivitiesErr(e.message || "Aktivite eklenemedi.");
    } finally {
      setCreating(false);
    }
  }

  const BackButton = () => (
    <button
      onClick={() => navigate(-1)}
      className="px-2.5 py-2 rounded-lg border border-border bg-card cursor-pointer text-sm font-medium text-foreground hover:bg-muted transition-colors"
    >
      ← Geri
    </button>
  );

  if (loading) {
    return (
      <div className="p-4">
        <div className="text-muted-foreground text-sm">Yükleniyor…</div>
      </div>
    );
  }

  if (errMsg) {
    return (
      <div className="p-4">
        <BackButton />
        <div className="mt-3 p-3 border border-destructive/30 bg-destructive/5 rounded-xl text-destructive text-sm">
          {errMsg}
        </div>
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="p-4">
        <BackButton />
        <div className="mt-3 text-muted-foreground text-sm">Müşteri bulunamadı.</div>
      </div>
    );
  }

  const recentBookings = detail?.recent_bookings || [];
  const openDeals = detail?.open_deals || [];
  const openTasks = detail?.open_tasks || [];

  const mergedIntoId = customer.merged_into;
  const isMerged = Boolean(customer.is_merged && mergedIntoId);

  return (
    <div className="p-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <BackButton />
        <div className="text-xs text-muted-foreground">
          ID: <code>{customer.id}</code>
        </div>
      </div>

      {isMerged ? (
        <div className="mt-3 p-3 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive text-sm">
          <div className="font-semibold mb-1">Bu müşteri kaydı birleştirildi.</div>
          <div>
            Tüm işlemler <code>{mergedIntoId}</code> IDli ana kayıt üzerinden yürütülüyor.
            {" "}
            <button
              type="button"
              onClick={() => navigate(`/app/crm/customers/${mergedIntoId}`)}
              className="ml-1 px-2 py-1 rounded-full border border-foreground bg-card cursor-pointer text-xs hover:bg-muted transition-colors"
            >
              Ana kayıda aç
            </button>
          </div>
        </div>
      ) : null}

      {/* Header card */}
      <div className="mt-3 border border-border rounded-xl p-3.5">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <h1 className="m-0 text-xl font-bold text-foreground">{customer.name}</h1>

            <div className="mt-1.5">
              <Badge>{customer.type === "corporate" ? "Kurumsal" : "Bireysel"}</Badge>
              {customer.tc_vkn ? <Badge>TC/VKN: {customer.tc_vkn}</Badge> : null}
            </div>

            <div className="mt-2 text-sm text-foreground">
              <PrimaryContactLine contacts={customer.contacts} />
            </div>
          </div>

          {/* Tags */}
          <div className="min-w-[280px] flex-[1_1_280px]">
            <div className="flex items-center justify-between">
              <div className="text-xs text-muted-foreground">Etiketler</div>

              {!editingTags ? (
                <button
                  onClick={() => {
                    setTagsErr("");
                    setTagsText(computedTagsText);
                    setEditingTags(true);
                  }}
                  className="px-2.5 py-2 rounded-lg border border-border bg-card cursor-pointer text-sm hover:bg-muted transition-colors"
                >
                  Düzenle
                </button>
              ) : null}
            </div>

            {!editingTags ? (
              <div className="mt-2">
                {(customer.tags || []).length ? (
                  (customer.tags || []).map((t) => <Badge key={t}>{t}</Badge>)
                ) : (
                  <div className="text-muted-foreground text-sm">Etiket yok</div>
                )}
              </div>
            ) : (
              <div className="mt-2">
                <input
                  value={tagsText}
                  onChange={(e) => setTagsText(e.target.value)}
                  placeholder="vip, istanbul, corporate"
                  className="w-full p-2.5 rounded-lg border border-border text-sm bg-card text-foreground"
                />

                <div className="mt-2 flex justify-end gap-2.5">
                  <button
                    onClick={() => setEditingTags(false)}
                    disabled={savingTags}
                    className="px-2.5 py-2 rounded-lg border border-border bg-card cursor-pointer text-sm hover:bg-muted transition-colors"
                  >
                    İptal
                  </button>

                  <button
                    onClick={saveTags}
                    disabled={savingTags}
                    className="px-2.5 py-2 rounded-lg border border-foreground bg-foreground text-primary-foreground cursor-pointer text-sm hover:opacity-90 transition-opacity"
                  >
                    {savingTags ? "Kaydediliyor…" : "Kaydet"}
                  </button>
                </div>

                {tagsErr ? (
                  <div className="mt-2.5 p-2.5 rounded-lg border border-destructive/30 bg-destructive/5 text-destructive text-sm">
                    {tagsErr}
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs
        value={activeTab}
        onChange={setActiveTab}
        items={[
          { value: "overview", label: "Ozet" },
          { value: "timeline", label: "Timeline" },
          { value: "activities", label: "Aktiviteler" },
        ]}
      />

      {/* Tab content */}
      {activeTab === "overview" ? (
        <div className="mt-3 grid grid-cols-[minmax(0,2fr)_minmax(0,1.5fr)] gap-4">
          {/* Left column */}
          <div className="flex flex-col gap-3">
            {/* Inbox panel */}
            <div className="border border-border rounded-xl p-3">
              <div className="flex items-center justify-between gap-2">
                <h2 className="m-0 text-base font-bold text-foreground">Inbox</h2>
                {inboxTotal > 0 ? (
                  <span className="text-xs text-muted-foreground">{inboxTotal} thread</span>
                ) : null}
              </div>

              {inboxLoading && (
                <div className="mt-2 text-sm text-muted-foreground">Inbox yükleniyor...</div>
              )}
              {!inboxLoading && inboxErr && (
                <div className="mt-2 text-sm text-destructive">Inbox yükleme hatası: {inboxErr}</div>
              )}
              {!inboxLoading && !inboxErr && inboxThreads.length === 0 && (
                <div className="mt-2 text-sm text-muted-foreground">Bu müşteri için henüz inbox kaydı yok.</div>
              )}
              {!inboxLoading && !inboxErr && inboxThreads.length > 0 && (
                <div className="mt-2 flex flex-col gap-1.5">
                  {inboxThreads.map((t) => (
                    <div
                      key={t.id}
                      className="p-2 rounded-lg border border-border flex items-center justify-between gap-2 text-sm"
                    >
                      <div className="min-w-0">
                        <div className="font-medium text-foreground whitespace-nowrap overflow-hidden text-ellipsis">
                          {t.subject || "(Konu yok)"}
                        </div>
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          {t.channel || "internal"} • {formatDateTime(t.last_message_at)}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          window.location.href = `/app/inbox?thread=${t.id}`;
                        }}
                        className="px-2.5 py-1.5 rounded-full border border-foreground bg-card cursor-pointer text-xs whitespace-nowrap hover:bg-muted transition-colors"
                      >
                        Inbox'ta aç
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent bookings */}
            <div className="border border-border rounded-xl p-3">
              <div className="font-bold text-sm text-foreground">Son Rezervasyonlar</div>

              <div className="mt-2">
                {recentBookings.length ? (
                  <ul className="m-0 pl-4">
                    {recentBookings.map((b) => (
                      <li key={b.id} className="mb-2">
                        <div className="font-semibold text-sm text-foreground">{b.id}</div>
                        <div className="text-xs text-muted-foreground">
                          {(b.status || "-") + " • " +
                            (b.total_amount ? `${b.total_amount} ${b.currency || ""}` : "") +
                            (b.created_at ? ` • ${new Date(b.created_at).toLocaleString("tr-TR")}` : "")}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-muted-foreground text-sm">Bu müşteri için henüz rezervasyon yok.</div>
                )}
              </div>
            </div>
          </div>

          {/* Right column */}
          <div className="flex flex-col gap-3">
            {/* Open deals */}
            <div className="border border-border rounded-xl p-3">
              <div className="font-bold text-sm text-foreground">Açık Fırsatlar</div>

              <div className="mt-2">
                {openDeals.length ? (
                  <ul className="m-0 pl-4">
                    {openDeals.map((d) => (
                      <li key={d.id} className="mb-2">
                        <div className="font-semibold text-sm text-foreground">{d.title || d.id}</div>
                        <div className="text-xs text-muted-foreground">
                          Stage: {d.stage || "-"} {d.amount ? ` • ${d.amount} ${d.currency || ""}` : ""}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-muted-foreground text-sm">Henüz açık fırsat yok. (PR#3 ile dolacak)</div>
                )}
              </div>
            </div>

            {/* Open tasks */}
            <div className="border border-border rounded-xl p-3">
              <div className="font-bold text-sm text-foreground">Açık Görevler</div>

              <div className="mt-2">
                {openTasks.length ? (
                  <ul className="m-0 pl-4">
                    {openTasks.map((t) => (
                      <li key={t.id} className="mb-2">
                        <div className="font-semibold text-sm text-foreground">{t.title || t.id}</div>
                        <div className="text-xs text-muted-foreground">
                          Due: {t.due_date ? new Date(t.due_date).toLocaleString("tr-TR") : "-"} • Priority: {t.priority || "-"}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-muted-foreground text-sm">Henüz açık görev yok. (PR#3 ile dolacak)</div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {activeTab === "timeline" ? (
        <TimelineTab customerId={customerId} />
      ) : null}

      {activeTab === "activities" ? (
        <div className="mt-3 border border-border rounded-xl p-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="font-bold text-sm text-foreground">Aktiviteler</div>
              <div className="mt-1 text-sm text-muted-foreground">
                Notlar / görüşmeler / e-postalar
              </div>
            </div>
          </div>

          {/* New activity form */}
          <form onSubmit={handleCreateActivity} className="mt-3">
            <textarea
              value={newBody}
              onChange={(e) => setNewBody(e.target.value)}
              placeholder="Kısa bir not yazın..."
              rows={3}
              className="w-full p-2.5 rounded-lg border border-border text-sm resize-y bg-card text-foreground placeholder:text-muted-foreground"
            />
            <div className="mt-2 flex justify-between items-center gap-2">
              <div className="text-xs text-muted-foreground">
                {activitiesTotal ? `${activitiesTotal} aktivite` : "Henüz aktivite yok"}
              </div>
              <button
                type="submit"
                disabled={creating || !newBody.trim()}
                className="px-2.5 py-2 rounded-lg border border-foreground bg-foreground text-primary-foreground text-sm disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer hover:opacity-90 transition-opacity"
              >
                {creating ? "Ekleniyor..." : "Not ekle"}
              </button>
            </div>
          </form>

          {/* Activity list */}
          <div className="mt-3">
            {activitiesLoading && (
              <div className="text-muted-foreground text-sm">Aktiviteler yükleniyor...</div>
            )}
            {!activitiesLoading && activitiesErr && (
              <div className="p-2.5 rounded-lg border border-destructive/30 bg-destructive/5 text-destructive text-sm">
                {activitiesErr}
              </div>
            )}
            {!activitiesLoading && !activitiesErr && !activities.length && (
              <div className="text-muted-foreground text-sm">Bu müşteri için henüz aktivite kaydı yok.</div>
            )}
            {!activitiesLoading && !activitiesErr && activities.length > 0 && (
              <ul className="list-none m-0 p-0 mt-2">
                {activities.map((act) => (
                  <li
                    key={act.id}
                    className="border border-border rounded-lg p-2.5 mb-2 bg-muted/50"
                  >
                    <div className="flex justify-between gap-2">
                      <div className="text-xs font-semibold text-foreground">
                        {act.type === "note" ? "Not" : act.type}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {act.created_at
                          ? new Date(act.created_at).toLocaleString("tr-TR")
                          : ""}
                      </div>
                    </div>
                    <div className="mt-1 text-sm text-foreground whitespace-pre-wrap break-words">
                      {act.body}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
