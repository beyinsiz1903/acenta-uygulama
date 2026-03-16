import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Clock,
  FileText,
  Send,
  CreditCard,
  AlertCircle,
  Trash2,
  Plus,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../../components/ui/dialog";
import { Textarea } from "../../components/ui/textarea";
import { toast } from "sonner";
import {
  fetchSettlementRunDetail,
  submitSettlement,
  approveSettlement,
  rejectSettlement,
  markPaidSettlement,
  addEntriesToDraft,
  removeEntryFromDraft,
  fetchUnassignedEntries,
} from "./lib/financeApi";

const fmt = (v) =>
  new Intl.NumberFormat("tr-TR", { style: "currency", currency: "EUR" }).format(v || 0);

const STATUS_CFG = {
  draft: { label: "Taslak", icon: FileText, color: "bg-zinc-100 text-zinc-700" },
  pending_approval: { label: "Onay Bekliyor", icon: Clock, color: "bg-amber-100 text-amber-800" },
  approved: { label: "Onayli", icon: CheckCircle2, color: "bg-blue-100 text-blue-800" },
  paid: { label: "Odendi", icon: CreditCard, color: "bg-emerald-100 text-emerald-800" },
  rejected: { label: "Reddedildi", icon: XCircle, color: "bg-red-100 text-red-800" },
  partially_reconciled: { label: "Kismi Uzlasma", icon: AlertCircle, color: "bg-orange-100 text-orange-800" },
  reconciled: { label: "Uzlasmis", icon: CheckCircle2, color: "bg-teal-100 text-teal-800" },
};

