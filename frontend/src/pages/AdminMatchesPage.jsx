import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, apiErrorMessage } from "../lib/api";
import { toast } from "../components/ui/sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "../components/ui/drawer";
import { Loader2, AlertCircle, Copy } from "lucide-react";
import { safeCopyText } from "../utils/copyText";

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
  const [eventsOpen, setEventsOpen] = useState(false);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState("");
  const [eventsData, setEventsData] = useState(null);
  const [eventsOnlyCancelled, setEventsOnlyCancelled] = useState(false);
  const [eventsSort, setEventsSort] = useState("created_desc");
  const [eventsShowBehavioral, setEventsShowBehavioral] = useState(true);
  const [eventsShowOperational, setEventsShowOperational] = useState(false);
  const [eventsReasonFilter, setEventsReasonFilter] = useState("");
  const [copiedBookingId, setCopiedBookingId] = useState(null);
  const [unblockRequest, setUnblockRequest] = useState({ loading: false, alreadyPending: false, taskId: null });

  const [selectedMatch, setSelectedMatch] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Parse deep-link query parameters (e.g. from exports)
  const searchParams = new URLSearchParams(location.search || "");
  const deeplinkMatchId = searchParams.get("match_id");
  const deeplinkOpenDrawer = searchParams.get("open_drawer") === "1";

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

  const loadEvents = async (match) => {
    if (!match) return;
    try {
      setEventsLoading(true);
      setEventsError("");
      setEventsData(null);
      const resp = await api.get(`/admin/matches/${match.id}/events`, {
        params: { days: 7 },
      });
      setEventsData(resp.data);
    } catch (e) {
      console.error("Match events fetch failed", e);
      setEventsError(apiErrorMessage(e));
    } finally {
      setEventsLoading(false);
    }
  };

  useEffect(() => {
    // Export deep-link: try to auto-open drawer for given match_id
    if (!deeplinkMatchId || !items || items.length === 0 || !deeplinkOpenDrawer) {
      return;
    }
    const found = items.find((m) => m.id === deeplinkMatchId);
    if (!found) {
      toast({
        title: "Bu eşleşme mevcut görünümde bulunamadı",
        description: "Gün sayısını artırmayı veya min_total değerini düşürmeyi deneyin.",
        duration: 3000,
      });
      return;
    }
    setSelectedMatch(found);
    setEventsOnlyCancelled(false);
    setEventsOpen(true);
    loadEvents(found);
  }, [items, deeplinkMatchId, deeplinkOpenDrawer]);

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
          <CardTitle>Match Riski</CardTitle>
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
        <h1 className="text-2xl font-bold text-foreground">Match Riski</h1>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm font-medium">Filtreler</CardTitle>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs">Sadece yüksek risk</span>
              <input
                type="checkbox"
                checked={onlyHighRisk}
                onChange={(e) => setOnlyHighRisk(e.target.checked)}
                data-testid="match-risk-only-high-risk"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs">Blokelileri gizle</span>
              <input
                type="checkbox"
                checked={hideBlocked}
                onChange={(e) => setHideBlocked(e.target.checked)}
                data-testid="match-risk-hide-blocked"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium" htmlFor="match-risk-sort">
                Sıralama
              </label>
              <select
                id="match-risk-sort"
                className="border rounded px-2 py-1 text-xs bg-background"
                value={sort}
                onChange={(e) => setSort(e.target.value)}
                data-testid="match-risk-sort"
              >
                <option value="high_risk_first">Yüksek risk önce</option>
                <option value="repeat_desc">Tekrar (7g) azalan</option>
                <option value="rate_desc">Gelmedi oranı azalan</option>
                <option value="total_desc">Toplam rezervasyon azalan</option>
                <option value="last_booking_desc">Son rezervasyon tarihi azalan</option>
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
                    const verifiedSharePct =
                      typeof item.verified_share === "number" ? item.verified_share * 100 : 0;
                    const verifiedOnly = item.risk_inputs?.verified_only;
                    return (
                      <TableRow
                        key={item.id}
                        className="cursor-pointer hover:bg-muted/40"
                        onClick={() => {
                          setSelectedMatch(item);
                          setEventsOnlyCancelled(false);
                          setEventsOpen(true);
                          loadEvents(item);
                        }}
                      >
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
                          <div className="flex items-center gap-1 text-xs">
                            <span
                              className={
                                "inline-flex items-center rounded-full px-2 py-0.5 border text-[10px] " +
                                (verifiedOnly ? "border-emerald-500 text-emerald-600" : "border-muted-foreground/40")
                              }
                              title={
                                verifiedOnly
                                  ? "Risk, yaln31zca verified outcomes kullan31larak hesapland31 (last 30d)."
                                  : "Verified outcomes only: pasif. Risk t fm outcomes tabanl31 hesaplan31yor."
                              }
                              data-testid="match-risk-verified-chip"
                            >
                              {verifiedOnly ? "V-ONLY" : "V"}
                              {" "}
                              {verifiedSharePct > 0 ? `${verifiedSharePct.toFixed(0)}%` : "0%"}
                            </span>
                          </div>
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
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/app/admin/matches/${item.id}`);
                            }}
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

      <Drawer open={eventsOpen} onOpenChange={setEventsOpen} data-testid="match-risk-events-drawer">
        <DrawerContent className="max-h-[80vh] overflow-hidden" data-testid="match-risk-events-drawer">
          <div className="mx-auto w-full max-w-4xl">
            <DrawerHeader className="flex items-start justify-between">
              <div>
                <DrawerTitle>
                  {selectedMatch?.agency_name || selectedMatch?.agency_id}  {" "}
                  {selectedMatch?.hotel_name || selectedMatch?.hotel_id}
                </DrawerTitle>
                {selectedMatch && (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {selectedMatch.action_status === "blocked" && (
                      <Badge
                        variant="destructive"
                        data-testid="match-drawer-blocked-badge"
                      >
                        Blocked by policy
                      </Badge>
                    )}
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      data-testid="match-risk-open-match-detail"
                      onClick={() => {
                        const id = selectedMatch.id;
                        setEventsOpen(false);
                        setEventsData(null);
                        setSelectedMatch(null);
                        navigate(`/app/admin/matches/${id}`);
                      }}
                    >
                      Open Match Detail
                    </Button>
                  </div>
                )}
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {selectedMatch?.high_risk && (
                    <Badge variant="destructive">HIGH</Badge>
                  )}
                  {Array.isArray(selectedMatch?.high_risk_reasons) &&
                    selectedMatch.high_risk_reasons.map((r) => (
                      <Badge key={r} variant="outline" className="text-[10px] px-1 py-0">
                        {r}
                      </Badge>
                    ))}
                </div>
                {eventsData && (
                  <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted-foreground">
                    <span>
                      Davranışsal iptaller (7g):{" "}
                      <span className="font-semibold">
                        {eventsData.summary.behavioral_cancel_count}
                      </span>
                    </span>
                    <span>
                      Operasyonel iptaller (7g):{" "}
                      <span className="font-semibold">
                        {eventsData.summary.operational_cancel_count}
                      </span>
                    </span>
                    <span>
                      Pencere içindeki toplam: <span className="font-semibold">{eventsData.summary.total_bookings_in_window}</span>
                    </span>
                  </div>
                )}

                {selectedMatch?.action_status === "blocked" && (
                  <div className="mt-2 flex flex-col gap-1 text-xs text-destructive">
                    <span>
                      Bu eşleşme şu anda politika tarafından blokeli. Yeni rezervasyonlar reddedilecek (MATCH_BLOCKED).
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      Blokenin kaldırılması için aşağıdan talep oluşturun. Onaylanması için bir adminin Approvals kuyruğunda aksiyon alması gerekir.
                    </span>
                  </div>
                )}
              </div>
              <DrawerClose asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  data-testid="match-risk-events-close"
                  onClick={() => {
                    setEventsData(null);
                    setSelectedMatch(null);
                  }}
                >
                  ×
                </Button>
              </DrawerClose>
              {eventsData && (
                <p className="px-4 pb-1 text-[11px] text-muted-foreground">
                  Showing:{" "}
                  {eventsOnlyCancelled ? "sadece iptaller" : "all statuses"}
                  {", "}
                  {eventsShowBehavioral ? "behavioral" : "no behavioral"}
                  {" / "}
                  {eventsShowOperational ? "operational" : "no operational"}
                  {eventsReasonFilter
                    ? `, reason contains "${eventsReasonFilter}"`
                    : ""}
                </p>
              )}
            </DrawerHeader>

            <div className="px-4 pb-4 space-y-3">
              {selectedMatch?.action_status === "blocked" && (
                <div className="flex items-center justify-between gap-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs">
                  <span>
                    Bu eşleşme <span className="font-semibold">blokeli</span>. Yeni rezervasyonlar reddedilecek (MATCH_BLOCKED).
                  </span>
                  <div className="flex items-center gap-2">
                    {unblockRequest.alreadyPending && (
                      <span
                        className="text-[11px] text-muted-foreground"
                        data-testid="match-drawer-request-unblock-pending"
                      >
                        Bloke kaldırma talebi zaten onay bekliyor.
                      </span>
                    )}
                    <Button
                      type="button"
                      size="sm"
                      variant="destructive"
                      data-testid="match-drawer-request-unblock"
                      disabled={unblockRequest.loading || unblockRequest.alreadyPending || !!unblockRequest.taskId}
                      onClick={async () => {
                        if (!selectedMatch) return;
                        try {
                          setUnblockRequest((prev) => ({ ...prev, loading: true }));
                          const resp = await api.post(`/admin/matches/${selectedMatch.id}/request-unblock`);
                          const already = !!resp.data?.already_pending;
                          const taskId = resp.data?.task_id || null;
                          setUnblockRequest({ loading: false, alreadyPending: already, taskId });
                          toast({
                            title: already ? "Bloke kaldırma talebi zaten mevcut" : "Bloke kaldırma talebi oluşturuldu",
                            description: already
                              ? "Bu eşleşme için zaten onay bekleyen bir görev var."
                              : "Approvals kuyruğunda yeni bir onay görevi oluşturuldu.",
                          });
                        } catch (e) {
                          setUnblockRequest((prev) => ({ ...prev, loading: false }));
                          toast({
                            title: "Failed to request unblock",
                            description: apiErrorMessage(e),
                            variant: "destructive",
                          });
                        }
                      }}
                    >
                      {unblockRequest.loading ? "Gönderiliyor..." : "Blokenin kaldırılmasını iste"}
                    </Button>
                  </div>
                </div>
              )}

              {eventsLoading && (
                <p
                  className="text-sm text-muted-foreground"
                  data-testid="match-risk-events-loading"
                >
                  Yükleniyor...
                </p>
              )}

              {eventsError && !eventsLoading && (
                <p
                  className="text-sm text-destructive"
                  data-testid="match-risk-events-error"
                >
                  Events alınamadı: {eventsError}
                </p>
              )}

              {eventsData && !eventsLoading && !eventsError && (
                <>
                  <div className="flex flex-col gap-2 mb-2">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-3 flex-wrap">
                        <div className="flex items-center gap-2">
                          <span className="text-xs">Sadece iptaller</span>
                          <input
                            type="checkbox"
                            checked={eventsOnlyCancelled}
                            onChange={(e) => setEventsOnlyCancelled(e.target.checked)}
                            data-testid="match-risk-events-only-cancelled"
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs">Tag filtre</span>
                          <label className="flex items-center gap-1 text-xs">
                            <input
                              type="checkbox"
                              checked={eventsShowBehavioral}
                              onChange={(e) => setEventsShowBehavioral(e.target.checked)}
                              data-testid="match-risk-events-tag-behavioral"
                            />
                            <span>davranışsal</span>
                          </label>
                          <label className="flex items-center gap-1 text-xs">
                            <input
                              type="checkbox"
                              checked={eventsShowOperational}
                              onChange={(e) => setEventsShowOperational(e.target.checked)}
                              data-testid="match-risk-events-tag-operational"
                            />
                            <span>operasyonel</span>
                          </label>
                        </div>
                        <div className="flex items-center gap-2">
                          <label className="text-xs" htmlFor="match-risk-events-reason-filter">
                            Sebep filtresi
                          </label>
                          <input
                            id="match-risk-events-reason-filter"
                            type="text"
                            className="border rounded px-2 py-1 text-xs bg-background min-w-[160px]"
                            placeholder="Sebep içinde ara..."
                            value={eventsReasonFilter}
                            onChange={(e) => setEventsReasonFilter(e.target.value)}
                            data-testid="match-risk-events-reason-filter"
                          />
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="space-y-1">
                          <label className="text-xs font-medium" htmlFor="match-risk-events-sort">
                            Sıralama
                          </label>
                          <select
                            id="match-risk-events-sort"
                            className="border rounded px-2 py-1 text-xs bg-background"
                            value={eventsSort}
                            onChange={(e) => setEventsSort(e.target.value)}
                            data-testid="match-risk-events-sort"
                          >
                            <option value="created_desc">Oluşturulma (yeni → eski)</option>
                            <option value="created_asc">Oluşturulma (eski → yeni)</option>
                          </select>
                        </div>
                        <Button
                          type="button"
                          size="xs"
                          variant="outline"
                          onClick={() => {
                            try {
                              const text = JSON.stringify(eventsData, null, 2);
                              if (navigator.clipboard && navigator.clipboard.writeText) {
                                navigator.clipboard.writeText(text);
                              } else {
                                const ta = document.createElement("textarea");
                                ta.value = text;
                                document.body.appendChild(ta);
                                ta.select();
                                document.execCommand("copy");
                                document.body.removeChild(ta);
                              }
                            } catch (e) {
                              console.error("Copy JSON failed", e);
                            }
                          }}
                          data-testid="match-risk-events-copy-json"
                        >
                          Copy JSON
                        </Button>
                      </div>
                    </div>
                  </div>

                  <div className="border rounded-md overflow-hidden" data-testid="match-risk-events-table">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Created at</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Cancel tag</TableHead>
                          <TableHead>Cancel reason</TableHead>
                          <TableHead>Booking ID</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(() => {
                          let rows = eventsData.items || [];
                          if (eventsOnlyCancelled) {
                            rows = rows.filter((i) => i.status === "cancelled");
                          }
                          rows = rows.filter((i) => {
                            if (i.cancel_tag === "behavioral" && !eventsShowBehavioral) return false;
                            if (i.cancel_tag === "operational" && !eventsShowOperational) return false;
                            return true;
                          });
                          if (eventsReasonFilter) {
                            const q = eventsReasonFilter.toLowerCase();
                            rows = rows.filter((i) => {
                              const reason = (i.cancel_reason || "").toLowerCase();
                              const note = (i.cancel_note || "").toLowerCase();
                              const raw = (i.raw_reason || "").toLowerCase();
                              return (
                                reason.includes(q) ||
                                note.includes(q) ||
                                raw.includes(q)
                              );
                            });
                          }
                          rows = [...rows].sort((a, b) => {
                            const da = a.created_at ? new Date(a.created_at).getTime() : 0;
                            const db = b.created_at ? new Date(b.created_at).getTime() : 0;
                            if (eventsSort === "created_asc") {
                              return da - db;
                            }
                            return db - da;
                          });
                          return rows.map((ev) => (
                            <TableRow key={ev.booking_id}>
                              <TableCell className="text-xs">
                                {ev.created_at ? new Date(ev.created_at).toLocaleString() : "-"}
                              </TableCell>
                              <TableCell className="text-xs">{ev.status}</TableCell>
                              <TableCell className="text-xs">
                                {ev.cancel_tag === "behavioral" && (
                                  <Badge variant="outline" className="text-[10px] px-1 py-0">
                                    behavioral
                                  </Badge>
                                )}
                                {ev.cancel_tag === "operational" && (
                                  <Badge variant="outline" className="text-[10px] px-1 py-0">
                                    operational
                                  </Badge>
                                )}
                                {ev.cancel_tag === "none" && (
                                  <span className="text-[10px] text-muted-foreground">none</span>
                                )}
                              </TableCell>
                              <TableCell className="text-xs font-mono max-w-[260px] truncate">
                                {ev.cancel_reason || "-"}
                              </TableCell>
                              <TableCell className="text-xs font-mono">
                                <button
                                  type="button"
                                  className="inline-flex items-center gap-1 text-xs underline-offset-2 hover:underline"
                                  onClick={async () => {
                                    try {
                                      if (!ev.booking_id) return;
                                      const ok = await safeCopyText(ev.booking_id);
                                      if (ok) {
                                        setCopiedBookingId(ev.booking_id);
                                        window.setTimeout(() => {
                                          setCopiedBookingId(null);
                                        }, 1200);
                                      }
                                    } catch (e) {
                                      console.error("Copy booking id failed", e);
                                    }
                                  }}
                                  data-testid={`match-risk-events-copy-booking-id-${ev.booking_id}`}
                                >
                                  <Copy className="h-3 w-3" />
                                  <span>
                                    {copiedBookingId === ev.booking_id
                                      ? "Copied"
                                      : ev.booking_id || "-"}
                                  </span>
                                </button>
                              </TableCell>
                            </TableRow>
                          ));
                        })()}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}
            </div>
          </div>
        </DrawerContent>
      </Drawer>
    </div>
  );
}
