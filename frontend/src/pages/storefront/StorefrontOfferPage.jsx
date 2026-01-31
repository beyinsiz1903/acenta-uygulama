import React, { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, apiErrorMessage } from "../../lib/api";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import EmptyState from "../../components/EmptyState";

export default function StorefrontOfferPage() {
  const { tenantKey, offerId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const searchId = searchParams.get("search_id") || "";

  const [offer, setOffer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!tenantKey || !offerId || !searchId) return;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/storefront/offers/${encodeURIComponent(offerId)}?search_id=${encodeURIComponent(searchId)}`, {
          headers: { "X-Tenant-Key": tenantKey },
        });
        setOffer(res.data || null);
      } catch (err) {
        const resp = err?.response?.data;
        const code = resp?.error?.code;
        if (code === "SESSION_EXPIRED") {
          setError("Arama oturumu süresi doldu, lütfen yeniden arama yapın.");
        } else if (code === "OFFER_NOT_FOUND") {
          setError("Bu teklif oturumda bulunamadı. Lütfen yeniden arayın.");
        } else {
          setError(apiErrorMessage(err));
        }
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [tenantKey, offerId, searchId]);

  const handleBack = () => {
    navigate(`/s/${encodeURIComponent(tenantKey)}`);
  };

  const handleCheckout = () => {
    if (!tenantKey || !offerId || !searchId) return;
    const qp = new URLSearchParams();
    qp.set("search_id", searchId);
    qp.set("offer_id", offerId);
    navigate(`/s/${encodeURIComponent(tenantKey)}/checkout?${qp.toString()}`);
  };

  if (!tenantKey || !offerId || !searchId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <EmptyState
          title="Eksik parametre"
          description="Teklifi görüntülemek için tenant, search_id ve offer_id gerekli."
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <div className="w-full max-w-xl space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-base font-semibold">Teklif Detayı</h1>
          <Button size="sm" variant="outline" className="h-8 text-xs" onClick={handleBack}>
            Yeni arama
          </Button>
        </div>

        {loading && <p className="text-[11px] text-muted-foreground">Teklif yükleniyor...</p>}

        {error && !loading && (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
            {error}
          </div>
        )}

        {!loading && !error && !offer && (
          <EmptyState
            title="Teklif bulunamadı"
            description="Bu teklif şu an için görüntülenemiyor. Lütfen yeni bir arama deneyin."
          />
        )}

        {!loading && !error && offer && (
          <Card className="p-3 text-[11px] space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold">Teklif #{offer.offer_id}</div>
                <div className="text-[10px] text-muted-foreground">Supplier: {offer.supplier || "mock"}</div>
              </div>
              <div className="text-sm font-bold">
                {offer.total_amount} {offer.currency}
              </div>
            </div>
            <div className="text-[10px] text-muted-foreground">
              Bu ekran, B2C vitrinde hızlı teklif detaylarını göstermek için minimaldir. Tam ürün/kampanya içerikleri
              ileriki fazlarda eklenecektir.
            </div>
            <div className="flex justify-end mt-2">
              <Button size="sm" className="h-8 text-xs" onClick={handleCheckout}>
                Rezervasyon Oluştur
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
