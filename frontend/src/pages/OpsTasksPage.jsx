import React, { useEffect, useState, useMemo } from "react";
import { useNavigate, Link } from "react-router-dom";
import { AlertCircle, CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { getUser } from "../lib/api";

function statusBadge(status) {
  switch (status) {
    case "open":
      return <Badge variant="outline">Açık</Badge>;
    case "in_progress":
      return <Badge variant="secondary">Devam ediyor</Badge>;
    case "done":
      return (
        <Badge variant="secondary" className="gap-1">
          <CheckCircle2 className="h-3 w-3" /> Tamamlandı
        </Badge>
      );
    case "cancelled":
      return (
        <Badge variant="outline" className="gap-1">
          <XCircle className="h-3 w-3" /> İptal
        </Badge>
      );
    default:
      return <Badge variant="outline">{status || "-"}</Badge>;
  }
}

function priorityBadge(priority) {
  switch (priority) {
    case "urgent":
      return <Badge variant="destructive">Acil</Badge>;
    case "high":
      return <Badge variant="secondary">Yüksek</Badge>;
    case "normal":
      return <Badge variant="outline">Normal</Badge>;
    case "low":
      return <Badge variant="outline">Düşük</Badge>;
    default:
      return <Badge variant="outline">{priority || "-"}</Badge>;
  }
}

function formatDateTime(value) {
  if (!value) return "-";
  try {
    const d = new Date(value);
    return d.toLocaleString();
  } catch {
    return String(value);
  }
}

export default function OpsTasksPage() {
  const navigate = useNavigate();
  const user = getUser();
  const myEmail = user?.email || "";

  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [statusFilter, setStatusFilter] = useState("open,in_progress");
  const [assigneeFilter, setAssigneeFilter] = useState("all");
  const [overdueOnly, setOverdueOnly] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setError("");
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (assigneeFilter === "me" && myEmail) params.assignee_email = myEmail;
      if (overdueOnly) params.overdue = true;
      const resp = await api.get("/ops/tasks", { params });
      setTasks(resp.data?.items || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, assigneeFilter, overdueOnly]);

  const onUpdateStatus = async (task, newStatus) => {
    try {
      await api.patch(`/ops/tasks/${task.task_id}`, { status: newStatus });
      await load();
    } catch (e) {
      // toast yerine basit alert; istenirse sonra toast eklenir
      // eslint-disable-next-line no-alert
      alert("Görev güncellenemedi: " + apiErrorMessage(e));
    }
  };

  const rows = useMemo(() => tasks || [], [tasks]);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">Görev Takibi</h1>
          <p className="text-xs text-muted-foreground">İade ve operasyon süreçlerinin takibi</p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle className="text-sm">Filtreler</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 text-xs">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Durum</div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="h-8 w-40 text-xs">
                <SelectValue placeholder="Durum" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="open,in_progress">Açık + Devam ediyor</SelectItem>
                <SelectItem value="open">Sadece açık</SelectItem>
                <SelectItem value="in_progress">Sadece devam ediyor</SelectItem>
                <SelectItem value="done">Tamamlanan</SelectItem>
                <SelectItem value="cancelled">İptal edilen</SelectItem>
                <SelectItem value="open,in_progress,done,cancelled">Hepsi</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Atanan</div>
            <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
              <SelectTrigger className="h-8 w-32 text-xs">
                <SelectValue placeholder="Atanan" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Herkes</SelectItem>
                <SelectItem value="me">Bana atanan</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <label className="inline-flex items-center gap-2 text-xs mt-5">
            <input
              type="checkbox"
              className="h-3 w-3"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
            />
            <span>Sadece gecikmiş</span>
          </label>

          <Button size="sm" variant="outline" className="ml-auto mt-3" onClick={load}>
            <Loader2 className="h-3 w-3 mr-1" /> Yenile
          </Button>
        </CardContent>
      </Card>

      <NewTaskForm onCreated={load} />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            Görevler
            {loading && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          {error && (
            <div className="flex items-center gap-2 text-destructive text-xs">
              <AlertCircle className="h-3 w-3" />
              <span>{error}</span>
            </div>
          )}

          {!loading && !rows.length && !error && (
            <div className="text-xs text-muted-foreground">Görev bulunamadı.</div>
          )}

          {rows.length > 0 && (
            <div className="border rounded-md overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-muted text-muted-foreground font-semibold">
                    <th className="px-2 py-1.5 text-left whitespace-nowrap" style={{width:'110px'}}>Son Tarih</th>
                    <th className="px-2 py-1.5 text-left whitespace-nowrap" style={{width:'70px'}}>Öncelik</th>
                    <th className="px-2 py-1.5 text-left" style={{minWidth:'120px'}}>Başlık</th>
                    <th className="px-2 py-1.5 text-left" style={{minWidth:'100px'}}>Talep</th>
                    <th className="px-2 py-1.5 text-left" style={{minWidth:'100px'}}>Rezervasyon</th>
                    <th className="px-2 py-1.5 text-left whitespace-nowrap" style={{width:'80px'}}>Tür</th>
                    <th className="px-2 py-1.5 text-left" style={{minWidth:'110px'}}>Atanan</th>
                    <th className="px-2 py-1.5 text-left whitespace-nowrap" style={{width:'90px'}}>Durum</th>
                    <th className="px-2 py-1.5 text-left whitespace-nowrap" style={{width:'120px'}}>İşlemler</th>
                  </tr>
                </thead>
                <tbody>
              {rows.map((t) => {
                const overdue = t.is_overdue && ["open", "in_progress"].includes(t.status);
                return (
                  <tr
                    key={t.task_id}
                    className="border-t align-middle"
                  >
                    <td className="px-2 py-1.5 whitespace-nowrap">
                      <div className="flex items-center gap-1">
                        {overdue && <Clock className="h-3 w-3 text-destructive flex-shrink-0" />}
                        <span className={overdue ? "text-destructive font-semibold" : ""}>
                          {formatDateTime(t.due_at)}
                        </span>
                      </div>
                    </td>
                    <td className="px-2 py-1.5">{priorityBadge(t.priority)}</td>
                    <td className="px-2 py-1.5">
                      <div className="truncate max-w-[180px]" title={t.title}>
                        {t.title}
                      </div>
                    </td>
                    <td className="px-2 py-1.5">
                      {t.entity_id ? (
                        <Button
                          variant="link"
                          size="xs"
                          className="px-0 text-xs truncate max-w-[120px] block"
                          title={t.entity_id}
                          onClick={() => navigate(`/app/admin/finance/refunds?case=${t.entity_id}`)}
                        >
                          {t.entity_id.length > 12 ? t.entity_id.slice(0, 8) + "..." : t.entity_id}
                        </Button>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="px-2 py-1.5">
                      {t.booking_id ? (
                        <Link
                          to={`/app/ops/bookings/${t.booking_id}`}
                          className="text-blue-600 hover:underline truncate block max-w-[120px]"
                          title={t.booking_id}
                        >
                          {t.booking_id.length > 12 ? t.booking_id.slice(0, 8) + "..." : t.booking_id}
                        </Link>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="px-2 py-1.5 truncate max-w-[80px]" title={t.task_type}>{t.task_type}</td>
                    <td className="px-2 py-1.5">
                      <div className="truncate max-w-[130px]" title={t.assignee_email}>
                        {t.assignee_email || "-"}
                      </div>
                    </td>
                    <td className="px-2 py-1.5">{statusBadge(t.status)}</td>
                    <td className="px-2 py-1.5">
                      <div className="flex items-center gap-1 flex-nowrap">
                      {t.status === "open" && (
                        <Button
                          size="xs"
                          variant="outline"
                          onClick={() => onUpdateStatus(t, "in_progress")}
                        >
                          Başlat
                        </Button>
                      )}
                      {t.status === "in_progress" && (
                        <Button size="xs" onClick={() => onUpdateStatus(t, "done")}>
                          Tamamla
                        </Button>
                      )}
                      {t.status !== "cancelled" && t.status !== "done" && (
                        <Button
                          size="xs"
                          variant="ghost"
                          onClick={() => onUpdateStatus(t, "cancelled")}
                        >
                          İptal
                        </Button>
                      )}
                    </div>
                    </td>
                  </tr>
                );
              })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

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
      const body = {
        entity_type: "refund_case",
        entity_id: entityId,
        task_type: "custom",
        title,
        description: description || null,
        priority,
        due_at: dueAt || null,
        sla_hours: slaHours ? Number(slaHours) : null,
        assignee_email: assigneeEmail || null,
        tags: tags
          ? tags
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean)
          : [],
        meta: { source: "ops_tasks_page" },
      };
      await api.post("/ops/tasks", body);
      if (onCreated) onCreated();
      setTitle("");
      setDescription("");
      setDueAt("");
      setSlaHours("");
      setAssigneeEmail("");
      setTags("");
      // entityId is left as is for convenience
      // eslint-disable-next-line no-alert
      alert("Görev oluşturuldu");
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert("Görev oluşturulamadı: " + apiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Yeni Görev</CardTitle>
      </CardHeader>
      <CardContent>
    <form onSubmit={onSubmit} className="grid gap-2 md:grid-cols-3 text-xs">
      <div className="space-y-1 md:col-span-1">
        <div className="text-xs text-muted-foreground">Talep Numarası *</div>
        <Input
          className="h-8"
          value={entityId}
          onChange={(e) => setEntityId(e.target.value)}
          placeholder="case_..."
        />
      </div>
      <div className="space-y-1 md:col-span-2">
        <div className="text-xs text-muted-foreground">Başlık *</div>
        <Input
          className="h-8"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Görev adı"
        />
      </div>
      <div className="space-y-1 md:col-span-3">
        <div className="text-xs text-muted-foreground">Açıklama</div>
        <Input
          className="h-8"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Açıklama (isteğe bağlı)"
        />
      </div>
      <div className="space-y-1">
        <div className="text-xs text-muted-foreground">Öncelik</div>
        <Select value={priority} onValueChange={setPriority}>
          <SelectTrigger className="h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="low">Düşük</SelectItem>
            <SelectItem value="normal">Normal</SelectItem>
            <SelectItem value="high">Yüksek</SelectItem>
            <SelectItem value="urgent">Acil</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1">
        <div className="text-xs text-muted-foreground">Son tarih (due_at)</div>
        <Input
          className="h-8"
          type="datetime-local"
          value={dueAt}
          onChange={(e) => setDueAt(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <div className="text-xs text-muted-foreground">SLA (saat)</div>
        <Input
          className="h-8"
          type="number"
          min={0}
          value={slaHours}
          onChange={(e) => setSlaHours(e.target.value)}
        />
      </div>
      <div className="space-y-1">
        <div className="text-xs text-muted-foreground">Atanan e-posta</div>
        <Input
          className="h-8"
          value={assigneeEmail}
          onChange={(e) => setAssigneeEmail(e.target.value)}
          placeholder="ops@acenta.test"
        />
      </div>
      <div className="space-y-1 md:col-span-2">
        <div className="text-xs text-muted-foreground">Etiketler (virgülle ayırın)</div>
        <Input
          className="h-8"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="refund, followup"
        />
      </div>
      <div className="flex items-end justify-end md:col-span-3 mt-1">
        <Button type="submit" size="sm" disabled={!canSubmit}>
          {submitting && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
          Oluştur
        </Button>
      </div>
    </form>
      </CardContent>
    </Card>
  );
}
