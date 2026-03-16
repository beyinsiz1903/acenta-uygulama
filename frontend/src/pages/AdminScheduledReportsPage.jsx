import React, { useState, useMemo } from "react";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Calendar, Clock, Mail, Plus, Trash2, RefreshCw, FileText } from "lucide-react";
import { PageShell, DataTable, StatusBadge } from "../design-system";
import { useScheduledReports, useCreateSchedule, useDeleteSchedule, useExecuteDueReports } from "../features/reporting/hooks";
import { toast } from "sonner";

const REPORT_TYPES = [
  { value: "sales_summary", label: "Satis Ozeti" },
  { value: "revenue_report", label: "Gelir Raporu" },
  { value: "occupancy", label: "Doluluk Raporu" },
  { value: "crm_pipeline", label: "CRM Pipeline" },
  { value: "financial_summary", label: "Finansal Ozet" },
];

const FREQUENCIES = [
  { value: "daily", label: "Gunluk" },
  { value: "weekly", label: "Haftalik" },
  { value: "monthly", label: "Aylik" },
];

const FREQ_STATUS_MAP = {
  daily: { color: "info", label: "Gunluk" },
  weekly: { color: "warning", label: "Haftalik" },
  monthly: { color: "success", label: "Aylik" },
};

function CreateScheduleForm({ onCreated }) {
  const [newSchedule, setNewSchedule] = useState({
    report_type: "sales_summary",
    frequency: "daily",
    email: "",
  });
  const createMutation = useCreateSchedule();

  const handleCreate = async () => {
    if (!newSchedule.email) return;
    try {
      await createMutation.mutateAsync(newSchedule);
      toast.success("Zamanlama olusturuldu");
      setNewSchedule({ report_type: "sales_summary", frequency: "daily", email: "" });
      onCreated?.();
    } catch (e) {
      toast.error("Olusturma hatasi: " + (e.response?.data?.error?.message || e.message));
    }
  };

  return (
    <div className="rounded-lg border p-4 bg-muted/20" data-testid="create-schedule-form">
      <h3 className="text-sm font-semibold mb-3">Yeni Rapor Zamanlamasi</h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="text-xs font-medium mb-1 block">Rapor Turu</label>
          <select
            value={newSchedule.report_type}
            onChange={(e) => setNewSchedule({ ...newSchedule, report_type: e.target.value })}
            className="w-full rounded-md border px-3 py-2 text-sm bg-background"
            data-testid="report-type-select"
          >
            {REPORT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Siklik</label>
          <select
            value={newSchedule.frequency}
            onChange={(e) => setNewSchedule({ ...newSchedule, frequency: e.target.value })}
            className="w-full rounded-md border px-3 py-2 text-sm bg-background"
            data-testid="frequency-select"
          >
            {FREQUENCIES.map((f) => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">E-posta</label>
          <input
            type="email"
            value={newSchedule.email}
            onChange={(e) => setNewSchedule({ ...newSchedule, email: e.target.value })}
            placeholder="rapor@sirket.com"
            className="w-full rounded-md border px-3 py-2 text-sm bg-background"
            data-testid="schedule-email-input"
          />
        </div>
      </div>
      <div className="flex justify-end gap-2 mt-3">
        <Button size="sm" onClick={handleCreate} disabled={createMutation.isPending || !newSchedule.email} data-testid="submit-schedule-btn">
          {createMutation.isPending ? "Olusturuluyor..." : "Olustur"}
        </Button>
      </div>
    </div>
  );
}

export default function AdminScheduledReportsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const { data: schedules = [], isLoading, isError, error, refetch } = useScheduledReports();
  const deleteMutation = useDeleteSchedule();
  const executeMutation = useExecuteDueReports();

  const handleDelete = async (id) => {
    if (!window.confirm("Bu zamanlanmis raporu silmek istediginize emin misiniz?")) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Zamanlama silindi");
    } catch (e) {
      toast.error("Silme hatasi: " + (e.response?.data?.error?.message || e.message));
    }
  };

  const handleTrigger = async () => {
    try {
      const result = await executeMutation.mutateAsync();
      const count = result?.count || 0;
      toast.success(`${count} rapor calistirildi (simulasyon).`);
    } catch (e) {
      toast.error("Tetikleme hatasi: " + (e.response?.data?.error?.message || e.message));
    }
  };

  const columns = useMemo(() => [
    {
      accessorKey: "report_type",
      header: "Rapor Turu",
      cell: ({ row }) => (
        <span className="flex items-center gap-2 font-medium text-sm">
          <FileText className="h-4 w-4 text-muted-foreground" />
          {REPORT_TYPES.find((t) => t.value === row.original.report_type)?.label || row.original.report_type}
        </span>
      ),
    },
    {
      accessorKey: "frequency",
      header: "Siklik",
      cell: ({ row }) => {
        const f = FREQ_STATUS_MAP[row.original.frequency];
        return f ? <StatusBadge status={row.original.frequency} color={f.color} label={f.label} size="sm" /> : <Badge variant="outline">{row.original.frequency}</Badge>;
      },
      size: 100,
    },
    {
      accessorKey: "email",
      header: "E-posta",
      cell: ({ row }) => (
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Mail className="h-3.5 w-3.5" />
          {row.original.email}
        </span>
      ),
    },
    {
      accessorKey: "next_run",
      header: "Sonraki Calistirma",
      cell: ({ row }) => (
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          {row.original.next_run ? new Date(row.original.next_run).toLocaleString("tr-TR") : "-"}
        </span>
      ),
      size: 160,
    },
    {
      accessorKey: "run_count",
      header: "Calistirma",
      cell: ({ row }) => <Badge variant="outline">{row.original.run_count || 0}</Badge>,
      size: 90,
    },
    {
      id: "actions",
      header: () => <span className="sr-only">Aksiyonlar</span>,
      cell: ({ row }) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => { e.stopPropagation(); handleDelete(row.original.id); }}
          data-testid={`delete-schedule-${row.original.id}`}
          className="h-7 text-destructive hover:text-destructive"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      ),
      enableSorting: false,
      size: 60,
    },
  ], []);

  return (
    <PageShell
      title="Zamanlanmis Raporlar"
      description="Otomatik rapor gonderimi zamanlamalarini yonetin."
      actions={
        <>
          <Button variant="outline" size="sm" onClick={handleTrigger} data-testid="trigger-btn" disabled={executeMutation.isPending}>
            <RefreshCw className="h-4 w-4 mr-1" /> Bekleyenleri Calistir
          </Button>
          <Button size="sm" onClick={() => setShowCreate(!showCreate)} data-testid="create-schedule-btn">
            <Plus className="h-4 w-4 mr-1" /> Yeni Zamanlama
          </Button>
        </>
      }
    >
      <div className="space-y-4" data-testid="scheduled-reports-page">
        {showCreate && <CreateScheduleForm onCreated={() => setShowCreate(false)} />}

        {isError && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600" data-testid="schedules-error">
            {error?.message || "Veriler yuklenemedi"}
            <Button variant="ghost" size="sm" className="ml-2 h-6 text-xs" onClick={() => refetch()}>Tekrar Dene</Button>
          </div>
        )}

        <DataTable
          data={schedules}
          columns={columns}
          loading={isLoading}
          pageSize={20}
          emptyState={
            <div className="flex flex-col items-center gap-2 py-8" data-testid="no-schedules">
              <Calendar className="h-12 w-12 opacity-30 text-muted-foreground" />
              <p className="text-sm font-medium text-muted-foreground">Henuz zamanlanmis rapor yok.</p>
            </div>
          }
        />
      </div>
    </PageShell>
  );
}
