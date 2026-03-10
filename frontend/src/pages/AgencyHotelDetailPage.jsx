import React, { useEffect, useState } from "react";

function buildHotelSeo(hotel) {
  if (!hotel) {
    return {
      title: "Otel Detayı | Acenta Portal",
      description: "Seçili otel için detaylar ve fiyatlar.",
      schema: null,
    };
  }
  const name = hotel.name || "Otel";
  const city = hotel.city || "";
  const title = city ? `${name} | ${city} Otel Fırsatları` : `${name} | Otel Fırsatları`;
  const desc = city
    ? `${name} için ${city} bölgesinde avantajlı fiyatlar, güvenli rezervasyon ve bayi özel kontenjanları.`
    : `${name} için avantajlı fiyatlar, güvenli rezervasyon ve bayi özel kontenjanları.`;

  const schema = {
    "@context": "https://schema.org",
    "@type": "Hotel",
    name,
    address: city ? { addressLocality: city } : undefined,
    url: window.location.href,
  };

  return { title, description: desc, schema };
}
import { useParams, useNavigate } from "react-router-dom";
import { Hotel, CalendarDays, Users, Loader2, AlertCircle, Search } from "lucide-react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";
import { HotelInventoryCalendar } from "../components/HotelInventoryCalendar";

export default function AgencyHotelDetailPage() {
  const { hotelId } = useParams();
  const navigate = useNavigate();
  const user = getUser();

  const [hotel, setHotel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);

  const [formData, setFormData] = useState({
    check_in: "",
    check_out: "",
    adults: 2,
    children: 0,
  });
  const [formError, setFormError] = useState("");

  useEffect(() => {
    loadHotelDetail();
  }, [hotelId]);

  // SEO: dynamic title & meta description
  useEffect(() => {
    if (!hotel) return;
    const { title, description, schema } = buildHotelSeo(hotel);
    document.title = title;
    let meta = document.querySelector('meta[name="description"]');
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "description";
      document.head.appendChild(meta);
    }
    meta.content = description;

    if (schema) {
      const script = document.createElement("script");
      script.type = "application/ld+json";
      script.id = "hotel-schema-jsonld";
      script.text = JSON.stringify(schema);
      const existing = document.getElementById("hotel-schema-jsonld");
      if (existing && existing.parentNode) existing.parentNode.removeChild(existing);
      document.head.appendChild(script);
    }

    return () => {
      const el = document.getElementById("hotel-schema-jsonld");
      if (el && el.parentNode) el.parentNode.removeChild(el);
    };
  }, [hotel]);

  async function loadHotelDetail() {
    setLoading(true);
    setError("");
    try {
      // Get all linked hotels
      const resp = await api.get("/agency/hotels");
      const rawData = resp.data || {};
      const hotels = Array.isArray(rawData) ? rawData : (rawData.items || []);
      
      // Find the hotel
      const foundHotel = hotels.find((h) => h.hotel_id === hotelId || h.id === hotelId);
      
      if (!foundHotel) {
        setError("Otel bulunamadı veya erişim yetkiniz yok");
        console.warn(`[HotelDetail] Hotel ${hotelId} not found or not linked`);
        return;
      }

      console.log("[HotelDetail] Loaded:", foundHotel);
      // Normalize field names
      setHotel({
        ...foundHotel,
        name: foundHotel.hotel_name || foundHotel.name || "",
        city: foundHotel.location || foundHotel.city || "",
      });
    } catch (err) {
      console.error("[HotelDetail] Load error:", err);
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
      const searchPayload = {
        hotel_id: hotelId,
        check_in: formData.check_in,
        check_out: formData.check_out,
        occupancy: {
          adults: formData.adults,
          children: formData.children,
        },
        currency: "TRY",
      };

      console.log("[HotelDetail] Search API call:", searchPayload);

      const resp = await api.post("/agency/search", searchPayload);
      const searchData = resp.data;

      console.log("[HotelDetail] Search response:", searchData);

      // Navigate to search results with search_id
      navigate(`/app/agency/search?search_id=${searchData.search_id}`, {
        state: { searchData },
      });
    } catch (err) {
      console.error("[HotelDetail] Search error:", err);
      setFormError(apiErrorMessage(err));
    } finally {
      setSearchLoading(false);
    }
  }

  // Loading state
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

  // Error state
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

  const nights = formData.check_in && formData.check_out
    ? Math.max(0, Math.floor((new Date(formData.check_out) - new Date(formData.check_in)) / (1000 * 60 * 60 * 24)))
    : 0;

  // Main view
  return (
    <div className="space-y-6">
      {/* Hotel Info */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Hotel className="h-5 w-5" />
                {hotel.name}
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                {hotel.city}
                {hotel.city && hotel.country && " • "}
                {hotel.country}
              </p>
            </div>
            <Button onClick={() => navigate("/app/agency/hotels")} variant="outline" size="sm">
              Geri
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Inventory Calendar View */}
      <HotelInventoryCalendar hotelId={hotelId} />

      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Müsaitlik Arama
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="space-y-6">
            {/* Dates */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="check-in" className="flex items-center gap-2">
                  <CalendarDays className="h-4 w-4" />
                  Giriş Tarihi *
                </Label>
                <Input
                  id="check-in"
                  type="date"
                  value={formData.check_in}
                  onChange={(e) => setFormData({ ...formData, check_in: e.target.value })}
                  disabled={searchLoading}
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="check-out" className="flex items-center gap-2">
                  <CalendarDays className="h-4 w-4" />
                  Çıkış Tarihi *
                </Label>
                <Input
                  id="check-out"
                  type="date"
                  value={formData.check_out}
                  onChange={(e) => setFormData({ ...formData, check_out: e.target.value })}
                  disabled={searchLoading}
                  min={formData.check_in || new Date().toISOString().split('T')[0]}
                />
              </div>
            </div>

            {nights > 0 && (
              <div className="text-sm text-muted-foreground">
                {nights} gece konaklama
              </div>
            )}

            {/* Guests */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="adults" className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Yetişkin Sayısı *
                </Label>
                <Input
                  id="adults"
                  type="number"
                  min="1"
                  max="10"
                  value={formData.adults}
                  onChange={(e) => setFormData({ ...formData, adults: parseInt(e.target.value) || 1 })}
                  disabled={searchLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="children">
                  Çocuk Sayısı
                </Label>
                <Input
                  id="children"
                  type="number"
                  min="0"
                  max="10"
                  value={formData.children}
                  onChange={(e) => setFormData({ ...formData, children: parseInt(e.target.value) || 0 })}
                  disabled={searchLoading}
                />
              </div>
            </div>

            {formError && (
              <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                {formError}
              </div>
            )}

            <Button type="submit" disabled={searchLoading} className="w-full gap-2">
              {searchLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {searchLoading ? "Aranıyor..." : "Müsaitlik Ara"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
