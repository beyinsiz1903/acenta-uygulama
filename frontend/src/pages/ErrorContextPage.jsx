import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Button } from "../components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { clearToken } from "../lib/api";

export default function ErrorContextPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const params = new URLSearchParams(location.search || "");
  const reason = params.get("reason") || "unknown";

  let detailMessage = "Hesap bağlamı eksik. Ajans veya otel bilgisi tanımlanmamış olabilir.";
  if (reason === "agency_id_missing") {
    detailMessage = "Acenta panellerine erişmek için hesabınıza bağlı bir ajans (agency_id) bulunmalıdır.";
  } else if (reason === "hotel_id_missing") {
    detailMessage = "Otel panellerine erişmek için hesabınıza bağlı bir otel (hotel_id) bulunmalıdır.";
  }

  const handleLogout = () => {
    try {
      clearToken();
    } catch {
      // ignore
    }
    navigate("/login", { replace: true });
  };

  const handleBackToLogin = () => {
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-background">
      <div className="w-full max-w-md">
        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>Hesap bağlamı eksik</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <p>{detailMessage}</p>
            <p>
              Lütfen sistem yöneticinizle iletişime geçerek hesabınıza doğru ajans/otel bilgisi
              tanımlandığından emin olun.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={handleBackToLogin}>
                Girişe dön
              </Button>
              <Button size="sm" onClick={handleLogout}>
                Çıkış yap
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
