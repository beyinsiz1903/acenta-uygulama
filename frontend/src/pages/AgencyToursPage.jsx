import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";

export default function AgencyToursPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const resp = await api.get("/agency/tours");
      setItems(Array.isArray(resp.data) ? resp.data : []);
    } catch (e) {
      console.error(apiErrorMessage(e) || e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h1 className="text-xl font-semibold">Turlarım</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            Yenile
          </Button>
          <Link to="/app/agency/tours/new">
            <Button>Yeni Tur</Button>
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="text-sm text-gray-600">Yükleniyor…</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-gray-600">Henüz tur yok.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map((t) => (
            <div key={t.id} className="rounded-xl border bg-white p-4 flex gap-3">
              <div className="w-28 h-20 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
                {t.images?.[0] ? (
                  <img src={t.images[0]} alt={t.title} className="w-28 h-20 object-cover" />
                ) : (
                  <div className="w-28 h-20 flex items-center justify-center text-xs text-gray-500">
                    Görsel yok
                  </div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold truncate">{t.title}</div>
                  <span
                    className={`text-xs px-2 py-1 rounded-full border ${
                      t.status === "active" ? "bg-green-50" : "bg-gray-50"
                    }`}
                  >
                    {t.status === "active" ? "Aktif" : "Taslak"}
                  </span>
                </div>
                <div className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {t.description || "—"}
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <div className="text-sm">
                    <span className="font-medium">{t.price ?? 0}</span>{" "}
                    <span className="text-gray-600">{t.currency || "TRY"}</span>
                  </div>
                  <Link to={`/app/agency/tours/${t.id}`} className="text-sm underline">
                    Düzenle
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
