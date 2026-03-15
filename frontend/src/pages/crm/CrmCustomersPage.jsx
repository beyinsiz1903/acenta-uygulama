import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Users, Plus, Mail, Phone, Tag, User, Building2, ChevronLeft, ChevronRight } from "lucide-react";
import { createCustomer, listCustomers } from "../../lib/crm";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { PageShell, DataTable, FilterBar, StatusBadge } from "../../design-system";

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

/* ───────── Create Customer Dialog ───────── */
function CreateCustomerDialog({ open, onOpenChange, onCreated }) {
  const [name, setName] = useState("");
  const [type, setType] = useState("individual");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) { setName(""); setType("individual"); setEmail(""); setPhone(""); setError(""); }
  }, [open]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const contacts = [];
      if (email.trim()) contacts.push({ type: "email", value: email.trim(), is_primary: true });
      if (phone.trim()) contacts.push({ type: "phone", value: phone.trim(), is_primary: !contacts.length });
      const created = await createCustomer({ name: name.trim(), type, contacts });
      onCreated?.(created);
      onOpenChange(false);
    } catch (e2) {
      setError(e2.message || "Müşteri oluşturulamadı.");
    } finally { setLoading(false); }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>Yeni Müşteri Oluştur</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 space-y-2">
              <Label>Ad Soyad / Unvan *</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} placeholder="Örn: ACME Travel" data-testid="crm-create-name" />
            </div>
            <div className="space-y-2">
              <Label>Tip</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger data-testid="crm-create-type"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="individual">Bireysel</SelectItem>
                  <SelectItem value="corporate">Kurumsal</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Birincil E-posta</Label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ops@acme.com" data-testid="crm-create-email" />
            </div>
            <div className="col-span-2 space-y-2">
              <Label>Birincil Telefon</Label>
              <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+90..." data-testid="crm-create-phone" />
            </div>
          </div>
          {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">{error}</div>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>İptal</Button>
            <Button type="submit" disabled={loading || name.trim().length < 2} data-testid="crm-create-submit">
              {loading ? "Oluşturuluyor..." : "Oluştur"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ═══════════════════════ MAIN PAGE ═══════════════════════ */
export default function CrmCustomersPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialSearch = searchParams.get("search") || "";
  const initialType = searchParams.get("type") || "";
  const initialTag = searchParams.get("tag") || "";
  const initialPage = Math.max(1, Number(searchParams.get("page") || "1") || 1);

  const [search, setSearch] = useState(initialSearch);
  const [type, setType] = useState(initialType);
  const [tag, setTag] = useState(initialTag);
  const [page, setPage] = useState(initialPage);

  const [data, setData] = useState({ items: [], total: 0, page: 1, page_size: 25 });
  const [loading, setLoading] = useState(false);
  const [errMsg, setErrMsg] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState(initialSearch);
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const queryParams = useMemo(() => {
    const qp = { page, page_size: 25 };
    if (debouncedSearch?.trim()) qp.search = debouncedSearch.trim();
    if (type) qp.type = type;
    if (tag?.trim()) qp.tag = [tag.trim()];
    return qp;
  }, [debouncedSearch, type, tag, page]);

  // Sync URL
  useEffect(() => {
    const next = {};
    if (search?.trim()) next.search = search.trim();
    if (type) next.type = type;
    if (tag?.trim()) next.tag = tag.trim();
    if (page > 1) next.page = String(page);
    setSearchParams(next, { replace: true });
  }, [search, type, tag, page]);

  async function refresh() {
    setLoading(true); setErrMsg("");
    try {
      const res = await listCustomers(queryParams);
      setData(res);
    } catch (e) { setErrMsg(e.message || "Liste yüklenemedi."); }
    finally { setLoading(false); }
  }

  useEffect(() => { refresh(); }, [queryParams]);

  const pageSize = data.page_size || 25;
  const hasPrev = page > 1;
  const hasNext = data.total > page * pageSize;

  // DataTable columns
  const columns = useMemo(() => [
    {
      accessorKey: "name",
      header: "Adı",
      cell: ({ row }) => {
        const c = row.original;
        const primaryContacts = (c.contacts || []).filter((x) => x?.is_primary);
        return (
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
              {c.type === "corporate" ? <Building2 className="h-4 w-4 text-primary" /> : <User className="h-4 w-4 text-primary" />}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground truncate">{c.name}</p>
              <div className="flex items-center gap-3 mt-0.5">
                {primaryContacts.length ? primaryContacts.map((x, idx) => (
                  <span key={idx} className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    {x.type === "email" ? <Mail className="h-3 w-3" /> : <Phone className="h-3 w-3" />}{x.value}
                  </span>
                )) : <span className="text-xs text-muted-foreground/50">Birincil iletişim yok</span>}
              </div>
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: "type",
      header: "Tip",
      cell: ({ row }) => (
        <StatusBadge
          status={row.original.type === "corporate" ? "active" : "processing"}
          label={row.original.type === "corporate" ? "Kurumsal" : "Bireysel"}
          color={row.original.type === "corporate" ? "info" : "success"}
        />
      ),
    },
    {
      id: "tags",
      header: "Etiketler",
      cell: ({ row }) => {
        const tags = row.original.tags || [];
        if (tags.length === 0) return <span className="text-xs text-muted-foreground/40">—</span>;
        const shown = tags.slice(0, 3);
        const remaining = tags.length - shown.length;
        return (
          <div className="flex flex-wrap gap-1">
            {shown.map((t) => (
              <span key={t} className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700 border border-violet-200 dark:bg-violet-950/30 dark:text-violet-300">{t}</span>
            ))}
            {remaining > 0 && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground border border-border/50">+{remaining}</span>}
          </div>
        );
      },
      enableSorting: false,
    },
    {
      accessorKey: "updated_at",
      header: "Son Güncelleme",
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatRelativeTime(row.original.updated_at)}</span>,
    },
  ], []);

  return (
    <PageShell
      title="Müşteriler"
      description="Müşterileri arayın, etiketleyin ve detayına inin."
      actions={
        <Button onClick={() => setCreateOpen(true)} className="gap-2" data-testid="crm-new-customer">
          <Plus className="h-4 w-4" />Yeni Müşteri
        </Button>
      }
    >
      {/* Filters */}
      <FilterBar
        search={{ placeholder: "Ara: isim / e-posta / telefon", value: search, onChange: (v) => { setPage(1); setSearch(v); } }}
        filters={[
          {
            key: "type", label: "Tip", value: type,
            onChange: (v) => { setPage(1); setType(v); },
            options: [{ value: "individual", label: "Bireysel" }, { value: "corporate", label: "Kurumsal" }],
          },
        ]}
        onReset={() => { setSearch(""); setType(""); setTag(""); setPage(1); }}
        actions={
          <span className="text-xs text-muted-foreground">Toplam: <span className="font-semibold text-foreground">{data.total}</span></span>
        }
      />

      {/* Error */}
      {errMsg && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{errMsg}</div>}

      {/* DataTable */}
      <DataTable
        data={data.items || []}
        columns={columns}
        loading={loading}
        pageSize={100}
        onRowClick={(row) => navigate(`/app/crm/customers/${row.id}`)}
        emptyState={
          <div className="flex flex-col items-center gap-3 py-8">
            <div className="h-14 w-14 rounded-full bg-muted/50 flex items-center justify-center"><Users className="h-6 w-6 text-muted-foreground/50" /></div>
            <p className="text-sm font-semibold text-foreground">Henüz müşteri yok</p>
            <p className="text-xs text-muted-foreground">İlk müşterinizi oluşturmak için butonu kullanın.</p>
            <Button onClick={() => setCreateOpen(true)} className="gap-2" data-testid="crm-empty-create">
              <Plus className="h-4 w-4" />Yeni Müşteri Oluştur
            </Button>
          </div>
        }
      />

      {/* Server-side Pagination */}
      {data.total > 0 && (
        <div className="flex items-center justify-between px-2" data-testid="crm-pagination">
          <Button variant="outline" size="sm" disabled={!hasPrev || loading} onClick={() => setPage((p) => Math.max(1, p - 1))} className="gap-1.5 text-xs" data-testid="crm-prev-page">
            <ChevronLeft className="h-4 w-4" />Önceki
          </Button>
          <span className="text-sm text-muted-foreground">Sayfa <span className="font-semibold text-foreground">{page}</span></span>
          <Button variant="outline" size="sm" disabled={!hasNext || loading} onClick={() => setPage((p) => p + 1)} className="gap-1.5 text-xs" data-testid="crm-next-page">
            Sonraki<ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      <CreateCustomerDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(created) => { refresh(); navigate(`/app/crm/customers/${created.id}`); }}
      />
    </PageShell>
  );
}
