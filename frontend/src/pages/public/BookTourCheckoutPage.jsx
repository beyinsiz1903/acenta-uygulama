import React, { useState } from "react";
import { useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import EmptyState from "../../components/EmptyState";
import { createTourPublicCheckout, apiErrorMessage } from "../../lib/publicBooking";

export default function BookTourCheckoutPage() {
  const { tourId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();

  const org = searchParams.get("org") || "";
  const partner = searchParams.get("partner") || "";
  const quoteId = searchParams.get("quote_id") || "";

  const fromState = location.state || {};
  const initialGuest = fromState.guest || {};

  const [fullName, setFullName] = useState(initialGuest.full_name || "");
  const [email, setEmail] = useState(initialGuest.email || "");
  const [phone, setPhone] = useState(initialGuest.phone || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!org || !quoteId) {
    const qpBackToSearch = new URLSearchParams();
    if (org) qpBackToSearch.set("org", org);
    if (partner) qpBackToSearch.set("partner", partner);

    return (
      <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
        <Card className="w-full max-w-lg p-4 space-y-3">
          <EmptyState
            title={"Teklif bilgisi bulunamadı"}
            description={"Bağlantı eksik veya hatalı. Lütfen tur sayfasından yeniden teklif alın."}
            action={
              <div className="flex justify-center">
                <Button
                  size="sm"
                  onClick={() => {
                    const qs = qpBackToSearch.toString();
                    navigate(qs ? `/book?${qs}` : "/book");
                  }}
                >
                  Geri dön
                </Button>
              </div>
            }
          />
        </Card>
      </div>
    );
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!org || !quoteId) return;

    setLoading(true);
    setError("");

    try {
      const body = {
        org,
        quote_id: quoteId,
        guest: {
          full_name: fullName,
          email,
          phone,
        },
      };

      const res = await createTourPublicCheckout(body);
      if (!res.ok) {
        setError(res.reason || "Rezervasyon tamamlanamadı. Lütfen tekrar deneyin.");
        return;
      }

      const qp = new URLSearchParams();
      qp.set("booking_code", res.booking_code || "");
      qp.set("org", org);
      if (partner) qp.set("partner", partner);

      navigate(`/book/complete?${qp.toString()}`);
    } catch (e2) {
      const msg = apiErrorMessage(e2.raw || e2) || e2.message || "Rezervasyon tamamlanamadı.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <Card className="w-full max-w-lg p-4 space-y-3">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Tur Checkout</h1>
          <p className="text-xs text-muted-foreground">
            Misafir bilgilerinizi doldurun, rezervasyonu tamamlayalım. Ödeme bu fazda offline/manuel kabul edilir.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div className="space-y-1">
            <label className="font-medium">Ad Soyad</label>
            <input
              type="text"
              className="w-full rounded-md border px-2 py-1"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1">
            <label className="font-medium">E-posta</label>
            <input
              type="email"
              className="w-full rounded-md border px-2 py-1"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1">
            <label className="font-medium">Telefon</label>
            <input
              type="tel"
              className="w-full rounded-md border px-2 py-1"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" size="sm" onClick={() => navigate(-1)}>
              Geri
            </Button>
            <Button type="submit" size="sm" disabled={!org || !quoteId || loading}>
              {loading ? "Rezervasyon oluşturuluyor..." : "Rezervasyonu tamamla"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
