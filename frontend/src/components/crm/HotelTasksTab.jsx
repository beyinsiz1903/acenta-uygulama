import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../../lib/api";
import { toast } from "sonner";

import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Label } from "../ui/label";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

import AddTaskModal from "./modals/AddTaskModal";

const STATUS_LABEL = {
  open: "Açık",
  done: "Tamam",
};

const STATUS_BADGE_CLASS = {
  open: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  done: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
};

function fmtDate(isoOrDateOnly) {
  if (!isoOrDateOnly) return "-";
  // due_date bazen "YYYY-MM-DD" olabilir
  const d = new Date(isoOrDateOnly);
  if (Number.isNaN(d.getTime())) return String(isoOrDateOnly);
  return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export default function HotelTasksTab({ hotelId, agencyId, user }) {
  const [status, setStatus] = useState("open"); // open | done | all
  const [assignee, setAssignee] = useState("me"); // me | all
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);

  const [openModal, setOpenModal] = useState(false);

  const isAgent = useMemo(() => {
    const roles = new Set(user?.roles || []);
    return roles.has("agency_agent");
  }, [user]);

  const canLoad = !!hotelId && !!agencyId;

  const load = useCallback(async () => {
    if (!canLoad) return;

    try {
      setLoading(true);

      const params = {
        hotel_id: hotelId,
        agency_id: agencyId,
      };

      if (status && status !== "all") params.status = status;
      if (assignee === "me") params.assignee = "me"; // backend: assignee=me

      const res = await api.get("/crm/hotel-tasks", { params });
      const data = res.data;
      const list = Array.isArray(data) ? data : (data?.tasks || []);
      setItems(list);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [canLoad, hotelId, agencyId, status, assignee]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleStatus = async (task) => {
    const taskId = task?._id || task?.id;
    if (!taskId) return;

    const next = (task.status || "open") === "done" ? "open" : "done";

    try {
      setUpdatingId(taskId);

      await api.patch(`/crm/hotel-tasks/${taskId}/status`, { status: next });

      // Optimistic UI
      setItems((prev) =>
        prev.map((x) =>
          (x._id || x.id) === taskId
            ? {
                ...x,
                status: next,
                completed_at: next === "done" ? new Date().toISOString() : null,
                updated_at: new Date().toISOString(),
              }
            : x
        )
      );

      toast.success(next === "done" ? "Görev tamamlandı" : "Görev tekrar açıldı");
    } catch (err) {
      // 403 gibi RBAC hatalarında net mesaj
      toast.error(apiErrorMessage(err));
    } finally {
      setUpdatingId(null);
    }
  };

  if (!agencyId) {
    return (
      <div data-testid="crm-tasks-tab" className="text-xs text-muted-foreground">
        Agency kimliği bulunamadı.
      </div>
    );
  }

  if (!hotelId) {
    return (
      <div data-testid="crm-tasks-tab" className="text-xs text-muted-foreground">
        Hotel bulunamadı.
      </div>
    );
  }

  return (
    <div data-testid="crm-tasks-tab" className="space-y-3">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center justify-between">
            <span>Görevler</span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={load}
                disabled={loading}
              >
                {loading ? "Yükleniyor..." : "Yenile"}
              </Button>
              <Button
                size="sm"
                className="h-8 text-xs"
                data-testid="tasks-add-button"
                onClick={() => setOpenModal(true)}
              >
                Görev Ekle
              </Button>
            </div>
          </CardTitle>
        </CardHeader>

        <CardContent className="pt-0">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Durum</Label>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger className="h-9 text-xs" data-testid="tasks-status-select">
                  <SelectValue placeholder="Durum seç" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="open">Açık</SelectItem>
                  <SelectItem value="done">Tamam</SelectItem>
                  <SelectItem value="all">Tümü</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs">Atanan</Label>
              <Select value={assignee} onValueChange={setAssignee}>
                <SelectTrigger className="h-9 text-xs" data-testid="tasks-assignee-select">
                  <SelectValue placeholder="Atanan seç" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="me">Bana Atananlar</SelectItem>
                  <SelectItem value="all">Tümü</SelectItem>
                </SelectContent>
              </Select>
              {isAgent && assignee === "all" ? (
                <div className="text-[10px] text-slate-500 mt-1">
                  Agent rolünde "Tümü" görünse bile RBAC gereği sadece scope içi döner.
                </div>
              ) : null}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          {loading ? (
            <div className="text-xs text-slate-500">Yükleniyor...</div>
          ) : items?.length ? (
            <div className="space-y-2">
              {items.map((task) => {
                const taskId = task?._id || task?.id;
                const s = task?.status || "open";
                const isUpdating = updatingId === taskId;

                return (
                  <div
                    key={taskId}
                    data-testid="task-list-row"
                    className="rounded-md border border-slate-200 p-3 flex items-start justify-between gap-3"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <div className="text-sm font-medium truncate">
                          {task?.title || "-"}
                        </div>

                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] border ${
                            STATUS_BADGE_CLASS[s] ||
                            "bg-slate-500/10 text-slate-400 border-slate-500/30"
                          }`}
                        >
                          {STATUS_LABEL[s] || s}
                        </span>

                        {task?.assignee_user_id && user?.id && String(task.assignee_user_id) === String(user.id) ? (
                          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] border bg-slate-500/10 text-slate-600 border-slate-300">
                            Bana
                          </span>
                        ) : null}
                      </div>

                      {task?.description ? (
                        <div className="text-xs text-slate-600 mt-1 whitespace-pre-wrap">
                          {task.description}
                        </div>
                      ) : null}

                      <div className="text-[11px] text-slate-500 mt-2 flex flex-wrap gap-x-4 gap-y-1">
                        <div>Vade: {fmtDate(task?.due_date)}</div>
                        {task?.updated_at ? <div>Güncelleme: {fmtDate(task.updated_at)}</div> : null}
                      </div>
                    </div>

                    <div className="shrink-0 flex flex-col items-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 text-xs"
                        data-testid="task-status-toggle"
                        onClick={() => toggleStatus(task)}
                        disabled={isUpdating}
                        title="Durum değiştir"
                      >
                        {isUpdating ? "..." : s === "done" ? "Tekrar Aç" : "Tamamla"}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-xs text-slate-500">Bu otel için görev bulunmuyor.</div>
          )}
        </CardContent>
      </Card>

      <AddTaskModal
        open={openModal}
        onOpenChange={setOpenModal}
        hotelId={hotelId}
        agencyId={agencyId}
        user={user}
        onCreated={load}
      />
    </div>
  );
}
