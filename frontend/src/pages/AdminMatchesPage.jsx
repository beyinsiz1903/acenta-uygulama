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
  const [onlyHighRisk, setOnlyHighRisk] = useState(false);
  const [hideBlocked, setHideBlocked] = useState(false);
  const [sort, setSort] = useState("high_risk_first");
  const navigate = useNavigate();

  const loadMatches = async (opts = {}) => {
    const days = opts.days ?? 30;
    const minTotal = opts.min_total ?? 3;
    try {
      setLoading(true);
      setError("");
      const resp = await api.get("/admin/matches", {
        params: {
          days,
          min_total: minTotal,
          include_action: 1,
          only_high_risk: onlyHighRisk ? 1 : 0,
          sort,
        },
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

  useEffect(() => {
    loadMatches();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onlyHighRisk, sort]);

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

  const displayedItems = hideBlocked
    ? items.filter((i) => i.action_status !== "blocked")
    : items;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Match Risk</h1>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm font-medium">Filtreler</CardTitle>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs">Only high risk</span>
              <input
                type="checkbox"
                checked={onlyHighRisk}
                onChange={(e) => setOnlyHighRisk(e.target.checked)}
                data-testid="match-risk-only-high-risk"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs">Hide blocked</span>
              <input
                type="checkbox"
                checked={hideBlocked}
                onChange={(e) => setHideBlocked(e.target.checked)}
                data-testid="match-risk-hide-blocked"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium" htmlFor="match-risk-sort">
                Sort by
              </label>
              <select
                id="match-risk-sort"
                className="border rounded px-2 py-1 text-xs bg-background"
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                data-testid="match-risk-sort"
              >
                <option value="high_risk_first">High risk first</option>
                <option value="repeat_desc">Repeat (7d) desc</option>
                <option value="rate_desc">Not-arrived rate desc</option>
                <option value="total_desc">Total bookings desc</option>
                <option value="last_booking_desc">Last booking desc</option>
              </select>
            </div>
          </div>
        </CardHeader>
      </Card>

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
          {displayedItems.length === 0 ? (
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
                    <TableHead>High risk</TableHead>
                    <TableHead>Reasons</TableHead>
                    <TableHead>Aksiyon</TableHead>
                    <TableHead></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedItems.map((item) => {
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
                          {item.high_risk && (
                            <Badge
                              variant="destructive"
                              data-testid="match-risk-row-high-badge"
                            >
                              HIGH
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {Array.isArray(item.high_risk_reasons) && item.high_risk_reasons.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {item.high_risk_reasons.map((r) => (
                                <Badge key={r} variant="outline" className="text-[10px] px-1 py-0">
                                  {r}
                                </Badge>
                              ))}
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              ok
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          {item.action_status && item.action_status !== "none" && (
                            <>
                              <Badge
                                variant={
                                  item.action_status === "blocked"
                                    ? "outline"
                                    : item.action_status === "manual_review"
                                    ? "secondary"
                                    : "outline"
                                }
                                data-testid={
                                  item.action_status === "blocked"
                                    ? "match-risk-row-blocked-badge"
                                    : "match-action-status-badge"
                                }
                              >
                                {item.action_status === "blocked" && "Blocked"}
                                {item.action_status === "manual_review" && "Manual review"}
                                {item.action_status === "watchlist" && "Watchlist"}
                                {!["blocked", "manual_review", "watchlist"].includes(item.action_status) &&
                                  item.action_status}
                              </Badge>
                              {item.action_status === "blocked" && (
                                <p className="mt-1 text-[10px] text-muted-foreground max-w-[220px]">
                                  Blocked: Uyarı/Export gönderimi yapılmaz. Delivery suppressed (blocked).
                                </p>
                              )}
                            </>
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
