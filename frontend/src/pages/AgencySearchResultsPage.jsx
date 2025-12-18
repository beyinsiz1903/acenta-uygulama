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
    
    // Navigate to booking placeholder
    const params = new URLSearchParams({
      search_id: searchId,
      room_type_id: roomTypeId,
      rate_plan_id: ratePlanId,
    });
    
    navigate(`/app/agency/booking/new?${params.toString()}`);
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
                Otellerime Dön
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  }

  const { hotel, stay, occupancy, rooms } = searchData;

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div className="flex items-center justify-between">
        <Button
          onClick={() => navigate(`/app/agency/hotels/${hotel.id}`)}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Aramaya Dön
        </Button>
      </div>

      {/* Search Context Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hotel className="h-5 w-5" />
            Arama Detayları
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Hotel className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">{hotel.name}</span>
              <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                Bağlı Otel
              </Badge>
            </div>

            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>
                {stay.check_in} - {stay.check_out}
                {stay.nights > 0 && ` (${stay.nights} gece)`}
              </span>
            </div>

            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Users className="h-4 w-4" />
              <span>
                {occupancy.adults} yetişkin
                {occupancy.children > 0 && `, ${occupancy.children} çocuk`}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Room Results */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Müsait Odalar ({rooms.length})</h2>

        {rooms.map((room) => (
          <Card key={room.room_type_id}>
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
              {room.rate_plans.map((ratePlan) => (
                <div
                  key={ratePlan.rate_plan_id}
                  className="flex items-center justify-between p-4 rounded-lg border hover:bg-accent/50 transition"
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
                      {stay.nights} gece toplam
                    </p>
                    <p className="text-lg font-bold text-primary">
                      {formatMoney(ratePlan.price.total, ratePlan.price.currency)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Gecelik: {formatMoney(ratePlan.price.per_night, ratePlan.price.currency)}
                    </p>
                  </div>

                  <Button
                    onClick={() => handleSelectRoom(room.room_type_id, ratePlan.rate_plan_id)}
                    className="ml-4"
                    disabled={loading}
                  >
                    Seç
                  </Button>
                </div>
              ))}
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
