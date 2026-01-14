// frontend/src/pages/crm/CrmCustomerDetailPage.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getCustomer, patchCustomer, listActivities, createActivity } from "../../lib/crm";

function Badge({ children }) {
  return (
    <span
      style={{
        display: "inline-flex",
        padding: "2px 8px",
        borderRadius: 999,
        border: "1px solid #ddd",
        fontSize: 12,
        lineHeight: "18px",
        marginRight: 6,
        marginBottom: 6,
      }}
    >
      {children}
    </span>
  );
}

function PrimaryContactLine({ contacts }) {
  const primary = (contacts || []).filter((c) => c?.is_primary);
  if (!primary.length) return <span style={{ color: "#666" }}>Birincil iletişim yok</span>;

  return (
    <>
      {primary.map((c, idx) => (
        <span key={idx} style={{ marginRight: 12 }}>
          {c.type === "email" ? "✉️" : "📞"} {c.value}
        </span>
      ))}
    </>
  );
}

function Tabs({ value, onChange, items }) {
  return (
    <div style={{ display: "flex", gap: 8, borderBottom: "1px solid #eee", marginTop: 12 }}>
      {items.map((it) => {
        const active = it.value === value;
        return (
          <button
            key={it.value}
            onClick={() => onChange(it.value)}
            style={{
              padding: "10px 10px",
              border: "none",
              borderBottom: active ? "2px solid #111" : "2px solid transparent",
              background: "transparent",
              cursor: "pointer",
              fontWeight: active ? 700 : 500,
              color: active ? "#111" : "#666",
            }}
          >
            {it.label}
          </button>
        );
      })}
    </div>
  );
}

