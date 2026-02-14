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
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter, SheetTrigger } from "../components/ui/sheet";

// room_type title/name -> string key ("standard" gibi) üretmek için
const normalizeKey = (s) =>
  String(s ?? "")
    .toLowerCase()
    .trim()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

// room_type objesinden eşleştirme anahtarı çıkar
const roomTypeKeyOf = (rt) =>
  // varsa explicit alanı kullan (ileride backend eklenirse)
  rt?.key || rt?.room_type_key || normalizeKey(rt?.title || rt?.name || rt?.label);

// /app/agency/hotels/:hotelId/search
// Amaç: Otel seçildikten sonra tarih + pax girip /api/agency/search çağrısını yapmak
// ve SONUÇ + teklif seçimini aynı ekranda yönetmek.
// Eski /app/agency/search sayfası fallback/debug amaçlı korunur.

export default function AgencyHotelSearchPage() {
  const { hotelId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const initialHotelFromState = location.state?.hotel || null;

  const [hotel, setHotel] = useState(initialHotelFromState);
  const [loading, setLoading] = useState(!initialHotelFromState);
  const [error, setError] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);

  // Search & selection state
  const [searchResult, setSearchResult] = useState(null);
  const [searchError, setSearchError] = useState("");
  const [selected, setSelected] = useState(null); // { room_type_id, rate_plan_id }
  const [lastSearchKey, setLastSearchKey] = useState(null);
  const [cacheLikely, setCacheLikely] = useState(false);

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
  }, [formData]);

  const [selectedRoomTypeKey, setSelectedRoomTypeKey] = useState("");
  const [selectedRatePlanId, setSelectedRatePlanId] = useState("");

  const [formError, setFormError] = useState("");

  // Frontend-only filters
  const [boardFilter, setBoardFilter] = useState("all");
  const [roomFilter, setRoomFilter] = useState("all");
  const [priceSort, setPriceSort] = useState("none"); // none | asc | desc
  const [onlyAvailable, setOnlyAvailable] = useState(true);

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
    setSearchError("");

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

      // Canonical key for frontend-only cache hint (aynı kriterlerle tekrar aramada)
      const key = JSON.stringify(payload);
      setCacheLikely(Boolean(lastSearchKey && lastSearchKey === key));
      setLastSearchKey(key);

      // Reset selection & filters on new search
      setSearchResult(searchData || null);
      setSelected(null);
      setBoardFilter("all");
      setRoomFilter("all");
      setPriceSort("none");
      setOnlyAvailable(true);
    } catch (err) {
      console.error("[AgencyHotelSearch] Search error:", err);
      const msg = apiErrorMessage(err);
      setSearchError(msg || "Müsaitlik aranırken bir hata oluştu");
      // Önceki sonuçları koruyoruz; sadece error gösteriyoruz
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
            Hızlı Rezervasyon&apos;a Dön
          </Button>
        </div>
      </div>
    );
  }

  // Derived search data
  const hasSearch = !!searchResult;
  const rooms = searchResult?.rooms || [];
  const stay = searchResult?.stay;
  const occupancy = searchResult?.occupancy;
  const hotelFromSearch = searchResult?.hotel;
  const filteredRatePlansByRoomKey = useMemo(() => {
    if (!selectedRoomTypeKey) return {};

    const result = {};
    (rooms || []).forEach((room) => {
      const roomKey = roomTypeKeyOf(room);
      const basePlans = room.rate_plans || [];

      if (!roomKey) {
        result[room.room_type_id] = basePlans;
        return;
      }

      const filtered = basePlans.filter((rp) => {
        const applies = rp?.applies_to_room_types;
        if (!applies) return true; // None -> tüm odalara uygulanır
        const list = Array.isArray(applies) ? applies : [applies];
        const normalizedList = list.map((x) => normalizeKey(x));
        return normalizedList.includes(normalizeKey(roomKey));
      });

      result[room.room_type_id] = filtered;
    });

    return result;
  }, [rooms, selectedRoomTypeKey]);

  const source = searchResult?.source;

  const cacheHint = useMemo(() => {
    if (!hasSearch || !cacheLikely) return null;
    // Sadece aynı kriterlerle tekrar arama yapıldığında gösteriyoruz
    return "Aynı kriterler (cache olabilir)";
  }, [hasSearch, cacheLikely]);

  const availableBoards = useMemo(() => {
    const set = new Set();
    rooms.forEach((room) => {
      (room.rate_plans || []).forEach((rp) => {
        if (rp.board) set.add(rp.board);
      });
    });
    return Array.from(set);
  }, [rooms]);

  const availableRoomTypes = useMemo(() => {
    return rooms.map((r) => ({
      id: r.room_type_id,
      name: r.name,
      key: roomTypeKeyOf(r),
    }));
  }, [rooms]);

  const filteredRooms = useMemo(() => {
    if (!rooms.length) return [];

    let nextRooms = rooms.map((room) => {
      // FAZ-2: room_type → rate_plan filtre (applies_to_room_types)
      const filteredByKey = filteredRatePlansByRoomKey[room.room_type_id];
      let ratePlans = (filteredByKey ?? room.rate_plans) || [];

      if (boardFilter !== "all") {
        ratePlans = ratePlans.filter((rp) => rp.board === boardFilter);
      }

      if (onlyAvailable) {
        // Oda tamamen stok dışıysa yine de gösteriyoruz ama 0 olanları altta bırakabiliriz
        // Şimdilik sadece room.inventory_left > 0 ise gösterelim
        if (!room.inventory_left || room.inventory_left <= 0) {
          ratePlans = [];
        }
      }

      if (priceSort !== "none") {
        ratePlans = [...ratePlans].sort((a, b) => {
          const at = a.price?.total ?? 0;
          const bt = b.price?.total ?? 0;
          return priceSort === "asc" ? at - bt : bt - at;
        });
      }

      return {
        ...room,
        rate_plans: ratePlans,
      };
    });

    if (roomFilter !== "all") {
      nextRooms = nextRooms.filter((r) => r.room_type_id === roomFilter);
    }

    // Oda içinde hiç rate plan kalmadıysa odayı gizle
    nextRooms = nextRooms.filter((r) => (r.rate_plans || []).length > 0);

    return nextRooms;
  }, [rooms, boardFilter, roomFilter, priceSort, onlyAvailable]);

  const selectedRoom = useMemo(() => {
    if (!selected || !rooms.length) return null;
    return (
      rooms.find((r) => r.room_type_id === selected.room_type_id) || null
    );
  }, [selected, rooms]);

  const selectedRatePlan = useMemo(() => {
    if (!selectedRoom || !selected) return null;
    return (
      (selectedRoom.rate_plans || []).find((rp) => rp.rate_plan_id === selected.rate_plan_id) || null
    );
  }, [selectedRoom, selected]);

  const handleSelectOffer = (room_type_id, rate_plan_id) => {
    setSelected({ room_type_id, rate_plan_id });
  };

  const handleClearSelection = () => {
    setSelected(null);
  };

  const handleContinueToBooking = () => {
    if (!searchResult || !selected) return;
    const searchId = searchResult.search_id;
    const params = new URLSearchParams({
      search_id: searchId,
      room_type_id: selected.room_type_id,
      rate_plan_id: selected.rate_plan_id,
    });

    navigate(`/app/agency/booking/new?${params.toString()}`, {
      state: { searchData: searchResult },
    });
  };

  const hasSelection = !!(selectedRoom && selectedRatePlan);

  const renderRuleSummary = () => {
    if (!hasSelection) return null;

    const cancellationText =
      selectedRatePlan.cancellation === "NON_REFUNDABLE"
        ? "İade politikası: İade edilemez"
        : "İade politikası: Ücretsiz iptal";

    const minStayText = "Min. konaklama şartı: Bu arama için uygun";
    const stopSellText = "Stop-sell: Satışa açık";

    return (
      <div className="space-y-1 text-xs text-muted-foreground">
        <p>{cancellationText}</p>
        <p>{minStayText}</p>
        <p>{stopSellText}</p>
      </div>
    );
  };

  const renderSourceBadge = () => {
    if (!source) return null;
    const label = source === "pms" ? "PMS" : source === "local" ? "Local" : source;

    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline" className="text-2xs uppercase tracking-wide">
          Kaynak: {label}
        </Badge>
        {cacheHint && (
          <span className="rounded-full bg-muted px-2 py-0.5 text-2xs text-muted-foreground">
            {cacheHint}
          </span>
        )}
      </div>
    );
  };

  const renderSelectedOfferSummary = (compact = false) => {
    if (!hasSelection) {
      return (
        <div className="text-sm text-muted-foreground">
          Henüz bir teklif seçmediniz. Devam etmek için bir teklif seçin.
        </div>
      );
    }

    const paxTotal = (occupancy?.adults || 0) + (occupancy?.children || 0);

    const maxAdults = Number(selectedRoom?.max_occupancy?.adults ?? 0) || 0;
    const maxChildren = Number(selectedRoom?.max_occupancy?.children ?? 0) || 0;
    const maxTotal = maxAdults + maxChildren;

    const maxTotalFallback =
      maxTotal > 0
        ? maxTotal
        : (Number(selectedRoom?.max_occupancy ?? 0) || 0);

    const overCapacity = maxTotalFallback > 0 && paxTotal > maxTotalFallback;

    return (
      <div className="space-y-3">
        <div className="space-y-1 text-sm">
          <div className="font-medium">{hotelFromSearch?.name}</div>
          {stay && (
            <div className="text-muted-foreground text-xs">
              {stay.check_in} - {stay.check_out}
              {stay.nights > 0 && ` (${stay.nights} gece)`}
            </div>
          )}
          {occupancy && (
            <div className="text-muted-foreground text-xs">
              {occupancy.adults} yetişkin
              {occupancy.children > 0 && `, ${occupancy.children} çocuk`}
            </div>
          )}
        </div>

        <div className="space-y-1 text-sm">
          <div className="font-medium">{selectedRoom?.name}</div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{selectedRatePlan?.name}</span>
            {selectedRatePlan?.board && (
              <Badge variant="secondary" className="text-2xs">
                {selectedRatePlan.board}
              </Badge>
            )}
          </div>
          <div className="text-xs text-muted-foreground">
            {selectedRatePlan?.cancellation === "NON_REFUNDABLE" ? (
              "İade edilemez"
            ) : (
              <span className="inline-flex items-center gap-1">
                <Check className="h-3 w-3 text-emerald-600" />
                Ücretsiz iptal
              </span>
            )}
          </div>
        </div>

        <div className="flex items-baseline justify-between gap-2">
          <div className="flex flex-col">
            <span className="text-xs text-muted-foreground">Toplam</span>
            <span className="text-xl font-bold text-primary">
              {formatMoney(selectedRatePlan?.price?.total ?? 0, selectedRatePlan?.price?.currency || "TRY")}
            </span>
            {stay?.nights > 0 && (
              <span className="text-xs text-muted-foreground">
                Gecelik: {formatMoney(selectedRatePlan?.price?.per_night ?? 0, selectedRatePlan?.price?.currency || "TRY")}
              </span>
            )}
          </div>
        </div>

        {overCapacity && (
          <div
            className="mt-2 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-md p-2"
            data-testid="pax-max-occupancy-warning"
          >
            Seçilen oda için kişi sayısı kapasiteyi aşıyor. Kapasite: {maxTotalFallback} kişi, Pax: {paxTotal} kişi.
            Gerekirse otele not ekleyerek durumu belirtmenizi öneririz.
          </div>
        )}

        {!compact && renderRuleSummary()}
      </div>
    );
  };

  const renderDesktopSelectedPanel = () => (
    <Card className="sticky top-4 rounded-2xl border bg-card shadow-sm">
      <CardHeader>
        <CardTitle className="text-base">Seçili Teklif</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {renderSourceBadge()}
        {renderSelectedOfferSummary()}
        <div className="flex flex-col gap-2 pt-2">
          <Button
            onClick={handleContinueToBooking}
            disabled={!hasSelection}
            className="w-full gap-2"
          >
            Devam Et
          </Button>
          <Button
            onClick={handleClearSelection}
            variant="outline"
            disabled={!hasSelection}
            className="w-full"
          >
            Seçimi Temizle
          </Button>
        </div>
      </CardContent>
    </Card>
  );

  const renderMobileSelectedSheet = () => {
    if (!hasSelection) return null;

    return (
      <>
        {/* Bottom bar trigger */}
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 backdrop-blur md:hidden">
          <div className="mx-auto flex max-w-3xl items-center justify-between gap-3 px-4 py-3">
            <div className="flex flex-col">
              <span className="text-xs text-muted-foreground">Seçili Teklif</span>
              <span className="text-sm font-semibold">
                {formatMoney(selectedRatePlan?.price?.total ?? 0, selectedRatePlan?.price?.currency || "TRY")}
              </span>
            </div>
            <Sheet>
              <SheetTrigger asChild>
                <Button size="sm" className="gap-2">
                  Detay / Devam Et
                </Button>
              </SheetTrigger>
              <SheetContent side="bottom" className="max-h-[80vh] flex flex-col">
                <SheetHeader className="pb-2">
                  <SheetTitle>Seçili Teklif</SheetTitle>
                </SheetHeader>
                <div className="flex-1 overflow-y-auto py-2">
                  {renderSourceBadge()}
                  <div className="mt-3">{renderSelectedOfferSummary(true)}</div>
                  <div className="mt-4">{renderRuleSummary()}</div>
                </div>
                <SheetFooter className="mt-2 flex flex-col gap-2">
                  <Button
                    onClick={handleContinueToBooking}
                    disabled={!hasSelection}
                    className="w-full gap-2"
                  >
                    Devam Et
                  </Button>
                  <Button
                    onClick={handleClearSelection}
                    variant="outline"
                    disabled={!hasSelection}
                    className="w-full"
                  >
                    Seçimi Temizle
                  </Button>
                </SheetFooter>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="space-y-6 pb-20 md:pb-6">
      <div className="flex items-center justify-between">
        <Button
          onClick={() => navigate(-1)}
          variant="outline"
          className="gap-2"
        >
          Geri
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="space-y-6">
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
                  Entegrasyon: {hotel.source === "pms" ? "PMS" : hotel.source === "local" ? "Local" : "-"}. Kanal bağlantıları otel
                  panelinden yönetilir.
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

          {/* Search results + filters */}
          {hasSearch && (
            <Card className="rounded-2xl border bg-card shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center justify-between text-base">
                  <span>Müsait Odalar ({rooms.length})</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Filters */}
                <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                  <div className="grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-4">
                    <div className="space-y-1">
                      <Label className="text-xs">Pansiyon</Label>
                      <Select
                        value={boardFilter}
                        onValueChange={setBoardFilter}
                        disabled={!rooms.length}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Tümü" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Tümü</SelectItem>
                          {availableBoards.map((b) => (
                            <SelectItem key={b} value={b}>
                              {b}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Oda Tipi</Label>
                      <Select
                        value={selectedRoomTypeKey || "all"}
                        onValueChange={(val) => {
                          const next = val === "all" ? "" : val;
                          setSelectedRoomTypeKey(next);
                          setSelectedRatePlanId("");
                          setSelected(null);
                        }}
                        disabled={!rooms.length}
                        data-testid="room-type-select"
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Tümü" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">Tümü</SelectItem>
                          {availableRoomTypes.map((rt) => (
                            <SelectItem key={rt.id} value={rt.key}>
                              {rt.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1">
                      <Label className="text-xs">Fiyat</Label>
                      <Select
                        value={priceSort}
                        onValueChange={setPriceSort}
                        disabled={!rooms.length}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue placeholder="Sıralama" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">Varsayılan</SelectItem>
                          <SelectItem value="asc">Artan</SelectItem>
                          <SelectItem value="desc">Azalan</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-3 md:justify-end">
                    <div className="flex items-center gap-2 text-xs">
                      <Switch
                        id="only-available"
                        checked={!!onlyAvailable}
                        onCheckedChange={(v) => setOnlyAvailable(!!v)}
                      />
                      <Label htmlFor="only-available" className="text-xs">
                        Sadece müsait odalar
                      </Label>
                    </div>
                  </div>
                </div>

                {searchError && (
                  <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                    {searchError}
                  </div>
                )}

                {!filteredRooms.length && !searchError && (
                  <div className="text-sm text-muted-foreground">
                    Seçili filtrelerle uygun oda bulunamadı. Filtreleri genişletmeyi deneyin.
                  </div>
                )}

                <div className="space-y-4">
                  {filteredRooms.map((room) => (
                    <Card key={room.room_type_id} className="border-muted">
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <div>
                            <CardTitle className="text-lg">{room.name}</CardTitle>
                            <p className="text-sm text-muted-foreground mt-1">
                              Maks: {room.max_occupancy?.adults} yetişkin, {room.max_occupancy?.children} çocuk
                            </p>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {room.inventory_left} oda kaldı
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {(room.rate_plans || []).map((ratePlan) => {
                          const isSelected =
                            selected?.room_type_id === room.room_type_id &&
                            selected?.rate_plan_id === ratePlan.rate_plan_id;
                          return (
                            <div
                              key={ratePlan.rate_plan_id}
                              className="flex items-center justify-between p-4 rounded-lg border hover:bg-accent/40 transition"
                            >
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <p className="font-medium">{ratePlan.name}</p>
                                  <Badge variant="secondary" className="text-xs">
                                    {ratePlan.board}
                                  </Badge>
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                  {ratePlan.cancellation === "NON_REFUNDABLE" ? (
                                    "İade edilemez"
                                  ) : (
                                    <span className="flex items-center gap-1">
                                      <Check className="h-3 w-3 text-emerald-600" />
                                      Ücretsiz iptal
                                    </span>
                                  )}
                                </p>
                              </div>

                              <div className="text-right ml-4">
                                <p className="text-xs text-muted-foreground">
                                  {stay?.nights} gece toplam
                                </p>
                                <p className="text-lg font-bold text-primary">
                                  {formatMoney(ratePlan.price?.total ?? 0, ratePlan.price?.currency || "TRY")}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  Gecelik: {formatMoney(ratePlan.price?.per_night ?? 0, ratePlan.price?.currency || "TRY")}
                                </p>
                              </div>

                              <Button
                                onClick={() => handleSelectOffer(room.room_type_id, ratePlan.rate_plan_id)}
                                className="ml-4"
                                variant={isSelected ? "secondary" : "default"}
                              >
                                {isSelected ? "Seçili" : "Seç"}
                              </Button>
                            </div>
                          );
                        })}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Desktop selected offer panel */}
        <div className="hidden md:block">
          {renderDesktopSelectedPanel()}
        </div>
      </div>

      {/* Mobile selected offer sheet & bottom bar */}
      {renderMobileSelectedSheet()}
    </div>
  );
}
