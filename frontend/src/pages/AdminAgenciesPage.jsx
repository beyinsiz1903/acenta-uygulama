import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Building2, Loader2, Plus, Settings2, Users, X } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { formatDateTime, safeName } from "../utils/formatters";
import { formatContractWindow, formatSeatUsage, getContractStatusMeta, getPaymentStatusMeta } from "../lib/agencyContract";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { toast } from "sonner";
import { PageShell, DataTable, SortableHeader, FilterBar, StatusBadge } from "../design-system";

const emptyAgencyForm = {
  name: "", parent_agency_id: "", contract_start_date: "", contract_end_date: "",
  payment_status: "paid", package_type: "", user_limit: "", status: "active",
};

function normalizeAgencyPayload(form) {
  return {
    name: form.name.trim(),
    parent_agency_id: form.parent_agency_id.trim() || null,
    contract_start_date: form.contract_start_date || null,
    contract_end_date: form.contract_end_date || null,
    payment_status: form.payment_status || null,
    package_type: form.package_type.trim() || null,
    user_limit: form.user_limit ? Number(form.user_limit) : null,
    status: form.status || "active",
  };
}

function AgencyContractBadge({ summary, testId }) {
  const meta = getContractStatusMeta(summary?.contract_status);
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${meta.className}`} data-testid={testId}>{meta.label}</span>
  );
}

function AgencyMiniSummary({ agency, prefix }) {
  const summary = agency?.contract_summary;
  const paymentMeta = getPaymentStatusMeta(summary?.payment_status);
  const testBase = `${prefix}-summary`;
  return (
    <div className="grid gap-2 rounded-2xl border bg-muted/20 p-4" data-testid={`${testBase}-card`}>
      <div className="flex flex-wrap items-center gap-2">
        <AgencyContractBadge summary={summary} testId={`${testBase}-contract-status`} />
        <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${paymentMeta.className}`} data-testid={`${testBase}-payment-status`}>{paymentMeta.label}</span>
      </div>
      <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
        <div className="flex items-center gap-2 rounded-xl bg-background px-3 py-2" data-testid={`${testBase}-contract-window`}><span>{formatContractWindow(summary)}</span></div>
        <div className="flex items-center gap-2 rounded-xl bg-background px-3 py-2" data-testid={`${testBase}-package-type`}><span>{summary?.package_type || "Paket tanımlanmadı"}</span></div>
        <div className="flex items-center gap-2 rounded-xl bg-background px-3 py-2" data-testid={`${testBase}-seat-usage`}><span>{formatSeatUsage(summary)}</span></div>
      </div>
      {summary?.warning_message && <p className="text-xs font-medium text-amber-700" data-testid={`${testBase}-warning-message`}>{summary.warning_message}</p>}
      {summary?.lock_message && <p className="text-xs font-medium text-rose-700" data-testid={`${testBase}-lock-message`}>{summary.lock_message}</p>}
    </div>
  );
}

