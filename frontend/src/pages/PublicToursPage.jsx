import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";

export default function PublicToursPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const resp = await api.get("/public/tours");
        if (!alive) return;
        setItems(Array.isArray(resp.data) ? resp.data : []);
      } catch (e) {
        console.error(apiErrorMessage(e) || e);
        if (!alive) return;
        setItems([]);
      } finally {
        if (alive) setLoading(false);
      }
    }
    load();
    return () => {
      alive = false;
    };
  }, []);

  const cards = useMemo(
    () =>
      items.map((t) => {
        const cover = t.images && t.images[0] ? t.images[0] : null;
        return (
          <Link key={t.id} to={`/tours/${t.id}`} className="block">
            <div className="rounded-xl border bg-white overflow-hidden hover:shadow-sm transition">
              <div className="h-40 bg-gray-100">
                {cover ? (
                  <img src={cover} alt={t.title} className="h-40 w-full object-cover" />
                ) : (
                  <div className="h-40 w-full flex items-center justify-center text-sm text-gray-500">
                    Görsel yok
                  </div>
                )}
              </div>
              <div className="p-4">
                <div className="font-semibold line-clamp-1">{t.title}</div>
                <div className="text-sm text-gray-600 line-clamp-2 mt-1">
                  {t.description || "—"}
                </div>
                <div className="mt-3 text-sm">
                  <span className="font-medium">{t.price ?? 0}</span>{" "}
                  <span className="text-gray-600">{t.currency || "TRY"}</span>
                </div>
              </div>
            </div>
          </Link>
        );
      }),
    [items],
  );

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h1 className="text-xl font-semibold">Turlar</h1>
        <Button variant="outline" onClick={() => window.location.reload()} disabled={loading}>
          Yenile
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-gray-600">Yükleniyor…</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-gray-600">Şu an listelenecek tur yok.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{cards}</div>
      )}
    </div>
  );
}
