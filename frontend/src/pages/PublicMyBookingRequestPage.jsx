import React, { useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { toast } from "sonner";

function PublicMyBookingRequestPage() {
  const [bookingCode, setBookingCode] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const code = bookingCode.trim();
    const emailValue = email.trim();
    if (!code || !emailValue) {
      toast.error("Lütfen rezervasyon kodu ve e-posta adresinizi girin.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/public/my-booking/request-link", {
        booking_code: code,
        email: emailValue,
      });
      toast.success("Eğer eşleşen bir rezervasyon varsa link e-posta adresinize gönderildi.");
    } catch (err) {
      // Sadece genel hata mesajı göster; backend zaten enumeration-safe
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-md bg-background rounded-2xl shadow-lg p-6 space-y-4">
        <h1 className="text-xl font-semibold text-foreground text-center">Rezervasyonumu Görüntüle</h1>
        <p className="text-sm text-muted-foreground text-center">
          Rezervasyon kodunuz ve e-posta adresinizi girerek rezervasyon özetinizi
          görüntülemek için bir erişim linki isteyebilirsiniz.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div className="space-y-1">
            <label className="text-sm font-medium text-foreground">Rezervasyon Kodu</label>
            <Input
              value={bookingCode}
              onChange={(e) => setBookingCode(e.target.value.toUpperCase())}
              placeholder="Örn: ABC123"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-foreground">E-posta</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ornek@eposta.com"
            />
          </div>

          <Button type="submit" className="w-full mt-2" disabled={loading}>
            {loading ? "Gönderiliyor..." : "Rezervasyon Linki Gönder"}
          </Button>
        </form>

        <p className="text-xs text-muted-foreground text-center">
          Güvenlik için, doğru bilgiler girilmiş olsa bile sadece “istek alındı”
          mesajı gösterilir; rezervasyonun varlığı bu ekrandan teyit edilmez.
        </p>
      </div>
    </div>
  );
}

export default PublicMyBookingRequestPage;
