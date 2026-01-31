import React, { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, apiErrorMessage } from "../../lib/api";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import EmptyState from "../../components/EmptyState";

export default function StorefrontCheckoutPage() {
  const { tenantKey } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const searchId = searchParams.get("search_id") || "";
  const offerId = searchParams.get("offer_id") || "";

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  if (!tenantKey || !searchId || !offerId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <EmptyState
          title="Eksik parametre"
          description="Rezervasyon için tenant, search_id ve offer_id gereklidir. Lütfen arama adımından başlayın."
        />
      </div>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);

    if (!fullName || !email || !phone) {
      setError("Lütfen ad, e-posta ve telefon alanlarını doldurun.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        search_id: searchId,
        offer_id: offerId,
        customer: {
          full_name: fullName,
          email,
          phone,
        },
      };
      const res = await api.post("/storefront/bookings", payload, {
        headers: { "X-Tenant-Key": tenantKey },
      });
      setResult(res.data || null);
    } catch (err) {
      const resp = err?.response?.data;
      const code = resp?.error?.code;
      if (code === "SESSION_EXPIRED") {
        setError("Arama oturumu süresi doldu. Lütfen yeniden arama yapın.");
        const qp = new URLSearchParams();
        qp.set("search_id", searchId);
        qp.set("offer_id", offerId);
        navigate(`/s/${encodeURIComponent(tenantKey)}/search?${qp.toString()}`);
        return;
      } else if (code === "INVALID_OFFER") {
        setError("Bu teklif artık geçerli değil. Lütfen yeni bir teklif seçin.");
      } else {
        setError(apiErrorMessage(err));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleBackToSearch = () => {
    navigate(`/s/${encodeURIComponent(tenantKey)}`);
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <div className="w-full max-w-xl space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-base font-semibold">Rezervasyon Bilgileri</h1>
          <Button size="sm" variant="outline" className="h-8 text-xs" onClick={handleBackToSearch}>
            Yeni arama
          </Button>
        </div>

        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
            {error}
          </div>
        )}

        {!result && (
          <Card className="p-3 text-[11px]">
            <form className="space-y-3" onSubmit={handleSubmit}>
              <div className="space-y-1">
                <Label className="text-[11px]">Ad Soyad</Label>
                <Input
                  className="h-8 text-xs"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Misafir Adı Soyadı"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[11px]">E-posta</Label>
                <Input
                  type="email"
                  className="h-8 text-xs"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ornek@misafir.com"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[11px]">Telefon</Label>
                <Input
                  className="h-8 text-xs"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+90 555 000 0000"
                />
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <Button type="submit" size="sm" className="h-8 text-xs" disabled={submitting}>
                  {submitting ? "Gönderiliyor..." : "Rezervasyon Oluştur"}
                </Button>
              </div>
            </form>
          </Card>
        )}

        {result && (
          <Card className="p-3 text-[11px] space-y-2">
            <h2 className="text-sm font-semibold">Rezervasyon Taslağı Oluşturuldu</h2>
            <p className="text-[11px] text-muted-foreground">
              Rezervasyonunuz henüz taslak durumundadır. Acenta / B2B portal üzerinden bu rezervasyonu onaylayabilir,
              ödemesini alabilir veya iptal edebilirsiniz.
            </p>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Booking ID</span>
                <span className="font-mono">{result.booking_id}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Durum</span>
                <span>{result.state}</span>
              </div>
            </div>
            <div className="pt-2 text-[11px] text-muted-foreground">
              Bu ekran POC amaçlıdır; ileriki fazlarda B2C ödeme ve voucher akışları eklenecektir.
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
