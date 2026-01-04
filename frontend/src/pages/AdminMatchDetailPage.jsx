import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Loader2, AlertCircle } from "lucide-react";

function StatusBadge({ status }) {
  const s = (status || "").toLowerCase();
  if (s === "confirmed") return <Badge className="bg-emerald-600 text-white">Onaylı</Badge>;
  if (s === "cancelled") return <Badge variant="destructive">İptal</Badge>;
  if (s === "pending") return <Badge variant="outline">Beklemede</Badge>;
  return <Badge variant="outline">{status}</Badge>;
}

export default function AdminMatchDetailPage() {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!id) return;
    const run = async () => {
      try {
        setLoading(true);
        setError("");
        const resp = await api.get(`/admin/matches/${id}`, {
          params: { days: 90, limit: 50 },
        });
        setData(resp.data);
      } catch (e) {
        console.error("Admin match detail fetch failed", e);
        setError(apiErrorMessage(e));
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Match Detayı</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-destructive text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return null;
  }

  const { agency_name, agency_id, hotel_name, hotel_id, range, metrics, bookings } = data;
  const cancelPct = (metrics?.cancel_rate || 0) * 100;
  const confirmPct = (metrics?.confirm_rate || 0) * 100;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Match Detayı</h1>
        <p className="text-sm text-muted-foreground">
          Acenta ve otel arasındaki eşleşme için son 90 güne ait detaylı metrikler ve rezervasyon listesi.
        </p>
        <p className="mt-2 text-sm">
          <span className="font-medium">Acenta:</span> {agency_name || agency_id} ({agency_id})
          <br />
          <span className="font-medium">Otel:</span> {hotel_name || hotel_id} ({hotel_id})
        </p>
        {range && (
          <p className="mt-1 text-xs text-muted-foreground">
            Dönem: {new Date(range.from).toLocaleDateString()} – {new Date(range.to).toLocaleDateString()} ({range.days} gün)
          </p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Toplam Rezervasyon</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.total_bookings ?? 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Onaylı / İptal</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-semibold">
              {metrics?.confirmed ?? 0} / {metrics?.cancelled ?? 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Onay oranı: {confirmPct.toFixed(1)}% · İptal oranı: {cancelPct.toFixed(1)}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Beklemede</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.pending ?? 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Ortalama Onay Süresi</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.avg_approval_hours ?? 0}</div>
            <p className="text-xs text-muted-foreground mt-1">saat</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Son Rezervasyonlar</CardTitle>
        </CardHeader>
        <CardContent>
          {(!bookings || bookings.length === 0) ? (
            <p className="text-sm text-muted-foreground">Bu dönem için rezervasyon bulunamadı.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kod</TableHead>
                    <TableHead>Misafir</TableHead>
                    <TableHead>Giriş / Çıkış</TableHead>
                    <TableHead className="text-right">Tutar</TableHead>
                    <TableHead>Durum</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bookings.map((b) => (
                    <TableRow key={b.id}>
                      <TableCell>{b.code}</TableCell>
                      <TableCell>{b.guest_name}</TableCell>
                      <TableCell>
                        {b.check_in_date} – {b.check_out_date}
                      </TableCell>
                      <TableCell className="text-right">
                        {b.total_amount?.toLocaleString("tr-TR", {
                          style: "currency",
                          currency: b.currency || "TRY",
                        })}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={b.status} />
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
