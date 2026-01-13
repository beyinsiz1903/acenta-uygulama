import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createCustomer, listCustomers } from "../../lib/crm";

function useDebouncedValue(value, delayMs = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

function formatRelativeTime(dateIso) {
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

function Modal({ open, title, onClose, children }) {
  if (!open) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.35)",
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
          width: "min(720px, 100%)",
          background: "#fff",
          borderRadius: 12,
          padding: 16,
          boxShadow: "0 10px 30px rgba(0,0,0,0.2)",
        }}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>{title}</h2>
          <button onClick={onClose} style={{ border: "none", background: "transparent", fontSize: 18, cursor: "pointer" }}>
            ×
          </button>
        </div>
        <div style={{ marginTop: 12 }}>{children}</div>
      </div>
    </div>
  );
}

export default function CrmCustomersPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialSearch = searchParams.get("search") || "";
  const initialType = searchParams.get("type") || "";
  const initialTag = searchParams.get("tag") || "";
  const initialPage = Number(searchParams.get("page") || "1");

  const [search, setSearch] = useState(initialSearch);
  const [type, setType] = useState(initialType);
  const [tag, setTag] = useState(initialTag);
  const [page, setPage] = useState(Number.isFinite(initialPage) && initialPage > 0 ? initialPage : 1);

  const debouncedSearch = useDebouncedValue(search, 350);

  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 25 });
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createErr, setCreateErr] = useState("");

  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("individual");
  const [newEmail, setNewEmail] = useState("");
  const [newPhone, setNewPhone] = useState("");

  const queryParams = useMemo(() => {
    const qp = {
      page,
      page_size: 25,
    };
    if (debouncedSearch?.trim()) qp.search = debouncedSearch.trim();
    if (type) qp.type = type;
    if (tag?.trim()) qp.tag = [tag.trim()];
    return qp;
  }, [debouncedSearch, type, tag, page]);

  useEffect(() => {
    const next = {};
    if (search?.trim()) next.search = search.trim();
    if (type) next.type = type;
    if (tag?.trim()) next.tag = tag.trim();
    if (page && page !== 1) next.page = String(page);
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, type, tag, page]);

  async function refresh() {
    setLoading(true);
    setErrMsg("");
    try {
      const res = await listCustomers(queryParams);
      setData(res);
    } catch (e) {
      setErrMsg(e.message || "Liste yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryParams]);

  function openCreate() {
    setCreateErr("");
    setNewName("");
    setNewType("individual");
    setNewEmail("");
    setNewPhone("");
    setCreateOpen(true);
  }

  async function submitCreate(e) {
    e.preventDefault();
    setCreateErr("");
    setCreateLoading(true);
    try {
      const contacts = [];
      if (newEmail.trim()) contacts.push({ type: "email", value: newEmail.trim(), is_primary: true });
      if (newPhone.trim()) contacts.push({ type: "phone", value: newPhone.trim(), is_primary: !contacts.length });
      const payload = {
        name: newName.trim(),
        type: newType,
        contacts,
      };
      const created = await createCustomer(payload);
      setCreateOpen(false);
      await refresh();
      navigate(`/app/crm/customers/${created.id}`);
    } catch (e2) {
      setCreateErr(e2.message || "Müşteri oluşturulamadı.");
    } finally {
      setCreateLoading(false);
    }
  }

  const hasPrev = page > 1;
  const hasNext = data.total > page * (data.page_size || 25);

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>CRM • Müşteriler</h1>
          <div style={{ color: "#666", marginTop: 4, fontSize: 13 }}>Müşterileri arayın, etiketleyin ve detayına inin.</div>
        </div>
        <button
          onClick={openCreate}
          style={{
            padding: "10px 12px",
            borderRadius: 10,
            border: "1px solid #111",
            background: "#111",
            color: "white",
            cursor: "pointer",
          }}
        >
          Yeni Mf50fteri
        </button>
      </div>

      <div
        style={{
          marginTop: 14,
          padding: 12,
          borderRadius: 12,
          border: "1px solid #eee",
          display: "flex",
          gap: 10,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <input
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
          placeholder="Ara: isim / e-posta / telefon"
          style={{ padding: 10, borderRadius: 10, border: "1px solid #ddd", minWidth: 280, flex: "1 1 280px" }}
        />

        <select
          value={type}
          onChange={(e) => {
            setPage(1);
            setType(e.target.value);
          }}
          style={{ padding: 10, borderRadius: 10, border: "1px solid #ddd" }}
        >
          <option value="">Tümü</option>
          <option value="individual">Bireysel</option>
          <option value="corporate">Kurumsal</option>
        </select>

        <input
          value={tag}
          onChange={(e) => {
            setPage(1);
            setTag(e.target.value);
          }}
          placeholder="Etiket (f6r: vip)"
          style={{ padding: 10, borderRadius: 10, border: "1px solid #ddd", width: 180 }}
        />

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ fontSize: 13, color: "#666" }}>
            Toplam: <b>{data.total}</b>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        {errMsg ? (
          <div style={{ padding: 12, border: "1px solid #f2caca", background: "#fff5f5", borderRadius: 12, color: "#8a1f1f" }}>{errMsg}</div>
        ) : null}

        <div style={{ marginTop: 10, border: "1px solid #eee", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ padding: 10, borderBottom: "1px solid #eee", background: "#fafafa", fontSize: 13, color: "#666" }}>
            {loading ? "Yfckleniyore280a6" : "Liste"}
          </div>

          {!loading && data.items?.length === 0 ? (
            <div style={{ padding: 18 }}>
              <div style={{ fontSize: 16, fontWeight: 600 }}>Henfcz mf50fteri yok.</div>
              <div style={{ marginTop: 6, color: "#666" }}>İlk mf50fterinizi oluf5turmak if7in “Yeni Mf50fteri” butonunu kullan0fn.</div>
              <button
                onClick={openCreate}
                style={{ marginTop: 12, padding: "10px 12px", borderRadius: 10, border: "1px solid #111", background: "#111", color: "white", cursor: "pointer" }}
              >
                Yeni Mf50fteri Oluf5tur
              </button>
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#fff" }}>
                  <th style={{ textAlign: "left", padding: 12, fontSize: 12, color: "#666", borderBottom: "1px solid #eee" }}>Ad0f</th>
                  <th style={{ textAlign: "left", padding: 12, fontSize: 12, color: "#666", borderBottom: "1px solid #eee" }}>Tip</th>
                  <th style={{ textAlign: "left", padding: 12, fontSize: 12, color: "#666", borderBottom: "1px solid #eee" }}>Etiketler</th>
                  <th style={{ textAlign: "left", padding: 12, fontSize: 12, color: "#666", borderBottom: "1px solid #eee" }}>Son gfcncelleme</th>
                </tr>
              </thead>
              <tbody>
                {data.items?.map((c) => {
                  const tagsArr = c.tags || [];
                  const shownTags = tagsArr.slice(0, 3);
                  const remaining = tagsArr.length - shownTags.length;

                  return (
                    <tr
                      key={c.id}
                      onClick={() => navigate(`/app/crm/customers/${c.id}`)}
                      style={{ cursor: "pointer" }}
                    >
                      <td style={{ padding: 12, borderBottom: "1px solid #f3f3f3" }}>
                        <div style={{ fontWeight: 600 }}>{c.name}</div>
                        <div style={{ fontSize: 12, color: "#666", marginTop: 2 }}>
                          {(c.contacts || []).filter((x) => x?.is_primary)?.map((x, idx) => (
                            <span key={idx} style={{ marginRight: 10 }}>
                              {x.type === "email" ? "✉️" : "📞"} {x.value}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: 12, borderBottom: "1px solid #f3f3f3" }}>
                        <Badge>{c.type === "corporate" ? "Kurumsal" : "Bireysel"}</Badge>
                      </td>
                      <td style={{ padding: 12, borderBottom: "1px solid #f3f3f3" }}>
                        {shownTags.map((t) => (
                          <Badge key={t}>{t}</Badge>
                        ))}
                        {remaining > 0 ? <Badge>+{remaining}</Badge> : null}
                      </td>
                      <td style={{ padding: 12, borderBottom: "1px solid #f3f3f3", color: "#444" }}>
                        {formatRelativeTime(c.updated_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        <div style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <button
            disabled={!hasPrev || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            style={{
              padding: "8px 10px",
              borderRadius: 10,
              border: "1px solid #ddd",
              background: hasPrev ? "#fff" : "#f6f6f6",
              cursor: hasPrev ? "pointer" : "not-allowed",
            }}
          >
            d6nceki
          </button>

          <div style={{ fontSize: 13, color: "#666" }}>
            Sayfa <b>{page}</b>
          </div>

          <button
            disabled={!hasNext || loading}
            onClick={() => setPage((p) => p + 1)}
            style={{
              padding: "8px 10px",
              borderRadius: 10,
              border: "1px solid #ddd",
              background: hasNext ? "#fff" : "#f6f6f6",
              cursor: hasNext ? "pointer" : "not-allowed",
            }}
          >
            Sonraki
          </button>
        </div>
      </div>

      <Modal open={createOpen} title="Yeni Mf50fteri Oluf5tur" onClose={() => (createLoading ? null : setCreateOpen(false))}>
        <form onSubmit={submitCreate}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <div style={{ gridColumn: "1 / -1" }}>
              <label style={{ fontSize: 12, color: "#666" }}>Ad Soyad / Unvan *</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
                minLength={2}
                placeholder="d6rn: ACME Travel"
                style={{ marginTop: 6, width: "100%", padding: 10, borderRadius: 10, border: "1px solid #ddd" }}
              />
            </div>

            <div>
              <label style={{ fontSize: 12, color: "#666" }}>Tip</label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                style={{ marginTop: 6, width: "100%", padding: 10, borderRadius: 10, border: "1px solid #ddd" }}
              >
                <option value="individual">Bireysel</option>
                <option value="corporate">Kurumsal</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: 12, color: "#666" }}>Birincil E-posta</label>
              <input
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="ops@acme.com"
                style={{ marginTop: 6, width: "100%", padding: 10, borderRadius: 10, border: "1px solid #ddd" }}
              />
            </div>

            <div style={{ gridColumn: "1 / -1" }}>
              <label style={{ fontSize: 12, color: "#666" }}>Birincil Telefon</label>
              <input
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
                placeholder="+90..."
                style={{ marginTop: 6, width: "100%", padding: 10, borderRadius: 10, border: "1px solid #ddd" }}
              />
            </div>
          </div>

          {createErr ? (
            <div style={{ marginTop: 10, padding: 10, borderRadius: 10, border: "1px solid #f2caca", background: "#fff5f5", color: "#8a1f1f" }}>
              {createErr}
            </div>
          ) : null}

          <div style={{ marginTop: 14, display: "flex", justifyContent: "flex-end", gap: 10 }}>
            <button
              type="button"
              onClick={() => setCreateOpen(false)}
              disabled={createLoading}
              style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #ddd", background: "#fff", cursor: "pointer" }}
            >
              İptal
            </button>
            <button
              type="submit"
              disabled={createLoading || newName.trim().length < 2}
              style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #111", background: "#111", color: "white", cursor: "pointer" }}
            >
              {createLoading ? "Oluf5turuluyore280a6" : "Oluf5tur"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
