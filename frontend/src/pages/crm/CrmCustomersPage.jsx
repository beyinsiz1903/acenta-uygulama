// frontend/src/pages/crm/CrmCustomersPage.jsx
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Users, Plus, Search, ChevronLeft, ChevronRight, X, Mail, Phone, Tag, User, Building2 } from "lucide-react";
import { createCustomer, listCustomers } from "../../lib/crm";

// ---- utils ----
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

function Badge({ children, variant }) {
  const base = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mr-1.5 mb-1";
  const variants = {
    default: "bg-muted text-muted-foreground border border-border/50",
    corporate: "bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-950/30 dark:text-blue-300 dark:border-blue-800",
    individual: "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800",
    tag: "bg-violet-50 text-violet-700 border border-violet-200 dark:bg-violet-950/30 dark:text-violet-300 dark:border-violet-800",
  };
  return <span className={`${base} ${variants[variant] || variants.default}`}>{children}</span>;
}

function Modal({ open, title, onClose, children, disableClose }) {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50"
      onMouseDown={() => (disableClose ? null : onClose())}
    >
      <div
        className="w-full max-w-lg bg-card rounded-xl border border-border/60 shadow-xl p-5"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-foreground">{title}</h2>
          <button
            type="button"
            onClick={() => (disableClose ? null : onClose())}
            className={`p-1 rounded-lg hover:bg-muted/50 transition-colors ${disableClose ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
            aria-label="Kapat"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ---- page ----
export default function CrmCustomersPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Read URL state
  const initialSearch = searchParams.get("search") || "";
  const initialType = searchParams.get("type") || "";
  const initialTag = searchParams.get("tag") || "";
  const initialPageRaw = Number(searchParams.get("page") || "1");
  const initialPage = Number.isFinite(initialPageRaw) && initialPageRaw > 0 ? initialPageRaw : 1;

  // Local state
  const [search, setSearch] = useState(initialSearch);
  const [type, setType] = useState(initialType);
  const [tag, setTag] = useState(initialTag);
  const [page, setPage] = useState(initialPage);

  const debouncedSearch = useDebouncedValue(search, 350);

  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 25 });
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");

  // Create modal state
  const [createOpen, setCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createErr, setCreateErr] = useState("");

  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("individual");
  const [newEmail, setNewEmail] = useState("");
  const [newPhone, setNewPhone] = useState("");

  const queryParams = useMemo(() => {
    const qp = { page, page_size: 25 };
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
      const name = newName.trim();
      const contacts = [];
      if (newEmail.trim()) contacts.push({ type: "email", value: newEmail.trim(), is_primary: true });
      if (newPhone.trim()) contacts.push({ type: "phone", value: newPhone.trim(), is_primary: !contacts.length });
      const payload = { name, type: newType, contacts };
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

  const pageSize = data.page_size || 25;
  const hasPrev = page > 1;
  const hasNext = data.total > page * pageSize;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Müşteriler
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Müşterileri arayın, etiketleyin ve detayına inin.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
        >
          <Plus className="h-4 w-4" />
          Yeni Müşteri
        </button>
      </div>

      {/* Filters */}
      <div className="rounded-xl border border-border/60 bg-card p-3 flex gap-3 flex-wrap items-center">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/50" />
          <input
            value={search}
            onChange={(e) => { setPage(1); setSearch(e.target.value); }}
            placeholder="Ara: isim / e-posta / telefon"
            className="w-full pl-9 pr-3 py-2.5 text-sm rounded-lg border border-border/60 bg-background text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
          />
        </div>

        <select
          value={type}
          onChange={(e) => { setPage(1); setType(e.target.value); }}
          className="px-3 py-2.5 text-sm rounded-lg border border-border/60 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
        >
          <option value="">Tümü</option>
          <option value="individual">Bireysel</option>
          <option value="corporate">Kurumsal</option>
        </select>

        <div className="relative">
          <Tag className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50" />
          <input
            value={tag}
            onChange={(e) => { setPage(1); setTag(e.target.value); }}
            placeholder="Etiket (ör: vip)"
            className="pl-9 pr-3 py-2.5 text-sm rounded-lg border border-border/60 bg-background text-foreground placeholder:text-muted-foreground/50 w-[180px] focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
          />
        </div>

        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            Toplam: <span className="font-semibold text-foreground">{data.total}</span>
          </span>
        </div>
      </div>

      {/* Error */}
      {errMsg && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 dark:border-rose-800 dark:bg-rose-950/30 px-4 py-3 text-sm text-rose-700 dark:text-rose-300">
          {errMsg}
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl border border-border/60 bg-card overflow-hidden">
        {/* Table header info */}
        <div className="px-4 py-3 border-b border-border/40 bg-muted/30 flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">
            {loading ? "Yükleniyor\u2026" : `${data.total} müşteri`}
          </span>
        </div>

        {!loading && (data.items || []).length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <div className="h-14 w-14 rounded-full bg-muted/50 flex items-center justify-center mb-4">
              <Users className="h-6 w-6 text-muted-foreground/50" />
            </div>
            <p className="text-sm font-semibold text-foreground mb-1">Henüz müşteri yok</p>
            <p className="text-sm text-muted-foreground mb-4">
              İlk müşterinizi oluşturmak için aşağıdaki butonu kullanın.
            </p>
            <button
              onClick={openCreate}
              className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
            >
              <Plus className="h-4 w-4" />
              Yeni Müşteri Oluştur
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border/40">
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Adı</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tip</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Etiketler</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Son Güncelleme</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted-foreground">
                      Yükleniyor...
                    </td>
                  </tr>
                ) : (data.items || []).map((c) => {
                  const tagsArr = c.tags || [];
                  const shownTags = tagsArr.slice(0, 3);
                  const remaining = tagsArr.length - shownTags.length;
                  const primaryContacts = (c.contacts || []).filter((x) => x?.is_primary);

                  return (
                    <tr
                      key={c.id}
                      onClick={() => navigate(`/app/crm/customers/${c.id}`)}
                      className="border-b border-border/20 last:border-0 cursor-pointer hover:bg-muted/30 transition-colors group"
                    >
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                            {c.type === "corporate" ? (
                              <Building2 className="h-4 w-4 text-primary" />
                            ) : (
                              <User className="h-4 w-4 text-primary" />
                            )}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                              {c.name}
                            </p>
                            <div className="flex items-center gap-3 mt-0.5">
                              {primaryContacts.length ? (
                                primaryContacts.map((x, idx) => (
                                  <span key={idx} className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                                    {x.type === "email" ? <Mail className="h-3 w-3" /> : <Phone className="h-3 w-3" />}
                                    {x.value}
                                  </span>
                                ))
                              ) : (
                                <span className="text-xs text-muted-foreground/50">Birincil iletişim yok</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3.5">
                        <Badge variant={c.type === "corporate" ? "corporate" : "individual"}>
                          {c.type === "corporate" ? "Kurumsal" : "Bireysel"}
                        </Badge>
                      </td>

                      <td className="px-4 py-3.5">
                        {shownTags.map((t) => (
                          <Badge key={t} variant="tag">{t}</Badge>
                        ))}
                        {remaining > 0 && <Badge variant="default">+{remaining}</Badge>}
                        {tagsArr.length === 0 && <span className="text-xs text-muted-foreground/40">—</span>}
                      </td>

                      <td className="px-4 py-3.5">
                        <span className="text-xs text-muted-foreground">{formatRelativeTime(c.updated_at)}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <button
          disabled={!hasPrev || loading}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          className={`inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium rounded-lg border transition-colors
            ${hasPrev
              ? "border-border/60 bg-card text-foreground hover:bg-muted/50 cursor-pointer"
              : "border-border/30 bg-muted/20 text-muted-foreground/50 cursor-not-allowed"
            }`}
        >
          <ChevronLeft className="h-4 w-4" />
          Önceki
        </button>

        <span className="text-sm text-muted-foreground">
          Sayfa <span className="font-semibold text-foreground">{page}</span>
        </span>

        <button
          disabled={!hasNext || loading}
          onClick={() => setPage((p) => p + 1)}
          className={`inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium rounded-lg border transition-colors
            ${hasNext
              ? "border-border/60 bg-card text-foreground hover:bg-muted/50 cursor-pointer"
              : "border-border/30 bg-muted/20 text-muted-foreground/50 cursor-not-allowed"
            }`}
        >
          Sonraki
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Create Modal */}
      <Modal
        open={createOpen}
        title="Yeni Müşteri Oluştur"
        onClose={() => setCreateOpen(false)}
        disableClose={createLoading}
      >
        <form onSubmit={submitCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Ad Soyad / Unvan *</label>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
                minLength={2}
                placeholder="Örn: ACME Travel"
                className="w-full px-3 py-2.5 text-sm rounded-lg border border-border/60 bg-background text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Tip</label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                className="w-full px-3 py-2.5 text-sm rounded-lg border border-border/60 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
              >
                <option value="individual">Bireysel</option>
                <option value="corporate">Kurumsal</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Birincil E-posta</label>
              <input
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="ops@acme.com"
                className="w-full px-3 py-2.5 text-sm rounded-lg border border-border/60 bg-background text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
              />
            </div>

            <div className="col-span-2">
              <label className="block text-xs font-medium text-muted-foreground mb-1.5">Birincil Telefon</label>
              <input
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
                placeholder="+90..."
                className="w-full px-3 py-2.5 text-sm rounded-lg border border-border/60 bg-background text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
              />
            </div>
          </div>

          {createErr && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 dark:border-rose-800 dark:bg-rose-950/30 px-3 py-2.5 text-xs text-rose-700 dark:text-rose-300">
              {createErr}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setCreateOpen(false)}
              disabled={createLoading}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-border/60 bg-card text-foreground hover:bg-muted/50 transition-colors"
            >
              İptal
            </button>
            <button
              type="submit"
              disabled={createLoading || newName.trim().length < 2}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createLoading ? "Oluşturuluyor\u2026" : "Oluştur"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
