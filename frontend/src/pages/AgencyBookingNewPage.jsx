import React from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { ShoppingCart, ArrowLeft, Calendar } from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";

export default function AgencyBookingNewPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const context = {
    search_id: searchParams.get("search_id"),
    room_type_id: searchParams.get("room_type_id"),
    rate_plan_id: searchParams.get("rate_plan_id"),
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button
          onClick={() => navigate(-1)}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Geri
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" />
            Rezervasyon Oluştur
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border-2 border-dashed bg-muted/20 p-12 text-center">
            <div className="mx-auto max-w-md space-y-4">
              <div className="text-4xl">📝</div>
              <p className="font-semibold text-foreground text-lg">
                FAZ-3: Rezervasyon Akışı
              </p>
              <p className="text-sm text-muted-foreground">
                Bu ekranda Faz-3'te rezervasyon formu görünecek:
              </p>
              <ul className="text-sm text-muted-foreground text-left space-y-2 max-w-xs mx-auto">
                <li>• Misafir bilgileri</li>
                <li>• Ödeme seçenekleri</li>
                <li>• Özel istekler</li>
                <li>• Onay & voucher</li>
              </ul>

              <div className="pt-4 space-y-2">
                <Badge variant="outline" className="text-xs">
                  Context hazır ✓
                </Badge>
                <div className="text-xs text-muted-foreground font-mono bg-muted/50 p-3 rounded">
                  search_id: {context.search_id}
                  <br />
                  room_type: {context.room_type_id}
                  <br />
                  rate_plan: {context.rate_plan_id}
                </div>
              </div>

              <Button onClick={() => navigate("/app/agency/hotels")} className="mt-4">
                <Calendar className="h-4 w-4 mr-2" />
                Yeni Arama Yap
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
