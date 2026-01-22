import React, { useCallback, useEffect, useState } from "react";
import { BarChart3, Download } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import EmptyState from "../components/EmptyState";

export default function ReportsPage() {
  const [resSummary, setResSummary] = useState([]);
  const [sales, setSales] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [a, b] = await Promise.all([
        api.get("/reports/reservations-summary"),
        api.get("/reports/sales-summary"),
      ]);
      setResSummary(a.data || []);
      setSales(b.data || []);
    } catch (e) {
      const msg = apiErrorMessage(e);
      // "Not Found" durumunda rapor verisi yok kabul ediyoruz; kırmızı hata göstermiyoruz.
      if (msg === "Not Found") {
        setResSummary([]);
        setSales([]);
      } else {
        setError(msg);
      }
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      load();
    }, 0);
    return () => clearTimeout(t);
  }, [load]);

  async function downloadCsv() {
    try {
      const resp = await api.get("/reports/sales-summary.csv", { responseType: "blob" });
      const blob = new Blob([resp.data], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "sales-summary.csv";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert(apiErrorMessage(e));
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold text-foreground">Raporlar</h2>
        <p className="text-sm text-muted-foreground">Özet satış ve rezervasyon raporları.</p>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="reports-error">
          {error}
        </div>
      ) : null}

      <Card className="rounded-2xl shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
            Satış Özeti
          </CardTitle>
          <Button variant="outline" onClick={downloadCsv} className="gap-2" data-testid="reports-csv">
            <Download className="h-4 w-4" /> CSV
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table data-testid="sales-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Gün</TableHead>
                  <TableHead>Rezervasyon</TableHead>
                  <TableHead>Ciro</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sales.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} className="py-6">
                      <EmptyState
                        title="Henüz satış özeti yok"
                        description="Satış raporu oluşturmak için önce rezervasyon ve tahsilat akışını kullanın."
                      />
                    </TableCell>
                  </TableRow>
                ) : (
                  sales.map((r) => (
                    <TableRow key={r.day}>
                      <TableCell className="font-medium text-foreground">{r.day}</TableCell>
                      <TableCell className="text-foreground/80">{r.count}</TableCell>
                      <TableCell className="text-foreground/80">{r.revenue}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Rezervasyon Durum Dağılımı</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="res-summary">
            {resSummary.length === 0 ? (
              <p className="col-span-2 md:col-span-4 text-xs text-muted-foreground">
                Henüz rezervasyon durum verisi oluşmamış. Rezervasyon oluştukça bu dağılım burada görünecektir.
              </p>
            ) : (
              resSummary.map((r) => (
                <div key={r.status} className="rounded-2xl border bg-card p-3">
                  <div className="text-xs text-muted-foreground">{r.status}</div>
                  <div className="text-2xl font-semibold text-foreground">{r.count}</div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