export default function CrmCustomerDetailPage() {
  const navigate = useNavigate();
  const { customerId } = useParams();

  const [loading, setLoading] = useState(true);
  const [errMsg, setErrMsg] = useState("");
  const [detail, setDetail] = useState(null); // CustomerDetailOut

  const customer = detail?.customer;

  const [activeTab, setActiveTab] = useState("overview");

  // Tags editing
  const [editingTags, setEditingTags] = useState(false);
  const [tagsText, setTagsText] = useState("");
  const [savingTags, setSavingTags] = useState(false);
  const [tagsErr, setTagsErr] = useState("");

  // Activities state
  const [activities, setActivities] = useState([]);
  const [activitiesTotal, setActivitiesTotal] = useState(0);
  const [activitiesLoading, setActivitiesLoading] = useState(false);
  const [activitiesErr, setActivitiesErr] = useState("");
  const [newBody, setNewBody] = useState("");
  const [creating, setCreating] = useState(false);

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

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId]);

  useEffect(() => {
    if (activeTab === "activities") {
      loadActivities();
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
      setActivitiesErr(e.message || "Aktiviteler y\u00fcklenemedi.");
      setActivities([]);
    } finally {
      setActivitiesLoading(false);
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

  // ---- Render states ----
  if (loading) {
    return (
      <div style={{ padding: 16 }}>
        <div style={{ color: "#666" }}>Yükleniyor{"\u2026"}</div>
      </div>
    );
  }

  if (errMsg) {
    return (
      <div style={{ padding: 16 }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: "8px 10px",
            borderRadius: 10,
            border: "1px solid #ddd",
            background: "#fff",
            cursor: "pointer",
          }}
        >
          {"\u2190"} Geri
        </button>

        <div
          style={{
            marginTop: 12,
            padding: 12,
            border: "1px solid #f2caca",
            background: "#fff5f5",
            borderRadius: 12,
            color: "#8a1f1f",
          }}
        >
          {errMsg}
        </div>
      </div>
    );
  }

  if (!customer) {
    return (
      <div style={{ padding: 16 }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: "8px 10px",
            borderRadius: 10,
            border: "1px solid #ddd",
            background: "#fff",
            cursor: "pointer",
          }}
        >
          {"\u2190"} Geri
        </button>

        <div style={{ marginTop: 12, color: "#666" }}>Müşteri bulunamadı.</div>
      </div>
    );
  }

  const recentBookings = detail?.recent_bookings || [];
  const openDeals = detail?.open_deals || [];
  const openTasks = detail?.open_tasks || [];

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
      setActivitiesErr(e.message || "Aktiviteler y\u00fcklenemedi.");
      setActivities([]);
    } finally {
      setActivitiesLoading(false);
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

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            padding: "8px 10px",
            borderRadius: 10,
            border: "1px solid #ddd",
            background: "#fff",
            cursor: "pointer",
          }}
        >
          {"\u2190"} Geri
        </button>

        <div style={{ color: "#666", fontSize: 12 }}>
          ID: <code>{customer.id}</code>
        </div>
      </div>

      {/* Header card */}
      <div style={{ marginTop: 12, border: "1px solid #eee", borderRadius: 12, padding: 14 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 22 }}>{customer.name}</h1>

            <div style={{ marginTop: 6 }}>
              <Badge>{customer.type === "corporate" ? "Kurumsal" : "Bireysel"}</Badge>
              {customer.tc_vkn ? <Badge>TC/VKN: {customer.tc_vkn}</Badge> : null}
            </div>

            <div style={{ marginTop: 8, fontSize: 13, color: "#444" }}>
              <PrimaryContactLine contacts={customer.contacts} />
            </div>
          </div>

          {/* Tags */}
          <div style={{ minWidth: 280, flex: "1 1 280px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ fontSize: 12, color: "#666" }}>Etiketler</div>

              {!editingTags ? (
                <button
                  onClick={() => {
                    setTagsErr("");
                    setTagsText(computedTagsText);
                    setEditingTags(true);
                  }}
                  style={{
                    padding: "8px 10px",
                    borderRadius: 10,
                    border: "1px solid #ddd",
                    background: "#fff",
                    cursor: "pointer",
                  }}
                >
                  Düzenle
                </button>
              ) : null}
            </div>

            {!editingTags ? (
              <div style={{ marginTop: 8 }}>
                {(customer.tags || []).length ? (
                  (customer.tags || []).map((t) => <Badge key={t}>{t}</Badge>)
                ) : (
                  <div style={{ color: "#666", fontSize: 13 }}>Etiket yok</div>
                )}
              </div>
            ) : (
              <div style={{ marginTop: 8 }}>
                <input
                  value={tagsText}
                  onChange={(e) => setTagsText(e.target.value)}
                  placeholder="vip, istanbul, corporate"
                  style={{ width: "100%", padding: 10, borderRadius: 10, border: "1px solid #ddd" }}
                />

                <div style={{ marginTop: 8, display: "flex", justifyContent: "flex-end", gap: 10 }}>
                  <button
                    onClick={() => setEditingTags(false)}
                    disabled={savingTags}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 10,
                      border: "1px solid #ddd",
                      background: "#fff",
                      cursor: "pointer",
                    }}
                  >
                    İptal
                  </button>

                  <button
                    onClick={saveTags}
                    disabled={savingTags}
                    style={{
                      padding: "8px 10px",
                      borderRadius: 10,
                      border: "1px solid #111",
                      background: "#111",
                      color: "white",
                      cursor: "pointer",
                    }}
                  >
                    {savingTags ? `Kaydediliyor${"\u2026"}` : "Kaydet"}
                  </button>
                </div>

                {tagsErr ? (
                  <div
                    style={{
                      marginTop: 10,
                      padding: 10,
                      borderRadius: 10,
                      border: "1px solid #f2caca",
                      background: "#fff5f5",
                      color: "#8a1f1f",
                    }}
                  >
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
          { value: "overview", label: "Özet" },
          { value: "activities", label: "Aktiviteler" },
        ]}
      />

      {/* Tab content */}
      {activeTab === "overview" ? (
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
          {/* Recent bookings */}
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 700 }}>Son Rezervasyonlar</div>

            <div style={{ marginTop: 8 }}>
              {recentBookings.length ? (
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {recentBookings.map((b) => (
                    <li key={b.id} style={{ marginBottom: 8 }}>
                      <div style={{ fontWeight: 600 }}>{b.id}</div>
                      <div style={{ fontSize: 12, color: "#666" }}>
                        {(b.status || "-") + " • " +
                          (b.total_amount ? `${b.total_amount} ${b.currency || ""}` : "") +
                          (b.created_at ? ` • ${new Date(b.created_at).toLocaleString("tr-TR")}` : "")}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: "#666", fontSize: 13 }}>Bu müşteri için henüz rezervasyon yok.</div>
              )}
            </div>
          </div>

          {/* Open deals */}
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 700 }}>Açık Fırsatlar</div>

            <div style={{ marginTop: 8 }}>
              {openDeals.length ? (
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {openDeals.map((d) => (
                    <li key={d.id} style={{ marginBottom: 8 }}>
                      <div style={{ fontWeight: 600 }}>{d.title || d.id}</div>
                      <div style={{ fontSize: 12, color: "#666" }}>
                        Stage: {d.stage || "-"} {d.amount ? ` • ${d.amount} ${d.currency || ""}` : ""}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: "#666", fontSize: 13 }}>Henüz açık fırsat yok. (PR#3 ile dolacak)</div>
              )}
            </div>
          </div>

          {/* Open tasks */}
          <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
            <div style={{ fontWeight: 700 }}>Açık Görevler</div>

            <div style={{ marginTop: 8 }}>
              {openTasks.length ? (
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {openTasks.map((t) => (
                    <li key={t.id} style={{ marginBottom: 8 }}>
                      <div style={{ fontWeight: 600 }}>{t.title || t.id}</div>
                      <div style={{ fontSize: 12, color: "#666" }}>
                        Due: {t.due_date ? new Date(t.due_date).toLocaleString("tr-TR") : "-"} • Priority: {t.priority || "-"}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: "#666", fontSize: 13 }}>Henüz açık görev yok. (PR#3 ile dolacak)</div>
              )}
            </div>
          </div>
        </div>
      ) : null}

      {activeTab === "activities" ? (
        <div style={{ marginTop: 12, border: "1px solid #eee", borderRadius: 12, padding: 12 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
            <div>
              <div style={{ fontWeight: 700 }}>Aktiviteler</div>
              <div style={{ marginTop: 4, fontSize: 13, color: "#666" }}>
                {"Notlar / g\u00f6r\u00fc\u015fmeler / e-postalar"}
              </div>
            </div>
          </div>

          {/* New activity form */}
          <form onSubmit={handleCreateActivity} style={{ marginTop: 12 }}>
            <textarea
              value={newBody}
              onChange={(e) => setNewBody(e.target.value)}
              placeholder={"K\u0131sa bir not yaz\u0131n..."}
              rows={3}
              style={{
                width: "100%",
                padding: 10,
                borderRadius: 10,
                border: "1px solid #ddd",
                fontSize: 13,
                resize: "vertical",
              }}
            />
            <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <div style={{ fontSize: 12, color: "#666" }}>
                {activitiesTotal ? `${activitiesTotal} aktivite` : "Hen\u00fcz aktivite yok"}
              </div>
              <button
                type="submit"
                disabled={creating || !newBody.trim()}
                style={{
                  padding: "8px 10px",
                  borderRadius: 10,
                  border: "1px solid #111",
                  background: "#111",
                  color: "white",
                  cursor: creating || !newBody.trim() ? "not-allowed" : "pointer",
                  fontSize: 13,
                }}
              >
                {creating ? "Ekleniyor..." : "Not ekle"}
              </button>
            </div>
          </form>

          {/* Activity list */}
          <div style={{ marginTop: 12 }}>
            {activitiesLoading ? (
              <div style={{ color: "#666", fontSize: 13 }}>Aktiviteler y\u00fckleniyor...</div>
            ) : activitiesErr ? (
              <div
                style={{
                  padding: 10,
                  borderRadius: 10,
                  border: "1px solid #f2caca",
                  background: "#fff5f5",
                  color: "#8a1f1f",
                  fontSize: 13,
                }}
              >
                {activitiesErr}
              </div>
            ) : !activities.length ? (
              <div style={{ color: "#666", fontSize: 13 }}>Bu m\u00fc\u015fteri i\u00e7in hen\u00fcz aktivite kayd\u0131 yok.</div>
            ) : (
              <ul style={{ listStyle: "none", margin: 0, padding: 0, marginTop: 8 }}>
                {activities.map((act) => (
                  <li
                    key={act.id}
                    style={{
                      border: "1px solid #eee",
                      borderRadius: 10,
                      padding: 10,
                      marginBottom: 8,
                      background: "#fafafa",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: "#444" }}>
                        {act.type === "note" ? "Not" : act.type}
                      </div>
                      <div style={{ fontSize: 11, color: "#666" }}>
                        {act.created_at
                          ? new Date(act.created_at).toLocaleString("tr-TR")
                          : ""}
                      </div>
                    </div>
                    <div
                      style={{
                        marginTop: 4,
                        fontSize: 13,
                        color: "#333",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                      }}
                    >
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
