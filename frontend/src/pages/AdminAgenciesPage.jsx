import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  Building2,
  CalendarRange,
  CreditCard,
  Loader2,
  Plus,
  Settings2,
  Users,
  X,
} from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { formatDateTime, safeName } from "../utils/formatters";
import {
  formatContractWindow,
  formatSeatUsage,
  getContractStatusMeta,
  getPaymentStatusMeta,
} from "../lib/agencyContract";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { toast } from "sonner";

const emptyAgencyForm = {
  name: "",
  parent_agency_id: "",
  contract_start_date: "",
  contract_end_date: "",
  payment_status: "paid",
  package_type: "",
  user_limit: "",
  status: "active",
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
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${meta.className}`}
      data-testid={testId}
    >
      {meta.label}
    </span>
  );
}

function AgencyMiniSummary({ agency, prefix }) {
  const summary = agency?.contract_summary;
  const paymentMeta = getPaymentStatusMeta(summary?.payment_status);

  return (
    <div className="grid gap-2 rounded-2xl border bg-muted/20 p-4" data-testid={`${prefix}-contract-summary`}>
      <div className="flex flex-wrap items-center gap-2">
        <AgencyContractBadge summary={summary} testId={`${prefix}-contract-status`} />
        <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${paymentMeta.className}`} data-testid={`${prefix}-payment-status`}>
          {paymentMeta.label}
        </span>
      </div>
      <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
        <div className="flex items-center gap-2 rounded-xl bg-background px-3 py-2" data-testid={`${prefix}-contract-window`}>
          <CalendarRange className="h-3.5 w-3.5 text-muted-foreground" />
          <span>{formatContractWindow(summary)}</span>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-background px-3 py-2" data-testid={`${prefix}-package-type`}>
          <CreditCard className="h-3.5 w-3.5 text-muted-foreground" />
          <span>{summary?.package_type || "Paket tanımlanmadı"}</span>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-background px-3 py-2" data-testid={`${prefix}-seat-usage`}>
          <Users className="h-3.5 w-3.5 text-muted-foreground" />
          <span>{formatSeatUsage(summary)}</span>
        </div>
      </div>
      {summary?.warning_message ? (
        <p className="text-xs font-medium text-amber-700" data-testid={`${prefix}-warning-message`}>
          {summary.warning_message}
        </p>
      ) : null}
      {summary?.lock_message ? (
        <p className="text-xs font-medium text-rose-700" data-testid={`${prefix}-lock-message`}>
          {summary.lock_message}
        </p>
      ) : null}
    </div>
  );
}

