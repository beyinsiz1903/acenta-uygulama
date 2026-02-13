import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import {
  MapPin, Clock, Users, ChevronLeft, CheckCircle, XCircle,
  Star, Calendar, Phone, Mail, User, FileText, ImageIcon,
  ChevronRight, Loader2,
} from "lucide-react";

const DEFAULT_IMAGES = [
  "https://images.unsplash.com/photo-1683669446872-f956fe268beb?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODF8MHwxfHNlYXJjaHwxfHx0b3VyJTIwbGFuZHNjYXBlfGVufDB8fHx8MTc3MTAwNTY2OXww&ixlib=rb-4.1.0&q=85&w=1200",
  "https://images.unsplash.com/photo-1554366347-897a5113f6ab?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA0MTJ8MHwxfHNlYXJjaHw0fHx0cmF2ZWwlMjBkZXN0aW5hdGlvbnxlbnwwfHx8fDE3NzEwMDU2NjR8MA&ixlib=rb-4.1.0&q=85&w=1200",
  "https://images.unsplash.com/photo-1584467541268-b040f83be3fd?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA0MTJ8MHwxfHNlYXJjaHwyfHx0cmF2ZWwlMjBkZXN0aW5hdGlvbnxlbnwwfHx8fDE3NzEwMDU2NjR8MA&ixlib=rb-4.1.0&q=85&w=1200",
];

function formatPrice(price, currency) {
  if (!price) return "";
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: currency || "EUR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price);
}

function resolveImage(src) {
  if (!src) return DEFAULT_IMAGES[0];
  const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
  return src.startsWith("/api/") ? `${backendUrl}${src}` : src;
}

