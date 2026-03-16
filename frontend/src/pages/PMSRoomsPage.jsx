import React, { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { DoorOpen, Plus, Pencil, Trash2, Building2, Layers } from "lucide-react";

const ROOM_STATUS_MAP = {
  available: { label: "Bos", color: "bg-green-100 text-green-700" },
  occupied: { label: "Dolu", color: "bg-red-100 text-red-700" },
  cleaning: { label: "Temizlik", color: "bg-amber-100 text-amber-700" },
  maintenance: { label: "Bakim", color: "bg-slate-100 text-slate-600" },
};

const ROOM_TYPES = ["Standard", "Deluxe", "Suite", "Family", "Economy", "Superior"];

function RoomFormDialog({ room, hotels, onSave, onClose }) {
  const [form, setForm] = useState({
    hotel_id: room?.hotel_id || (hotels[0]?.id || ""),
    room_number: room?.room_number || "",
    room_type: room?.room_type || "Standard",
    floor: room?.floor ?? "",
    status: room?.status || "available",
    notes: room?.notes || "",
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.room_number.trim()) {
      toast.error("Oda numarasi gerekli");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        ...form,
        floor: form.floor !== "" ? parseInt(form.floor) : null,
      };
      if (room?.id) {
        await api.put(`/agency/pms/rooms/${room.id}`, payload);
        toast.success("Oda guncellendi");
      } else {
        await api.post("/agency/pms/rooms", payload);
        toast.success("Oda olusturuldu");
      }
      onSave();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Islem basarisiz");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-background rounded-xl shadow-2xl w-full max-w-md m-4"
        onClick={(e) => e.stopPropagation()}
        data-testid="room-form-dialog"
      >
        <div className="p-5 border-b">
          <h2 className="text-lg font-bold">{room?.id ? "Oda Duzenle" : "Yeni Oda Ekle"}</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {!room?.id && (
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Otel</label>
              <Select value={form.hotel_id} onValueChange={(v) => setForm({...form, hotel_id: v})}>
                <SelectTrigger data-testid="room-hotel-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {hotels.map((h) => (
                    <SelectItem key={h.id} value={h.id}>{h.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Oda No</label>
              <Input
                value={form.room_number}
                onChange={(e) => setForm({...form, room_number: e.target.value})}
                placeholder="101"
                data-testid="room-number-field"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Kat</label>
              <Input
                type="number"
                value={form.floor}
                onChange={(e) => setForm({...form, floor: e.target.value})}
                placeholder="1"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Oda Tipi</label>
              <Select value={form.room_type} onValueChange={(v) => setForm({...form, room_type: v})}>
                <SelectTrigger data-testid="room-type-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROOM_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Durum</label>
              <Select value={form.status} onValueChange={(v) => setForm({...form, status: v})}>
                <SelectTrigger data-testid="room-status-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(ROOM_STATUS_MAP).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1 block">Notlar</label>
            <Input
              value={form.notes}
              onChange={(e) => setForm({...form, notes: e.target.value})}
              placeholder="Opsiyonel notlar"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>Vazgec</Button>
            <Button type="submit" disabled={saving} data-testid="save-room-btn">
              {saving ? "Kaydediliyor..." : (room?.id ? "Guncelle" : "Olustur")}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function PMSRoomsPage() {
  const queryClient = useQueryClient();
  const [selectedHotel, setSelectedHotel] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [showForm, setShowForm] = useState(false);
  const [editingRoom, setEditingRoom] = useState(null);

  const { data: roomsData, isLoading: loading, refetch } = useQuery({
    queryKey: ["pms", "rooms", selectedHotel, selectedStatus],
    queryFn: async () => {
      const params = [];
      if (selectedHotel !== "all") params.push(`hotel_id=${selectedHotel}`);
      if (selectedStatus !== "all") params.push(`status=${selectedStatus}`);
      const qs = params.length ? `?${params.join("&")}` : "";
      const [roomsRes, dashRes] = await Promise.all([
        api.get(`/agency/pms/rooms${qs}`),
        api.get("/agency/pms/dashboard"),
      ]);
      return { rooms: roomsRes.data.items || [], hotels: dashRes.data.hotels || [] };
    },
    staleTime: 30_000,
    onError: () => toast.error("Veri yuklenemedi"),
  });
  const rooms = roomsData?.rooms || [];
  const hotels = roomsData?.hotels || [];

  const deleteMutation = useMutation({
    mutationFn: (roomId) => api.delete(`/agency/pms/rooms/${roomId}`),
    onSuccess: () => {
      toast.success("Oda silindi");
      queryClient.invalidateQueries({ queryKey: ["pms", "rooms"] });
    },
    onError: (err) => toast.error(err.response?.data?.detail || "Silme basarisiz"),
  });

  const handleDelete = (room) => {
    if (!window.confirm(`${room.room_number} nolu oda silinsin mi?`)) return;
    deleteMutation.mutate(room.id);
  };

  // Group rooms by floor
  const groupedByFloor = rooms.reduce((acc, room) => {
    const floor = room.floor ?? 0;
    if (!acc[floor]) acc[floor] = [];
    acc[floor].push(room);
    return acc;
  }, {});
  const floors = Object.keys(groupedByFloor).sort((a, b) => Number(a) - Number(b));

  // Stats
  const totalRooms = rooms.length;
  const availableRooms = rooms.filter(r => r.status === "available").length;
  const occupiedRooms = rooms.filter(r => r.status === "occupied").length;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="pms-rooms-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Oda Yonetimi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Toplam {totalRooms} oda - {availableRooms} bos, {occupiedRooms} dolu
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedHotel} onValueChange={setSelectedHotel}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Otel" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tum Oteller</SelectItem>
              {hotels.map((h) => (
                <SelectItem key={h.id} value={h.id}>{h.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={selectedStatus} onValueChange={setSelectedStatus}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Durum" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tumu</SelectItem>
              {Object.entries(ROOM_STATUS_MAP).map(([k, v]) => (
                <SelectItem key={k} value={k}>{v.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => { setEditingRoom(null); setShowForm(true); }} data-testid="add-room-btn">
            <Plus className="h-4 w-4 mr-1" /> Oda Ekle
          </Button>
        </div>
      </div>

      {/* Room Grid by Floor */}
      {rooms.length === 0 ? (
        <Card className="border-0 shadow-sm">
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <DoorOpen className="h-10 w-10 mb-3 opacity-40" />
            <p className="text-sm font-medium">Henuz oda eklenmemis</p>
            <p className="text-xs mt-1 mb-4">Otelin odalarini tanimlamak icin oda ekleyin</p>
            <Button size="sm" onClick={() => { setEditingRoom(null); setShowForm(true); }}>
              <Plus className="h-4 w-4 mr-1" /> Ilk Odayi Ekle
            </Button>
          </CardContent>
        </Card>
      ) : (
        floors.map((floor) => (
          <div key={floor}>
            <div className="flex items-center gap-2 mb-3">
              <Layers className="h-4 w-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                {floor === "0" ? "Zemin Kat" : `${floor}. Kat`}
              </h2>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {groupedByFloor[floor].map((room) => {
                const statusInfo = ROOM_STATUS_MAP[room.status] || ROOM_STATUS_MAP.available;
                return (
                  <Card
                    key={room.id}
                    className="border shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                    data-testid={`room-card-${room.room_number}`}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-bold text-lg">{room.room_number}</p>
                          <p className="text-xs text-muted-foreground">{room.room_type}</p>
                        </div>
                        <Badge className={`text-[10px] px-1.5 py-0 ${statusInfo.color}`} variant="outline">
                          {statusInfo.label}
                        </Badge>
                      </div>
                      {room.hotel_id && (
                        <p className="text-[10px] text-muted-foreground mt-1 truncate">
                          {hotels.find(h => h.id === room.hotel_id)?.name || ""}
                        </p>
                      )}
                      <div className="flex items-center gap-1 mt-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0"
                          onClick={() => { setEditingRoom(room); setShowForm(true); }}
                          data-testid={`edit-room-${room.room_number}`}
                        >
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0 text-destructive"
                          onClick={() => handleDelete(room)}
                          data-testid={`delete-room-${room.room_number}`}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        ))
      )}

      {/* Room Form Dialog */}
      {showForm && (
        <RoomFormDialog
          room={editingRoom}
          hotels={hotels}
          onSave={() => { setShowForm(false); setEditingRoom(null); refetch(); }}
          onClose={() => { setShowForm(false); setEditingRoom(null); }}
        />
      )}
    </div>
  );
}
