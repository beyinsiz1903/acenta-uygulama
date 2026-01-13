import React, { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { createPublicQuote, apiErrorMessage } from "../../lib/publicBooking";

function isoTodayOffset(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function BookProductPage() {
  const { productId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const org = searchParams.get("org") || "";

  const [dateFrom, setDateFrom] = useState(isoTodayOffset(1));
  const [dateTo, setDateTo] = useState(isoTodayOffset(2));
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [rooms, setRooms] = useState(1);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [quote, setQuote] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!org) return;

    setLoading(true);
    setError("");
    setQuote(null);

    try {
      const body = {
        org,
        product_id: productId,
        date_from: dateFrom,
        date_to: dateTo,
        pax: { adults: Number(adults) || 1, children: Number(children) || 0 },
        rooms: Number(rooms) || 1,
        currency: "EUR",
      };
      const res = await createPublicQuote(body);
      setQuote(res);

      const qp = new URLSearchParams();
      qp.set("org", org);
      qp.set("quote_id", res.quote_id);
      navigate(`/book/${productId}/checkout?${qp.toString()}`);
    } catch (e2) {
      setError(apiErrorMessage(e2));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <Card className="w-full max-w-lg p-4 space-y-3">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Ürün Seçimi</h1>
          <p className="text-xs text-muted-foreground">
            Seçtiğiniz ürün için tarih ve misafir bilgilerini seçip bir fiyat teklifi oluşturun.
          </p>
        </div>

        <div className="text-xs space-y-1">
          <div>
            <span className="font-medium">Product ID:</span> <span className="font-mono break-all">{productId}</span>
          </div>
          <div>
            <span className="font-medium">Org:</span> <span className="font-mono break-all">{org || "-"}</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="font-medium">Giriş tarihi</label>
              <input
                type="date"
                className="w-full rounded-md border px-2 py-1"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <label className="font-medium">Çıkış tarihi</label>
              <input
                type="date"
                className="w-full rounded-md border px-2 py-1"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1">
              <label className="font-medium">Yetişkin</label>
              <input
                type="number"
                min={1}
                max={10}
                className="w-full rounded-md border px-2 py-1"
                value={adults}
                onChange={(e) => setAdults(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="font-medium">Çocuk</label>
              <input
                type="number"
                min={0}
                max={10}
                className="w-full rounded-md border px-2 py-1"
                value={children}
                onChange={(e) => setChildren(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="font-medium">Oda</label>
              <input
                type="number"
                min={1}
                max={10}
                className="w-full rounded-md border px-2 py-1"
                value={rooms}
                onChange={(e) => setRooms(e.target.value)}
              />
            </div>
          </div>

          {error && <div className="text-red-600 text-xs">{error}</div>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" size="sm" onClick={() => navigate(-1)}>
              Geri
            </Button>
            <Button type="submit" size="sm" disabled={!org || loading}>
              {loading ? "Teklif alınıyor..." : "Teklif al ve devam et"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}