export default function TourDetailPage() {
  const { tourId } = useParams();
  const navigate = useNavigate();
  const [tour, setTour] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeImageIdx, setActiveImageIdx] = useState(0);
  const [activeTab, setActiveTab] = useState("details");

  // Reservation form
  const [showReservation, setShowReservation] = useState(false);
  const [resForm, setResForm] = useState({
    travel_date: "",
    adults: 2,
    children: 0,
    guest_name: "",
    guest_email: "",
    guest_phone: "",
    notes: "",
  });
  const [resLoading, setResLoading] = useState(false);
  const [resError, setResError] = useState("");
  const [resSuccess, setResSuccess] = useState(null);

  useEffect(() => {
    if (!tourId) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const res = await api.get(`/tours/${tourId}`);
        if (!cancelled) setTour(res.data);
      } catch (e) {
        if (!cancelled) setError("Tur bilgileri yuklenemedi.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [tourId]);

  const handleReservation = async (e) => {
    e.preventDefault();
    setResLoading(true);
    setResError("");
    setResSuccess(null);
    try {
      const res = await api.post(`/tours/${tourId}/reserve`, resForm);
      setResSuccess(res.data);
    } catch (e) {
      setResError(
        e?.response?.data?.message || "Rezervasyon olusturulurken hata olustu."
      );
    } finally {
      setResLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !tour) {
    return (
      <Card className="p-8 text-center">
        <p className="text-red-500 mb-3">{error || "Tur bulunamadi."}</p>
        <Button variant="outline" onClick={() => navigate("/app/tours")}>
          <ChevronLeft className="h-4 w-4 mr-1" />
          Turlara Don
        </Button>
      </Card>
    );
  }

  const allImages = tour.images && tour.images.length > 0
    ? tour.images
    : tour.cover_image
    ? [tour.cover_image]
    : DEFAULT_IMAGES;

  const participants = Math.max((resForm.adults || 0) + (resForm.children || 0), 1);
  const subtotal = (tour.base_price || 0) * participants;
  const taxes = Math.round(subtotal * 0.1 * 100) / 100;
  const total = subtotal + taxes;

  return (
    <div>
      {/* Back Button */}
      <Button
        variant="ghost"
        size="sm"
        className="mb-4"
        onClick={() => navigate("/app/tours")}
      >
        <ChevronLeft className="h-4 w-4 mr-1" />
        Turlara Don
      </Button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Image Gallery */}
          <Card className="overflow-hidden">
            <div className="relative h-72 md:h-96">
              <img
                src={resolveImage(allImages[activeImageIdx])}
                alt={tour.name}
                className="w-full h-full object-cover"
                onError={(e) => { e.target.src = DEFAULT_IMAGES[0]; }}
              />
              {allImages.length > 1 && (
                <>
                  <button
                    className="absolute left-3 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white rounded-full p-2 shadow"
                    onClick={() => setActiveImageIdx((i) => (i - 1 + allImages.length) % allImages.length)}
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <button
                    className="absolute right-3 top-1/2 -translate-y-1/2 bg-white/80 hover:bg-white rounded-full p-2 shadow"
                    onClick={() => setActiveImageIdx((i) => (i + 1) % allImages.length)}
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </>
              )}
              {tour.category && (
                <Badge className="absolute top-4 left-4 bg-white/90 text-foreground">
                  {tour.category}
                </Badge>
              )}
            </div>
            {allImages.length > 1 && (
              <div className="flex gap-2 p-3 overflow-x-auto">
                {allImages.map((img, i) => (
                  <button
                    key={i}
                    className={`flex-shrink-0 w-16 h-12 rounded-md overflow-hidden border-2 transition ${
                      i === activeImageIdx ? "border-primary" : "border-transparent opacity-60 hover:opacity-100"
                    }`}
                    onClick={() => setActiveImageIdx(i)}
                  >
                    <img
                      src={resolveImage(img)}
                      alt={`${tour.name} ${i + 1}`}
                      className="w-full h-full object-cover"
                      onError={(e) => { e.target.src = DEFAULT_IMAGES[i % DEFAULT_IMAGES.length]; }}
                    />
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Tour Info */}
          <Card className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold mb-1">{tour.name}</h1>
                <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                  {tour.destination && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-4 w-4" />
                      {tour.destination}
                    </span>
                  )}
                  {tour.departure_city && (
                    <span className="flex items-center gap-1">
                      <MapPin className="h-4 w-4 text-blue-500" />
                      Kalkis: {tour.departure_city}
                    </span>
                  )}
                  {tour.duration_days > 0 && (
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      {tour.duration_days} Gun {tour.duration_days > 1 ? `/ ${tour.duration_days - 1} Gece` : ""}
                    </span>
                  )}
                  {tour.max_participants > 0 && (
                    <span className="flex items-center gap-1">
                      <Users className="h-4 w-4" />
                      Maks. {tour.max_participants} Kisi
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-primary">
                  {formatPrice(tour.base_price, tour.currency)}
                </div>
                <p className="text-xs text-muted-foreground">kisi basi</p>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 border-b mb-4">
              {["details", "itinerary", "includes"].map((tab) => (
                <button
                  key={tab}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                    activeTab === tab
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab === "details" && "Detaylar"}
                  {tab === "itinerary" && "Program"}
                  {tab === "includes" && "Dahil / Haric"}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            {activeTab === "details" && (
              <div className="space-y-4">
                {tour.description && (
                  <div>
                    <h3 className="font-semibold mb-2">Aciklama</h3>
                    <p className="text-sm text-muted-foreground whitespace-pre-line leading-relaxed">
                      {tour.description}
                    </p>
                  </div>
                )}
                {tour.highlights && tour.highlights.length > 0 && (
                  <div>
                    <h3 className="font-semibold mb-2">One Cikan Ozellikler</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {tour.highlights.map((h, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <Star className="h-4 w-4 text-yellow-500 flex-shrink-0" />
                          <span>{h}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "itinerary" && (
              <div className="space-y-4">
                {(!tour.itinerary || tour.itinerary.length === 0) ? (
                  <p className="text-sm text-muted-foreground">Henuz program bilgisi eklenmemis.</p>
                ) : (
                  tour.itinerary.map((day, i) => (
                    <div key={i} className="flex gap-4">
                      <div className="flex flex-col items-center">
                        <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm">
                          {i + 1}
                        </div>
                        {i < tour.itinerary.length - 1 && (
                          <div className="w-0.5 flex-1 bg-border mt-1" />
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <h4 className="font-semibold text-sm">
                          {day.title || `${i + 1}. Gun`}
                        </h4>
                        {day.description && (
                          <p className="text-sm text-muted-foreground mt-1 whitespace-pre-line">
                            {day.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === "includes" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="font-semibold mb-3 text-green-600 flex items-center gap-1">
                    <CheckCircle className="h-4 w-4" />
                    Fiyata Dahil
                  </h3>
                  {(!tour.includes || tour.includes.length === 0) ? (
                    <p className="text-sm text-muted-foreground">Bilgi eklenmemis.</p>
                  ) : (
                    <ul className="space-y-2">
                      {tour.includes.map((item, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <h3 className="font-semibold mb-3 text-red-600 flex items-center gap-1">
                    <XCircle className="h-4 w-4" />
                    Fiyata Dahil Degil
                  </h3>
                  {(!tour.excludes || tour.excludes.length === 0) ? (
                    <p className="text-sm text-muted-foreground">Bilgi eklenmemis.</p>
                  ) : (
                    <ul className="space-y-2">
                      {tour.excludes.map((item, i) => (
                        <li key={i} className="flex items-center gap-2 text-sm">
                          <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Right: Reservation Sidebar */}
        <div className="space-y-6">
          <Card className="p-6 sticky top-4">
            <h2 className="text-lg font-bold mb-4">Rezervasyon Yap</h2>

            {resSuccess ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-5 w-5" />
                  <span className="font-semibold">Rezervasyon Olusturuldu!</span>
                </div>
                <div className="bg-green-50 dark:bg-green-950/20 rounded-lg p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Kod:</span>
                    <span className="font-mono font-bold">{resSuccess.reservation_code}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Toplam:</span>
                    <span className="font-bold">{formatPrice(resSuccess.total, resSuccess.currency)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Durum:</span>
                    <Badge variant="outline">Beklemede</Badge>
                  </div>
                </div>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    setResSuccess(null);
                    setResForm({ travel_date: "", adults: 2, children: 0, guest_name: "", guest_email: "", guest_phone: "", notes: "" });
                  }}
                >
                  Yeni Rezervasyon
                </Button>
              </div>
            ) : (
              <form onSubmit={handleReservation} className="space-y-4">
                {/* Date */}
                <div className="space-y-1">
                  <label className="text-sm font-medium flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    Seyahat Tarihi *
                  </label>
                  <Input
                    type="date"
                    required
                    value={resForm.travel_date}
                    onChange={(e) => setResForm({ ...resForm, travel_date: e.target.value })}
                  />
                </div>

                {/* Participants */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Yetiskin *</label>
                    <Input
                      type="number"
                      min={1}
                      max={50}
                      value={resForm.adults}
                      onChange={(e) => setResForm({ ...resForm, adults: parseInt(e.target.value) || 1 })}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-sm font-medium">Cocuk</label>
                    <Input
                      type="number"
                      min={0}
                      max={50}
                      value={resForm.children}
                      onChange={(e) => setResForm({ ...resForm, children: parseInt(e.target.value) || 0 })}
                    />
                  </div>
                </div>

                {/* Guest Info */}
                <div className="space-y-1">
                  <label className="text-sm font-medium flex items-center gap-1">
                    <User className="h-4 w-4" />
                    Misafir Adi Soyadi *
                  </label>
                  <Input
                    required
                    placeholder="Ornek: Ahmet Yilmaz"
                    value={resForm.guest_name}
                    onChange={(e) => setResForm({ ...resForm, guest_name: e.target.value })}
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium flex items-center gap-1">
                    <Mail className="h-4 w-4" />
                    E-posta
                  </label>
                  <Input
                    type="email"
                    placeholder="ornek@email.com"
                    value={resForm.guest_email}
                    onChange={(e) => setResForm({ ...resForm, guest_email: e.target.value })}
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium flex items-center gap-1">
                    <Phone className="h-4 w-4" />
                    Telefon
                  </label>
                  <Input
                    type="tel"
                    placeholder="+90 5XX XXX XX XX"
                    value={resForm.guest_phone}
                    onChange={(e) => setResForm({ ...resForm, guest_phone: e.target.value })}
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-sm font-medium flex items-center gap-1">
                    <FileText className="h-4 w-4" />
                    Notlar
                  </label>
                  <textarea
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[60px]"
                    placeholder="Ozel istekleriniz..."
                    value={resForm.notes}
                    onChange={(e) => setResForm({ ...resForm, notes: e.target.value })}
                  />
                </div>

                {/* Price Summary */}
                <div className="bg-muted/50 rounded-lg p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      {formatPrice(tour.base_price, tour.currency)} x {participants} kisi
                    </span>
                    <span>{formatPrice(subtotal, tour.currency)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Vergiler (%10)</span>
                    <span>{formatPrice(taxes, tour.currency)}</span>
                  </div>
                  <div className="flex justify-between font-bold text-base pt-2 border-t">
                    <span>Toplam</span>
                    <span className="text-primary">{formatPrice(total, tour.currency)}</span>
                  </div>
                </div>

                {resError && (
                  <p className="text-sm text-red-500">{resError}</p>
                )}

                <Button type="submit" className="w-full" disabled={resLoading}>
                  {resLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Olusturuluyor...
                    </>
                  ) : (
                    "Rezervasyon Olustur"
                  )}
                </Button>
              </form>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
