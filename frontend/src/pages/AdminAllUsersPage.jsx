import React, { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { safeName } from "../utils/formatters";
import {
  UserPlus, ShieldCheck, ShieldOff,
  Pencil, Trash2, Lock, Loader2,
} from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import DemoSeedButton from "../components/DemoSeedButton";
import {
  formatContractWindow,
  formatSeatUsage,
  getContractStatusMeta,
} from "../lib/agencyContract";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../components/ui/dialog";
import {
  AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle,
  AlertDialogDescription, AlertDialogFooter, AlertDialogCancel, AlertDialogAction,
} from "../components/ui/alert-dialog";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import { PageShell, DataTable, SortableHeader, FilterBar, StatusBadge } from "../design-system";
import { useAdminUsers, useAdminAgencies, adminUserKeys } from "../features/governance/hooks";
import { useQueryClient } from "@tanstack/react-query";

/* ── Helper ─────────────────────────────────────────────── */
const agencyRole = (roles) => {
  if (roles?.includes("agency_admin")) return "agency_admin";
  return "agency_agent";
};

/* ── Create User Dialog ─────────────────────────────────── */
function CreateUserDialog({ open, onOpenChange, agencies, onCreated }) {
  const [form, setForm] = useState({ name: "", email: "", password: "", agency_id: "", role: "agency_agent" });
  const [saving, setSaving] = useState(false);
  const selectedAgency = agencies.find((a) => a.id === form.agency_id);
  const reset = () => setForm({ name: "", email: "", password: "", agency_id: "", role: "agency_agent" });

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.email || !form.password || !form.agency_id) { toast.error("Tüm zorunlu alanları doldurun"); return; }
    setSaving(true);
    try {
      await api.post("/admin/all-users", form);
      toast.success("Kullanıcı oluşturuldu");
      reset(); onOpenChange(false); onCreated();
    } catch (err) { toast.error(apiErrorMessage(err)); }
    finally { setSaving(false); }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) reset(); onOpenChange(v); }}>
      <DialogContent className="sm:max-w-md" data-testid="create-user-dialog">
        <DialogHeader><DialogTitle>Yeni Kullanıcı Ekle</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="cu-name">Ad Soyad</Label>
            <Input id="cu-name" data-testid="create-user-name" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} placeholder="Örnek: Ahmet Yılmaz" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="cu-email">E-posta *</Label>
            <Input id="cu-email" type="email" data-testid="create-user-email" required value={form.email} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} placeholder="ornek@acenta.com" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="cu-pass">Şifre *</Label>
            <Input id="cu-pass" type="password" data-testid="create-user-password" required minLength={6} value={form.password} onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))} placeholder="En az 6 karakter" />
          </div>
          <div className="space-y-2">
            <Label htmlFor="cu-agency">Acenta *</Label>
            <select id="cu-agency" data-testid="create-user-agency" required className="w-full h-9 rounded-md border bg-background px-3 text-sm" value={form.agency_id} onChange={(e) => setForm((p) => ({ ...p, agency_id: e.target.value }))}>
              <option value="">Acenta seçin...</option>
              {agencies.map((a) => (
                <option key={a.id} value={a.id}>
                  {safeName(a.name)}{a.contract_summary?.user_limit != null ? ` · ${a.active_user_count || 0}/${a.contract_summary.user_limit}` : ""}
                </option>
              ))}
            </select>
          </div>
          {selectedAgency?.contract_summary && (
            <div className="rounded-xl border bg-muted/20 px-3 py-3 text-xs text-muted-foreground" data-testid="create-user-agency-summary">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`inline-flex items-center rounded-full border px-2 py-1 font-semibold ${getContractStatusMeta(selectedAgency.contract_summary.contract_status).className}`} data-testid="create-user-agency-contract-status">
                  {getContractStatusMeta(selectedAgency.contract_summary.contract_status).label}
                </span>
                <span data-testid="create-user-agency-seat-usage">{formatSeatUsage(selectedAgency.contract_summary)}</span>
              </div>
              <div className="mt-2" data-testid="create-user-agency-contract-window">{formatContractWindow(selectedAgency.contract_summary)}</div>
              {selectedAgency.contract_summary.warning_message && <div className="mt-2 font-medium text-amber-700" data-testid="create-user-agency-warning-message">{selectedAgency.contract_summary.warning_message}</div>}
              {selectedAgency.contract_summary.lock_message && <div className="mt-2 font-medium text-rose-700" data-testid="create-user-agency-lock-message">{selectedAgency.contract_summary.lock_message}</div>}
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="cu-role">Rol</Label>
            <select id="cu-role" data-testid="create-user-role" className="w-full h-9 rounded-md border bg-background px-3 text-sm" value={form.role} onChange={(e) => setForm((p) => ({ ...p, role: e.target.value }))}>
              <option value="agency_admin">Yönetici</option>
              <option value="agency_agent">Satış/Operasyon</option>
            </select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>İptal</Button>
            <Button type="submit" data-testid="create-user-submit" disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <UserPlus className="h-4 w-4 mr-1" />}
              Oluştur
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ── Edit User Dialog ───────────────────────────────────── */
function EditUserDialog({ open, onOpenChange, userToEdit, agencies, onUpdated }) {
  const [form, setForm] = useState({ name: "", email: "", role: "agency_agent", status: "active", agency_id: "" });
  const [saving, setSaving] = useState(false);
  const selectedAgency = agencies.find((a) => a.id === form.agency_id);

  useEffect(() => {
    if (userToEdit) setForm({ name: userToEdit.name || "", email: userToEdit.email || "", role: agencyRole(userToEdit.roles), status: userToEdit.status || "active", agency_id: userToEdit.agency_id || "" });
  }, [userToEdit]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!userToEdit) return;
    setSaving(true);
    try { await api.put(`/admin/all-users/${userToEdit.id}`, form); toast.success("Kullanıcı güncellendi"); onOpenChange(false); onUpdated(); }
    catch (err) { toast.error(apiErrorMessage(err)); }
    finally { setSaving(false); }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" data-testid="edit-user-dialog">
        <DialogHeader><DialogTitle>Kullanıcıyı Düzenle</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>Ad Soyad</Label>
            <Input data-testid="edit-user-name" value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} />
          </div>
          <div className="space-y-2">
            <Label>E-posta</Label>
            <Input type="email" data-testid="edit-user-email" value={form.email} onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} />
          </div>
          <div className="space-y-2">
            <Label>Acenta</Label>
            <select data-testid="edit-user-agency" className="w-full h-9 rounded-md border bg-background px-3 text-sm" value={form.agency_id} onChange={(e) => setForm((p) => ({ ...p, agency_id: e.target.value }))}>
              <option value="">Acenta seçin...</option>
              {agencies.map((a) => <option key={a.id} value={a.id}>{safeName(a.name)}</option>)}
            </select>
          </div>
          {selectedAgency?.contract_summary && (
            <div className="rounded-xl border bg-muted/20 px-3 py-3 text-xs text-muted-foreground" data-testid="edit-user-agency-summary">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`inline-flex items-center rounded-full border px-2 py-1 font-semibold ${getContractStatusMeta(selectedAgency.contract_summary.contract_status).className}`}>{getContractStatusMeta(selectedAgency.contract_summary.contract_status).label}</span>
                <span>{formatSeatUsage(selectedAgency.contract_summary)}</span>
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label>Rol</Label>
              <select data-testid="edit-user-role" className="w-full h-9 rounded-md border bg-background px-3 text-sm" value={form.role} onChange={(e) => setForm((p) => ({ ...p, role: e.target.value }))}>
                <option value="agency_admin">Yönetici</option>
                <option value="agency_agent">Satış/Operasyon</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Durum</Label>
              <select data-testid="edit-user-status" className="w-full h-9 rounded-md border bg-background px-3 text-sm" value={form.status} onChange={(e) => setForm((p) => ({ ...p, status: e.target.value }))}>
                <option value="active">Aktif</option>
                <option value="disabled">Pasif</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>İptal</Button>
            <Button type="submit" data-testid="edit-user-submit" disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Pencil className="h-4 w-4 mr-1" />}
              Kaydet
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ── Delete Confirmation ────────────────────────────────── */
function DeleteUserDialog({ open, onOpenChange, userToDelete, onDeleted }) {
  const [deleting, setDeleting] = useState(false);
  async function handleDelete() {
    if (!userToDelete) return;
    setDeleting(true);
    try { await api.delete(`/admin/all-users/${userToDelete.id}`); toast.success(`${userToDelete.email} silindi`); onOpenChange(false); onDeleted(); }
    catch (err) { toast.error(apiErrorMessage(err)); }
    finally { setDeleting(false); }
  }
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent data-testid="delete-user-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>Kullanıcıyı Sil</AlertDialogTitle>
          <AlertDialogDescription><strong>{userToDelete?.email}</strong> kullanıcısını kalıcı olarak silmek istediğinize emin misiniz?</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>İptal</AlertDialogCancel>
          <AlertDialogAction data-testid="delete-user-confirm" onClick={handleDelete} disabled={deleting} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
            {deleting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Trash2 className="h-4 w-4 mr-1" />}
            Sil
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

/* ── Permissions Dialog ─────────────────────────────────── */
function PermissionsDialog({ open, onOpenChange, userToEdit, onUpdated }) {
  const [screens, setScreens] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selected, setSelected] = useState([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const isAdmin = userToEdit?.roles?.includes("agency_admin");

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const [screensRes, templatesRes, permsRes] = await Promise.all([
          api.get("/admin/permissions/screens"),
          api.get("/admin/permissions/templates"),
          userToEdit ? api.get(`/admin/all-users/${userToEdit.id}/permissions`) : Promise.resolve({ data: { allowed_screens: [] } }),
        ]);
        if (!cancelled) {
          setScreens(screensRes.data || []);
          setTemplates(templatesRes.data || []);
          setSelected(permsRes.data?.allowed_screens || []);
        }
      } catch { if (!cancelled) setScreens([]); }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [open, userToEdit]);

  function toggleScreen(key) { setSelected((prev) => prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]); }
  const activeTemplateKey = templates.find((t) => t.screens.length === selected.length && t.screens.every((s) => selected.includes(s)))?.key || null;

  async function handleSave() {
    if (!userToEdit) return;
    setSaving(true);
    try { await api.put(`/admin/all-users/${userToEdit.id}/permissions`, { allowed_screens: selected }); toast.success("Yetkiler güncellendi"); onOpenChange(false); onUpdated(); }
    catch (err) { toast.error(apiErrorMessage(err)); }
    finally { setSaving(false); }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg" data-testid="permissions-dialog" aria-describedby="permissions-dialog-desc">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Lock className="h-5 w-5 text-primary" /> Ekran Yetkileri</DialogTitle>
          {userToEdit && (
            <p className="text-sm text-muted-foreground mt-1" id="permissions-dialog-desc">
              {userToEdit.name || userToEdit.email}
              {isAdmin && <Badge className="ml-2 bg-emerald-500/10 text-emerald-700 border-emerald-500/20 text-[10px]">Yönetici - Tam Erişim</Badge>}
            </p>
          )}
        </DialogHeader>
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
        ) : isAdmin ? (
          <div className="rounded-xl border bg-emerald-50/50 dark:bg-emerald-950/20 p-4 text-sm text-muted-foreground" data-testid="permissions-admin-notice">
            <ShieldCheck className="h-5 w-5 text-emerald-600 mb-2" />
            <p>Yönetici rolündeki kullanıcılar tüm ekranlara otomatik olarak erişebilir.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {templates.length > 0 && (
              <div className="space-y-1.5" data-testid="permissions-templates">
                <p className="text-xs font-medium text-muted-foreground">Hazır Şablonlar</p>
                <div className="flex flex-wrap gap-1.5">
                  {templates.map((tpl) => (
                    <button key={tpl.key} type="button" data-testid={`template-${tpl.key}`} onClick={() => setSelected([...tpl.screens])} title={tpl.description}
                      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${activeTemplateKey === tpl.key ? "border-primary bg-primary/10 text-primary" : "border-border bg-muted/30 text-muted-foreground hover:bg-muted/60"}`}>
                      {tpl.label}<span className="ml-1 text-[10px] opacity-60">({tpl.screens.length})</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">{selected.length === 0 ? "Hiçbir ekran seçilmedi — tam erişim" : `${selected.length} / ${screens.length} ekran seçili`}</p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setSelected(screens.map((s) => s.key))} data-testid="permissions-select-all">Tümünü Seç</Button>
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => setSelected([])} data-testid="permissions-deselect-all">Temizle</Button>
              </div>
            </div>
            <div className="rounded-xl border bg-muted/20 p-1 space-y-0.5 max-h-[320px] overflow-y-auto">
              {screens.map((screen) => (
                <label key={screen.key} className="flex items-center gap-3 rounded-lg px-3 py-2.5 cursor-pointer transition-colors hover:bg-accent" data-testid={`permission-screen-${screen.key}`}>
                  <input type="checkbox" checked={selected.includes(screen.key)} onChange={() => toggleScreen(screen.key)} className="h-4 w-4 rounded border-border text-primary focus:ring-primary" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground">{screen.label}</div>
                    <div className="text-xs text-muted-foreground">{screen.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>İptal</Button>
          {!isAdmin && <Button onClick={handleSave} disabled={saving || loading} data-testid="permissions-save-btn">{saving ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Lock className="h-4 w-4 mr-1" />}Kaydet</Button>}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ═══════════════════════ MAIN PAGE ═══════════════════════ */

const STATUS_OPTIONS = [
  { value: "active", label: "Aktif" },
  { value: "disabled", label: "Pasif" },
];

export default function AdminAllUsersPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [agencyFilter, setAgencyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [permissionsOpen, setPermissionsOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  const { data: users = [], isLoading: usersLoading, refetch: refetchUsers } = useAdminUsers();
  const { data: agencies = [], isLoading: agenciesLoading } = useAdminAgencies();
  const isLoading = usersLoading || agenciesLoading;

  function reloadAll() {
    queryClient.invalidateQueries({ queryKey: adminUserKeys.all });
  }

  const filtered = useMemo(() => {
    let list = users;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((u) => u.email?.toLowerCase().includes(q) || u.name?.toLowerCase().includes(q) || u.agency_name?.toLowerCase().includes(q));
    }
    if (agencyFilter) list = list.filter((u) => u.agency_id === agencyFilter);
    if (statusFilter) list = list.filter((u) => u.status === statusFilter);
    return list;
  }, [users, search, agencyFilter, statusFilter]);

  async function handleStatusToggle(u) {
    if (!u.agency_id) return;
    const newStatus = u.status === "active" ? "disabled" : "active";
    try { await api.patch(`/admin/agencies/${u.agency_id}/users/${u.id}`, { status: newStatus }); toast.success(`${u.email} durumu güncellendi`); reloadAll(); }
    catch (err) { toast.error(apiErrorMessage(err)); }
  }

  async function handleRoleChange(u, newRole) {
    if (!u.agency_id) return;
    try { await api.patch(`/admin/agencies/${u.agency_id}/users/${u.id}`, { role: newRole }); toast.success(`${u.email} rolü güncellendi`); reloadAll(); }
    catch (err) { toast.error(apiErrorMessage(err)); }
  }

  const agencyFilterOptions = useMemo(() => agencies.map((a) => ({ value: a.id, label: a.name })), [agencies]);

  // KPI summaries
  const kpis = useMemo(() => ({
    total: users.length,
    active: users.filter((u) => u.status === "active").length,
    disabled: users.filter((u) => u.status === "disabled").length,
    agencyCount: agencies.length,
  }), [users, agencies]);

  const columns = useMemo(() => [
    {
      accessorKey: "email",
      header: ({ column }) => <SortableHeader column={column}>Email</SortableHeader>,
      cell: ({ row }) => <span className="font-mono text-xs">{row.original.email}</span>,
    },
    {
      accessorKey: "name",
      header: ({ column }) => <SortableHeader column={column}>Ad</SortableHeader>,
      cell: ({ row }) => <span className="text-sm">{row.original.name || "-"}</span>,
    },
    {
      accessorKey: "agency_name",
      header: "Acenta",
      cell: ({ row }) =>
        row.original.agency_name ? (
          <button className="text-xs text-primary hover:underline" onClick={(e) => { e.stopPropagation(); navigate(`/app/admin/agencies/${row.original.agency_id}/users`); }} data-testid={`go-agency-${row.original.id}`}>
            {row.original.agency_name}
          </button>
        ) : <span className="text-xs text-muted-foreground">-</span>,
    },
    {
      id: "role",
      header: "Rol",
      cell: ({ row }) => (
        <select data-testid={`role-select-${row.original.id}`} className="h-8 rounded-md border bg-background px-2 text-xs" value={agencyRole(row.original.roles)}
          onChange={(e) => handleRoleChange(row.original, e.target.value)} onClick={(e) => e.stopPropagation()}>
          <option value="agency_admin">Yönetici</option>
          <option value="agency_agent">Satış/Operasyon</option>
        </select>
      ),
    },
    {
      accessorKey: "status",
      header: "Durum",
      cell: ({ row }) => <StatusBadge status={row.original.status === "active" ? "active" : "inactive"} label={row.original.status === "active" ? "Aktif" : "Pasif"} />,
    },
    {
      accessorKey: "created_at",
      header: ({ column }) => <SortableHeader column={column}>Oluşturma</SortableHeader>,
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{row.original.created_at ? new Date(row.original.created_at).toLocaleDateString("tr-TR") : "-"}</span>,
    },
    {
      id: "actions",
      header: () => <span className="sr-only">Aksiyonlar</span>,
      cell: ({ row }) => {
        const u = row.original;
        return (
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <DemoSeedButton buttonLabel="Demo" defaultTargetUserId={u.id} triggerClassName="inline-flex items-center gap-1 rounded-md border border-sky-200 bg-sky-50 px-2 py-1 text-xs font-medium text-sky-700 transition-colors hover:bg-sky-100" triggerTestId={`seed-demo-user-${u.id}`} />
            <Button variant="outline" size="sm" data-testid={`permissions-user-${u.id}`} onClick={() => { setSelectedUser(u); setPermissionsOpen(true); }} className="text-xs gap-1 h-8" title="Ekran Yetkileri">
              <Lock className="h-3.5 w-3.5" />
              {u.allowed_screens?.length > 0 && <span className="text-[10px] font-bold bg-primary/10 text-primary rounded-full px-1">{u.allowed_screens.length}</span>}
            </Button>
            <Button variant="outline" size="sm" data-testid={`toggle-status-${u.id}`} onClick={() => handleStatusToggle(u)} className="text-xs gap-1 h-8">
              {u.status === "active" ? <><ShieldOff className="h-3.5 w-3.5" /> Pasif</> : <><ShieldCheck className="h-3.5 w-3.5" /> Aktif</>}
            </Button>
            <Button variant="outline" size="icon" className="h-8 w-8" data-testid={`edit-user-${u.id}`} onClick={() => { setSelectedUser(u); setEditOpen(true); }}>
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button variant="outline" size="icon" className="h-8 w-8 text-destructive hover:bg-destructive/10" data-testid={`delete-user-${u.id}`} onClick={() => { setSelectedUser(u); setDeleteOpen(true); }}>
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        );
      },
      enableSorting: false,
    },
  ], [navigate, agencies, handleRoleChange, handleStatusToggle]);

  return (
    <PageShell
      title="Kullanıcı Yönetimi"
      description={`Tüm acentalardaki kullanıcıları görüntüleyip yönetin (${users.length} kullanıcı, ${agencies.length} acenta)`}
      actions={
        <Button data-testid="add-user-btn" onClick={() => setCreateOpen(true)} size="sm" className="gap-1.5 text-xs font-medium h-9">
          <UserPlus className="h-3.5 w-3.5" /> Yeni Kullanıcı
        </Button>
      }
    >
      <div className="space-y-4" data-testid="all-users-page">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg border bg-card p-4">
            <div className="text-xs text-muted-foreground">Toplam Kullanıcı</div>
            <div className="text-2xl font-bold text-foreground mt-1" data-testid="total-users-count">{kpis.total}</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="text-xs text-muted-foreground">Aktif</div>
            <div className="text-2xl font-bold text-emerald-600 mt-1" data-testid="active-users-count">{kpis.active}</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="text-xs text-muted-foreground">Pasif</div>
            <div className="text-2xl font-bold text-red-500 mt-1" data-testid="disabled-users-count">{kpis.disabled}</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="text-xs text-muted-foreground">Acenta Sayısı</div>
            <div className="text-2xl font-bold text-foreground mt-1" data-testid="agency-count">{kpis.agencyCount}</div>
          </div>
        </div>

        <FilterBar
          search={{ placeholder: "Email, isim veya acenta ara...", value: search, onChange: setSearch }}
          filters={[
            { key: "agency", label: "Acenta", value: agencyFilter, onChange: setAgencyFilter, options: agencyFilterOptions },
            { key: "status", label: "Durum", value: statusFilter, onChange: setStatusFilter, options: STATUS_OPTIONS },
          ]}
          onReset={() => { setSearch(""); setAgencyFilter(""); setStatusFilter(""); }}
        />

        <DataTable
          data={filtered}
          columns={columns}
          loading={isLoading}
          pageSize={20}
          emptyState={
            <div className="flex flex-col items-center gap-3 py-8">
              <p className="text-sm font-medium text-muted-foreground">
                {search || agencyFilter || statusFilter ? "Filtrelere uyan kullanıcı bulunamadı" : "Henüz kullanıcı yok"}
              </p>
            </div>
          }
        />
      </div>

      <CreateUserDialog open={createOpen} onOpenChange={setCreateOpen} agencies={agencies} onCreated={reloadAll} />
      <EditUserDialog open={editOpen} onOpenChange={setEditOpen} userToEdit={selectedUser} agencies={agencies} onUpdated={reloadAll} />
      <DeleteUserDialog open={deleteOpen} onOpenChange={setDeleteOpen} userToDelete={selectedUser} onDeleted={reloadAll} />
      <PermissionsDialog open={permissionsOpen} onOpenChange={setPermissionsOpen} userToEdit={selectedUser} onUpdated={reloadAll} />
    </PageShell>
  );
}
