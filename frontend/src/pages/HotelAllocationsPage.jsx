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

export default function HotelAllocationsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [roomType, setRoomType] = useState("standard");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [allotment, setAllotment] = useState(2);
  const [isActive, setIsActive] = useState(true);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/hotel/allocations");
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
        allotment: Number(allotment || 0),
        is_active: isActive,
        channel: "agency_extranet",
      };
      await api.post("/hotel/allocations", payload);
      setOpen(false);
      setStartDate("");
      setEndDate("");
      setAllotment(2);
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
      await api.put(`/hotel/allocations/${item.id}`, {
        room_type: item.room_type,
        start_date: item.start_date,
        end_date: item.end_date,
        allotment: item.allotment,
        is_active: !item.is_active,
        channel: "agency_extranet",
      });
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }

  async function onDelete(item) {
    if (!window.confirm("Bu allocation kaydını silmek istiyor musunuz?")) return;

    setItems((prev) => (prev || []).filter((x) => x.id !== item.id));

    try {
      await api.delete(`/hotel/allocations/${item.id}`);
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
          <h1 className="text-2xl font-bold text-foreground">Allocation (Allotment) Yönetimi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            agency_extranet kanalı için oda allotment tanımlayın.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Yenile
          </Button>
          <Button onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Yeni Allocation
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
          Hiç allocation eklemezseniz, sistem oda satışı için varsayılan kapasiteyi kullanır. Buraya eklediğiniz
          allotment kuralları, acenta tarafında aynı anda satılabilecek oda sayısını <span className="font-semibold">sınırlar</span>.
        </p>
      </div>


      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Oda Tipi</TableHead>
              <TableHead>Tarih Aralığı</TableHead>
              <TableHead>Allotment</TableHead>
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
                  Henüz allocation kaydı yok.
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
                  <TableCell className="font-semibold">{it.allotment}</TableCell>
                  <TableCell>
                    <button className="inline-flex items-center gap-2" onClick={() => toggleActive(it)}>
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
            <DialogTitle>Yeni Allocation</DialogTitle>
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
              <Label>Allotment</Label>
              <Input
                type="number"
                min={0}
                value={allotment}
                onChange={(e) => setAllotment(e.target.value)}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Bu allotment kuralı, Syroce üzerinden satış yapan <span className="font-semibold">tüm acentalar</span> için geçerlidir.
              Belirttiğiniz sayı, aynı anda satılabilecek oda sayısını doğrudan sınırlar.
            </p>


            <div className="flex items-center justify-between rounded-xl border bg-muted/30 px-3 py-2">
              <div>
                <div className="text-sm font-medium">Aktif</div>
                <div className="text-xs text-muted-foreground">Pasif ise allotment uygulanmaz.</div>
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
