import React, { useEffect, useState } from "react";
import { Megaphone, AlertCircle } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

export function B2BAnnouncementsCard() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get("/b2b/announcements");
        if (cancelled) return;
        setItems(res.data?.items || []);
      } catch (e) {
        if (cancelled) return;
        setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading && items.length === 0 && !error) {
    return (
      <Card className="rounded-2xl border bg-card shadow-sm">
        <CardHeader className="flex items-center justify-between space-y-0">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Megaphone className="h-4 w-4" />
              B2B Duyuruları
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">Duyurular yükleniyor...</p>
        </CardContent>
      </Card>
    );
  }

  if (!items.length && !error) {
    // Hiç duyuru yoksa kart göstermeyelim; portal sade kalsın.
    return null;
  }

  return (
    <Card className="rounded-2xl border bg-card shadow-sm">
      <CardHeader className="flex items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Megaphone className="h-4 w-4" />
            B2B Duyuruları
          </CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Sizin için yayınlanan önemli duyuru ve bilgilendirmeler.
          </p>
        </div>
        {items.length > 0 && (
          <Badge variant="outline" className="text-[11px]">
            {items.length} duyuru
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive">
            <AlertCircle className="h-4 w-4 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {!error && (
          <ul className="space-y-2">
            {items.map((it) => (
              <li key={it.id} className="rounded-lg border bg-muted/40 px-3 py-2">
                <div className="text-[11px] font-semibold text-foreground">{it.title}</div>
                <div className="mt-1 text-[11px] text-muted-foreground whitespace-pre-line">{it.body}</div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
