import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, Calendar, Plus, RefreshCw, Trash2 } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";

import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";

const ROOM_TYPES = [
  { value: "standard", label: "Standard" },
  { value: "deluxe", label: "Deluxe" },
];

export default function HotelStopSellPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [roomType, setRoomType] = useState("standard");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [isActive, setIsActive] = useState(true);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/hotel/stop-sell");
      setItems(resp.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const sorted = useMemo(() => {
    return [...(items || [])].sort(
      (a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at)
    );
  }, [items]);

  async function onCreate() {
    setSaving(true);
    setError("");
    try {
      const payload = {
        room_type: roomType,
        start_date: startDate,
        end_date: endDate,
        reason,
        is_active: isActive,
      };
      await api.post("/hotel/stop-sell", payload);
      setOpen(false);
      setStartDate("");
      setEndDate("");
      setReason("");
      setIsActive(true);
      setRoomType("standard");
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(item) {
    try {
      await api.put(`/hotel/stop-sell/${item.id}`, {
        room_type: item.room_type,
        start_date: item.start_date,
        end_date: item.end_date,
        reason: item.reason,
        is_active: !item.is_active,
      });
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }

  async function onDelete(item) {
    if (!window.confirm("Bu stop-sell kaydını silmek istiyor musunuz?")) return;

    // Optimistic remove to avoid “silindi ama listede kaldı” hissi
    setItems((prev) => (prev || []).filter((x) => x.id !== item.id));

    try {
      await api.delete(`/hotel/stop-sell/${item.id}`);
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
      await load();
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Stop-sell Yönetimi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Seçtiğiniz oda tipini belirli tarihlerde satışa kapatın.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Yenile
          </Button>
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Yeni Stop-sell
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
          <div className="text-sm text-foreground">{error}</div>
        </div>
      ) : null}
      <div className="rounded-2xl border bg-muted/20 p-4 text-xs text-muted-foreground space-y-1">
        <div className="font-medium text-foreground">Varsayılan davranış</div>
        <p>
          Hiç stop-sell eklemezseniz, tüm odalar ve tarihler satışa açıktır. Buraya eklediğiniz kurallar,
          acenta panelindeki satışları <span className="font-semibold">engeller</span>.
        </p>
      </div>


      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Oda Tipi</TableHead>
              <TableHead>Tarih Aralığı</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Aktif</TableHead>
              <TableHead className="text-right">Aksiyon</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : sorted.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  Henüz stop-sell kaydı yok.
                </TableCell>
              </TableRow>
            ) : (
              sorted.map((it) => (
                <TableRow key={it.id} className="hover:bg-accent/40">
                  <TableCell className="font-medium">
                    {ROOM_TYPES.find((r) => r.value === it.room_type)?.label || it.room_type}
                  </TableCell>
                  <TableCell className="text-sm">
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      <span>{it.start_date} → {it.end_date}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {it.reason || "-"}
                  </TableCell>
                  <TableCell>
                    <button
                      className="inline-flex items-center gap-2"
                      onClick={() => toggleActive(it)}
                      title="Aktif/pasif"
                    >
                      <Switch checked={!!it.is_active} />
                      <Badge variant={it.is_active ? "default" : "secondary"}>
                        {it.is_active ? "Aktif" : "Pasif"}
                      </Badge>
                    </button>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="icon" onClick={() => onDelete(it)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Yeni Stop-sell</DialogTitle>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label>Oda Tipi</Label>
              <select
                className="h-10 w-full rounded-md border bg-background px-3 text-sm"
                value={roomType}
                onChange={(e) => setRoomType(e.target.value)}
              >
                {ROOM_TYPES.map((rt) => (
                  <option key={rt.value} value={rt.value}>{rt.label}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-2">
                <Label>Başlangıç</Label>
                <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              </div>
              <div className="grid gap-2">
                <Label>Bitiş</Label>
                <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              </div>
            </div>

            <div className="grid gap-2">
            <p className="text-xs text-muted-foreground">
              Bu stop-sell kuralı, Syroce üzerinden satış yapan <span className="font-semibold">tüm acentaları</span> etkiler.
              Yanlış tarih veya oda seçimi, ilgili dönemde satış kaybına yol açabilir.
            </p>

              <Label>Reason</Label>
              <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="örn: bakım" />
            </div>

            <div className="flex items-center justify-between rounded-xl border bg-muted/30 px-3 py-2">
              <div>
                <div className="text-sm font-medium">Aktif</div>
                <div className="text-xs text-muted-foreground">Kapalı/pasif yaparsanız kural uygulanmaz.</div>
              </div>
              <Switch checked={isActive} onCheckedChange={setIsActive} />
            </div>
          </div>

          <DialogFooter className="mt-2">
            <Button variant="outline" onClick={() => setOpen(false)} disabled={saving}>Vazgeç</Button>
            <Button onClick={onCreate} disabled={saving || !startDate || !endDate}>
              {saving ? "Kaydediliyor..." : "Kaydet"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
