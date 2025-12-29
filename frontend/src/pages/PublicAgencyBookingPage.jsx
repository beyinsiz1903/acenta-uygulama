import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { api, apiErrorMessage } from "../lib/api";
import { useToast } from "../hooks/use-toast";

import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";

function todayISO() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function addDaysISO(baseISO, days) {
  const d = new Date(`${baseISO}T00:00:00`);
  d.setDate(d.getDate() + days);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export default function PublicAgencyBookingPage() {
  const { agencySlug } = useParams();
  const { toast } = useToast();

  const [loading, setLoading] = useState(false);
  const [agencyInfo, setAgencyInfo] = useState({ name: null, logo_url: null });
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");

  const [selectedHotel, setSelectedHotel] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const [fromDate, setFromDate] = useState(todayISO());
  const [toDate, setToDate] = useState(addDaysISO(todayISO(), 2));
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);

  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [note, setNote] = useState("");

  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const resp = await api.get(`/public/agency/${agencySlug}/hotels`);
      setAgencyInfo({
        name: resp.data?.agency_name || null,
        logo_url: resp.data?.agency_logo_url || null,
      });
      setItems(resp.data?.items || []);
    } catch (err) {
      toast({
        title: "Yüklenemedi",
        description: apiErrorMessage(err),
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (agencySlug) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agencySlug]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((h) => {
      const name = (h.hotel_name || "").toLowerCase();
      const loc = (h.location || "").toLowerCase();
      return name.includes(q) || loc.includes(q);
    });
  }, [items, search]);

  function openRequest(h) {
    setSelectedHotel(h);
    setDialogOpen(true);
    setCustomerName("");
    setCustomerPhone("");
    setCustomerEmail("");
    setNote("");
  }

  async function submitRequest() {
    if (!selectedHotel) return;

    if (!customerName.trim() || customerName.trim().length < 2) {
      toast({
        title: "Eksik bilgi",
        description: "Ad Soyad gerekli.",
        variant: "destructive",
      });
      return;
    }
    if (!customerPhone.trim() || customerPhone.trim().length < 5) {
      toast({
        title: "Eksik bilgi",
        description: "Telefon gerekli.",
        variant: "destructive",
      });
      return;
    }

    const minNights = Number(selectedHotel.min_nights || 1);
    const nights = Math.round(
      (new Date(`${toDate}T00:00:00`) - new Date(`${fromDate}T00:00:00`)) / 86400000,
    );
    if (nights < minNights) {
      toast({
        title: "Gece sayısı yetersiz",
        description: `Bu otel için minimum ${minNights} gece seçmelisiniz.`,
        variant: "destructive",
      });
      return;
    }

    setSubmitting(true);
    try {
      const body = {
        hotel_id: selectedHotel.hotel_id,
        from_date: fromDate,
        to_date: toDate,
        adults: Number(adults) || 1,
        children: Number(children) || 0,
        customer_name: customerName.trim(),
        customer_phone: customerPhone.trim(),
        customer_email: customerEmail.trim() || null,
        note: note.trim() || null,
        idempotency_key: null,
      };

      const resp = await api.post(`/public/agency/${agencySlug}/booking-requests`, body);

      toast({
        title: "Talep gönderildi",
        description: `Talebiniz alındı. (ID: ${resp.data?.request_id || "-"})`,
      });
      setDialogOpen(false);
    } catch (err) {
      toast({
        title: "Gönderilemedi",
        description: apiErrorMessage(err),
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-2xl font-semibold">{agencyInfo.name || "Acenta"}</div>
            <div className="text-sm text-muted-foreground">
              Otelleri görüntüleyin ve rezervasyon talebi oluşturun.
            </div>
          </div>
          {agencyInfo.logo_url ? (
            <img src={agencyInfo.logo_url} alt="logo" className="h-10 w-auto rounded" />
          ) : null}
        </div>

        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <Label>Arama</Label>
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Otel adı veya lokasyon…"
            />
          </div>
          <Button variant="outline" onClick={() => load()} disabled={loading}>
            {loading ? "Yükleniyor…" : "Yenile"}
          </Button>
        </div>

        {loading ? (
          <div className="text-sm text-muted-foreground">Yükleniyor…</div>
        ) : filtered.length === 0 ? (
          <div className="text-sm text-muted-foreground">
            Bu acenta için public satışta otel bulunamadı.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map((h) => (
              <div key={h.hotel_id} className="border rounded-lg p-4 space-y-2 bg-card">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-medium">{h.hotel_name || "Otel"}</div>
                    <div className="text-xs text-muted-foreground">{h.location || ""}</div>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-end">
                    <Badge variant="secondary">Min {h.min_nights || 1} gece</Badge>
                    <Badge variant="outline">
                      %{Number(h.commission_percent || 0).toFixed(1)} kom
                    </Badge>
                    <Badge variant="outline">
                      %{Number(h.markup_percent || 0).toFixed(1)} mk
                    </Badge>
                  </div>
                </div>

                {h.cover_image ? (
                  <img
                    src={h.cover_image}
                    alt="cover"
                    className="w-full h-40 object-cover rounded-md border"
                  />
                ) : null}

                <Button className="w-full mt-2" onClick={() => openRequest(h)}>
                  Rezervasyon Talebi Gönder
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rezervasyon Talebi</DialogTitle>
            <DialogDescription>
              {selectedHotel?.hotel_name || ""} için bilgileri doldurun.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Giriş</Label>
                <Input
                  type="date"
                  value={fromDate}
                  min={new Date().toISOString().slice(0, 10)}
                  onChange={(e) => setFromDate(e.target.value)}
                />
              </div>
              <div>
                <Label>Çıkış</Label>
                <Input
                  type="date"
                  value={toDate}
                  min={fromDate || new Date().toISOString().slice(0, 10)}
                  onChange={(e) => setToDate(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Yetişkin</Label>
                <Input value={String(adults)} onChange={(e) => setAdults(e.target.value)} />
              </div>
              <div>
                <Label>Çocuk</Label>
                <Input value={String(children)} onChange={(e) => setChildren(e.target.value)} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Ad Soyad</Label>
                <Input value={customerName} onChange={(e) => setCustomerName(e.target.value)} />
              </div>
              <div>
                <Label>Telefon</Label>
                <Input value={customerPhone} onChange={(e) => setCustomerPhone(e.target.value)} />
              </div>
            </div>

            <div>
              <Label>E-posta (opsiyonel)</Label>
              <Input value={customerEmail} onChange={(e) => setCustomerEmail(e.target.value)} />
            </div>

            <div>
              <Label>Not (opsiyonel)</Label>
              <Input value={note} onChange={(e) => setNote(e.target.value)} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              İptal
            </Button>
            <Button onClick={submitRequest} disabled={submitting}>
              {submitting ? "Gönderiliyor…" : "Talebi Gönder"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
