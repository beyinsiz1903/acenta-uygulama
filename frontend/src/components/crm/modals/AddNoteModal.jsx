import React, { useState } from "react";
import { api, apiErrorMessage } from "../../../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../../ui/dialog";
import { Button } from "../../ui/button";
import { Input } from "../../ui/input";
import { Textarea } from "../../ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../ui/select";
import { useToast } from ""; // placeholder, adjust if toast hook exists

// NOTE: If you already use sonner/toast in project, wire it here instead of placeholder

export default function AddNoteModal({ open, onOpenChange, hotelId, agencyId, onCreated }) {
  const [type, setType] = useState("note");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [callOutcome, setCallOutcome] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e?.preventDefault?.();
    if (!hotelId || !agencyId) return;
    setLoading(true);
    try {
      await api.post("/crm/hotel-notes", {
        hotel_id: hotelId,
        agency_id: agencyId,
        type,
        subject,
        body,
        call_outcome: type === "call" && callOutcome ? callOutcome : null,
      });
      if (onCreated) onCreated();
      onOpenChange(false);
      setSubject("");
      setBody("");
      setCallOutcome("");
      setType("note");
    } catch (err) {
      alert(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit} className="space-y-4" data-testid="notes-modal">
          <DialogHeader>
            <DialogTitle>Not Ekle</DialogTitle>
          </DialogHeader>

          <div className="grid gap-2">
            <label className="text-xs text-muted-foreground">Tip</label>
            <Select value={type} onValueChange={setType} data-testid="note-type-select">
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="note">Not</SelectItem>
                <SelectItem value="call">Arama</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <label className="text-xs text-muted-foreground">Başlık</label>
            <Input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
            />
          </div>

          <div className="grid gap-2">
            <label className="text-xs text-muted-foreground">Detay</label>
            <Textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={4}
            />
          </div>

          {type === "call" && (
            <div className="grid gap-2">
              <label className="text-xs text-muted-foreground">Arama sonucu</label>
              <Input
                value={callOutcome}
                onChange={(e) => setCallOutcome(e.target.value)}
                placeholder="Ulaşıldı / Ulaşılamadı / Geri dönüş bekleniyor..."
              />
            </div>
          )}

          <DialogFooter className="mt-2 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Vazgeç
            </Button>
            <Button type="submit" disabled={loading}>
              Kaydet
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
