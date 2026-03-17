import React, { useState, useMemo } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Clock, Loader2 } from "lucide-react";

import { api, apiErrorMessage, getUser } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Label } from "../components/ui/label";
import { PageShell, DataTable, FilterBar, StatusBadge } from "../design-system";
import { useOpsTasks } from "../features/operations/hooks";

function formatDT(value) {
  if (!value) return "-";
  try { return new Date(value).toLocaleString("tr-TR"); } catch { return String(value); }
}

const STATUS_OPTIONS = [
  { value: "open,in_progress", label: "Açık + Devam ediyor" },
  { value: "open", label: "Sadece açık" },
  { value: "in_progress", label: "Sadece devam ediyor" },
  { value: "done", label: "Tamamlanan" },
  { value: "cancelled", label: "İptal edilen" },
  { value: "open,in_progress,done,cancelled", label: "Hepsi" },
];

const PRIORITY_OPTIONS = [
  { value: "urgent", label: "Acil" },
  { value: "high", label: "Yüksek" },
  { value: "normal", label: "Normal" },
  { value: "low", label: "Düşük" },
];

/* ─── New Task Form ─── */
function NewTaskForm({ onCreated }) {
  const [entityId, setEntityId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("normal");
  const [dueAt, setDueAt] = useState("");
  const [slaHours, setSlaHours] = useState("");
  const [assigneeEmail, setAssigneeEmail] = useState("");
  const [tags, setTags] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = entityId && title && !submitting;

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    try {
      setSubmitting(true);
      await api.post("/ops/tasks", {
        entity_type: "refund_case",
        entity_id: entityId,
        task_type: "custom",
        title,
        description: description || null,
        priority,
        due_at: dueAt || null,
        sla_hours: slaHours ? Number(slaHours) : null,
        assignee_email: assigneeEmail || null,
        tags: tags ? tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
        meta: { source: "ops_tasks_page" },
      });
      onCreated?.();
      setTitle(""); setDescription(""); setDueAt(""); setSlaHours(""); setAssigneeEmail(""); setTags("");
    } catch (e) {
      alert("Görev oluşturulamadı: " + apiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="rounded-lg border" data-testid="new-task-form">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">Yeni Görev</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="grid gap-2.5 md:grid-cols-3 text-xs">
          <div className="space-y-1.5 md:col-span-1">
            <Label className="text-xs text-muted-foreground">Talep Numarası *</Label>
            <Input className="h-8" value={entityId} onChange={(e) => setEntityId(e.target.value)} placeholder="case_..." data-testid="task-entity-id" />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <Label className="text-xs text-muted-foreground">Başlık *</Label>
            <Input className="h-8" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Görev adı" data-testid="task-title" />
          </div>
          <div className="space-y-1.5 md:col-span-3">
            <Label className="text-xs text-muted-foreground">Açıklama</Label>
            <Input className="h-8" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Açıklama (isteğe bağlı)" data-testid="task-desc" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Öncelik</Label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger className="h-8 text-xs" data-testid="task-priority"><SelectValue /></SelectTrigger>
              <SelectContent>
                {PRIORITY_OPTIONS.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Son tarih</Label>
            <Input className="h-8" type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} data-testid="task-due" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">SLA (saat)</Label>
            <Input className="h-8" type="number" min={0} value={slaHours} onChange={(e) => setSlaHours(e.target.value)} data-testid="task-sla" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Atanan e-posta</Label>
            <Input className="h-8" value={assigneeEmail} onChange={(e) => setAssigneeEmail(e.target.value)} placeholder="ops@acenta.test" data-testid="task-assignee" />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <Label className="text-xs text-muted-foreground">Etiketler (virgülle ayırın)</Label>
            <Input className="h-8" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="refund, followup" data-testid="task-tags" />
          </div>
          <div className="flex items-end justify-end md:col-span-3 mt-1">
            <Button type="submit" size="sm" disabled={!canSubmit} data-testid="task-submit">
              {submitting && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              Oluştur
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

/* ═══════════════════════ MAIN PAGE ═══════════════════════ */

export default function OpsTasksPage() {
  const navigate = useNavigate();
  const user = getUser();
  const myEmail = user?.email || "";

  const [statusFilter, setStatusFilter] = useState("open,in_progress");
  const [assigneeFilter, setAssigneeFilter] = useState("");

  const queryFilters = useMemo(() => {
    const params = {};
    if (statusFilter) params.status = statusFilter;
    if (assigneeFilter === "me" && myEmail) params.assignee_email = myEmail;
    return params;
  }, [statusFilter, assigneeFilter, myEmail]);

  const { data: tasksData, isLoading, isError, error, refetch } = useOpsTasks(queryFilters);
  const tasks = useMemo(() => tasksData?.items || tasksData || [], [tasksData]);

  async function onUpdateStatus(task, newStatus) {
    try {
      await api.patch(`/ops/tasks/${task.task_id}`, { status: newStatus });
      refetch();
    } catch (e) {
      alert("Görev güncellenemedi: " + apiErrorMessage(e));
    }
  }

  const columns = useMemo(() => [
    {
      accessorKey: "due_at",
      header: "Son Tarih",
      cell: ({ row }) => {
        const t = row.original;
        const overdue = t.is_overdue && ["open", "in_progress"].includes(t.status);
        return (
          <div className="flex items-center gap-1">
            {overdue && <Clock className="h-3 w-3 text-destructive shrink-0" />}
            <span className={overdue ? "text-destructive font-semibold text-xs" : "text-xs"}>{formatDT(t.due_at)}</span>
          </div>
        );
      },
      size: 140,
    },
    {
      accessorKey: "priority",
      header: "Öncelik",
      cell: ({ row }) => {
        const p = row.original.priority;
        const map = { urgent: "danger", high: "warning", normal: "info", low: "muted" };
        const labelMap = { urgent: "Acil", high: "Yüksek", normal: "Normal", low: "Düşük" };
        return <StatusBadge status={p} color={map[p]} label={labelMap[p] || p} size="sm" />;
      },
      size: 90,
    },
    {
      accessorKey: "title",
      header: "Başlık",
      cell: ({ row }) => <span className="text-sm truncate max-w-[180px] block" title={row.original.title}>{row.original.title}</span>,
    },
    {
      accessorKey: "entity_id",
      header: "Talep",
      cell: ({ row }) =>
        row.original.entity_id ? (
          <Button
            variant="link" size="sm" className="px-0 text-xs truncate max-w-[120px] block h-auto"
            title={row.original.entity_id}
            onClick={(e) => { e.stopPropagation(); navigate(`/app/admin/finance/refunds?case=${row.original.entity_id}`); }}
          >
            {row.original.entity_id.length > 12 ? row.original.entity_id.slice(0, 8) + "..." : row.original.entity_id}
          </Button>
        ) : <span className="text-xs text-muted-foreground">-</span>,
    },
    {
      accessorKey: "booking_id",
      header: "Rezervasyon",
      cell: ({ row }) =>
        row.original.booking_id ? (
          <Link
            to={`/app/ops/bookings/${row.original.booking_id}`}
            className="text-xs text-blue-600 hover:underline truncate block max-w-[120px]"
            title={row.original.booking_id}
            onClick={(e) => e.stopPropagation()}
          >
            {row.original.booking_id.length > 12 ? row.original.booking_id.slice(0, 8) + "..." : row.original.booking_id}
          </Link>
        ) : <span className="text-xs text-muted-foreground">-</span>,
    },
    {
      accessorKey: "assignee_email",
      header: "Atanan",
      cell: ({ row }) => <span className="text-xs truncate max-w-[130px] block" title={row.original.assignee_email}>{row.original.assignee_email || "-"}</span>,
    },
    {
      accessorKey: "status",
      header: "Durum",
      cell: ({ row }) => {
        const s = row.original.status;
        const map = { open: "pending", in_progress: "processing", done: "completed", cancelled: "cancelled" };
        const labelMap = { open: "Açık", in_progress: "Devam Ediyor", done: "Tamamlandı", cancelled: "İptal" };
        return <StatusBadge status={map[s] || s} label={labelMap[s] || s} />;
      },
    },
    {
      id: "actions",
      header: () => <span className="sr-only">İşlemler</span>,
      cell: ({ row }) => {
        const t = row.original;
        return (
          <div className="flex items-center gap-1">
            {t.status === "open" && (
              <Button size="sm" variant="outline" className="h-7 text-xs" onClick={(e) => { e.stopPropagation(); onUpdateStatus(t, "in_progress"); }} data-testid={`task-start-${t.task_id}`}>
                Başlat
              </Button>
            )}
            {t.status === "in_progress" && (
              <Button size="sm" className="h-7 text-xs" onClick={(e) => { e.stopPropagation(); onUpdateStatus(t, "done"); }} data-testid={`task-done-${t.task_id}`}>
                Tamamla
              </Button>
            )}
            {t.status !== "cancelled" && t.status !== "done" && (
              <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={(e) => { e.stopPropagation(); onUpdateStatus(t, "cancelled"); }} data-testid={`task-cancel-${t.task_id}`}>
                İptal
              </Button>
            )}
          </div>
        );
      },
      enableSorting: false,
    },
  ], [navigate, onUpdateStatus]);

  return (
    <PageShell
      title="Görev Takibi"
      description="İade ve operasyon süreçlerinin takibi"
    >
      <div className="space-y-4" data-testid="ops-tasks-page">
        <FilterBar
          filters={[
            { key: "status", label: "Durum", value: statusFilter, onChange: setStatusFilter, options: STATUS_OPTIONS },
            { key: "assignee", label: "Atanan", value: assigneeFilter, onChange: setAssigneeFilter, options: [{ value: "me", label: "Bana atanan" }] },
          ]}
          onReset={() => { setStatusFilter("open,in_progress"); setAssigneeFilter(""); }}
          actions={
            <Button variant="outline" size="sm" className="h-9 gap-1.5 text-xs" onClick={() => refetch()} data-testid="ops-tasks-refresh">
              <Loader2 className="h-3.5 w-3.5" /> Yenile
            </Button>
          }
        />

        <NewTaskForm onCreated={() => refetch()} />

        {isError && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600" data-testid="ops-tasks-error">
            {error?.message || "Veriler yüklenemedi"}
            <Button variant="ghost" size="sm" className="ml-2 h-6 text-xs" onClick={() => refetch()}>Tekrar Dene</Button>
          </div>
        )}

        <DataTable
          data={tasks}
          columns={columns}
          loading={isLoading}
          pageSize={20}
          emptyState={
            <div className="flex flex-col items-center gap-2 py-8">
              <p className="text-sm font-medium text-muted-foreground">Görev bulunamadı</p>
              <p className="text-xs text-muted-foreground/70">Filtreleri değiştirerek tekrar deneyin.</p>
            </div>
          }
        />
      </div>
    </PageShell>
  );
}