export default function AdminAgenciesPage() {
  const navigate = useNavigate();
  const [agencies, setAgencies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [formData, setFormData] = useState(emptyAgencyForm);
  const [formError, setFormError] = useState("");

  const [editOpen, setEditOpen] = useState(false);
  const [editingAgency, setEditingAgency] = useState(null);
  const [editForm, setEditForm] = useState(emptyAgencyForm);
  const [editError, setEditError] = useState("");
  const [editLoading, setEditLoading] = useState(false);

  useEffect(() => {
    loadAgencies();
  }, []);

  const metrics = useMemo(() => {
    return {
      total: agencies.length,
      expiringSoon: agencies.filter((agency) => agency.contract_summary?.contract_status === "expiring_soon").length,
      expired: agencies.filter((agency) => agency.contract_summary?.contract_status === "expired").length,
      seatsLimited: agencies.filter((agency) => agency.contract_summary?.user_limit != null).length,
    };
  }, [agencies]);

  async function loadAgencies() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/admin/agencies/");
      const sorted = (resp.data || []).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setAgencies(sorted);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setFormError("");

    const name = formData.name.trim();
    if (!name) {
      setFormError("Acenta adı boş olamaz");
      return;
    }

    setCreateLoading(true);
    try {
      await api.post("/admin/agencies", normalizeAgencyPayload(formData));
      toast.success("Acenta oluşturuldu. Şimdi kullanıcı yönetiminden ilk kullanıcıyı ekleyebilirsiniz.");
      setFormData(emptyAgencyForm);
      setShowForm(false);
      await loadAgencies();
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setCreateLoading(false);
    }
  }

  function openEditDialog(agency) {
    setEditingAgency(agency);
    setEditForm({
      name: agency.name || "",
      parent_agency_id: agency.parent_agency_id || "",
      contract_start_date: agency.contract_start_date || "",
      contract_end_date: agency.contract_end_date || "",
      payment_status: agency.payment_status || "",
      package_type: agency.package_type || "",
      user_limit: agency.user_limit != null ? String(agency.user_limit) : "",
      status: agency.status || "active",
    });
    setEditError("");
    setEditOpen(true);
  }

  async function handleEditSave() {
    if (!editingAgency) return;
    setEditError("");
    setEditLoading(true);
    try {
      await api.put(`/admin/agencies/${editingAgency.id}`, normalizeAgencyPayload(editForm));
      toast.success("Acenta sözleşmesi güncellendi");
      await loadAgencies();
      setEditOpen(false);
    } catch (err) {
      setEditError(apiErrorMessage(err));
    } finally {
      setEditLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6" data-testid="admin-agencies-page">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Acentalar</h1>
          <p className="mt-1 text-sm text-muted-foreground">Acenta ve sözleşme yönetimi yükleniyor...</p>
        </div>

        <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border bg-card p-12 shadow-sm" data-testid="admin-agencies-loading">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Acentalar yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6" data-testid="admin-agencies-page">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Acentalar</h1>
          <p className="mt-1 text-sm text-muted-foreground">Acenta ve sözleşme yönetimi</p>
        </div>

        <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-destructive/50 bg-destructive/5 p-8" data-testid="admin-agencies-error-state">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Acentalar yüklenemedi</p>
            <p className="mt-1 text-sm text-muted-foreground">{error}</p>
          </div>
          <Button data-testid="admin-agencies-retry" onClick={loadAgencies}>Tekrar dene</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-agencies-page">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Acentalar</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Yeni acenta açın, sözleşme süresini tanımlayın ve ardından kullanıcı oluşturun.
          </p>
        </div>
        <Button data-testid="admin-agencies-toggle-create" onClick={() => setShowForm((prev) => !prev)} className="gap-2">
          {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showForm ? "Formu Kapat" : "Yeni Acenta"}
        </Button>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        {[
          { label: "Toplam Acenta", value: metrics.total, testId: "agency-total-count" },
          { label: "Süresi Dolacak", value: metrics.expiringSoon, testId: "agency-expiring-count" },
          { label: "Kısıtlı", value: metrics.expired, testId: "agency-expired-count" },
          { label: "Lİmitli Paket", value: metrics.seatsLimited, testId: "agency-seat-limited-count" },
        ].map((item) => (
          <div key={item.testId} className="rounded-2xl border bg-card p-4 shadow-sm" data-testid={item.testId}>
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{item.label}</div>
            <div className="mt-2 text-3xl font-semibold text-foreground">{item.value}</div>
          </div>
        ))}
      </div>

      {showForm ? (
        <div className="rounded-[1.75rem] border bg-card p-6 shadow-sm" data-testid="admin-agencies-create-form-card">
          <div className="mb-5 flex items-center gap-2">
            <Building2 className="h-5 w-5 text-primary" />
            <div>
              <h2 className="text-lg font-semibold text-foreground">Yeni Acenta Oluştur</h2>
              <p className="text-sm text-muted-foreground">Önce acentayı oluşturun, sonra kullanıcıyı bu acenteye bağlayın.</p>
            </div>
          </div>

          <form onSubmit={handleCreate} className="space-y-5">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="agency-name">Acenta Adı *</Label>
                <Input
                  id="agency-name"
                  data-testid="agency-create-name"
                  value={formData.name}
                  onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="Örn: X Turizm"
                  disabled={createLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="agency-parent">Üst Acenta ID</Label>
                <Input
                  id="agency-parent"
                  data-testid="agency-create-parent"
                  value={formData.parent_agency_id}
                  onChange={(e) => setFormData((prev) => ({ ...prev, parent_agency_id: e.target.value }))}
                  placeholder="Opsiyonel"
                  disabled={createLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="agency-start-date">Başlangıç Tarihi</Label>
                <Input
                  id="agency-start-date"
                  type="date"
                  data-testid="agency-create-start-date"
                  value={formData.contract_start_date}
                  onChange={(e) => setFormData((prev) => ({ ...prev, contract_start_date: e.target.value }))}
                  disabled={createLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="agency-end-date">Bitiş Tarihi</Label>
                <Input
                  id="agency-end-date"
                  type="date"
                  data-testid="agency-create-end-date"
                  value={formData.contract_end_date}
                  onChange={(e) => setFormData((prev) => ({ ...prev, contract_end_date: e.target.value }))}
                  disabled={createLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="agency-payment-status">Ödeme Durumu</Label>
                <select
                  id="agency-payment-status"
                  data-testid="agency-create-payment-status"
                  className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                  value={formData.payment_status}
                  onChange={(e) => setFormData((prev) => ({ ...prev, payment_status: e.target.value }))}
                  disabled={createLoading}
                >
                  <option value="paid">Ödendi</option>
                  <option value="pending">Bekliyor</option>
                  <option value="overdue">Gecikmiş</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="agency-package-type">Paket Tipi</Label>
                <Input
                  id="agency-package-type"
                  data-testid="agency-create-package-type"
                  value={formData.package_type}
                  onChange={(e) => setFormData((prev) => ({ ...prev, package_type: e.target.value }))}
                  placeholder="Örn: Yıllık Pro"
                  disabled={createLoading}
                />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="agency-user-limit">Kullanıcı Limiti</Label>
                <Input
                  id="agency-user-limit"
                  type="number"
                  min="1"
                  data-testid="agency-create-user-limit"
                  value={formData.user_limit}
                  onChange={(e) => setFormData((prev) => ({ ...prev, user_limit: e.target.value }))}
                  placeholder="Boş bırakılırsa sınırsız"
                  disabled={createLoading}
                />
              </div>
            </div>

            {formError ? (
              <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive" data-testid="agency-create-error">
                {formError}
              </div>
            ) : null}

            <div className="flex flex-wrap justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                data-testid="agency-create-cancel"
                onClick={() => {
                  setShowForm(false);
                  setFormData(emptyAgencyForm);
                  setFormError("");
                }}
                disabled={createLoading}
              >
                Vazgeç
              </Button>
              <Button type="submit" data-testid="agency-create-submit" disabled={createLoading} className="gap-2">
                {createLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                {createLoading ? "Kaydediliyor..." : "Acentayı Oluştur"}
              </Button>
            </div>
          </form>
        </div>
      ) : null}

      {agencies.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border bg-card p-12 shadow-sm" data-testid="admin-agencies-empty-state">
          <div className="grid h-16 w-16 place-items-center rounded-full bg-muted">
            <Building2 className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="max-w-md text-center">
            <p className="font-semibold text-foreground">Henüz acenta yok</p>
            <p className="mt-2 text-sm text-muted-foreground">İlk acentayı oluşturup sözleşme süresini tanımlayabilirsiniz.</p>
          </div>
        </div>
      ) : (
        <div className="overflow-hidden rounded-[1.75rem] border bg-card shadow-sm" data-testid="admin-agencies-table-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="font-semibold">Acenta</TableHead>
                <TableHead className="font-semibold">Paket & Süre</TableHead>
                <TableHead className="font-semibold">Kullanıcı</TableHead>
                <TableHead className="font-semibold">Durum</TableHead>
                <TableHead className="font-semibold">Oluşturma</TableHead>
                <TableHead className="font-semibold text-right">İşlem</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {agencies.map((agency) => {
                const paymentMeta = getPaymentStatusMeta(agency.contract_summary?.payment_status);
                const activeBadge = (agency.status || "active") === "active";
                return (
                  <TableRow key={agency.id} data-testid={`agency-row-${agency.id}`}>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="font-medium text-foreground" data-testid={`agency-name-${agency.id}`}>{safeName(agency.name)}</div>
                        <div className="text-xs text-muted-foreground" data-testid={`agency-id-${agency.id}`}>{agency.id}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-2 text-xs text-muted-foreground">
                        <div className="flex flex-wrap items-center gap-2">
                          <AgencyContractBadge summary={agency.contract_summary} testId={`agency-contract-status-${agency.id}`} />
                          <span className={`inline-flex items-center rounded-full border px-2 py-1 font-semibold ${paymentMeta.className}`} data-testid={`agency-payment-status-${agency.id}`}>
                            {paymentMeta.label}
                          </span>
                        </div>
                        <div data-testid={`agency-contract-window-${agency.id}`}>{formatContractWindow(agency.contract_summary)}</div>
                        <div data-testid={`agency-package-type-${agency.id}`}>{agency.contract_summary?.package_type || "Paket tanımlanmadı"}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1 text-xs text-muted-foreground">
                        <div data-testid={`agency-seat-usage-${agency.id}`}>{formatSeatUsage(agency.contract_summary)}</div>
                        <div data-testid={`agency-seat-remaining-${agency.id}`}>
                          {agency.remaining_user_slots == null ? "Sınırsız" : `${agency.remaining_user_slots} boş koltuk`}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-2">
                        <Badge className={activeBadge ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-600"} data-testid={`agency-active-status-${agency.id}`}>
                          {activeBadge ? "Aktif" : "Pasif"}
                        </Badge>
                        {agency.contract_summary?.warning_message ? (
                          <p className="max-w-[260px] text-xs font-medium text-amber-700" data-testid={`agency-warning-message-${agency.id}`}>
                            {agency.contract_summary.warning_message}
                          </p>
                        ) : null}
                        {agency.contract_summary?.lock_message ? (
                          <p className="max-w-[260px] text-xs font-medium text-rose-700" data-testid={`agency-lock-message-${agency.id}`}>
                            {agency.contract_summary.lock_message}
                          </p>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground" data-testid={`agency-created-at-${agency.id}`}>
                      {formatDateTime(agency.created_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="gap-1.5"
                          data-testid={`agency-users-${agency.id}`}
                          onClick={() => navigate(`/app/admin/agencies/${agency.id}/users`)}
                        >
                          <Users className="h-3.5 w-3.5" />
                          Kullanıcılar
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          className="gap-1.5"
                          data-testid={`agency-edit-${agency.id}`}
                          onClick={() => openEditDialog(agency)}
                        >
                          <Settings2 className="h-3.5 w-3.5" />
                          Düzenle
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-3xl" data-testid="agency-edit-dialog">
          <DialogHeader>
            <DialogTitle>Acenta Sözleşmesini Düzenle</DialogTitle>
            <DialogDescription>
              1 ay kala uyarı gösterilir; süre geçerse agency kullanıcıları kısıtlama mesajı görür.
            </DialogDescription>
          </DialogHeader>

          {editingAgency ? (
            <div className="space-y-5">
              <AgencyMiniSummary agency={editingAgency} prefix="agency-edit" />

              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="agency-edit-name">Acenta Adı</Label>
                  <Input
                    id="agency-edit-name"
                    data-testid="agency-edit-name"
                    value={editForm.name}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, name: e.target.value }))}
                    disabled={editLoading}
                  />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="agency-edit-parent">Üst Acenta ID</Label>
                  <Input
                    id="agency-edit-parent"
                    data-testid="agency-edit-parent"
                    value={editForm.parent_agency_id}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, parent_agency_id: e.target.value }))}
                    placeholder="Boş bırakılırsa ana acenta"
                    disabled={editLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-start-date">Başlangıç Tarihi</Label>
                  <Input
                    id="agency-edit-start-date"
                    type="date"
                    data-testid="agency-edit-start-date"
                    value={editForm.contract_start_date}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, contract_start_date: e.target.value }))}
                    disabled={editLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-end-date">Bitiş Tarihi</Label>
                  <Input
                    id="agency-edit-end-date"
                    type="date"
                    data-testid="agency-edit-end-date"
                    value={editForm.contract_end_date}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, contract_end_date: e.target.value }))}
                    disabled={editLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-payment-status">Ödeme Durumu</Label>
                  <select
                    id="agency-edit-payment-status"
                    data-testid="agency-edit-payment-status"
                    className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                    value={editForm.payment_status}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, payment_status: e.target.value }))}
                    disabled={editLoading}
                  >
                    <option value="">Tanımsız</option>
                    <option value="paid">Ödendi</option>
                    <option value="pending">Bekliyor</option>
                    <option value="overdue">Gecikmiş</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-package-type">Paket Tipi</Label>
                  <Input
                    id="agency-edit-package-type"
                    data-testid="agency-edit-package-type"
                    value={editForm.package_type}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, package_type: e.target.value }))}
                    placeholder="Örn: Yıllık Pro"
                    disabled={editLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-user-limit">Kullanıcı Limiti</Label>
                  <Input
                    id="agency-edit-user-limit"
                    type="number"
                    min="1"
                    data-testid="agency-edit-user-limit"
                    value={editForm.user_limit}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, user_limit: e.target.value }))}
                    placeholder="Boş bırakılırsa sınırsız"
                    disabled={editLoading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agency-edit-status">Durum</Label>
                  <select
                    id="agency-edit-status"
                    data-testid="agency-edit-status"
                    className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                    value={editForm.status}
                    onChange={(e) => setEditForm((prev) => ({ ...prev, status: e.target.value }))}
                    disabled={editLoading}
                  >
                    <option value="active">Aktif</option>
                    <option value="disabled">Pasif</option>
                  </select>
                </div>
              </div>

              {editError ? (
                <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive" data-testid="agency-edit-error">
                  {editError}
                </div>
              ) : null}

              <div className="flex flex-wrap justify-between gap-2">
                <Button
                  type="button"
                  variant="outline"
                  data-testid="agency-edit-users-shortcut"
                  onClick={() => navigate(`/app/admin/agencies/${editingAgency.id}/users`)}
                  disabled={editLoading}
                >
                  Kullanıcıları Aç
                </Button>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="outline" data-testid="agency-edit-cancel" onClick={() => setEditOpen(false)} disabled={editLoading}>
                    İptal
                  </Button>
                  <Button type="button" data-testid="agency-edit-save" onClick={handleEditSave} disabled={editLoading} className="gap-2">
                    {editLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Settings2 className="h-4 w-4" />}
                    {editLoading ? "Kaydediliyor..." : "Kaydet"}
                  </Button>
                </div>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}