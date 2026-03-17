import React, { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Megaphone, AlertCircle } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";

export function B2BAnnouncementsCard() {
  const { data: items = [], isLoading: loading, error, refetch } = useQuery({
    queryKey: ["b2b", "announcements"],
    queryFn: async () => {
      const resp = await api.get("/b2b/announcements");
      return resp.data || [];
    },
    staleTime: 30_000,
  });

  

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
          <Badge variant="outline" className="text-xs">
            {items.length} duyuru
          </Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
            <AlertCircle className="h-4 w-4 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {!error && (
          <ul className="space-y-2">
            {items.map((it) => (
              <li key={it.id} className="rounded-lg border bg-muted/40 px-3 py-2">
                <div className="text-xs font-semibold text-foreground">{it.title}</div>
                <div className="mt-1 text-xs text-muted-foreground whitespace-pre-line">{it.body}</div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
