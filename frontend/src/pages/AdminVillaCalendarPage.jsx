import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, apiErrorMessage } from "../lib/api";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
      {text}
    </div>
  );
}

function useMonth(yearProp, monthProp) {
  const today = new Date();
  const [year, setYear] = useState(yearProp || today.getFullYear());
  const [month, setMonth] = useState(monthProp || today.getMonth() + 1); // 1-12

  const firstDay = useMemo(() => new Date(year, month - 1, 1), [year, month]);

  const days = useMemo(() => {
    const startWeekday = firstDay.getDay() || 7; // 1=Mon .. 7=Sun
    const daysInMonth = new Date(year, month, 0).getDate();

    const cells = [];
    // We render a 6x7 grid for simplicity
    const totalCells = 42;

    // start from Monday-based grid index
    for (let i = 0; i < totalCells; i += 1) {
      const dayOffset = i - (startWeekday - 1);
      const cellDate = new Date(year, month - 1, 1 + dayOffset);
      const inCurrentMonth = cellDate.getMonth() === month - 1;
      const iso = cellDate.toISOString().slice(0, 10);
      cells.push({ dateObj: cellDate, dateStr: iso, inCurrentMonth });
    }
    return cells;
  }, [firstDay, month, year]);

  const goPrev = () => {
    setMonth((prev) => {
      if (prev === 1) {
        setYear((y) => y - 1);
        return 12;
      }
      return prev - 1;
    });
  };

  const goNext = () => {
    setMonth((prev) => {
      if (prev === 12) {
        setYear((y) => y + 1);
        return 1;
      }
      return prev + 1;
    });
  };

  return { year, month, days, goPrev, goNext };
}

