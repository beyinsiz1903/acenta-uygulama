import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Hotel, Calendar, Users, ArrowLeft, Loader2 } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";

export default function AgencySearchResultsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [hotel, setHotel] = useState(null);
  const [loading, setLoading] = useState(true);

  // Extract search context from URL
  const searchContext = {
    hotel_id: searchParams.get("hotel_id"),
    check_in: searchParams.get("check_in"),
    check_out: searchParams.get("check_out"),
    adults: parseInt(searchParams.get("adults")) || 0,
    children: parseInt(searchParams.get("children")) || 0,
  };

  useEffect(() => {
    console.log("[SearchResults] Context:", searchContext);
    loadHotelInfo();
  }, []);

  async function loadHotelInfo() {
    setLoading(true);
    try {
      const resp = await api.get("/agency/hotels");
      const hotels = resp.data || [];
      const foundHotel = hotels.find((h) => h.id === searchContext.hotel_id);
      setHotel(foundHotel);
    } catch (err) {
      console.error("[SearchResults] Load error:", err);
    } finally {
      setLoading(false);
    }
  }

  const nights = searchContext.check_in && searchContext.check_out
    ? Math.floor((new Date(searchContext.check_out) - new Date(searchContext.check_in)) / (1000 * 60 * 60 * 24))
    : 0;

  return (
    <div className="space-y-6">
      {/* Back button + Search summary */}
      <div className="flex items-center justify-between">
        <Button
          onClick={() => navigate(`/app/agency/hotels/${searchContext.hotel_id}`)}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Aramaya D\u00f6n
        </Button>
      </div>

      {/* Search Context Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hotel className="h-5 w-5" />
            Arama Detaylar\u0131
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Y\u00fckleniyor...
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Hotel className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{hotel?.name || "Bilinmeyen Otel"}</span>
                <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                  Ba\u011fl\u0131 Otel
                </Badge>
              </div>

              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>
                  {searchContext.check_in} - {searchContext.check_out}
                  {nights > 0 && ` (${nights} gece)`}
                </span>
              </div>

              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Users className="h-4 w-4" />
                <span>
                  {searchContext.adults} yeti\u015fkin
                  {searchContext.children > 0 && `, ${searchContext.children} \u00e7ocuk`}
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Mock Results */}
      <Card>
        <CardHeader>
          <CardTitle>M\u00fcsait Odalar (Mock)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border-2 border-dashed bg-muted/20 p-12 text-center">
            <div className="mx-auto max-w-md space-y-3">
              <div className="text-4xl">\ud83d\uded1</div>
              <p className="font-semibold text-foreground">
                FAZ-2.1: Availability Mock
              </p>
              <p className="text-sm text-muted-foreground">
                Bu ekranda Faz-2.1'de mock oda verileri g\u00f6r\u00fcnecek.
                <br />
                Faz-2.2'de ger\u00e7ek PMS/CM entegrasyonu eklenecek.
              </p>
              <div className="pt-4">
                <Badge variant="outline" className="text-xs">
                  Context haz\u0131r \u2713 | API entegrasyonu bekleniyor
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
