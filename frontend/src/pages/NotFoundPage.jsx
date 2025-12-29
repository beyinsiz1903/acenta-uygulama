import React from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="max-w-md text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tight text-foreground">Sayfa bulunamadı</h1>
        <p className="text-sm text-muted-foreground">
          Aradığınız sayfa mevcut değil veya taşınmış olabilir. Lütfen adresi kontrol edin
          veya ana panele geri dönün.
        </p>
        <div className="flex items-center justify-center gap-3 pt-2">
          <Button asChild>
            <Link to="/login">Giriş ekranına dön</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
