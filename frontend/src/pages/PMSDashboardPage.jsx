import React, { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Input } from "../components/ui/input";
import { toast } from "sonner";
import { LogIn, LogOut, BedDouble, Users, CalendarCheck, Plane, Building2, Search, ChevronDown, ChevronUp, Phone, Mail, DoorOpen, Hash } from "lucide-react";

const PMS_STATUS_MAP = {
  pending: { label: "Beklemede", color: "bg-slate-100 text-slate-700" },
  arrival: { label: "Giris", color: "bg-blue-100 text-blue-700" },
  in_house: { label: "Otelde", color: "bg-green-100 text-green-700" },
  departure: { label: "Cikis", color: "bg-amber-100 text-amber-700" },
  checked_out: { label: "Cikis Yapti", color: "bg-gray-100 text-gray-500" },
  no_show: { label: "Gelmedi", color: "bg-red-100 text-red-700" },
  cancelled: { label: "Iptal", color: "bg-red-100 text-red-600" },
};

function StatCard({ icon: Icon, label, value, subtitle, color = "text-primary" }) {
  return (
    <Card className="border-0 shadow-sm hover:shadow-md transition-shadow">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
            <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
          </div>
          <div className={`p-2.5 rounded-lg bg-muted/50`}>
            <Icon className="h-5 w-5 text-muted-foreground" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ReservationRow({ item, onCheckIn, onCheckOut, onViewDetail }) {
  const status = PMS_STATUS_MAP[item.pms_status] || PMS_STATUS_MAP.pending;

  return (
    <div
      className="flex items-center gap-4 p-4 border-b last:border-b-0 hover:bg-muted/30 transition-colors cursor-pointer"
      data-testid={`pms-reservation-row-${item.id}`}
      onClick={() => onViewDetail(item)}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-semibold text-sm truncate">{item.guest_name || "Misafir"}</p>
          <Badge className={`text-[10px] px-1.5 py-0 ${status.color}`} variant="outline">{status.label}</Badge>
        </div>
        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <CalendarCheck className="h-3 w-3" />
            {item.check_in} - {item.check_out}
          </span>
          {item.room_number && (
            <span className="flex items-center gap-1">
              <DoorOpen className="h-3 w-3" />
              Oda {item.room_number}
            </span>
          )}
          {item.pax && (
            <span className="flex items-center gap-1">
              <Users className="h-3 w-3" />
              {item.pax} kisi
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
          {item.hotel_name && (
            <span className="flex items-center gap-1">
              <Building2 className="h-3 w-3" />
              {item.hotel_name}
            </span>
          )}
          {item.arrival_flight?.flight_no && (
            <span className="flex items-center gap-1 text-blue-600">
              <Plane className="h-3 w-3" />
              {item.arrival_flight.flight_no}
            </span>
          )}
          {item.pnr && (
            <span className="flex items-center gap-1">
              <Hash className="h-3 w-3" />
              {item.pnr}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {(item.pms_status === "arrival" || item.pms_status === "pending" || !item.pms_status) && item.check_in <= new Date().toISOString().slice(0, 10) && (
          <Button
            size="sm"
            variant="default"
            className="h-8 text-xs"
            onClick={(e) => { e.stopPropagation(); onCheckIn(item); }}
            data-testid={`check-in-btn-${item.id}`}
          >
            <LogIn className="h-3 w-3 mr-1" /> Giris
          </Button>
        )}
        {item.pms_status === "in_house" && (
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs"
            onClick={(e) => { e.stopPropagation(); onCheckOut(item); }}
            data-testid={`check-out-btn-${item.id}`}
          >
            <LogOut className="h-3 w-3 mr-1" /> Cikis
          </Button>
        )}
      </div>
    </div>
  );
}

function ReservationDetailPanel({ item, onClose, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    guest_name: item.guest_name || "",
    guest_phone: item.guest_phone || "",
    guest_email: item.guest_email || "",
    pax: item.pax || 1,
    room_number: item.room_number || "",
    notes: item.notes || "",
    arrival_flight_no: item.arrival_flight?.flight_no || "",
    arrival_airline: item.arrival_flight?.airline || "",
    arrival_airport: item.arrival_flight?.airport || "",
    arrival_flight_datetime: item.arrival_flight?.flight_datetime || "",
    departure_flight_no: item.departure_flight?.flight_no || "",
    departure_airline: item.departure_flight?.airline || "",
    departure_airport: item.departure_flight?.airport || "",
    departure_flight_datetime: item.departure_flight?.flight_datetime || "",
    tour_operator: item.tour_info?.operator || "",
    tour_name: item.tour_info?.tour_name || "",
    tour_code: item.tour_info?.tour_code || "",
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        guest_name: form.guest_name,
        guest_phone: form.guest_phone,
        guest_email: form.guest_email,
        pax: parseInt(form.pax) || 1,
        room_number: form.room_number,
        notes: form.notes,
        arrival_flight: {
          flight_no: form.arrival_flight_no,
          airline: form.arrival_airline,
          airport: form.arrival_airport,
          flight_datetime: form.arrival_flight_datetime,
        },
        departure_flight: {
          flight_no: form.departure_flight_no,
          airline: form.departure_airline,
          airport: form.departure_airport,
          flight_datetime: form.departure_flight_datetime,
        },
        tour_info: {
          operator: form.tour_operator,
          tour_name: form.tour_name,
          tour_code: form.tour_code,
        },
      };
      await api.put(`/agency/pms/reservations/${item.id}`, payload);
      toast.success("Rezervasyon guncellendi");
      setEditing(false);
      onUpdate();
    } catch {
      toast.error("Guncelleme basarisiz");
    } finally {
      setSaving(false);
    }
  };

  const status = PMS_STATUS_MAP[item.pms_status] || PMS_STATUS_MAP.pending;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-background rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4"
        onClick={(e) => e.stopPropagation()}
        data-testid="pms-reservation-detail"
      >
        <div className="flex items-center justify-between p-5 border-b">
          <div>
            <h2 className="text-lg font-bold">{item.guest_name || "Misafir"}</h2>
            <div className="flex items-center gap-2 mt-1">
              <Badge className={`text-xs ${status.color}`}>{status.label}</Badge>
              {item.pnr && <span className="text-xs text-muted-foreground">PNR: {item.pnr}</span>}
            </div>
          </div>
          <div className="flex gap-2">
            {!editing && (
              <Button size="sm" variant="outline" onClick={() => setEditing(true)} data-testid="edit-reservation-btn">
                Duzenle
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={onClose}>Kapat</Button>
          </div>
        </div>

        <div className="p-5 space-y-5">
          {/* Stay Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Giris Tarihi</p>
              <p className="font-medium text-sm">{item.check_in}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Cikis Tarihi</p>
              <p className="font-medium text-sm">{item.check_out}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Gece</p>
              <p className="font-medium text-sm">{item.nights || "-"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Oda Tipi</p>
              <p className="font-medium text-sm">{item.room_type || "-"}</p>
            </div>
          </div>

          {/* Guest Info */}
          <div>
            <h3 className="text-sm font-semibold mb-2">Misafir Bilgileri</h3>
            {editing ? (
              <div className="grid grid-cols-2 gap-3">
                <Input value={form.guest_name} onChange={(e) => setForm({...form, guest_name: e.target.value})} placeholder="Ad Soyad" data-testid="guest-name-input" />
                <Input value={form.guest_phone} onChange={(e) => setForm({...form, guest_phone: e.target.value})} placeholder="Telefon" />
                <Input value={form.guest_email} onChange={(e) => setForm({...form, guest_email: e.target.value})} placeholder="E-posta" />
                <Input type="number" value={form.pax} onChange={(e) => setForm({...form, pax: e.target.value})} placeholder="Kisi Sayisi" />
                <Input value={form.room_number} onChange={(e) => setForm({...form, room_number: e.target.value})} placeholder="Oda No" data-testid="room-number-input" />
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="flex items-center gap-2"><Users className="h-3.5 w-3.5 text-muted-foreground" /> {form.pax} kisi</div>
                {form.guest_phone && <div className="flex items-center gap-2"><Phone className="h-3.5 w-3.5 text-muted-foreground" /> {form.guest_phone}</div>}
                {form.guest_email && <div className="flex items-center gap-2"><Mail className="h-3.5 w-3.5 text-muted-foreground" /> {form.guest_email}</div>}
                {form.room_number && <div className="flex items-center gap-2"><DoorOpen className="h-3.5 w-3.5 text-muted-foreground" /> Oda {form.room_number}</div>}
              </div>
            )}
          </div>

          {/* Flight Info */}
          <div>
            <h3 className="text-sm font-semibold mb-2 flex items-center gap-2"><Plane className="h-4 w-4" /> Ucus Bilgileri</h3>
            {editing ? (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">Gelis Ucusu</p>
                <div className="grid grid-cols-2 gap-3">
                  <Input value={form.arrival_flight_no} onChange={(e) => setForm({...form, arrival_flight_no: e.target.value})} placeholder="Ucus No (TK1234)" data-testid="arrival-flight-input" />
                  <Input value={form.arrival_airline} onChange={(e) => setForm({...form, arrival_airline: e.target.value})} placeholder="Havayolu" />
                  <Input value={form.arrival_airport} onChange={(e) => setForm({...form, arrival_airport: e.target.value})} placeholder="Havaalani" />
                  <Input type="datetime-local" value={form.arrival_flight_datetime} onChange={(e) => setForm({...form, arrival_flight_datetime: e.target.value})} />
                </div>
                <p className="text-xs text-muted-foreground mt-2">Donus Ucusu</p>
                <div className="grid grid-cols-2 gap-3">
                  <Input value={form.departure_flight_no} onChange={(e) => setForm({...form, departure_flight_no: e.target.value})} placeholder="Ucus No" data-testid="departure-flight-input" />
                  <Input value={form.departure_airline} onChange={(e) => setForm({...form, departure_airline: e.target.value})} placeholder="Havayolu" />
                  <Input value={form.departure_airport} onChange={(e) => setForm({...form, departure_airport: e.target.value})} placeholder="Havaalani" />
                  <Input type="datetime-local" value={form.departure_flight_datetime} onChange={(e) => setForm({...form, departure_flight_datetime: e.target.value})} />
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Gelis</p>
                  {form.arrival_flight_no ? (
                    <p>{form.arrival_flight_no} {form.arrival_airline && `(${form.arrival_airline})`} {form.arrival_airport && `- ${form.arrival_airport}`}</p>
                  ) : (
                    <p className="text-muted-foreground">Girilmemis</p>
                  )}
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Donus</p>
                  {form.departure_flight_no ? (
                    <p>{form.departure_flight_no} {form.departure_airline && `(${form.departure_airline})`} {form.departure_airport && `- ${form.departure_airport}`}</p>
                  ) : (
                    <p className="text-muted-foreground">Girilmemis</p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Tour Info */}
          <div>
            <h3 className="text-sm font-semibold mb-2">Tur Bilgileri</h3>
            {editing ? (
              <div className="grid grid-cols-3 gap-3">
                <Input value={form.tour_operator} onChange={(e) => setForm({...form, tour_operator: e.target.value})} placeholder="Tur Operatoru" data-testid="tour-operator-input" />
                <Input value={form.tour_name} onChange={(e) => setForm({...form, tour_name: e.target.value})} placeholder="Tur Adi" />
                <Input value={form.tour_code} onChange={(e) => setForm({...form, tour_code: e.target.value})} placeholder="Tur Kodu" />
              </div>
            ) : (
              <div className="text-sm">
                {form.tour_operator || form.tour_name ? (
                  <p>{form.tour_operator} {form.tour_name && `- ${form.tour_name}`} {form.tour_code && `(${form.tour_code})`}</p>
                ) : (
                  <p className="text-muted-foreground">Girilmemis</p>
                )}
              </div>
            )}
          </div>

          {/* Notes */}
          <div>
            <h3 className="text-sm font-semibold mb-2">Notlar</h3>
            {editing ? (
              <textarea
                className="w-full border rounded-md p-2 text-sm min-h-[80px] resize-y"
                value={form.notes}
                onChange={(e) => setForm({...form, notes: e.target.value})}
                placeholder="Not ekleyin..."
              />
            ) : (
              <p className="text-sm text-muted-foreground">{item.notes || "Not yok"}</p>
            )}
          </div>

          {/* Price Info */}
          {item.total_price > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Fiyat Bilgisi</h3>
              <p className="text-lg font-bold text-primary">
                {item.total_price?.toLocaleString("tr-TR")} {item.currency || "TRY"}
              </p>
            </div>
          )}

          {editing && (
            <div className="flex justify-end gap-2 pt-2 border-t">
              <Button variant="ghost" onClick={() => setEditing(false)}>Vazgec</Button>
              <Button onClick={handleSave} disabled={saving} data-testid="save-reservation-btn">
                {saving ? "Kaydediliyor..." : "Kaydet"}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PMSDashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [selectedHotel, setSelectedHotel] = useState("all");
  const [activeTab, setActiveTab] = useState("arrivals");
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [listLoading, setListLoading] = useState(false);
  const [selectedReservation, setSelectedReservation] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  const hotelParam = selectedHotel === "all" ? "" : `hotel_id=${selectedHotel}`;

  const loadDashboard = useCallback(async () => {
    try {
      const params = selectedHotel !== "all" ? `?hotel_id=${selectedHotel}` : "";
      const res = await api.get(`/agency/pms/dashboard${params}`);
      setDashboard(res.data);
    } catch {
      toast.error("Dashboard yuklenemedi");
    } finally {
      setLoading(false);
    }
  }, [selectedHotel]);

  const loadList = useCallback(async () => {
    setListLoading(true);
    try {
      let endpoint = `/agency/pms/${activeTab}`;
      const params = [];
      if (selectedHotel !== "all") params.push(`hotel_id=${selectedHotel}`);
      if (searchQuery) params.push(`search=${encodeURIComponent(searchQuery)}`);
      if (activeTab === "reservations" && params.length === 0) params.push("limit=100");
      const qs = params.length ? `?${params.join("&")}` : "";
      const res = await api.get(`${endpoint}${qs}`);
      setList(res.data.items || []);
    } catch {
      toast.error("Liste yuklenemedi");
    } finally {
      setListLoading(false);
    }
  }, [activeTab, selectedHotel, searchQuery]);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);
  useEffect(() => { loadList(); }, [loadList]);

  const handleCheckIn = async (item) => {
    try {
      await api.post(`/agency/pms/reservations/${item.id}/check-in`);
      toast.success(`${item.guest_name} giris yapti`);
      loadDashboard();
      loadList();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Giris basarisiz");
    }
  };

  const handleCheckOut = async (item) => {
    try {
      await api.post(`/agency/pms/reservations/${item.id}/check-out`);
      toast.success(`${item.guest_name} cikis yapti`);
      loadDashboard();
      loadList();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Cikis basarisiz");
    }
  };

  const tabs = [
    { key: "arrivals", label: "Girisler", icon: LogIn },
    { key: "in-house", label: "Otelde", icon: BedDouble },
    { key: "departures", label: "Cikislar", icon: LogOut },
    { key: "reservations", label: "Tum Rezervasyonlar", icon: CalendarCheck },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="pms-dashboard">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">PMS Paneli</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {dashboard?.date} - Otel operasyonlari
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedHotel} onValueChange={setSelectedHotel}>
            <SelectTrigger className="w-[220px]" data-testid="hotel-selector">
              <SelectValue placeholder="Otel Sec" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tum Oteller</SelectItem>
              {dashboard?.hotels?.map((h) => (
                <SelectItem key={h.id} value={h.id}>{h.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={LogIn} label="Girisler" value={dashboard?.arrivals || 0} subtitle="Bugun" color="text-blue-600" />
        <StatCard icon={BedDouble} label="Otelde" value={dashboard?.in_house || 0} subtitle="Mevcut" color="text-green-600" />
        <StatCard icon={LogOut} label="Cikislar" value={dashboard?.departures || 0} subtitle="Bugun" color="text-amber-600" />
        <StatCard
          icon={Building2}
          label="Doluluk"
          value={`${dashboard?.occupancy_rate || 0}%`}
          subtitle={`${dashboard?.occupied_rooms || 0}/${dashboard?.total_rooms || 0} oda`}
          color="text-primary"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
            data-testid={`pms-tab-${tab.key}`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Search bar for reservations tab */}
      {activeTab === "reservations" && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Misafir adi, PNR veya oda no ile ara..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            data-testid="pms-search-input"
          />
        </div>
      )}

      {/* List */}
      <Card className="border-0 shadow-sm">
        <CardContent className="p-0">
          {listLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : list.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <BedDouble className="h-10 w-10 mb-3 opacity-40" />
              <p className="text-sm font-medium">Kayit bulunamadi</p>
              <p className="text-xs mt-1">Bu tarih ve filtre icin veri yok</p>
            </div>
          ) : (
            list.map((item) => (
              <ReservationRow
                key={item.id}
                item={item}
                onCheckIn={handleCheckIn}
                onCheckOut={handleCheckOut}
                onViewDetail={setSelectedReservation}
              />
            ))
          )}
        </CardContent>
      </Card>

      {/* Reservation Detail Modal */}
      {selectedReservation && (
        <ReservationDetailPanel
          item={selectedReservation}
          onClose={() => setSelectedReservation(null)}
          onUpdate={() => {
            setSelectedReservation(null);
            loadList();
            loadDashboard();
          }}
        />
      )}
    </div>
  );
}
