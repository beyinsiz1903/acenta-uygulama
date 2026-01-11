import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { toast } from "sonner";

function PublicMyBookingRequestPage() {
  const [pnr, setPnr] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!pnr || (!lastName && !email)) {
      toast.error("Lütfen PNR ve soyad veya e-posta girin.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/public/my-booking/request-access", {
        pnr: pnr.trim(),
        last_name: lastName.trim() || undefined,
        email: email.trim() || undefined,
      });
      toast.success("Erişim linki (varsa) kayıtlı e-posta adresinize gönderildi.");
    } catch (err) {
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
          PNR ve soyad veya e-posta adresinizi girerek rezervasyon özetinizi
          görüntülemek için tek kullanımlık bir erişim linki isteyebilirsiniz.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div className="space-y-1">
            <label className="text-sm font-medium text-foreground">PNR</label>
            <Input
              value={pnr}
              onChange={(e) => setPnr(e.target.value.toUpperCase())}
              placeholder="Örn: ABC123"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-sm font-medium text-foreground">Soyad</label>
              <Input
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Opsiyonel"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-foreground">E-posta</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Opsiyonel"
              />
            </div>
          </div>

          <Button type="submit" className="w-full mt-2" disabled={loading}>
            {loading ? "Gönderiliyor..." : "Erişim Linki Gönder"}
          </Button>
        </form>

        <p className="text-[11px] text-muted-foreground text-center">
          Güvenlik için, doğru kombinasyon girilmiş olsa bile sadece “istek alındı”
          mesajı gösterilir; rezervasyonun varlığı bu ekrandan teyit edilmez.
        </p>
      </div>
    </div>
  );
}

export default PublicMyBookingRequestPage;
