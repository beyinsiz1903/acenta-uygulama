import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { CalendarDays, Users, Loader2, AlertCircle, Search, Check } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { formatMoney } from "../lib/format";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "../components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter } from "../components/ui/sheet";

// /app/agency/hotels/:hotelId/search
// Amaç: Otel seçildikten sonra tarih + pax girip /api/agency/search çağrısını yapmak
// ve /app/agency/search?search_id=... sayfasına yönlendirmek.

export default function AgencyHotelSearchPage() {
  const { hotelId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const initialHotelFromState = location.state?.hotel || null;

  const [hotel, setHotel] = useState(initialHotelFromState);
  const [loading, setLoading] = useState(!initialHotelFromState);
  const [error, setError] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);

  const [formData, setFormData] = useState({
    check_in: "",
    check_out: "",
    adults: 2,
    children: 0,
  });
  const nights = useMemo(() => {
    const { check_in, check_out } = formData;
    if (!check_in || !check_out) return null;
    const start = new Date(check_in);
    const end = new Date(check_out);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null;
    const diffMs = end.getTime() - start.getTime();
    const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : null;
  }, [formData.check_in, formData.check_out]);

  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (!initialHotelFromState) {
      loadHotel();
    }
    // eslint-disable-next-line
  }, [hotelId]);

  async function loadHotel() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/agency/hotels");
      const items = resp.data?.items || resp.data || [];
      const found = items.find((h) => h.hotel_id === hotelId);

      if (!found) {
        setError("Otel bulunamadı veya erişim yetkiniz yok");
        return;
      }

      setHotel(found);
    } catch (err) {
      console.error("[AgencyHotelSearch] Load error:", err);
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function validateForm() {
    const { check_in, check_out, adults } = formData;

    if (!check_in || !check_out) {
      return "Giriş ve çıkış tarihleri gerekli";
    }

    const checkInDate = new Date(check_in);
    const checkOutDate = new Date(check_out);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (checkInDate < today) {
      return "Giriş tarihi bugünden önce olamaz";
    }

    if (checkOutDate <= checkInDate) {
      return "Çıkış tarihi giriş tarihinden sonra olmalı";
    }

    const nights = Math.floor((checkOutDate - checkInDate) / (1000 * 60 * 60 * 24));
    if (nights < 1) {
      return "En az 1 gece kalmanız gerekli";
    }

    if (adults < 1) {
      return "En az 1 yetişkin gerekli";
    }

    return null;
  }

  async function handleSearch(e) {
    e.preventDefault();
    setFormError("");

    const validationError = validateForm();
    if (validationError) {
      setFormError(validationError);
      return;
    }

    setSearchLoading(true);
    try {
      const payload = {
        hotel_id: hotelId,
        check_in: formData.check_in,
        check_out: formData.check_out,
        occupancy: {
          adults: formData.adults,
          children: formData.children,
        },
        currency: "TRY",
      };

      console.log("[AgencyHotelSearch] Search payload:", payload);

      const resp = await api.post("/agency/search", payload);
      const searchData = resp.data;

      console.log("[AgencyHotelSearch] Search response:", searchData);

      navigate(`/app/agency/search?search_id=${searchData.search_id}`, {
        state: { searchData },
      });
    } catch (err) {
      console.error("[AgencyHotelSearch] Search error:", err);
      setFormError(apiErrorMessage(err));
    } finally {
      setSearchLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Otel bilgileri yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !hotel) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">{error || "Otel bulunamadı"}</p>
          </div>
          <Button onClick={() => navigate("/app/agency/hotels")} variant="outline">
            Otellerime Dön
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button
          onClick={() => navigate(-1)}
          variant="outline"
          className="gap-2"
        >
          Geri
        </Button>
      </div>

      <Card className="rounded-2xl border bg-card shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Rezervasyon Arama
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 space-y-1">
            <div className="text-lg font-semibold">{hotel.hotel_name || "-"}</div>
            <div className="text-sm text-muted-foreground">
              {hotel.location || "Lokasyon bilgisi yok"}
            </div>
            <div className="text-xs text-muted-foreground">
              Entegrasyon: {hotel.source === "pms" ? "PMS" : hotel.source === "local" ? "Local" : "-"}. Kanal bağlantıları otel panelinden yönetilir.
            </div>
          </div>

          <form onSubmit={handleSearch} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div className="space-y-1">
              <Label htmlFor="check_in" className="flex items-center gap-2">
                <CalendarDays className="h-4 w-4" />
                Giriş
              </Label>
              <Input
                id="check_in"
                type="date"
                value={formData.check_in}
                onChange={(e) => setFormData({ ...formData, check_in: e.target.value })}
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="check_out" className="flex items-center gap-2">
                <CalendarDays className="h-4 w-4" />
                Çıkış
              </Label>
              <Input
                id="check_out"
                type="date"
                value={formData.check_out}
                onChange={(e) => setFormData({ ...formData, check_out: e.target.value })}
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="adults" className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Yetişkin
              </Label>
              <Input
                id="adults"
                type="number"
                min={1}
                value={formData.adults}
                onChange={(e) => setFormData({ ...formData, adults: Number(e.target.value || 0) })}
              />
            </div>

            <div className="md:col-span-4 text-xs text-muted-foreground">
              Gece sayısı: <span className="font-medium">{nights ?? "-"}</span>
            </div>

            <div className="space-y-1">
              <Label htmlFor="children" className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                Çocuk
              </Label>
              <Input
                id="children"
                type="number"
                min={0}
                value={formData.children}
                onChange={(e) => setFormData({ ...formData, children: Number(e.target.value || 0) })}
              />
            </div>

            {formError && (
              <div className="md:col-span-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                {formError}
              </div>
            )}

            <div className="md:col-span-4 flex justify-end">
              <Button type="submit" disabled={searchLoading} className="gap-2">
                {searchLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {searchLoading ? "Aranıyor..." : "Müsaitlik Ara"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
