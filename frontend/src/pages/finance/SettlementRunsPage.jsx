import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Filter,
  Plus,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { toast } from "sonner";
import { fetchSettlementRuns, fetchSettlementRunStats, createSettlementDraft } from "./lib/financeApi";

const fmt = (v) => new Intl.NumberFormat("tr-TR", { style: "currency", currency: "EUR" }).format(v || 0);

const STATUS_CONFIG = {
  draft: { label: "Taslak", icon: FileText, color: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300" },
  pending_approval: { label: "Onay Bekliyor", icon: Clock, color: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" },
  approved: { label: "Onaylı", icon: CheckCircle2, color: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300" },
  paid: { label: "Ödendi", icon: CheckCircle2, color: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300" },
  partially_reconciled: { label: "Kısmi Uzlaşma", icon: AlertCircle, color: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300" },
  reconciled: { label: "Uzlaşmış", icon: CheckCircle2, color: "bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300" },
  rejected: { label: "Reddedildi", icon: XCircle, color: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300" },
};

export default function SettlementRunsPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [draft, setDraft] = useState({ run_type: "AGENCY", entity_id: "", entity_name: "", period_start: "", period_end: "", notes: "" });

  const { data: runsData, isLoading } = useQuery({
    queryKey: ["settlement-runs", statusFilter, typeFilter],
    queryFn: () =>
      fetchSettlementRuns({
        status: statusFilter === "all" ? undefined : statusFilter,
        run_type: typeFilter === "all" ? undefined : typeFilter,
      }),
  });

  const { data: stats } = useQuery({
    queryKey: ["settlement-run-stats"],
    queryFn: fetchSettlementRunStats,
  });

  const createMut = useMutation({
    mutationFn: (data) => createSettlementDraft(data),
    onSuccess: (d) => {
      toast.success(`Taslak ${d.run_id} olusturuldu`);
      setCreateOpen(false);
      setDraft({ run_type: "AGENCY", entity_id: "", entity_name: "", period_start: "", period_end: "", notes: "" });
      qc.invalidateQueries({ queryKey: ["settlement-runs"] });
      qc.invalidateQueries({ queryKey: ["settlement-run-stats"] });
      navigate(`/app/admin/finance/settlement-runs-v2/${d.run_id}`);
    },
    onError: (e) => toast.error(e.message),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  const runs = runsData?.runs || [];
  const byStatus = stats?.by_status || {};

  return (
    <div className="space-y-6" data-testid="settlement-runs-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" data-testid="settlement-runs-title">Mutabakat Calistirmalari</h1>
          <p className="text-sm text-muted-foreground mt-1">Mutabakat donemleri, onay ve odeme durumlari</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => setCreateOpen(true)} data-testid="create-draft-btn">
            <Plus className="h-4 w-4 mr-1.5" /> Yeni Taslak
          </Button>
          <Button variant="outline" size="sm" onClick={() => navigate("/app/admin/finance/overview-v2")} data-testid="back-to-overview-btn">
            Genel Bakis
          </Button>
        </div>
      </div>

      {/* Status Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="settlement-status-cards">
        {Object.entries(STATUS_CONFIG).map(([key, cfg]) => {
          const data = byStatus[key] || { count: 0, total_amount: 0 };
          return (
            <Card
              key={key}
              className={`cursor-pointer transition-shadow hover:shadow-md ${statusFilter === key ? "ring-2 ring-primary" : ""}`}
              onClick={() => setStatusFilter(statusFilter === key ? "all" : key)}
            >
              <CardContent className="p-3">
                <div className="flex items-center gap-2 mb-1">
                  <cfg.icon className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">{cfg.label}</span>
                </div>
                <div className="text-lg font-bold">{data.count}</div>
                <div className="text-xs text-muted-foreground">{fmt(data.total_amount)}</div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3" data-testid="settlement-filters">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px] h-9 text-sm" data-testid="status-filter">
            <SelectValue placeholder="Durum" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tüm Durumlar</SelectItem>
            {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
              <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[180px] h-9 text-sm" data-testid="type-filter">
            <SelectValue placeholder="Tür" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tüm Türler</SelectItem>
            <SelectItem value="AGENCY">Acenta</SelectItem>
            <SelectItem value="SUPPLIER">Tedarikçi</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Runs Table */}
      <Card>
        <CardContent className="p-0" data-testid="settlement-runs-table">
          <div className="overflow-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Çalıştırma No</TableHead>
                  <TableHead className="text-xs">Tür</TableHead>
                  <TableHead className="text-xs">Varlık</TableHead>
                  <TableHead className="text-xs">Dönem</TableHead>
                  <TableHead className="text-xs text-right">Tutar</TableHead>
                  <TableHead className="text-xs text-center">Kayıt</TableHead>
                  <TableHead className="text-xs">Durum</TableHead>
                  <TableHead className="text-xs">Notlar</TableHead>
                  <TableHead className="text-xs w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run) => {
                  const cfg = STATUS_CONFIG[run.status] || STATUS_CONFIG.draft;
                  return (
                    <TableRow
                      key={run.run_id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => navigate(`/app/admin/finance/settlement-runs-v2/${run.run_id}`)}
                      data-testid={`settlement-row-${run.run_id}`}
                    >
                      <TableCell className="font-mono text-sm font-medium">{run.run_id}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {run.run_type === "AGENCY" ? "Acenta" : "Tedarikçi"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">{run.entity_name}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {run.period_start} — {run.period_end}
                      </TableCell>
                      <TableCell className="text-right font-medium text-sm">{fmt(run.total_amount)}</TableCell>
                      <TableCell className="text-center text-sm">{run.entries_count}</TableCell>
                      <TableCell>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
                          <cfg.icon className="h-3 w-3" />
                          {cfg.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">{run.notes}</TableCell>
                      <TableCell>
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </TableCell>
                    </TableRow>
                  );
                })}
                {runs.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      Mutabakat çalıştırması bulunamadı
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Create Draft Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Yeni Settlement Taslagi</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Tur</label>
              <Select value={draft.run_type} onValueChange={(v) => setDraft({ ...draft, run_type: v })}>
                <SelectTrigger className="h-9" data-testid="draft-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="AGENCY">Acenta</SelectItem>
                  <SelectItem value="SUPPLIER">Tedarikci</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">Varlik ID</label>
                <Input placeholder="AGN-001" value={draft.entity_id} onChange={(e) => setDraft({ ...draft, entity_id: e.target.value })} data-testid="draft-entity-id" />
              </div>
              <div>
                <label className="text-sm font-medium">Varlik Adi</label>
                <Input placeholder="Sunshine Travel" value={draft.entity_name} onChange={(e) => setDraft({ ...draft, entity_name: e.target.value })} data-testid="draft-entity-name" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">Donem Baslangic</label>
                <Input type="date" value={draft.period_start} onChange={(e) => setDraft({ ...draft, period_start: e.target.value })} data-testid="draft-period-start" />
              </div>
              <div>
                <label className="text-sm font-medium">Donem Bitis</label>
                <Input type="date" value={draft.period_end} onChange={(e) => setDraft({ ...draft, period_end: e.target.value })} data-testid="draft-period-end" />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">Notlar</label>
              <Textarea placeholder="Taslak notlari..." value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} data-testid="draft-notes" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Iptal</Button>
            <Button
              onClick={() => createMut.mutate(draft)}
              disabled={!draft.entity_id || !draft.entity_name || !draft.period_start || !draft.period_end || createMut.isPending}
              data-testid="confirm-create-draft-btn"
            >
              Olustur
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
