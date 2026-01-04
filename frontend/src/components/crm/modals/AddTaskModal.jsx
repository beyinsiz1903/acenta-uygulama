import React, { useMemo, useState } from "react";
import { api, apiErrorMessage } from "../../../lib/api";
import { toast } from "sonner";

import { Button } from "../../ui/button";
import { Input } from "../../ui/input";
import { Label } from "../../ui/label";
import { Textarea } from "../../ui/textarea";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../../ui/dialog";

export default function AddTaskModal({
  open,
  onOpenChange,
  hotelId,
  agencyId,
  user,
  onCreated,
}) {
  const isAgent = useMemo(() => {
    const roles = new Set(user?.roles || []);
    return roles.has("agency_agent");
  }, [user]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState(""); // YYYY-MM-DD
  const [assignToMe, setAssignToMe] = useState(true); // admin için basit seçenek
  const [saving, setSaving] = useState(false);

  const canSubmit = title.trim().length > 0 && !!hotelId && !!agencyId && !saving;

  const reset = () => {
    setTitle("");
    setDescription("");
    setDueDate("");
    setAssignToMe(true);
  };

  const handleClose = (nextOpen) => {
    if (!nextOpen) reset();
    onOpenChange?.(nextOpen);
  };

  const submit = async () => {
    if (!canSubmit) return;

    try {
      setSaving(true);

      const payload = {
        hotel_id: hotelId,
        agency_id: agencyId,
        title: title.trim(),
        description: description.trim() || null,
        due_date: dueDate ? dueDate : null,
      };

      // agency_agent için backend default self (assignee) yapıyor; göndermiyoruz
      // agency_admin için "Bana ata" seçiliyse assignee gönder
      if (!isAgent && assignToMe && user?.id) {
        payload.assignee_user_id = user.id;
      }

      await api.post("/crm/hotel-tasks", payload);

      toast.success("Görev oluşturuldu");
      handleClose(false);
      onCreated?.();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent data-testid="tasks-modal" className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-sm">Görev Ekle</DialogTitle>
          <DialogDescription className="text-xs">
            Bu otele ait takip görevini oluşturun.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1">
            <Label className="text-xs">Başlık</Label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Örn: Yarın 11:00 arama"
              className="h-9 text-sm"
            />
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Açıklama</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Örn: Karar verici: işletme sahibi. İtiraz: fiyat."
              className="min-h-[80px] text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Bitiş Tarihi</Label>
              <Input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="h-9 text-sm"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs">&nbsp;</Label>
              {!isAgent ? (
                <div className="flex items-center gap-2 h-9">
                  <input
                    id="assign-to-me"
                    type="checkbox"
                    checked={assignToMe}
                    onChange={(e) => setAssignToMe(e.target.checked)}
                    className="rounded border-slate-600"
                  />
                  <label htmlFor="assign-to-me" className="text-xs text-slate-600">
                    Bana ata
                  </label>
                </div>
              ) : (
                <div className="text-xs text-slate-500 h-9 flex items-center">
                  Bu görev size atanacak
                </div>
              )}
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleClose(false)}
            disabled={saving}
          >
            Vazgeç
          </Button>
          <Button size="sm" onClick={submit} disabled={!canSubmit}>
            {saving ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
