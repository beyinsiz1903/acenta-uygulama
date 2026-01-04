import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Loader2, AlertCircle } from "lucide-react";

function RiskBadge({ cancelRate }) {
  if (!cancelRate || cancelRate <= 0.05) {
    return <Badge variant="outline">Düşük</Badge>;
  }
  if (cancelRate <= 0.15) {
    return <Badge variant="secondary">Orta</Badge>;
  }
  return <Badge variant="destructive">Yüksek</Badge>;
}

export default function AdminMatchesPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [items, setItems] = useState([]);
  const [range, setRange] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        setError("");
        const resp = await api.get("/admin/matches", {
          params: { days: 30, min_total: 3, include_action: 1 },
        });
        setItems(resp.data?.items || []);
        setRange(resp.data?.range || null);
      } catch (e) {
        console.error("Admin matches fetch failed", e);
        setError(apiErrorMessage(e));
      } finally {
        setLoading(false);
      }
    };

    run();
  }, []);

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
          <CardTitle>Match Risk</CardTitle>
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Match Risk</h1>
        <p className="text-sm text-muted-foreground">
          Acenta–otel eşleşmelerini (agency–hotel pairs) son 30 güne göre özetler. Yüksek iptal oranına sahip
          eşleşmeleri buradan inceleyebilirsiniz.
        </p>
        {range && (
          <p className="mt-1 text-xs text-muted-foreground">
            Dönem: {new Date(range.from).toLocaleDateString()} – {new Date(range.to).toLocaleDateString()} ({range.days} gün)
          </p>
        )}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-medium">Eşleşmeler</CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <p className="text-sm text-muted-foreground">Bu dönem için eşleşme bulunamadı.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Acenta</TableHead>
                    <TableHead>Otel</TableHead>
                    <TableHead className="text-right">Toplam</TableHead>
                    <TableHead className="text-right">Onaylı</TableHead>
                    <TableHead className="text-right">İptal</TableHead>
                    <TableHead className="text-right">İptal Oranı</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead>Aksiyon</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => {
                    const cancelPct = (item.cancel_rate || 0) * 100;
                    return (
                      <TableRow key={item.id}>
                        <TableCell>{item.agency_name || item.agency_id}</TableCell>
                        <TableCell>{item.hotel_name || item.hotel_id}</TableCell>
                        <TableCell className="text-right font-medium">{item.total_bookings}</TableCell>
                        <TableCell className="text-right">{item.confirmed}</TableCell>
                        <TableCell className="text-right">{item.cancelled}</TableCell>
                        <TableCell className="text-right">{cancelPct.toFixed(1)}%</TableCell>
                        <TableCell>
                          <RiskBadge cancelRate={item.cancel_rate} />
                        </TableCell>
                        <TableCell>
                          {item.action_status && item.action_status !== "none" && (
                            <Badge
                              variant={
                                item.action_status === "blocked"
                                  ? "destructive"
                                  : item.action_status === "manual_review"
                                  ? "secondary"
                                  : "outline"
                              }
                              data-testid="match-action-status-badge"
                            >
                              {item.action_status === "blocked" && "Blocked"}
                              {item.action_status === "manual_review" && "Manual review"}
                              {item.action_status === "watchlist" && "Watchlist"}
                              {!["blocked", "manual_review", "watchlist"].includes(item.action_status) &&
                                item.action_status}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(`/app/admin/matches/${item.id}`)}
                          >
                            Detay
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