export default function SettlementRunDetailPage() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [selectedEntries, setSelectedEntries] = useState([]);

  const { data: run, isLoading } = useQuery({
    queryKey: ["settlement-run-detail", runId],
    queryFn: () => fetchSettlementRunDetail(runId),
  });

  const { data: unassigned = [] } = useQuery({
    queryKey: ["unassigned-entries", run?.entity_type, run?.entity_id],
    queryFn: () => fetchUnassignedEntries({ entity_type: run?.entity_type, entity_id: run?.entity_id }),
    enabled: addOpen && run?.status === "draft",
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["settlement-run-detail", runId] });
    qc.invalidateQueries({ queryKey: ["settlement-runs"] });
    qc.invalidateQueries({ queryKey: ["settlement-run-stats"] });
  };

  const submitMut = useMutation({
    mutationFn: () => submitSettlement(runId),
    onSuccess: () => { toast.success("Onaya gonderildi"); invalidate(); },
    onError: (e) => toast.error(e.message),
  });

  const approveMut = useMutation({
    mutationFn: () => approveSettlement(runId),
    onSuccess: () => { toast.success("Onaylandi"); invalidate(); },
    onError: (e) => toast.error(e.message),
  });

  const rejectMut = useMutation({
    mutationFn: () => rejectSettlement(runId, "admin", rejectReason),
    onSuccess: () => { toast.success("Reddedildi"); setRejectOpen(false); setRejectReason(""); invalidate(); },
    onError: (e) => toast.error(e.message),
  });

  const paidMut = useMutation({
    mutationFn: () => markPaidSettlement(runId),
    onSuccess: () => { toast.success("Odendi olarak isaretlendi"); invalidate(); },
    onError: (e) => toast.error(e.message),
  });

  const addMut = useMutation({
    mutationFn: (ids) => addEntriesToDraft(runId, ids),
    onSuccess: (d) => {
      toast.success(`${d.linked} kayit eklendi`);
      setAddOpen(false);
      setSelectedEntries([]);
      invalidate();
    },
    onError: (e) => toast.error(e.message),
  });

  const removeMut = useMutation({
    mutationFn: (entryId) => removeEntryFromDraft(runId, entryId),
    onSuccess: () => { toast.success("Kayit cikarildi"); invalidate(); },
    onError: (e) => toast.error(e.message),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!run || run.error) {
    return (
      <div className="text-center py-20 text-muted-foreground">
        <p>Settlement run bulunamadi</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate(-1)}>Geri Don</Button>
      </div>
    );
  }

  const cfg = STATUS_CFG[run.status] || STATUS_CFG.draft;
  const entries = run.entries || [];
  const history = run.history || [];

  const toggleEntry = (id) => {
    setSelectedEntries((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6" data-testid="settlement-run-detail-page">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)} data-testid="back-btn">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight" data-testid="run-id-title">{run.run_id}</h1>
            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.color}`} data-testid="run-status-badge">
              <cfg.icon className="h-3.5 w-3.5" />
              {cfg.label}
            </span>
            <Badge variant="outline">{run.run_type === "AGENCY" ? "Acenta" : "Tedarikci"}</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {run.entity_name} &middot; {run.period_start} — {run.period_end}
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground mb-1">Toplam Tutar</p>
            <p className="text-xl font-bold" data-testid="total-amount">{fmt(run.total_amount)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground mb-1">Kayit Sayisi</p>
            <p className="text-xl font-bold" data-testid="entries-count">{run.entries_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground mb-1">Olusturulma</p>
            <p className="text-sm font-medium">{run.created_at?.slice(0, 10)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground mb-1">Notlar</p>
            <p className="text-sm font-medium truncate">{run.notes || "—"}</p>
          </CardContent>
        </Card>
      </div>

      {/* Action Buttons */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Islemler</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3" data-testid="workflow-actions">
          {run.status === "draft" && (
            <>
              <Button size="sm" onClick={() => setAddOpen(true)} data-testid="add-entries-btn">
                <Plus className="h-4 w-4 mr-1.5" /> Kayit Ekle
              </Button>
              <Button size="sm" onClick={() => submitMut.mutate()} disabled={submitMut.isPending || run.entries_count === 0} data-testid="submit-btn">
                <Send className="h-4 w-4 mr-1.5" /> Onaya Gonder
              </Button>
            </>
          )}
          {run.status === "pending_approval" && (
            <>
              <Button size="sm" variant="default" onClick={() => approveMut.mutate()} disabled={approveMut.isPending} data-testid="approve-btn">
                <CheckCircle2 className="h-4 w-4 mr-1.5" /> Onayla
              </Button>
              <Button size="sm" variant="destructive" onClick={() => setRejectOpen(true)} data-testid="reject-btn">
                <XCircle className="h-4 w-4 mr-1.5" /> Reddet
              </Button>
            </>
          )}
          {run.status === "approved" && (
            <Button size="sm" onClick={() => paidMut.mutate()} disabled={paidMut.isPending} data-testid="mark-paid-btn">
              <CreditCard className="h-4 w-4 mr-1.5" /> Odendi Isaretle
            </Button>
          )}
          {["paid", "reconciled"].includes(run.status) && (
            <p className="text-sm text-muted-foreground italic">Bu calistirma tamamlanmistir, islem yapilamaz.</p>
          )}
        </CardContent>
      </Card>

      {/* Entries Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Bagli Kayitlar ({entries.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Kayit No</TableHead>
                  <TableHead className="text-xs">Tur</TableHead>
                  <TableHead className="text-xs">Hesap</TableHead>
                  <TableHead className="text-xs">Varlik</TableHead>
                  <TableHead className="text-xs">Rezervasyon</TableHead>
                  <TableHead className="text-xs text-right">Tutar</TableHead>
                  <TableHead className="text-xs">Durum</TableHead>
                  {run.status === "draft" && <TableHead className="text-xs w-10"></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((e) => (
                  <TableRow key={e.entry_id} data-testid={`entry-row-${e.entry_id}`}>
                    <TableCell className="font-mono text-sm">{e.entry_id}</TableCell>
                    <TableCell>
                      <Badge variant={e.entry_type === "DEBIT" ? "default" : "secondary"} className="text-xs">
                        {e.entry_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{e.account_type}</TableCell>
                    <TableCell className="text-sm">{e.entity_name}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{e.booking_ref}</TableCell>
                    <TableCell className="text-right font-medium text-sm">{fmt(e.amount)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">{e.financial_status}</Badge>
                    </TableCell>
                    {run.status === "draft" && (
                      <TableCell>
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => removeMut.mutate(e.entry_id)} data-testid={`remove-entry-${e.entry_id}`}>
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
                {entries.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={run.status === "draft" ? 8 : 7} className="text-center py-8 text-muted-foreground">
                      Bu calistirmaya henuz kayit eklenmemis
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* History Timeline */}
      {history.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Gecmis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3" data-testid="history-timeline">
              {history.map((h, i) => (
                <div key={i} className="flex items-start gap-3 text-sm">
                  <div className="w-2 h-2 mt-1.5 rounded-full bg-primary shrink-0" />
                  <div>
                    <span className="font-medium capitalize">{h.action}</span>
                    <span className="text-muted-foreground"> — {h.actor}</span>
                    {h.reason && <span className="text-muted-foreground"> ({h.reason})</span>}
                    <p className="text-xs text-muted-foreground">{h.timestamp?.slice(0, 19).replace("T", " ")}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Reject Dialog */}
      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Settlement Reddet</DialogTitle>
          </DialogHeader>
          <Textarea placeholder="Red nedeni..." value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} data-testid="reject-reason-input" />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectOpen(false)}>Iptal</Button>
            <Button variant="destructive" onClick={() => rejectMut.mutate()} disabled={rejectMut.isPending} data-testid="confirm-reject-btn">Reddet</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Entries Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Atanmamis Kayitlari Ekle</DialogTitle>
          </DialogHeader>
          <div className="max-h-[400px] overflow-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10"></TableHead>
                  <TableHead className="text-xs">Kayit No</TableHead>
                  <TableHead className="text-xs">Hesap</TableHead>
                  <TableHead className="text-xs">Rezervasyon</TableHead>
                  <TableHead className="text-xs text-right">Tutar</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(Array.isArray(unassigned) ? unassigned : []).map((e) => (
                  <TableRow key={e.entry_id} className="cursor-pointer" onClick={() => toggleEntry(e.entry_id)}>
                    <TableCell>
                      <input type="checkbox" checked={selectedEntries.includes(e.entry_id)} readOnly className="rounded" />
                    </TableCell>
                    <TableCell className="font-mono text-sm">{e.entry_id}</TableCell>
                    <TableCell className="text-sm">{e.account_type}</TableCell>
                    <TableCell className="text-xs">{e.booking_ref}</TableCell>
                    <TableCell className="text-right text-sm font-medium">{fmt(e.amount)}</TableCell>
                  </TableRow>
                ))}
                {(!unassigned || unassigned.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-6 text-muted-foreground">Atanmamis kayit bulunamadi</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>Iptal</Button>
            <Button onClick={() => addMut.mutate(selectedEntries)} disabled={selectedEntries.length === 0 || addMut.isPending} data-testid="confirm-add-entries-btn">
              {selectedEntries.length} Kayit Ekle
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
