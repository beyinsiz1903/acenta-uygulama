import React, { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { api, apiErrorMessage } from "../../lib/api";
import { createTourPublicQuote } from "../../lib/publicBooking";
import { useSeo } from "../../hooks/useSeo";

export default function BookTourProductPage() {
  const { tourId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const org = searchParams.get("org") || "";
  const partner = searchParams.get("partner") || "";

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tour, setTour] = useState(null);

  const [date, setDate] = useState("");
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [quoting, setQuoting] = useState(false);
  const [quoteError, setQuoteError] = useState("");

  useSeo({
    title: tour ? `${tour.name} | Tur` : "Tur Detayı | Syroce",
    description: tour?.description || "Seçtiğiniz tur için detayları görüntüleyin.",
    canonicalPath: tourId ? `/book/tour/${tourId}` : "/book",
    type: "product",
  });

  useEffect(() => {
    if (!org || !tourId) return;

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/public/tours/${tourId}`, { params: { org } });
        if (cancelled) return;
        setTour(res.data || null);
      } catch (e) {
        if (cancelled) return;
        setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

  const handleQuote = async (e) => {
    e.preventDefault();
    if (!org || !tourId || !date) {
      setQuoteError("Tarih ve organizasyon bilgisi zorunludur.");
      return;
    }
    setQuoting(true);
    setQuoteError("");

    try {
      const body = {
        org,
        tour_id: tourId,
        date,
        pax: {
          adults: Number(adults) || 1,
          children: Number(children) || 0,
        },
        currency: tour?.currency || "EUR",
      };
      const res = await createTourPublicQuote(body);

      const qp = new URLSearchParams();
      qp.set("org", org);
      if (partner) qp.set("partner", partner);
      qp.set("quote_id", res.quote_id);
      const qs = qp.toString();

      navigate(qs ? `/book/tour/${tourId}/checkout?${qs}` : `/book/tour/${tourId}/checkout`, {
        state: { quote: res, tour },
      });
    } catch (e2) {
      const msg = e2?.message || apiErrorMessage(e2.raw || e2) || "Teklif alınamadı.";
      setQuoteError(msg);
    } finally {
      setQuoting(false);
  };

    }
  };

      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [org, tourId]);

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <Card className="w-full max-w-lg p-4 space-y-3">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Tur Detayı</h1>
          <p className="text-xs text-muted-foreground">
            Seçtiğiniz tur için özet bilgileri görüntüleyin. Rezervasyon akışı bir sonraki fazda eklenecektir.
          </p>
        </div>

        {!org && (
          <p className="text-xs text-red-600">
            Kuruluş parametresi eksik. Lütfen URL&apos;ye ?org=&lt;organization_id&gt; parametresi ekleyin.
          </p>
        )}

        {loading && (
          <p className="text-xs text-muted-foreground">Tur bilgileri yükleniyor...</p>
        )}

        {error && (
          <p className="text-xs text-red-600">{error}</p>
        )}

        {tour && (
          <div className="space-y-3 text-xs">
            <div className="space-y-1">
              <div className="font-semibold text-sm">{tour.name}</div>
              {tour.destination && (
                <div className="text-muted-foreground">Bölge / Destinasyon: {tour.destination}</div>
              )}
            </div>
            {tour.description && (
              <div className="space-y-1">
                <div className="font-medium">Açıklama</div>
                <p className="text-muted-foreground whitespace-pre-line">{tour.description}</p>
              </div>
            )}
            <div className="space-y-1">
              <div className="font-medium">Başlangıç fiyatı</div>
              <div className="font-mono text-sm">
                {tour.base_price?.toFixed ? tour.base_price.toFixed(2) : tour.base_price} {tour.currency}
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" size="sm" onClick={() => navigate(-1)}>
            Geri
          </Button>
        </div>
      </Card>
    </div>
  );
}
