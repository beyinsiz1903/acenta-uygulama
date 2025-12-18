import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Hotel, CalendarDays, Users, Loader2, AlertCircle, Search } from "lucide-react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { toast } from "sonner";

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

  async function loadHotelDetail() {
    setLoading(true);
    setError("");
    try {
      // Get all linked hotels
      const resp = await api.get("/agency/hotels");
      const hotels = resp.data || [];
      
      // Find the hotel
      const foundHotel = hotels.find((h) => h.id === hotelId);
      
      if (!foundHotel) {
        setError("Otel bulunamad\u0131 veya eri\u015fim yetkiniz yok");
        console.warn(`[HotelDetail] Hotel ${hotelId} not found or not linked`);
        return;
      }

      console.log("[HotelDetail] Loaded:", foundHotel);
      setHotel(foundHotel);
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
      return "Giri\u015f ve \u00e7\u0131k\u0131\u015f tarihleri gerekli";
    }

    const checkInDate = new Date(check_in);
    const checkOutDate = new Date(check_out);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    if (checkInDate < today) {
      return "Giri\u015f tarihi bug\u00fcnden \u00f6nce olamaz";
    }

    if (checkOutDate <= checkInDate) {
      return "\u00c7\u0131k\u0131\u015f tarihi giri\u015f tarihinden sonra olmal\u0131";
    }

    const nights = Math.floor((checkOutDate - checkInDate) / (1000 * 60 * 60 * 24));
    if (nights < 1) {
      return "En az 1 gece kalman\u0131z gerekli";
    }

    if (adults < 1) {
      return "En az 1 yeti\u015fkin gerekli";
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
    console.log("[HotelDetail] Search context:", {
      hotel_id: hotelId,
      hotel_name: hotel?.name,
      agency_id: user?.agency_id,
      ...formData,
    });

    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 1000));

    // Navigate to search results with context
    const params = new URLSearchParams({
      hotel_id: hotelId,
      check_in: formData.check_in,
      check_out: formData.check_out,
      adults: formData.adults.toString(),
      children: formData.children.toString(),
    });

    navigate(`/app/agency/search?${params.toString()}`);
    setSearchLoading(false);
  }

  // Loading state
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Otel bilgileri y\u00fckleniyor...</p>
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
            <p className="font-semibold text-foreground">{error || "Otel bulunamad\u0131"}</p>
          </div>
          <Button onClick={() => navigate("/app/agency/hotels")} variant="outline">
            Otellerime D\u00f6n
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
                {hotel.city && hotel.country && " \u2022 "}
                {hotel.country}
              </p>
            </div>
            <Button onClick={() => navigate("/app/agency/hotels")} variant="outline" size="sm">
              Geri
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Search Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            M\u00fcsaitlik Arama
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="space-y-6">
            {/* Dates */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="check-in" className="flex items-center gap-2">
                  <CalendarDays className="h-4 w-4" />
                  Giri\u015f Tarihi *
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
                  \u00c7\u0131k\u0131\u015f Tarihi *
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
                  Yeti\u015fkin Say\u0131s\u0131 *
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
                  \u00c7ocuk Say\u0131s\u0131
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
              {searchLoading ? "Aran\u0131yor..." : "M\u00fcsaitlik Ara"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
