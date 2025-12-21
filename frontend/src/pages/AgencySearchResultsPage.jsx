import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate, useLocation } from "react-router-dom";
import { Hotel, Calendar, Users, ArrowLeft, Loader2, Check } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { formatMoney } from "../lib/format";

export default function AgencySearchResultsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [searchData, setSearchData] = useState(location.state?.searchData || null);
  const [loading, setLoading] = useState(!searchData);

  const searchId = searchParams.get("search_id");

  useEffect(() => {
    console.log("[SearchResults] search_id:", searchId);
    console.log("[SearchResults] searchData from state:", searchData);
  }, [searchId, searchData]);

  function handleSelectRoom(roomTypeId, ratePlanId) {
    console.log("[SearchResults] Room selected:", { searchId, roomTypeId, ratePlanId });
    
    setLoading(true);
    
    // Navigate to booking draft
    const params = new URLSearchParams({
      search_id: searchId,
      room_type_id: roomTypeId,
      rate_plan_id: ratePlanId,
    });
    
    navigate(`/app/agency/booking/new?${params.toString()}`, {
      state: { searchData },
    });
  }

  if (loading || !searchData) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          {loading ? (
            <>
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Arama sonuçları yükleniyor...</p>
            </>
          ) : (
            <div className="text-center">
              <p className="font-semibold text-foreground">Arama sonucu bulunamadı</p>
              <p className="text-sm text-muted-foreground mt-1">
                Lütfen yeni bir arama yapın.
              </p>
              <Button onClick={() => navigate("/app/agency/hotels")} className="mt-4">
                Aramaya Dön
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  }

  const { hotel, stay, occupancy, rooms } = searchData;

  // Gross/Net/Komisyon hesapları backend'den geliyorsa burada sadece gösterim yapıyoruz.
  // Varsayım: ratePlan.price.total = acentaya satış fiyatı (gross),
  // commission_amount ve net_amount alanları varsa onları kullan; yoksa sadece total göster.

  return (
    <div className="space-y-6">
      {/* Header + Back */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-foreground">Hızlı Rezervasyon</h1>
          <p className="text-sm text-muted-foreground">
            Adım 2/3 — Fiyatları seçin (Net &amp; komisyon dahil).
          </p>
        </div>
        <Button
          onClick={() => navigate(`/app/agency/hotels/${hotel.id}`)}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Aramaya Dön
        </Button>
      </div>

      {/* Seçim Özeti Chip */}
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge variant="outline" className="flex items-center gap-1 px-3 py-1 rounded-full">
          <Hotel className="h-3 w-3" />
          <span className="font-medium">{hotel.name}</span>
        </Badge>
        <Badge variant="outline" className="flex items-center gap-1 px-3 py-1 rounded-full">
          <Calendar className="h-3 w-3" />
          <span>
            {stay.check_in} - {stay.check_out}
            {stay.nights > 0 && ` (${stay.nights} gece)`}
          </span>
        </Badge>
        <Badge variant="outline" className="flex items-center gap-1 px-3 py-1 rounded-full">
          <Users className="h-3 w-3" />
          <span>
            {occupancy.adults} yetişkin
            {occupancy.children > 0 && `, ${occupancy.children} çocuk`}
          </span>
        </Badge>
      </div>

      {/* Room Results */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Müsait Odalar ({rooms.length})</h2>

        {rooms.map((room) => (
          <Card key={room.room_type_id} className="border rounded-2xl">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-lg">{room.name}</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    Maks: {room.max_occupancy.adults} yetişkin, {room.max_occupancy.children} çocuk
                  </p>
                </div>
                <Badge variant="outline" className="text-xs">
                  {room.inventory_left} oda kaldı
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {room.rate_plans.map((ratePlan) => {
                const total = ratePlan.price.total;
                const currency = ratePlan.price.currency;
                const perNight = ratePlan.price.per_night;
                const commissionAmount = ratePlan.commission_amount ?? ratePlan.commission;
                const commissionRate = ratePlan.commission_rate ?? ratePlan.commission_percent ?? ratePlan.commission_pct;
                const netAmount = ratePlan.net_amount ?? ratePlan.net_total ?? ratePlan.net;

                return (
                  <div
                    key={ratePlan.rate_plan_id}
                    className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-4 rounded-xl border hover:bg-accent/40 transition cursor-pointer"
                    onClick={() => handleSelectRoom(room.room_type_id, ratePlan.rate_plan_id)}
                  >
                    {/* Sol: Oda / board / iptal */}
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium truncate max-w-[220px]">{ratePlan.name}</p>
                        {ratePlan.board && (
                          <Badge variant="secondary" className="text-xs">
                            {ratePlan.board}
                          </Badge>
                        )}
                        {ratePlan.cancellation !== "NON_REFUNDABLE" && (
                          <Badge className="text-xs bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30 flex items-center gap-1">
                            <Check className="h-3 w-3" /> Ücretsiz iptal
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {ratePlan.cancellation === "NON_REFUNDABLE" ? "İade edilemez" : "Esnek iptal koşulu"}
                      </p>
                    </div>

                    {/* Orta: Toplam fiyat */}
                    <div className="text-right md:text-center md:min-w-[140px]">
                      <p className="text-xs text-muted-foreground">{stay.nights} gece toplam</p>
                      <p className="text-xl font-bold text-primary">
                        {formatMoney(total, currency)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Gecelik: {formatMoney(perNight, currency)}
                      </p>
                    </div>

                    {/* Sağ: Net & Komisyon */}
                    <div className="text-right md:min-w-[170px]">
                      {typeof netAmount === "number" && (
                        <p className="text-sm font-semibold text-foreground">
                          Net: {formatMoney(netAmount, currency)}
                        </p>
                      )}
                      {typeof commissionAmount === "number" && (
                        <p className="text-xs text-muted-foreground">
                          Komisyon: {formatMoney(commissionAmount, currency)}
                          {typeof commissionRate === "number" && ` (%${commissionRate})`}
                        </p>
                      )}
                      {!netAmount && !commissionAmount && (
                        <p className="text-xs text-muted-foreground">Net/komisyon detayları onay ekranında gösterilecek.</p>
                      )}

                      <Button
                        size="sm"
                        className="mt-2 w-full md:w-auto"
                        disabled={loading}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectRoom(room.room_type_id, ratePlan.rate_plan_id);
                        }}
                      >
                        Rezervasyon Oluştur
                      </Button>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Mock Notice */}
      <Card className="border-dashed">
        <CardContent className="pt-6">
          <div className="text-center text-sm text-muted-foreground">
            <p className="font-semibold">FAZ-2.1: Mock Data</p>
            <p className="mt-1">
              Bu veriler mock&apos;tur. Faz-2.2&apos;de gerçek PMS/CM entegrasyonu eklenecek.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