/* ───────── Create Agency Form ───────── */
function CreateAgencyForm({ onCreated, onCancel }) {
  const [formData, setFormData] = useState(emptyAgencyForm);
  const [formError, setFormError] = useState("");
  const [createLoading, setCreateLoading] = useState(false);

  async function handleCreate(e) {
    e.preventDefault();
    setFormError("");
    if (!formData.name.trim()) { setFormError("Acenta adı boş olamaz"); return; }
    setCreateLoading(true);
    try {
      await api.post("/admin/agencies", normalizeAgencyPayload(formData));
      toast.success("Acenta oluşturuldu.");
      setFormData(emptyAgencyForm);
      onCreated?.();
    } catch (err) { setFormError(apiErrorMessage(err)); }
    finally { setCreateLoading(false); }
  }

  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm" data-testid="admin-agencies-create-form-card">
      <div className="mb-5 flex items-center gap-2">
        <Building2 className="h-5 w-5 text-primary" />
        <div>
          <h2 className="text-lg font-semibold text-foreground">Yeni Acenta Oluştur</h2>
          <p className="text-sm text-muted-foreground">Önce acentayı oluşturun, sonra kullanıcıyı bağlayın.</p>
        </div>
      </div>
      <form onSubmit={handleCreate} className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="agency-name">Acenta Adı *</Label>
            <Input id="agency-name" data-testid="agency-create-name" value={formData.name} onChange={(e) => setFormData((p) => ({ ...p, name: e.target.value }))} placeholder="Örn: X Turizm" disabled={createLoading} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="agency-parent">Üst Acenta ID</Label>
            <Input id="agency-parent" data-testid="agency-create-parent" value={formData.parent_agency_id} onChange={(e) => setFormData((p) => ({ ...p, parent_agency_id: e.target.value }))} placeholder="Opsiyonel" disabled={createLoading} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="agency-start-date">Başlangıç Tarihi</Label>
            <Input id="agency-start-date" type="date" data-testid="agency-create-start-date" value={formData.contract_start_date} onChange={(e) => setFormData((p) => ({ ...p, contract_start_date: e.target.value }))} disabled={createLoading} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="agency-end-date">Bitiş Tarihi</Label>
            <Input id="agency-end-date" type="date" data-testid="agency-create-end-date" value={formData.contract_end_date} onChange={(e) => setFormData((p) => ({ ...p, contract_end_date: e.target.value }))} disabled={createLoading} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="agency-payment-status">Ödeme Durumu</Label>
            <select id="agency-payment-status" data-testid="agency-create-payment-status" className="h-9 w-full rounded-md border bg-background px-3 text-sm" value={formData.payment_status} onChange={(e) => setFormData((p) => ({ ...p, payment_status: e.target.value }))} disabled={createLoading}>
              <option value="paid">Ödendi</option><option value="pending">Bekliyor</option><option value="overdue">Gecikmiş</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="agency-package-type">Paket Tipi</Label>
            <Input id="agency-package-type" data-testid="agency-create-package-type" value={formData.package_type} onChange={(e) => setFormData((p) => ({ ...p, package_type: e.target.value }))} placeholder="Örn: Yıllık Pro" disabled={createLoading} />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="agency-user-limit">Kullanıcı Limiti</Label>
            <Input id="agency-user-limit" type="number" min="1" data-testid="agency-create-user-limit" value={formData.user_limit} onChange={(e) => setFormData((p) => ({ ...p, user_limit: e.target.value }))} placeholder="Boş bırakılırsa sınırsız" disabled={createLoading} />
          </div>
        </div>
        {formError && <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive" data-testid="agency-create-error">{formError}</div>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" data-testid="agency-create-cancel" onClick={onCancel} disabled={createLoading}>Vazgeç</Button>
          <Button type="submit" data-testid="agency-create-submit" disabled={createLoading} className="gap-2">
            {createLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            {createLoading ? "Kaydediliyor..." : "Acentayı Oluştur"}
          </Button>
        </div>
      </form>
    </div>
  );
}

/* ═══════════════════════ MAIN PAGE ═══════════════════════ */
export default function AdminAgenciesPage() {
  const navigate = useNavigate();
  const [agencies, setAgencies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [searchQ, setSearchQ] = useState("");

  // Edit dialog state
  const [editOpen, setEditOpen] = useState(false);
  const [editingAgency, setEditingAgency] = useState(null);
  const [editForm, setEditForm] = useState(emptyAgencyForm);
  const [editError, setEditError] = useState("");
  const [editLoading, setEditLoading] = useState(false);

  async function loadAgencies() {
    setLoading(true); setError("");
    try {
      const resp = await api.get("/admin/agencies/");
      const sorted = (resp.data || []).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setAgencies(sorted);
    } catch (err) { setError(apiErrorMessage(err)); }
    finally { setLoading(false); }
  }

  useEffect(() => { loadAgencies(); }, []);

  const metrics = useMemo(() => ({
    total: agencies.length,
    expiringSoon: agencies.filter((a) => a.contract_summary?.contract_status === "expiring_soon").length,
    expired: agencies.filter((a) => a.contract_summary?.contract_status === "expired").length,
    seatsLimited: agencies.filter((a) => a.contract_summary?.user_limit != null).length,
  }), [agencies]);

  // Filter agencies by search
  const filteredAgencies = useMemo(() => {
    if (!searchQ) return agencies;
    const lower = searchQ.toLowerCase();
    return agencies.filter((a) => (a.name || "").toLowerCase().includes(lower) || (a.id || "").toLowerCase().includes(lower));
  }, [agencies, searchQ]);

  function openEditDialog(agency) {
    setEditingAgency(agency);
    setEditForm({
      name: agency.name || "", parent_agency_id: agency.parent_agency_id || "",
      contract_start_date: agency.contract_start_date || "", contract_end_date: agency.contract_end_date || "",
      payment_status: agency.payment_status || "", package_type: agency.package_type || "",
      user_limit: agency.user_limit != null ? String(agency.user_limit) : "", status: agency.status || "active",
    });
    setEditError(""); setEditOpen(true);
  }

  async function handleEditSave() {
    if (!editingAgency) return;
    setEditError(""); setEditLoading(true);
    try {
      await api.put(`/admin/agencies/${editingAgency.id}`, normalizeAgencyPayload(editForm));
      toast.success("Acenta sözleşmesi güncellendi");
      await loadAgencies();
      setEditOpen(false);
    } catch (err) { setEditError(apiErrorMessage(err)); }
    finally { setEditLoading(false); }
  }

  // DataTable columns
  const columns = useMemo(() => [
    {
      accessorKey: "name",
      header: ({ column }) => <SortableHeader column={column}>Acenta</SortableHeader>,
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="font-medium text-foreground" data-testid={`agency-name-${row.original.id}`}>{safeName(row.original.name)}</div>
          <div className="text-xs text-muted-foreground" data-testid={`agency-id-${row.original.id}`}>{row.original.id}</div>
        </div>
      ),
    },
    {
      id: "contract",
      header: "Paket & Süre",
      cell: ({ row }) => {
        const paymentMeta = getPaymentStatusMeta(row.original.contract_summary?.payment_status);
        return (
          <div className="space-y-2 text-xs text-muted-foreground">
            <div className="flex flex-wrap items-center gap-2">
              <AgencyContractBadge summary={row.original.contract_summary} testId={`agency-contract-status-${row.original.id}`} />
              <span className={`inline-flex items-center rounded-full border px-2 py-1 font-semibold ${paymentMeta.className}`} data-testid={`agency-payment-status-${row.original.id}`}>{paymentMeta.label}</span>
            </div>
            <div data-testid={`agency-contract-window-${row.original.id}`}>{formatContractWindow(row.original.contract_summary)}</div>
            <div data-testid={`agency-package-type-${row.original.id}`}>{row.original.contract_summary?.package_type || "Paket tanımlanmadı"}</div>
          </div>
        );
      },
      enableSorting: false,
    },
    {
      id: "users",
      header: "Kullanıcı",
      cell: ({ row }) => (
        <div className="space-y-1 text-xs text-muted-foreground">
          <div data-testid={`agency-seat-usage-${row.original.id}`}>{formatSeatUsage(row.original.contract_summary)}</div>
          <div data-testid={`agency-seat-remaining-${row.original.id}`}>{row.original.remaining_user_slots == null ? "Sınırsız" : `${row.original.remaining_user_slots} boş koltuk`}</div>
        </div>
      ),
      enableSorting: false,
    },
    {
      id: "status",
      header: "Durum",
      cell: ({ row }) => {
        const activeBadge = (row.original.status || "active") === "active";
        return (
          <div className="space-y-2">
            <StatusBadge status={activeBadge ? "active" : "inactive"} />
            {row.original.contract_summary?.warning_message && (
              <p className="max-w-[260px] text-xs font-medium text-amber-700" data-testid={`agency-warning-message-${row.original.id}`}>{row.original.contract_summary.warning_message}</p>
            )}
            {row.original.contract_summary?.lock_message && (
              <p className="max-w-[260px] text-xs font-medium text-rose-700" data-testid={`agency-lock-message-${row.original.id}`}>{row.original.contract_summary.lock_message}</p>
            )}
          </div>
        );
      },
      enableSorting: false,
    },
    {
      accessorKey: "created_at",
      header: ({ column }) => <SortableHeader column={column}>Oluşturma</SortableHeader>,
      cell: ({ row }) => <span className="text-sm text-muted-foreground" data-testid={`agency-created-at-${row.original.id}`}>{formatDateTime(row.original.created_at)}</span>,
    },
    {
      id: "actions",
      header: () => <span className="sr-only">İşlem</span>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" size="sm" className="gap-1.5 h-7 text-xs" data-testid={`agency-users-${row.original.id}`} onClick={(e) => { e.stopPropagation(); navigate(`/app/admin/agencies/${row.original.id}/users`); }}>
            <Users className="h-3 w-3" />Kullanıcılar
          </Button>
          <Button type="button" size="sm" className="gap-1.5 h-7 text-xs" data-testid={`agency-edit-${row.original.id}`} onClick={(e) => { e.stopPropagation(); openEditDialog(row.original); }}>
            <Settings2 className="h-3 w-3" />Düzenle
          </Button>
        </div>
      ),
      enableSorting: false,
    },
  ], [navigate]);

  return (
    <PageShell
      title="Acentalar"
      description="Yeni acenta açın, sözleşme süresini tanımlayın ve ardından kullanıcı oluşturun."
      loading={loading && agencies.length === 0}
      actions={
        <Button data-testid="admin-agencies-toggle-create" onClick={() => setShowForm((prev) => !prev)} className="gap-2">
          {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showForm ? "Formu Kapat" : "Yeni Acenta"}
        </Button>
      }
    >
      {/* KPI Cards */}
      <div className="grid gap-3 md:grid-cols-4" data-testid="admin-agencies-page">
        {[
          { label: "Toplam Acenta", value: metrics.total, testId: "agency-total-count" },
          { label: "Süresi Dolacak", value: metrics.expiringSoon, testId: "agency-expiring-count" },
          { label: "Kısıtlı", value: metrics.expired, testId: "agency-expired-count" },
          { label: "Limitli Paket", value: metrics.seatsLimited, testId: "agency-seat-limited-count" },
        ].map((item) => (
          <div key={item.testId} className="rounded-xl border bg-card p-4 shadow-sm" data-testid={item.testId}>
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.label}</div>
            <div className="mt-2 text-3xl font-semibold text-foreground">{item.value}</div>
          </div>
        ))}
      </div>

      {/* Create Form */}
      {showForm && (
        <CreateAgencyForm
          onCreated={() => { setShowForm(false); loadAgencies(); }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Error State */}
      {error && (
        <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-destructive/50 bg-destructive/5 p-8" data-testid="admin-agencies-error-state">
          <div className="text-center">
            <p className="font-semibold text-foreground">Acentalar yüklenemedi</p>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
          </div>
          <Button data-testid="admin-agencies-retry" onClick={loadAgencies}>Tekrar dene</Button>
        </div>
      )}

      {/* Search + DataTable */}
      {!error && (
        <div className="space-y-3">
          <FilterBar
            search={{ placeholder: "Acenta ara...", value: searchQ, onChange: setSearchQ }}
            onReset={() => setSearchQ("")}
          />
          <DataTable
            data={filteredAgencies}
            columns={columns}
            loading={loading}
            pageSize={20}
            emptyState={
              <div className="flex flex-col items-center gap-3 py-8">
                <div className="grid h-14 w-14 place-items-center rounded-full bg-muted"><Building2 className="h-7 w-7 text-muted-foreground" /></div>
                <p className="text-sm font-medium text-muted-foreground">Henüz acenta yok</p>
                <p className="text-xs text-muted-foreground/70">İlk acentayı oluşturup sözleşme süresini tanımlayabilirsiniz.</p>
              </div>
            }
          />
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-3xl" data-testid="agency-edit-dialog">
          <DialogHeader>
            <DialogTitle>Acenta Sözleşmesini Düzenle</DialogTitle>
            <DialogDescription>1 ay kala uyarı gösterilir; süre geçerse agency kullanıcıları kısıtlama mesajı görür.</DialogDescription>
          </DialogHeader>
          {editingAgency && (
            <div className="space-y-5">
              <AgencyMiniSummary agency={editingAgency} prefix="agency-edit" />
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="agency-edit-name">Acenta Adı</Label>
                  <Input id="agency-edit-name" data-testid="agency-edit-name" value={editForm.name} onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))} disabled={editLoading} />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="agency-edit-parent">Üst Acenta ID</Label>
                  <Input id="agency-edit-parent" data-testid="agency-edit-parent" value={editForm.parent_agency_id} onChange={(e) => setEditForm((p) => ({ ...p, parent_agency_id: e.target.value }))} placeholder="Boş bırakılırsa ana acenta" disabled={editLoading} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-start-date">Başlangıç Tarihi</Label>
                  <Input id="agency-edit-start-date" type="date" data-testid="agency-edit-start-date" value={editForm.contract_start_date} onChange={(e) => setEditForm((p) => ({ ...p, contract_start_date: e.target.value }))} disabled={editLoading} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-end-date">Bitiş Tarihi</Label>
                  <Input id="agency-edit-end-date" type="date" data-testid="agency-edit-end-date" value={editForm.contract_end_date} onChange={(e) => setEditForm((p) => ({ ...p, contract_end_date: e.target.value }))} disabled={editLoading} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-payment-status">Ödeme Durumu</Label>
                  <select id="agency-edit-payment-status" data-testid="agency-edit-payment-status" className="h-9 w-full rounded-md border bg-background px-3 text-sm" value={editForm.payment_status} onChange={(e) => setEditForm((p) => ({ ...p, payment_status: e.target.value }))} disabled={editLoading}>
                    <option value="">Tanımsız</option><option value="paid">Ödendi</option><option value="pending">Bekliyor</option><option value="overdue">Gecikmiş</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-package-type">Paket Tipi</Label>
                  <Input id="agency-edit-package-type" data-testid="agency-edit-package-type" value={editForm.package_type} onChange={(e) => setEditForm((p) => ({ ...p, package_type: e.target.value }))} placeholder="Örn: Yıllık Pro" disabled={editLoading} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-user-limit">Kullanıcı Limiti</Label>
                  <Input id="agency-edit-user-limit" type="number" min="1" data-testid="agency-edit-user-limit" value={editForm.user_limit} onChange={(e) => setEditForm((p) => ({ ...p, user_limit: e.target.value }))} placeholder="Boş bırakılırsa sınırsız" disabled={editLoading} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-status">Durum</Label>
                  <select id="agency-edit-status" data-testid="agency-edit-status" className="h-9 w-full rounded-md border bg-background px-3 text-sm" value={editForm.status} onChange={(e) => setEditForm((p) => ({ ...p, status: e.target.value }))} disabled={editLoading}>
                    <option value="active">Aktif</option><option value="disabled">Pasif</option>
                  </select>
                </div>
              </div>
              {editError && <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive" data-testid="agency-edit-error">{editError}</div>}
              <div className="flex justify-between gap-2">
                <Button type="button" variant="outline" data-testid="agency-edit-users-shortcut" onClick={() => navigate(`/app/admin/agencies/${editingAgency.id}/users`)} disabled={editLoading}>Kullanıcıları Aç</Button>
                <div className="flex gap-2">
                  <Button type="button" variant="outline" data-testid="agency-edit-cancel" onClick={() => setEditOpen(false)} disabled={editLoading}>İptal</Button>
                  <Button type="button" data-testid="agency-edit-save" onClick={handleEditSave} disabled={editLoading} className="gap-2">
                    {editLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Settings2 className="h-4 w-4" />}
                    {editLoading ? "Kaydediliyor..." : "Kaydet"}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </PageShell>
  );
}
