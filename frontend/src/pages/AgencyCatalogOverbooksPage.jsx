import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import { toast } from "react-hot-toast";

function startOfTodayISO() {
  return new Date().toISOString().slice(0, 10);
}

function addDaysISO(iso, days) {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function AgencyCatalogOverbooksPage() {
  const [start, setStart] = useState(() => startOfTodayISO());
  const [end, setEnd] = useState(() => addDaysISO(startOfTodayISO(), 30));
  const [q, setQ] = useState("");
  const [items, setItems] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(false);

  async function fetchOverbooks(e) {
    if (e) e.preventDefault();
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (start) params.set("start", start);
      if (end) params.set("end", end);
      if (q) params.set("q", q);
      const resp = await api.get(`/agency/catalog/overbooks?${params.toString()}`);
      setItems(resp.data?.items || []);
      setMeta(resp.data?.meta || null);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchOverbooks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Overbooklar</h1>
          <p className="text-sm text-muted-foreground">
            Bu sayfada kapasite doluyken alınan (overbook) katalog rezervasyonları listelenir.
          </p>
        </div>
      </div>

      <form className="grid gap-3 md:grid-cols-4 items-end" onSubmit={fetchOverbooks}>
        <div className="space-y-1 text-sm">
          <label className="font-medium">Başlangıç</label>
          <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </div>
        <div className="space-y-1 text-sm">
          <label className="font-medium">Bitiş</label>
          <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </div>
        <div className="space-y-1 text-sm">
          <label className="font-medium">Arama (misafir)</label>
          <Input
            type="text"
            placeholder="İsim, e-posta veya telefon"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="submit"
            size="sm"
            disabled={loading}
            data-testid="btn-overbooks-fetch"
          >
            Listele
          </Button>
        </div>
      </form>

      <Card className="p-3 text-sm">
        {items.length === 0 ? (
          <div
            className="text-xs text-muted-foreground"
            data-testid="overbooks-empty"
          >
            Bu aralıkta overbook kayıtı bulunamadı.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="border-b text-muted-foreground">
                <tr className="text-left">
                  <th className="py-1 pr-2">Tarih(ler)</th>
                  <th className="py-1 pr-2">Misafir</th>
                  <th className="py-1 pr-2">Pax/Units</th>
                  <th className="py-1 pr-2">Durum</th>
                  <th className="py-1 pr-2">Toplam</th>
                  <th className="py-1 pr-2">Link</th>
                </tr>
              </thead>
              <tbody>
                {items.map((b) => {
                  const alloc = b.allocation || {};
                  const guest = b.guest || {};
                  const dates = b.dates || {};
                  const pricing = b.pricing || {};
                  const days = alloc.days || [];
                  return (
                    <tr
                      key={b.id}
                      className="border-b last:border-b-0 hover:bg-muted/40"
                      data-testid="overbook-row"
                    >
                      <td className="py-1 pr-2 align-top" data-testid="overbook-date">
                        {days.length ? days.join(", ") : dates.start}
                      </td>
                      <td className="py-1 pr-2 align-top" data-testid="overbook-guest">
                        <div>{guest.full_name || "-"}</div>
                        <div className="text-[11px] text-muted-foreground">
                          {guest.email || guest.phone || ""}
                        </div>
                      </td>
                      <td className="py-1 pr-2 align-top" data-testid="overbook-units">
                        <div>
                          Pax: {b.pax}
                        </div>
                        <div className="text-[11px] text-muted-foreground">
                          Units: {alloc.units} ({alloc.mode || "pax"})
                        </div>
                      </td>
                      <td className="py-1 pr-2 align-top" data-testid="overbook-status">
                        <div className="flex items-center gap-1">
                          <span className="capitalize">{b.status}</span>
                          {alloc.overbook && (
                            <span
                              className="px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-900 text-[10px] border border-amber-300"
                              data-testid="overbook-badge"
                            >
                              Overbook
                            </span>
                          )}
                        </div>
                        {alloc.overbook_reason && (
                          <div className="text-[11px] text-muted-foreground" data-testid="overbook-reason">
                            Neden: {alloc.overbook_reason}
                          </div>
                        )}
                      </td>
                      <td className="py-1 pr-2 align-top">
                        {pricing.total != null ? (
                          <span>
                            {pricing.total} {pricing.currency || ""}
                          </span>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td className="py-1 pr-2 align-top">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          data-testid="btn-overbook-open-booking"
                          onClick={() => {
                            // navigate via full page reload for simplicity
                            window.location.href = `/app/agency/catalog/bookings/${b.id}`;
                          }}
                        >
                          Detay
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
