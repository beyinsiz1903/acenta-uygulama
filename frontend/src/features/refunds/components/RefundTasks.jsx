import React, { useState, useEffect } from "react";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../../../components/ui/dialog";
import { toast } from "../../../components/ui/sonner";
import { Loader2, Clock } from "lucide-react";
import { refundsApi } from "../api";
import { apiErrorMessage, getUser } from "../../../lib/api";
import { TaskStatusBadge, PriorityBadge } from "./RefundBadges";

function RefundTaskCreateDialogButton({ caseData, onCreated }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("normal");
  const [dueAt, setDueAt] = useState("");
  const [slaHours, setSlaHours] = useState("");
  const [assigneeEmail, setAssigneeEmail] = useState("");
  const [tags, setTags] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const canSubmit = !!caseData?.case_id && title && !submitting;

  const onSubmit = async () => {
    if (!canSubmit) return;
    try {
      setSubmitting(true);
      await refundsApi.createTask({
        entity_type: "refund_case", entity_id: caseData.case_id,
        task_type: "custom", title,
        description: description || null, priority,
        due_at: dueAt || null, sla_hours: slaHours ? Number(slaHours) : null,
        assignee_email: assigneeEmail || null,
        tags: tags ? tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
        meta: { source: "refund_detail", case_id: caseData.case_id },
      });
      toast({ title: "Gorev olusturuldu" });
      setTitle(""); setDescription(""); setDueAt(""); setSlaHours(""); setAssigneeEmail(""); setTags("");
      setOpen(false);
      if (onCreated) onCreated();
    } catch (e) {
      toast({ title: "Gorev olusturulamadi", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button size="xs" variant="outline" onClick={() => setOpen(true)} data-testid="create-task-btn">Yeni gorev</Button>
      <DialogContent>
        <DialogHeader><DialogTitle>Yeni gorev olustur</DialogTitle></DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="text-xs text-muted-foreground">case: <span className="font-mono text-xs">{caseData?.case_id}</span></div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Baslik *</div>
            <Input type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Gorev basligi" />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Aciklama</div>
            <Input type="text" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Ops notu (opsiyonel)" />
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Oncelik</div>
              <select className="h-8 rounded-md border bg-background px-2 text-xs" value={priority} onChange={(e) => setPriority(e.target.value)}>
                <option value="low">Dusuk</option>
                <option value="normal">Normal</option>
                <option value="high">Yuksek</option>
                <option value="urgent">Acil</option>
              </select>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Atanan e-posta</div>
              <Input type="email" value={assigneeEmail} onChange={(e) => setAssigneeEmail(e.target.value)} placeholder="ops@acenta.test" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Son tarih (due_at)</div>
              <Input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">SLA (saat)</div>
              <Input type="number" min={0} value={slaHours} onChange={(e) => setSlaHours(e.target.value)} />
            </div>
          </div>
          <div className="space-y-1 text-xs">
            <div className="text-xs text-muted-foreground">Etiketler (virgulle ayirin)</div>
            <Input type="text" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="refund, followup" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={submitting}>Iptal</Button>
          <Button onClick={onSubmit} disabled={!canSubmit} data-testid="create-task-submit">
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Olustur
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RefundTasksSection({ caseData }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyTaskId, setBusyTaskId] = useState("");
  const user = getUser();
  const myEmail = user?.email || "";
  const hasCase = !!caseData?.case_id;

  const load = async () => {
    if (!hasCase) return;
    try {
      setLoading(true); setError("");
      const resp = await refundsApi.listTasks(caseData.case_id);
      setItems(resp?.items || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hasCase) load(); else setItems([]);
  }, [caseData?.case_id]);

  const onQuickStatus = async (task, status) => {
    try {
      await refundsApi.updateTask(task.task_id, { status });
      await load();
    } catch (e) {
      toast({ title: "Gorev guncellenemedi", description: apiErrorMessage(e), variant: "destructive" });
    }
  };

  const onAssign = async (task, assigneeEmail) => {
    if (!task?.task_id) return;
    try {
      setBusyTaskId(task.task_id);
      await refundsApi.updateTask(task.task_id, { assignee_email: assigneeEmail || null });
      await load();
      toast({ title: assigneeEmail ? "Gorev ustlenildi" : "Gorev birakildi" });
    } catch (e) {
      toast({ title: "Islem basarisiz", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setBusyTaskId("");
    }
  };

  if (!hasCase) return null;

  return (
    <div className="rounded-lg border bg-muted/20 p-3 space-y-2" data-testid="refund-tasks-section">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-semibold text-muted-foreground">Gorevler</div>
        <RefundTaskCreateDialogButton caseData={caseData} onCreated={load} />
      </div>
      {loading ? (
        <div className="text-xs text-muted-foreground">Gorevler yukleniyor...</div>
      ) : error ? (
        <div className="text-xs text-destructive">{error}</div>
      ) : !items.length ? (
        <div className="text-xs text-muted-foreground">Bu refund icin gorev yok.</div>
      ) : (
        <div className="space-y-1 text-xs">
          {items.map((t) => {
            const overdue = t.is_overdue && ["open", "in_progress"].includes(t.status);
            return (
              <div key={t.task_id} className="flex items-center justify-between gap-2 rounded border bg-background px-2 py-1">
                <div className="flex flex-col gap-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <TaskStatusBadge status={t.status} />
                    <PriorityBadge priority={t.priority} />
                    {overdue && (
                      <span className="text-2xs text-destructive flex items-center gap-1">
                        <Clock className="h-3 w-3" /> SLA asildi
                      </span>
                    )}
                  </div>
                  <div className="truncate font-medium" title={t.title}>{t.title}</div>
                  <div className="text-xs text-muted-foreground flex flex-wrap gap-2">
                    <span>Tip: {t.task_type}</span>
                    {t.due_at && <span>Due: {new Date(t.due_at).toLocaleString()}</span>}
                    {t.assignee_email && <span>Atanan: {t.assignee_email}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {!t.assignee_email && myEmail && (
                    <Button size="xs" variant="outline" disabled={busyTaskId === t.task_id} onClick={() => onAssign(t, myEmail)}>Ustlen</Button>
                  )}
                  {t.assignee_email && t.assignee_email === myEmail && (
                    <Button size="xs" variant="ghost" disabled={busyTaskId === t.task_id} onClick={() => onAssign(t, null)}>Birak</Button>
                  )}
                  {t.status === "open" && (
                    <Button size="xs" variant="outline" onClick={() => onQuickStatus(t, "in_progress")}>Baslat</Button>
                  )}
                  {t.status === "in_progress" && (
                    <Button size="xs" onClick={() => onQuickStatus(t, "done")}>Tamamla</Button>
                  )}
                  {t.status !== "done" && t.status !== "cancelled" && (
                    <Button size="xs" variant="ghost" onClick={() => onQuickStatus(t, "cancelled")}>Iptal</Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
