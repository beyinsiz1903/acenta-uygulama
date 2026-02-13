import React, { useEffect, useState } from "react";
import { AlertCircle, ActivityIcon } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import EmptyState from "../components/EmptyState";

function formatAmountCents(amountCents, currency = "EUR") {
  const amount = (amountCents || 0) / 100;
  try {
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency,
      minimumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency}`;
  }
}

export default function AdminB2BFunnelPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get("/admin/b2b/funnel/summary");
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

  const hasData = items && items.length > 0;

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground">Satış Hunisi Özeti</h1>
        <p className="text-sm text-muted-foreground">
          Son 30 gün içinde bayiler üzerinden gelen teklif ve satışların finansal özetini gösterir.
        </p>
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <ActivityIcon className="h-4 w-4" /> Satış Hunisi
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Bayiler ve iş ortakları üzerinden gelen teklif trafiğini görüntüler.
            </p>
          </div>
          {hasData && (
            <div className="text-right text-xs text-muted-foreground">
              <div>Partner sayısı: <span className="font-semibold">{items.length}</span></div>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {loading && !hasData && (
            <p className="text-xs text-muted-foreground">Veriler yükleniyor...</p>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 mt-0.5" />
              <div>{error}</div>
            </div>
          )}

          {!loading && !error && !hasData && (
            <EmptyState
              title="Henüz veri yok"
              description="Son 30 gün içinde bayiler üzerinden gelen teklif kaydı bulunamadı. İş ortaklarınız üzerinden ilk satışlarınızı oluşturduktan sonra bu alan dolacaktır."
              icon={<ActivityIcon className="h-8 w-8 text-muted-foreground" />}
              className="py-8"
            />
          )}

          {!loading && !error && hasData && (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Partner</TableHead>
                    <TableHead className="text-xs text-right">Teklif Sayısı</TableHead>
                    <TableHead className="text-xs text-right">Toplam Tutar</TableHead>
                    <TableHead className="text-xs">İlk Teklif</TableHead>
                    <TableHead className="text-xs">Son Teklif</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((it) => (
                    <TableRow key={it.partner}>
                      <TableCell className="text-xs">
                        <div className="flex flex-col">
                          <span className="font-medium truncate max-w-[220px]">{it.partner}</span>
                          <span className="text-[10px] text-muted-foreground">partner_id</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {it.total_quotes}
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {formatAmountCents(it.total_amount_cents, "EUR")}
                      </TableCell>
                      <TableCell className="text-[11px] text-muted-foreground">
                        {it.first_quote_at || "-"}
                      </TableCell>
                      <TableCell className="text-[11px] text-muted-foreground">
                        {it.last_quote_at || "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}