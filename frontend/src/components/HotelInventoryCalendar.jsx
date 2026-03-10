import React, { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2, AlertCircle, Ban } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { api, apiErrorMessage } from "../lib/api";

const WEEKDAYS_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"];

function daysInMonth(year, month) {
  return new Date(year, month + 1, 0).getDate();
}

function firstDayOfMonth(year, month) {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1; // Monday = 0
}

function formatDate(y, m, d) {
  return `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

function formatPrice(val) {
  if (val == null) return "-";
  return new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(val);
}

function monthLabel(year, month) {
  const labels = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
  ];
  return `${labels[month]} ${year}`;
}

export function HotelInventoryCalendar({ hotelId }) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [selectedRoomType, setSelectedRoomType] = useState("all");
  const [expandedDate, setExpandedDate] = useState(null);

  useEffect(() => {
    if (!hotelId) return;
    loadData();
  }, [hotelId, year, month]);

  async function loadData() {
    setLoading(true);
    setError("");
    try {
      const startDate = formatDate(year, month, 1);
      const endDay = daysInMonth(year, month);
      const endDate = formatDate(year, month, endDay);
      const resp = await api.get(
        `/agency/availability/${hotelId}?start_date=${startDate}&end_date=${endDate}`
      );
      setData(resp.data);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function prevMonth() {
    if (month === 0) { setYear(year - 1); setMonth(11); }
    else setMonth(month - 1);
    setExpandedDate(null);
  }

  function nextMonth() {
    if (month === 11) { setYear(year + 1); setMonth(0); }
    else setMonth(month + 1);
    setExpandedDate(null);
  }

  // Build a lookup: { "2026-03-15": [ {room_type, price, allotment, stop_sale}, ...] }
  const gridByDate = useMemo(() => {
    if (!data?.grid) return {};
    const map = {};
    for (const cell of data.grid) {
      if (!map[cell.date]) map[cell.date] = [];
      map[cell.date].push(cell);
    }
    return map;
  }, [data]);

  const roomTypes = data?.room_types || [];

  const totalDays = daysInMonth(year, month);
  const startOffset = firstDayOfMonth(year, month);

  const todayStr = formatDate(today.getFullYear(), today.getMonth(), today.getDate());

  function getCellSummary(dateStr) {
    const rooms = gridByDate[dateStr];
    if (!rooms || rooms.length === 0) return null;

    const filtered = selectedRoomType === "all"
      ? rooms
      : rooms.filter((r) => r.room_type === selectedRoomType);

    if (filtered.length === 0) return null;

    const minPrice = Math.min(...filtered.filter((r) => r.price != null).map((r) => r.price));
    const totalAllotment = filtered.reduce((sum, r) => sum + (r.allotment || 0), 0);
    const anyStopSale = filtered.some((r) => r.stop_sale);
    const allStopSale = filtered.every((r) => r.stop_sale);

    return { minPrice: isFinite(minPrice) ? minPrice : null, totalAllotment, anyStopSale, allStopSale, rooms: filtered };
  }

  function getCellColor(summary) {
    if (!summary) return "bg-muted/30";
    if (summary.allStopSale) return "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800";
    if (summary.totalAllotment === 0) return "bg-orange-50 dark:bg-orange-950/30 border-orange-200 dark:border-orange-800";
    if (summary.totalAllotment <= 3) return "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800";
    return "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800";
  }

  return (
    <Card data-testid="hotel-inventory-calendar">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <CardTitle className="text-base font-semibold" data-testid="calendar-title">
            Envanter Takvimi
          </CardTitle>
          <div className="flex items-center gap-2">
            {roomTypes.length > 0 && (
              <Select
                value={selectedRoomType}
                onValueChange={(v) => { setSelectedRoomType(v); setExpandedDate(null); }}
              >
                <SelectTrigger className="w-[160px] h-8 text-xs" data-testid="calendar-room-type-filter">
                  <SelectValue placeholder="Oda Tipi" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tüm Oda Tipleri</SelectItem>
                  {roomTypes.map((rt) => (
                    <SelectItem key={rt} value={rt}>{rt}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between mt-2">
          <Button variant="ghost" size="sm" onClick={prevMonth} data-testid="calendar-prev-month">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium" data-testid="calendar-month-label">
            {monthLabel(year, month)}
          </span>
          <Button variant="ghost" size="sm" onClick={nextMonth} data-testid="calendar-next-month">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {loading && (
          <div className="flex items-center justify-center py-12 gap-2">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">Envanter yükleniyor...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-sm text-destructive py-4">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!loading && !error && (
          <>
            {/* Legend */}
            <div className="flex flex-wrap gap-3 mb-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-emerald-100 dark:bg-emerald-900/40 border border-emerald-300" />
                Müsait
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-amber-100 dark:bg-amber-900/40 border border-amber-300" />
                Az Kaldı
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-orange-100 dark:bg-orange-900/40 border border-orange-300" />
                Kontenjan Yok
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-red-100 dark:bg-red-900/40 border border-red-300" />
                Satış Durduruldu
              </span>
            </div>

            {/* Weekday headers */}
            <div className="grid grid-cols-7 gap-1 mb-1">
              {WEEKDAYS_TR.map((d) => (
                <div key={d} className="text-center text-xs font-medium text-muted-foreground py-1">
                  {d}
                </div>
              ))}
            </div>

            {/* Calendar grid */}
            <div className="grid grid-cols-7 gap-1">
              {/* Empty offset cells */}
              {Array.from({ length: startOffset }).map((_, i) => (
                <div key={`empty-${i}`} className="aspect-square" />
              ))}

              {/* Day cells */}
              {Array.from({ length: totalDays }).map((_, i) => {
                const day = i + 1;
                const dateStr = formatDate(year, month, day);
                const summary = getCellSummary(dateStr);
                const isToday = dateStr === todayStr;
                const isPast = dateStr < todayStr;
                const isExpanded = expandedDate === dateStr;

                return (
                  <button
                    key={day}
                    data-testid={`calendar-day-${dateStr}`}
                    onClick={() => {
                      if (summary) setExpandedDate(isExpanded ? null : dateStr);
                    }}
                    className={`
                      relative rounded-lg border text-left p-1 min-h-[72px] transition-all
                      ${getCellColor(summary)}
                      ${isPast ? "opacity-50" : ""}
                      ${isToday ? "ring-2 ring-primary/50" : ""}
                      ${isExpanded ? "ring-2 ring-primary" : ""}
                      ${summary ? "cursor-pointer hover:shadow-md" : "cursor-default"}
                    `}
                  >
                    <div className={`text-xs font-medium ${isToday ? "text-primary" : "text-foreground"}`}>
                      {day}
                    </div>
                    {summary ? (
                      <div className="mt-0.5 space-y-0.5">
                        {summary.allStopSale ? (
                          <div className="flex items-center gap-0.5">
                            <Ban className="h-3 w-3 text-red-500" />
                            <span className="text-[10px] text-red-600 dark:text-red-400 font-medium">Kapalı</span>
                          </div>
                        ) : (
                          <>
                            {summary.minPrice != null && (
                              <div className="text-[10px] font-semibold text-foreground leading-tight">
                                {formatPrice(summary.minPrice)} TL
                              </div>
                            )}
                            <div className={`text-[10px] leading-tight ${summary.totalAllotment <= 3 ? "text-amber-700 dark:text-amber-400 font-medium" : "text-muted-foreground"}`}>
                              {summary.totalAllotment} oda
                            </div>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="text-[10px] text-muted-foreground/50 mt-1">-</div>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Expanded day detail */}
            {expandedDate && gridByDate[expandedDate] && (
              <ExpandedDayDetail
                dateStr={expandedDate}
                rooms={selectedRoomType === "all" ? gridByDate[expandedDate] : gridByDate[expandedDate].filter((r) => r.room_type === selectedRoomType)}
                onClose={() => setExpandedDate(null)}
              />
            )}

            {/* Stats bar */}
            {data && (
              <div className="flex flex-wrap items-center gap-4 mt-4 pt-3 border-t text-xs text-muted-foreground" data-testid="calendar-stats">
                <span>Toplam kayıt: <strong className="text-foreground">{data.total_records}</strong></span>
                <span>Oda tipleri: <strong className="text-foreground">{roomTypes.join(", ") || "-"}</strong></span>
                {data.sheet_connected && (
                  <Badge variant="outline" className="text-[10px] border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-300">
                    E-Tablo Bağlı
                  </Badge>
                )}
                {data.last_sync_at && (
                  <span>Son sync: <strong className="text-foreground">{new Date(data.last_sync_at).toLocaleString("tr-TR")}</strong></span>
                )}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ExpandedDayDetail({ dateStr, rooms, onClose }) {
  const dateParts = dateStr.split("-");
  const displayDate = `${dateParts[2]}/${dateParts[1]}/${dateParts[0]}`;

  return (
    <div
      className="mt-3 rounded-xl border bg-card shadow-sm p-4 animate-in slide-in-from-top-2 duration-200"
      data-testid={`calendar-day-detail-${dateStr}`}
    >
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-foreground">{displayDate} Detay</h4>
        <Button variant="ghost" size="sm" onClick={onClose} className="h-6 px-2 text-xs">
          Kapat
        </Button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {rooms.map((r) => (
          <div
            key={r.room_type}
            className={`rounded-lg border px-3 py-2 ${r.stop_sale ? "bg-red-50 dark:bg-red-950/20 border-red-200" : "bg-background"}`}
            data-testid={`day-detail-room-${r.room_type}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold">{r.room_type}</span>
              {r.stop_sale && (
                <Badge variant="destructive" className="text-[10px] h-4 px-1">Satış Durduruldu</Badge>
              )}
            </div>
            <div className="mt-1 flex items-baseline gap-3 text-xs">
              <span className="text-muted-foreground">Fiyat:</span>
              <span className="font-semibold text-foreground">
                {r.price != null ? `${formatPrice(r.price)} TL` : "-"}
              </span>
            </div>
            <div className="flex items-baseline gap-3 text-xs">
              <span className="text-muted-foreground">Kontenjan:</span>
              <span className={`font-semibold ${(r.allotment || 0) <= 3 ? "text-amber-600" : "text-foreground"}`}>
                {r.allotment != null ? `${r.allotment} oda` : "-"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
