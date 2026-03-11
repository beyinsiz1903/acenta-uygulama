import React, { useState } from "react";
import { Loader2, CalendarPlus, Check, X } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "./ui/dialog";
import { Badge } from "./ui/badge";
import { api, apiErrorMessage } from "../lib/api";
import { toast } from "sonner";

function formatPrice(val) {
  if (val == null) return "-";
  return new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(val);
}

export function QuickReservationDialog({ open, onOpenChange, hotelId, hotelName, roomType, dateStr, price, allotment, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    guest_name: "",
    guest_phone: "",
    guest_email: "",
    pax: 1,
    nights: 1,
    notes: "",
  });

  // Calculate check_out from dateStr + nights
  function calcCheckOut(checkIn, nights) {
    try {
      const d = new Date(checkIn);
      d.setDate(d.getDate() + nights);
      return d.toISOString().slice(0, 10);
    } catch {
      return checkIn;
    }
  }

  const checkOut = calcCheckOut(dateStr, form.nights);
  const estimatedTotal = price ? price * form.nights : 0;

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.guest_name.trim()) {
      toast.error("Misafir adı zorunludur");
      return;
    }

    setLoading(true);
    try {
      const resp = await api.post("/agency/reservations/quick", {
        hotel_id: hotelId,
        room_type: roomType,
        check_in: dateStr,
        check_out: checkOut,
        guest_name: form.guest_name.trim(),
        guest_phone: form.guest_phone || null,
        guest_email: form.guest_email || null,
        pax: form.pax,
        notes: form.notes || null,
      });

      const data = resp.data;
      toast.success(
        `Rezervasyon oluşturuldu! ${data.hotel_name} - ${data.room_type} (${data.check_in} → ${data.check_out})`,
        { duration: 5000 }
      );

      if (data.writeback_job_id) {
        toast.info("E-Tabloya yazılıyor...", { duration: 3000 });
      }

      onOpenChange(false);
      setForm({ guest_name: "", guest_phone: "", guest_email: "", pax: 1, nights: 1, notes: "" });
      if (onSuccess) onSuccess(data);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md" data-testid="quick-reservation-dialog" aria-describedby="quick-reservation-desc">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <CalendarPlus className="h-4 w-4 text-primary" />
            Hızlı Rezervasyon
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Hotel & Room Summary */}
          <div id="quick-reservation-desc" className="rounded-lg border bg-muted/30 p-3 space-y-1">
            <div className="text-sm font-medium">{hotelName}</div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline" className="text-[10px]">{roomType}</Badge>
              <span>{dateStr}</span>
              {price && <span className="font-semibold text-foreground">{formatPrice(price)} TL/gece</span>}
              {allotment != null && (
                <span className={allotment <= 3 ? "text-amber-600" : ""}>
                  {allotment} oda müsait
                </span>
              )}
            </div>
          </div>

          {/* Guest Name */}
          <div className="space-y-1.5">
            <Label htmlFor="guest_name" className="text-xs">Misafir Adı *</Label>
            <Input
              id="guest_name"
              data-testid="reservation-guest-name"
              value={form.guest_name}
              onChange={(e) => update("guest_name", e.target.value)}
              placeholder="Ad Soyad"
              required
            />
          </div>

          {/* Phone & Email */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="guest_phone" className="text-xs">Telefon</Label>
              <Input
                id="guest_phone"
                data-testid="reservation-guest-phone"
                value={form.guest_phone}
                onChange={(e) => update("guest_phone", e.target.value)}
                placeholder="+90 5xx"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="guest_email" className="text-xs">E-posta</Label>
              <Input
                id="guest_email"
                data-testid="reservation-guest-email"
                type="email"
                value={form.guest_email}
                onChange={(e) => update("guest_email", e.target.value)}
                placeholder="misafir@mail.com"
              />
            </div>
          </div>

          {/* Pax & Nights */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="pax" className="text-xs">Kişi Sayısı</Label>
              <Input
                id="pax"
                data-testid="reservation-pax"
                type="number"
                min={1}
                max={10}
                value={form.pax}
                onChange={(e) => update("pax", parseInt(e.target.value) || 1)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="nights" className="text-xs">Gece Sayısı</Label>
              <Input
                id="nights"
                data-testid="reservation-nights"
                type="number"
                min={1}
                max={30}
                value={form.nights}
                onChange={(e) => update("nights", parseInt(e.target.value) || 1)}
              />
            </div>
          </div>

          {/* Check-out & Total */}
          <div className="rounded-lg border bg-muted/20 p-3 flex items-center justify-between text-sm">
            <div>
              <span className="text-muted-foreground">Çıkış: </span>
              <span className="font-medium">{checkOut}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Toplam: </span>
              <span className="font-semibold text-foreground">{formatPrice(estimatedTotal)} TL</span>
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <Label htmlFor="notes" className="text-xs">Notlar</Label>
            <Input
              id="notes"
              data-testid="reservation-notes"
              value={form.notes}
              onChange={(e) => update("notes", e.target.value)}
              placeholder="Opsiyonel notlar..."
            />
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              <X className="h-3.5 w-3.5 mr-1" />
              İptal
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={loading}
              data-testid="reservation-submit-btn"
            >
              {loading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
              ) : (
                <Check className="h-3.5 w-3.5 mr-1" />
              )}
              Rezervasyon Oluştur
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