export default function AdminVillaCalendarPage() {
  const { productId } = useParams();

  const { year, month, days, goPrev, goNext } = useMonth();

  const [feeds, setFeeds] = useState([]);
  const [feedsLoading, setFeedsLoading] = useState(false);
  const [feedsError, setFeedsError] = useState("");
  const [newFeedUrl, setNewFeedUrl] = useState("");
  const [savingFeed, setSavingFeed] = useState(false);
  const [syncingFeedId, setSyncingFeedId] = useState("");

  const [calendarData, setCalendarData] = useState({ blocked_dates: [] });
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [calendarError, setCalendarError] = useState("");

  const blockedSet = useMemo(() => new Set(calendarData.blocked_dates || []), [
    calendarData,
  ]);

  const loadFeeds = async () => {
    if (!productId) return;
    setFeedsLoading(true);
    setFeedsError("");
    try {
      const res = await api.get("/admin/ical/feeds", {
        params: { product_id: productId },
      });
      setFeeds(res.data || []);
    } catch (e) {
      setFeedsError(apiErrorMessage(e));
    } finally {
      setFeedsLoading(false);
    }
  };

  const loadCalendar = async () => {
    if (!productId) return;
    setCalendarLoading(true);
    setCalendarError("");
    try {
      const res = await api.get("/admin/ical/calendar", {
        params: { product_id: productId, year, month },
      });
      setCalendarData(res.data || { blocked_dates: [] });
    } catch (e) {
      setCalendarError(apiErrorMessage(e));
    } finally {
      setCalendarLoading(false);
    }
  };

  useEffect(() => {
    void loadFeeds();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId]);

  useEffect(() => {
    void loadCalendar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId, year, month]);

  const addFeed = async () => {
    if (!productId || !newFeedUrl) return;
    setSavingFeed(true);
    setFeedsError("");
    try {
      await api.post("/admin/ical/feeds", {
        product_id: productId,
        url: newFeedUrl,
      });
      setNewFeedUrl("");
      await loadFeeds();
    } catch (e) {
      setFeedsError(apiErrorMessage(e));
    } finally {
      setSavingFeed(false);
    }
  };

  const syncFeed = async (feedId) => {
    if (!feedId) return;
    setSyncingFeedId(feedId);
    setFeedsError("");
    try {
      await api.post("/admin/ical/sync", { feed_id: feedId });
      await loadFeeds();
      await loadCalendar();
    } catch (e) {
      setFeedsError(apiErrorMessage(e));
    } finally {
      setSyncingFeedId("");
    }
  };

  const monthLabel = useMemo(() => {
    const d = new Date(year, month - 1, 1);
    return d.toLocaleDateString("tr-TR", { month: "long", year: "numeric" });
  }, [year, month]);

  return (
    <div
      className="space-y-4"
      data-testid="villa-calendar-root"
    >
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold">Villa Takvimi</h1>
            <Badge variant="secondary" className="text-2xs">
              iCal + Takvim v1
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Seçili villa ürünü için iCal feed&apos;lerini yönetin ve bloklu günleri
            takvim üzerinde görün.
          </p>
          {productId && (
            <div className="text-xs text-muted-foreground">
              Product ID: <span className="font-mono">{productId}</span>
            </div>
          )}
        </div>
        <Link
          to="/app/admin/catalog"
          className="text-xs text-muted-foreground hover:underline"
        >
          ← Kataloğa dön
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Calendar */}
        <Card className="p-3 text-xs lg:col-span-2">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={goPrev}
              >
                Önceki
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={goNext}
              >
                Sonraki
              </Button>
            </div>
            <div className="text-sm font-semibold">{monthLabel}</div>
            {calendarLoading && (
              <div className="text-xs text-muted-foreground">Yükleniyor...</div>
            )}
          </div>

          <FieldError text={calendarError} />

          <div className="mt-2 rounded-md border">
            <div className="grid grid-cols-7 border-b bg-muted/40 py-1 text-center text-2xs font-semibold">
              <div>Pzt</div>
              <div>Sal</div>
              <div>Çar</div>
              <div>Per</div>
              <div>Cum</div>
              <div>Cmt</div>
              <div>Paz</div>
            </div>
            <div className="grid grid-cols-7 text-xs">
              {days.map((d) => {
                const isBlocked = blockedSet.has(d.dateStr);
                const baseClasses = "h-10 border-r border-b px-1 py-1";
                const muted = !d.inCurrentMonth;
                const cls = [
                  baseClasses,
                  muted ? "text-muted-foreground/70 bg-muted/20" : "bg-background",
                  isBlocked ? "bg-red-50 text-red-800" : "",
                ]
                  .filter(Boolean)
                  .join(" ");

                const dayNum = d.dateObj.getDate();
                return (
                  <div
                    key={d.dateStr + String(dayNum)}
                    className={cls}
                    data-testid={`villa-calendar-day-${d.dateStr}`}
                  >
                    <div className="text-2xs font-semibold">{dayNum}</div>
                    {isBlocked && (
                      <div className="mt-1 rounded bg-red-500/10 text-2xs text-red-800">
                        Bloklu
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-3 flex items-center gap-3 text-2xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <span className="h-3 w-3 rounded bg-red-500/20" />
              <span>Bloklu gün (iCal)</span>
            </div>
          </div>
        </Card>

        {/* iCal Feeds Panel */}
        <Card className="p-3 text-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">iCal Feed&apos;ler</div>
            {feedsLoading && (
              <div className="text-xs text-muted-foreground">Yükleniyor...</div>
            )}
          </div>

          <FieldError text={feedsError} />

          <div className="space-y-2">
            <Label
              htmlFor="villa-ical-feed-url"
              className="text-xs"
            >
              Yeni iCal URL
            </Label>
            <div className="flex gap-2">
              <Input
                id="villa-ical-feed-url"
                data-testid="villa-ical-feed-url-input"
                placeholder="https://... veya mock://demo"
                className="h-8 text-xs"
                value={newFeedUrl}
                onChange={(e) => setNewFeedUrl(e.target.value)}
              />
              <Button
                size="sm"
                data-testid="villa-ical-feed-add-btn"
                onClick={addFeed}
                disabled={savingFeed || !newFeedUrl}
              >
                {savingFeed ? "Ekleniyor..." : "Ekle"}
              </Button>
            </div>
            <p className="text-2xs text-muted-foreground">
              Test ortamı için <code className="rounded bg-muted px-1">mock://</code> ile
              başlayan URL kullanarak örnek bloklar oluşturabilirsiniz.
            </p>
          </div>

          <div className="mt-3 rounded-md border overflow-hidden">
            <div className="grid grid-cols-4 bg-muted/40 px-2 py-2 text-2xs font-semibold">
              <div>URL</div>
              <div>Status</div>
              <div>Last Sync</div>
              <div className="text-right">Aksiyon</div>
            </div>
            <div className="max-h-60 overflow-y-auto text-xs">
              {feeds.map((f) => (
                <div
                  key={f.id}
                  className="grid grid-cols-4 items-center border-t px-2 py-2"
                  data-testid={`villa-ical-feed-row-${f.id}`}
                >
                  <div className="truncate" title={f.url}>
                    {f.url}
                  </div>
                  <div>
                    <Badge
                      variant={f.status === "active" ? "secondary" : "outline"}
                      className="text-2xs"
                    >
                      {f.status || "-"}
                    </Badge>
                  </div>
                  <div className="truncate" title={f.last_sync_at || "-"}>
                    {f.last_sync_at ? String(f.last_sync_at).slice(0, 19) : "-"}
                  </div>
                  <div className="text-right">
                    <Button
                      size="xs"
                      className="h-7 px-2 text-2xs"
                      data-testid={`villa-ical-feed-sync-btn-${f.id}`}
                      onClick={() => syncFeed(f.id)}
                      disabled={syncingFeedId === f.id}
                    >
                      {syncingFeedId === f.id ? "Sync..." : "Sync Now"}
                    </Button>
                  </div>
                </div>
              ))}
              {!feeds.length && !feedsLoading && (
                <div className="px-2 py-4 text-xs text-muted-foreground">
                  Henüz feed yok.
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
