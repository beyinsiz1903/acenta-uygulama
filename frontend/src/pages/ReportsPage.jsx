import React, { useEffect, useState } from "react";
import { BarChart3, Download } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export default function ReportsPage() {
  const [resSummary, setResSummary] = useState([]);
  const [sales, setSales] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const [a, b] = await Promise.all([
        api.get("/reports/reservations-summary"),
        api.get("/reports/sales-summary"),
      ]);
      setResSummary(a.data || []);
      setSales(b.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  }

  useEffect(() => {

    load();
  }, []);

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
        <h2 className="text-2xl font-semibold text-slate-900">Raporlar</h2>
        <p className="text-sm text-slate-600">Özet satış ve rezervasyon raporları.</p>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="reports-error">
          {error}
        </div>
      ) : null}

      <Card className="rounded-2xl shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-slate-500" />
            Satış Özeti
          </CardTitle>
          <Button variant="outline" onClick={downloadCsv} className="gap-2" data-testid="reports-csv">
            <Download className="h-4 w-4" /> CSV
          </Button>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="sales-table">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-2">Gün</th>
                  <th className="py-2">Rezervasyon</th>
                  <th className="py-2">Ciro</th>
                </tr>
              </thead>
              <tbody>
                {sales.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="py-6 text-slate-500">Kayıt yok.</td>
                  </tr>
                ) : (
                  sales.map((r) => (
                    <tr key={r.day} className="border-t">
                      <td className="py-3 font-medium text-slate-900">{r.day}</td>
                      <td className="py-3 text-slate-700">{r.count}</td>
                      <td className="py-3 text-slate-700">{r.revenue}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Rezervasyon Durum Dağılımı</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="res-summary">
            {resSummary.map((r) => (
              <div key={r.status} className="rounded-2xl border bg-white p-3">
                <div className="text-xs text-slate-500">{r.status}</div>
                <div className="text-2xl font-semibold text-slate-900">{r.count}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
