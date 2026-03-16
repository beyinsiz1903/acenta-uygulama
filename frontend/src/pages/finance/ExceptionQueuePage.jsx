import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  Filter,
  Eye,
  X,
  ShieldCheck,
  ArrowUpDown,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../../components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../../components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";
import { Textarea } from "../../components/ui/textarea";
import { Input } from "../../components/ui/input";
import { toast } from "sonner";
import {
  fetchExceptions,
  fetchExceptionStats,
  resolveException,
  dismissException,
} from "./lib/financeApi";

const fmt = (v) =>
  new Intl.NumberFormat("tr-TR", { style: "currency", currency: "EUR" }).format(v || 0);

const SEVERITY_CFG = {
  high: { label: "Yuksek", color: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300" },
  medium: { label: "Orta", color: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" },
  low: { label: "Dusuk", color: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300" },
};

const STATUS_CFG = {
  open: { label: "Acik", color: "bg-amber-100 text-amber-800" },
  resolved: { label: "Cozuldu", color: "bg-emerald-100 text-emerald-800" },
  dismissed: { label: "Kapatildi", color: "bg-zinc-100 text-zinc-700" },
};

const TYPE_LABELS = {
  amount_mismatch: "Tutar Uyumsuzlugu",
  duplicate_entry: "Mukerrer Kayit",
  currency_mismatch: "Doviz Uyumsuzlugu",
  missing_invoice: "Eksik Fatura",
  booking_status_conflict: "Durum Catismasi",
};

export default function ExceptionQueuePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [resolveOpen, setResolveOpen] = useState(false);
  const [dismissOpen, setDismissOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedExc, setSelectedExc] = useState(null);
  const [resolution, setResolution] = useState("");
  const [resolveNotes, setResolveNotes] = useState("");
  const [dismissReason, setDismissReason] = useState("");

  const { data: excData, isLoading } = useQuery({
    queryKey: ["finance-exceptions", statusFilter, severityFilter, typeFilter],
    queryFn: () =>
      fetchExceptions({
        status: statusFilter === "all" ? undefined : statusFilter,
        severity: severityFilter === "all" ? undefined : severityFilter,
        exception_type: typeFilter === "all" ? undefined : typeFilter,
      }),
  });

  const { data: stats } = useQuery({
    queryKey: ["finance-exception-stats"],
    queryFn: fetchExceptionStats,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["finance-exceptions"] });
    qc.invalidateQueries({ queryKey: ["finance-exception-stats"] });
  };

  const resolveMut = useMutation({
    mutationFn: () => resolveException(selectedExc?.exception_id, { resolution, notes: resolveNotes }),
    onSuccess: () => {
      toast.success("Exception cozuldu");
      setResolveOpen(false);
      setResolution("");
      setResolveNotes("");
      invalidate();
    },
    onError: (e) => toast.error(e.message),
  });

  const dismissMut = useMutation({
    mutationFn: () => dismissException(selectedExc?.exception_id, dismissReason),
    onSuccess: () => {
      toast.success("Exception kapatildi");
      setDismissOpen(false);
      setDismissReason("");
      invalidate();
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

  const exceptions = excData?.exceptions || [];
  const byStatus = stats?.by_status || {};
  const bySeverity = stats?.by_severity || {};

  return (
    <div className="space-y-6" data-testid="exception-queue-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" data-testid="exception-queue-title">Exception Kuyrugu</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Finansal uyumsuzluklar ve istisna yonetimi
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => navigate("/app/admin/finance/overview-v2")} data-testid="back-to-overview-btn">
          Genel Bakis
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3" data-testid="exception-stats">
        <Card className={`${statusFilter === "open" ? "ring-2 ring-primary" : ""} cursor-pointer`} onClick={() => setStatusFilter(statusFilter === "open" ? "all" : "open")}>
          <CardContent className="p-3">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              <span className="text-xs font-medium text-muted-foreground">Acik</span>
            </div>
            <p className="text-lg font-bold">{byStatus.open?.count || 0}</p>
            <p className="text-xs text-muted-foreground">{fmt(byStatus.open?.total_amount || 0)}</p>
          </CardContent>
        </Card>
        <Card className={`${statusFilter === "resolved" ? "ring-2 ring-primary" : ""} cursor-pointer`} onClick={() => setStatusFilter(statusFilter === "resolved" ? "all" : "resolved")}>
          <CardContent className="p-3">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              <span className="text-xs font-medium text-muted-foreground">Cozuldu</span>
            </div>
            <p className="text-lg font-bold">{byStatus.resolved?.count || 0}</p>
            <p className="text-xs text-muted-foreground">{fmt(byStatus.resolved?.total_amount || 0)}</p>
          </CardContent>
        </Card>
        {Object.entries(SEVERITY_CFG).map(([key, cfg]) => (
          <Card key={key} className={`${severityFilter === key ? "ring-2 ring-primary" : ""} cursor-pointer`} onClick={() => setSeverityFilter(severityFilter === key ? "all" : key)}>
            <CardContent className="p-3">
              <div className="flex items-center gap-2 mb-1">
                <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs font-medium text-muted-foreground">{cfg.label}</span>
              </div>
              <p className="text-lg font-bold">{bySeverity[key]?.count || 0}</p>
              <p className="text-xs text-muted-foreground">{fmt(bySeverity[key]?.total_amount || 0)}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3" data-testid="exception-filters">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px] h-9 text-sm" data-testid="exc-status-filter">
            <SelectValue placeholder="Durum" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tum Durumlar</SelectItem>
            <SelectItem value="open">Acik</SelectItem>
            <SelectItem value="resolved">Cozuldu</SelectItem>
            <SelectItem value="dismissed">Kapatildi</SelectItem>
          </SelectContent>
        </Select>
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="w-[160px] h-9 text-sm" data-testid="exc-severity-filter">
            <SelectValue placeholder="Oncelik" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tum Oncelikler</SelectItem>
            <SelectItem value="high">Yuksek</SelectItem>
            <SelectItem value="medium">Orta</SelectItem>
            <SelectItem value="low">Dusuk</SelectItem>
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[180px] h-9 text-sm" data-testid="exc-type-filter">
            <SelectValue placeholder="Tur" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tum Turler</SelectItem>
            <SelectItem value="amount_mismatch">Tutar Uyumsuzlugu</SelectItem>
            <SelectItem value="duplicate_entry">Mukerrer Kayit</SelectItem>
            <SelectItem value="currency_mismatch">Doviz Uyumsuzlugu</SelectItem>
            <SelectItem value="missing_invoice">Eksik Fatura</SelectItem>
            <SelectItem value="booking_status_conflict">Durum Catismasi</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Exceptions Table */}
      <Card>
        <CardContent className="p-0" data-testid="exception-table">
          <div className="overflow-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">No</TableHead>
                  <TableHead className="text-xs">Tur</TableHead>
                  <TableHead className="text-xs">Oncelik</TableHead>
                  <TableHead className="text-xs">Varlik</TableHead>
                  <TableHead className="text-xs">Rezervasyon</TableHead>
                  <TableHead className="text-xs text-right">Fark</TableHead>
                  <TableHead className="text-xs">Durum</TableHead>
                  <TableHead className="text-xs w-24">Islem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {exceptions.map((exc) => {
                  const sevCfg = SEVERITY_CFG[exc.severity] || SEVERITY_CFG.low;
                  const stCfg = STATUS_CFG[exc.status] || STATUS_CFG.open;
                  return (
                    <TableRow key={exc.exception_id} data-testid={`exc-row-${exc.exception_id}`}>
                      <TableCell className="font-mono text-sm font-medium">{exc.exception_id}</TableCell>
                      <TableCell className="text-xs">{TYPE_LABELS[exc.exception_type] || exc.exception_type}</TableCell>
                      <TableCell>
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${sevCfg.color}`}>
                          {sevCfg.label}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">{exc.entity_name}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{exc.booking_ref}</TableCell>
                      <TableCell className="text-right font-medium text-sm text-destructive">{fmt(exc.amount_difference)}</TableCell>
                      <TableCell>
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${stCfg.color}`}>
                          {stCfg.label}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setSelectedExc(exc); setDetailOpen(true); }} data-testid={`view-exc-${exc.exception_id}`}>
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                          {exc.status === "open" && (
                            <>
                              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setSelectedExc(exc); setResolveOpen(true); }} data-testid={`resolve-exc-${exc.exception_id}`}>
                                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                              </Button>
                              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => { setSelectedExc(exc); setDismissOpen(true); }} data-testid={`dismiss-exc-${exc.exception_id}`}>
                                <X className="h-3.5 w-3.5 text-muted-foreground" />
                              </Button>
                            </>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {exceptions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                      Exception bulunamadi
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{selectedExc?.exception_id} - Detay</DialogTitle>
          </DialogHeader>
          {selectedExc && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-muted-foreground">Tur</p>
                  <p className="font-medium">{TYPE_LABELS[selectedExc.exception_type]}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Kaynak</p>
                  <p className="font-medium">{selectedExc.source}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Beklenen</p>
                  <p className="font-medium">{fmt(selectedExc.expected_amount)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Gerceklesen</p>
                  <p className="font-medium">{fmt(selectedExc.actual_amount)}</p>
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Aciklama</p>
                <p>{selectedExc.description}</p>
              </div>
              {selectedExc.related_settlement_run && (
                <div>
                  <p className="text-xs text-muted-foreground">Ilgili Settlement</p>
                  <p className="font-mono">{selectedExc.related_settlement_run}</p>
                </div>
              )}
              {selectedExc.resolution && (
                <div>
                  <p className="text-xs text-muted-foreground">Cozum</p>
                  <p>{selectedExc.resolution} — {selectedExc.resolved_by} ({selectedExc.resolved_at?.slice(0, 10)})</p>
                  {selectedExc.resolution_notes && <p className="text-xs text-muted-foreground mt-1">{selectedExc.resolution_notes}</p>}
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailOpen(false)}>Kapat</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Resolve Dialog */}
      <Dialog open={resolveOpen} onOpenChange={setResolveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Exception Coz — {selectedExc?.exception_id}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">Cozum Yontemi</label>
              <Input placeholder="ornegin: adjusted, waived, corrected" value={resolution} onChange={(e) => setResolution(e.target.value)} data-testid="resolve-method-input" />
            </div>
            <div>
              <label className="text-sm font-medium">Notlar</label>
              <Textarea placeholder="Cozum detaylari..." value={resolveNotes} onChange={(e) => setResolveNotes(e.target.value)} data-testid="resolve-notes-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setResolveOpen(false)}>Iptal</Button>
            <Button onClick={() => resolveMut.mutate()} disabled={!resolution || resolveMut.isPending} data-testid="confirm-resolve-btn">Coz</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dismiss Dialog */}
      <Dialog open={dismissOpen} onOpenChange={setDismissOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Exception Kapat — {selectedExc?.exception_id}</DialogTitle>
          </DialogHeader>
          <Textarea placeholder="Kapatma nedeni..." value={dismissReason} onChange={(e) => setDismissReason(e.target.value)} data-testid="dismiss-reason-input" />
          <DialogFooter>
            <Button variant="outline" onClick={() => setDismissOpen(false)}>Iptal</Button>
            <Button variant="secondary" onClick={() => dismissMut.mutate()} disabled={dismissMut.isPending} data-testid="confirm-dismiss-btn">Kapat</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
