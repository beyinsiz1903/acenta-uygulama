import React, { useState, useEffect, useCallback, useMemo } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { useNavigate } from "react-router-dom";
import {
  CalendarDays, Hotel, RefreshCw, AlertTriangle, CheckCircle2,
  XCircle, ChevronLeft, Search, Clock, TrendingUp,
  ArrowRight, Loader2, WifiOff, BarChart3, Eye,
  Filter, ChevronDown, ChevronUp, Activity, Bed,
  DollarSign, Ban, Calendar, FileSpreadsheet, RotateCcw,
  Send, User, Hash, BookOpen,
} from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   ACENTA MÜSAİTLİK PANELİ
   E-Tablo verilerinden otomatik senkronize edilmiş müsaitlik
   ═══════════════════════════════════════════════════════════════ */

// ── Helpers ──────────────────────────────────────────────

function formatDate(d) {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleString("tr-TR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return "—"; }
}

function formatShortDate(d) {
  if (!d) return "—";
  try {
    const dt = new Date(d + "T00:00:00");
    return dt.toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });
  } catch { return d; }
}

function formatDayName(d) {
  if (!d) return "";
  try {
    const dt = new Date(d + "T00:00:00");
    return dt.toLocaleDateString("tr-TR", { weekday: "short" });
  } catch { return ""; }
}

function formatPrice(p) {
  if (p === null || p === undefined) return "—";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 0 }).format(p);
}

function relativeTime(d) {
  if (!d) return "Bilinmiyor";
  const now = new Date();
  const then = new Date(d);
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "Az önce";
  if (diffMin < 60) return `${diffMin} dk önce`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} saat önce`;
  const diffDay = Math.floor(diffHour / 24);
  return `${diffDay} gün önce`;
}

function getToday() {
  return new Date().toISOString().split("T")[0];
}

function addDays(dateStr, days) {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().split("T")[0];
}

// ── Status Badge ─────────────────────────────────────────

function SyncBadge({ status }) {
  const map = {
    success: { bg: "bg-emerald-50", text: "text-emerald-700", icon: CheckCircle2, label: "Güncel" },
    no_change: { bg: "bg-blue-50", text: "text-blue-700", icon: CheckCircle2, label: "Değişiklik Yok" },
    error: { bg: "bg-red-50", text: "text-red-700", icon: XCircle, label: "Hata" },
    failed: { bg: "bg-red-50", text: "text-red-700", icon: XCircle, label: "Başarısız" },
    partial: { bg: "bg-amber-50", text: "text-amber-700", icon: AlertTriangle, label: "Kısmi" },
    not_configured: { bg: "bg-gray-100", text: "text-gray-500", icon: WifiOff, label: "Bağlı Değil" },
  };
  const s = map[status] || map.not_configured;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${s.bg} ${s.text}`}>
      <Icon className="w-3 h-3" />
      {s.label}
    </span>
  );
}

// ── Availability Cell ─────────────────────────────────────

function AvailabilityCell({ cell }) {
  if (!cell || (cell.price === null && cell.allotment === null)) {
    return (
      <div className="p-1.5 text-center rounded bg-gray-50 border border-gray-100 min-w-[80px]">
        <span className="text-xs text-gray-300">—</span>
      </div>
    );
  }

  const isStopped = cell.stop_sale === true;
  const allotment = cell.allotment;
  const isLow = allotment !== null && allotment > 0 && allotment <= 3;
  const isSoldOut = allotment !== null && allotment === 0;

  let bgClass = "bg-emerald-50 border-emerald-200";
  let textColor = "text-emerald-800";

  if (isStopped) {
    bgClass = "bg-red-50 border-red-200";
    textColor = "text-red-700";
  } else if (isSoldOut) {
    bgClass = "bg-gray-100 border-gray-200";
    textColor = "text-gray-500";
  } else if (isLow) {
    bgClass = "bg-amber-50 border-amber-200";
    textColor = "text-amber-700";
  }

  return (
    <div className={`p-1.5 text-center rounded border min-w-[80px] transition-all hover:shadow-sm ${bgClass}`}>
      {isStopped ? (
        <div className="flex flex-col items-center gap-0.5">
          <Ban className="w-3.5 h-3.5 text-red-500" />
          <span className="text-2xs font-medium text-red-600">KAPALI</span>
        </div>
      ) : (
        <>
          {cell.price !== null && cell.price !== undefined && (
            <p className={`text-xs font-bold ${textColor}`}>{formatPrice(cell.price)}</p>
          )}
          {allotment !== null && allotment !== undefined && (
            <p className={`text-2xs ${isSoldOut ? "text-gray-400" : isLow ? "text-amber-600 font-semibold" : "text-emerald-600"}`}>
              {isSoldOut ? "Tükendi" : `${allotment} oda`}
            </p>
          )}
        </>
      )}
    </div>
  );
}

// ── Hotel Summary Card ────────────────────────────────────

function HotelCard({ hotel, onSelect }) {
  return (
    <div
      onClick={() => onSelect(hotel.hotel_id)}
      className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md hover:border-blue-300 transition-all cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-sm">
            <Hotel className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
              {hotel.hotel_name}
            </h3>
            <p className="text-xs text-gray-500">{hotel.city} {hotel.stars ? `· ${"★".repeat(hotel.stars)}` : ""}</p>
          </div>
        </div>
        <SyncBadge status={hotel.sheet_connected ? (hotel.last_sync_status || "success") : "not_configured"} />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3">
        <div className="text-center p-2 bg-blue-50 rounded-lg">
          <p className="text-lg font-bold text-blue-700">{hotel.available_dates_count}</p>
          <p className="text-2xs text-blue-500">Müsait Gün</p>
        </div>
        <div className="text-center p-2 bg-emerald-50 rounded-lg">
          <p className="text-lg font-bold text-emerald-700">{hotel.room_types_count}</p>
          <p className="text-2xs text-emerald-500">Oda Tipi</p>
        </div>
        <div className="text-center p-2 bg-purple-50 rounded-lg">
          <p className="text-lg font-bold text-purple-700">{hotel.total_allotment}</p>
          <p className="text-2xs text-purple-500">Toplam Oda</p>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {hotel.last_data_update ? relativeTime(hotel.last_data_update) : "Veri yok"}
        </span>
        {hotel.min_price && (
          <span className="flex items-center gap-1 text-emerald-600 font-medium">
            <DollarSign className="w-3 h-3" />
            {formatPrice(hotel.min_price)} — {formatPrice(hotel.max_price)}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-center justify-center gap-1 text-xs text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">
        <span>Detaylı Müsaitlik</span>
        <ArrowRight className="w-3 h-3" />
      </div>
    </div>
  );
}

// ── Changes Timeline ──────────────────────────────────────

function ChangesTimeline({ changes }) {
  if (!changes || changes.length === 0) {
    return (
      <div className="text-center py-6 text-gray-400">
        <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">Henüz değişiklik kaydı yok</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
      {changes.slice(0, 20).map((ch, i) => (
        <div key={ch.run_id || i} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-gray-100 hover:border-gray-200 transition-colors">
          <div className={`mt-0.5 p-1.5 rounded-full flex-shrink-0 ${
            ch.upserted > 0 ? "bg-emerald-100 text-emerald-600" : "bg-blue-100 text-blue-600"
          }`}>
            {ch.upserted > 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-800 truncate">{ch.hotel_name}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {ch.upserted > 0
                ? `${ch.upserted} satır güncellendi (${ch.rows_read} okundu)`
                : `${ch.rows_read} satır kontrol edildi, değişiklik yok`
              }
            </p>
            <p className="text-2xs text-gray-400 mt-1">{formatDate(ch.started_at)}</p>
          </div>
          <span className={`px-2 py-0.5 rounded-full text-2xs font-medium ${
            ch.status === "success" ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
          }`}>
            {ch.trigger === "scheduled" ? "Otomatik" : "Manuel"}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Detail Grid View ──────────────────────────────────────

function AvailabilityGrid({ data, startDate, endDate, onDateChange }) {
  if (!data || !data.hotel) {
    return null;
  }

  const { hotel, dates, room_types, grid } = data;

  // Build lookup: grid_map[date][room_type] = cell
  const gridMap = useMemo(() => {
    const m = {};
    (grid || []).forEach((cell) => {
      if (!m[cell.date]) m[cell.date] = {};
      m[cell.date][cell.room_type] = cell;
    });
    return m;
  }, [grid]);

  // Stats
  const totalRooms = grid.reduce((acc, c) => acc + (c.allotment || 0), 0);
  const stopSaleCount = grid.filter((c) => c.stop_sale).length;
  const avgPrice = grid.filter((c) => c.price).reduce((acc, c, _, arr) => acc + c.price / arr.length, 0);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Hotel className="w-5 h-5 text-blue-600" />
            {hotel.name}
          </h2>
          <p className="text-sm text-gray-500">{hotel.city} {hotel.stars ? `· ${"★".repeat(hotel.stars)}` : ""}</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-1.5">
            <Calendar className="w-4 h-4 text-gray-400" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => onDateChange(e.target.value, endDate)}
              className="text-sm border-0 outline-none bg-transparent"
            />
            <span className="text-gray-300">→</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => onDateChange(startDate, e.target.value)}
              className="text-sm border-0 outline-none bg-transparent"
            />
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
          <p className="text-2xl font-bold text-blue-600">{dates.length}</p>
          <p className="text-xs text-gray-500">Tarih</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
          <p className="text-2xl font-bold text-emerald-600">{totalRooms}</p>
          <p className="text-xs text-gray-500">Toplam Oda</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
          <p className="text-2xl font-bold text-purple-600">{room_types.length}</p>
          <p className="text-xs text-gray-500">Oda Tipi</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-3 text-center">
          <p className="text-2xl font-bold text-red-500">{stopSaleCount}</p>
          <p className="text-xs text-gray-500">Kapalı Hücre</p>
        </div>
      </div>

      {/* Sync Info */}
      {data.last_sync_at && (
        <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Son senkronizasyon: {formatDate(data.last_sync_at)}</span>
          <SyncBadge status={data.last_sync_status || "success"} />
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs flex-wrap">
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-emerald-50 border border-emerald-200"></span>
          Müsait
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-amber-50 border border-amber-200"></span>
          Az Kaldı (≤3)
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-gray-100 border border-gray-200"></span>
          Tükendi
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-red-50 border border-red-200"></span>
          Satış Kapalı
        </span>
        <span className="flex items-center gap-1">
          <span className="w-4 h-4 rounded bg-gray-50 border border-gray-100"></span>
          Veri Yok
        </span>
      </div>

      {/* Grid */}
      {dates.length > 0 && room_types.length > 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-3 py-2.5 text-xs font-semibold text-gray-600 sticky left-0 bg-gray-50 z-10 min-w-[120px]">
                    <Bed className="w-3.5 h-3.5 inline mr-1" />
                    Oda Tipi
                  </th>
                  {dates.map((d) => (
                    <th key={d} className="text-center px-1 py-2.5 text-xs font-medium text-gray-500 min-w-[85px]">
                      <div>{formatShortDate(d)}</div>
                      <div className="text-2xs text-gray-400 font-normal">{formatDayName(d)}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {room_types.map((rt) => (
                  <tr key={rt} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-3 py-2 text-sm font-medium text-gray-800 sticky left-0 bg-white z-10 border-r border-gray-100">
                      {rt}
                    </td>
                    {dates.map((d) => {
                      const cell = gridMap[d]?.[rt] || null;
                      return (
                        <td key={`${d}-${rt}`} className="px-1 py-1.5">
                          <AvailabilityCell cell={cell} />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <CalendarDays className="w-12 h-12 mx-auto text-gray-300 mb-3" />
          <h3 className="text-lg font-medium text-gray-700 mb-1">Müsaitlik Verisi Bulunamadı</h3>
          <p className="text-sm text-gray-400">
            {data.sheet_connected
              ? "Sheet bağlantısı mevcut ancak seçilen tarih aralığında veri yok. Farklı tarih deneyin."
              : "Bu otel için henüz e-tablo bağlantısı yapılmamış. Admin ile iletişime geçin."
            }
          </p>
        </div>
      )}
    </div>
  );
}

// ── Write-Back Stats Panel ────────────────────────────────

function WriteBackStatsBar({ stats }) {
  if (!stats) return null;
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
      {[
        { label: "Kuyrukta", value: stats.queued || 0, color: "text-blue-600", bg: "bg-blue-50" },
        { label: "Tamamlandı", value: stats.completed || 0, color: "text-emerald-600", bg: "bg-emerald-50" },
        { label: "Başarısız", value: stats.failed || 0, color: "text-red-600", bg: "bg-red-50" },
        { label: "Yeniden Deneme", value: stats.retry || 0, color: "text-amber-600", bg: "bg-amber-50" },
        { label: "Toplam", value: stats.total || 0, color: "text-gray-700", bg: "bg-gray-50" },
      ].map((s) => (
        <div key={s.label} className={`${s.bg} rounded-lg p-2.5 text-center`}>
          <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
          <p className="text-2xs text-gray-500">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

// ── Write-Back Reservation Row ────────────────────────────

function WriteBackEventBadge({ type }) {
  const map = {
    reservation_created: { bg: "bg-blue-50", text: "text-blue-700", label: "Rezervasyon" },
    reservation_cancelled: { bg: "bg-red-50", text: "text-red-700", label: "Rez. İptal" },
    booking_confirmed: { bg: "bg-emerald-50", text: "text-emerald-700", label: "Booking Onay" },
    booking_cancelled: { bg: "bg-red-50", text: "text-red-700", label: "Booking İptal" },
    booking_amended: { bg: "bg-amber-50", text: "text-amber-700", label: "Değişiklik" },
  };
  const s = map[type] || { bg: "bg-gray-50", text: "text-gray-600", label: type };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-2xs font-medium ${s.bg} ${s.text}`}>
      {s.label}
    </span>
  );
}

function WriteBackStatusBadge({ status }) {
  const map = {
    queued: { bg: "bg-blue-50", text: "text-blue-600", icon: Clock, label: "Kuyrukta" },
    completed: { bg: "bg-emerald-50", text: "text-emerald-600", icon: CheckCircle2, label: "Yazıldı" },
    failed: { bg: "bg-red-50", text: "text-red-600", icon: XCircle, label: "Başarısız" },
    retry: { bg: "bg-amber-50", text: "text-amber-600", icon: RotateCcw, label: "Yeniden" },
    skipped_duplicate: { bg: "bg-gray-50", text: "text-gray-500", icon: CheckCircle2, label: "Atlanan" },
    skipped_no_connection: { bg: "bg-gray-50", text: "text-gray-500", icon: WifiOff, label: "Bağlantı Yok" },
    skipped_not_configured: { bg: "bg-gray-50", text: "text-gray-500", icon: WifiOff, label: "Ayar Yok" },
  };
  const s = map[status] || map.queued;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-medium ${s.bg} ${s.text}`}>
      <Icon className="w-3 h-3" />
      {s.label}
    </span>
  );
}

// ── Write-Back Panel (shown in detail view) ───────────────

function WriteBackPanel({ hotelId }) {
  const [stats, setStats] = useState(null);
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, resRes] = await Promise.all([
        api.get("/agency/writeback/stats"),
        api.get("/agency/writeback/reservations", {
          params: { hotel_id: hotelId || undefined, limit: 30 },
        }),
      ]);
      setStats(statsRes.data);
      setReservations(resRes.data?.items || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [hotelId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRetry = async (jobId) => {
    setRetrying(jobId);
    try {
      await api.post(`/agency/writeback/retry/${jobId}`);
      await fetchData();
    } catch {
      // silent
    } finally {
      setRetrying(null);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats */}
      <WriteBackStatsBar stats={stats} />

      {/* Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-start gap-2">
        <FileSpreadsheet className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
        <div className="text-xs text-blue-700">
          <p className="font-medium">E-Tablo Geri Yazım</p>
          <p className="mt-0.5">Rezervasyon ve booking işlemleri otomatik olarak otel e-tablosuna yazılır. Müsaitlik (allotment) otomatik güncellenir.</p>
        </div>
      </div>

      {/* Reservation List */}
      {reservations.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <BookOpen className="w-10 h-10 mx-auto text-gray-300 mb-2" />
          <p className="text-sm text-gray-500">Henüz write-back kaydı yok</p>
          <p className="text-xs text-gray-400 mt-1">Rezervasyon veya booking yapıldığında otomatik olarak burada görünecek.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-3 py-2.5 text-xs font-medium text-gray-500">İşlem</th>
                  <th className="text-left px-3 py-2.5 text-xs font-medium text-gray-500">Otel</th>
                  <th className="text-left px-3 py-2.5 text-xs font-medium text-gray-500">Misafir</th>
                  <th className="text-left px-3 py-2.5 text-xs font-medium text-gray-500">Tarih</th>
                  <th className="text-left px-3 py-2.5 text-xs font-medium text-gray-500">Oda</th>
                  <th className="text-right px-3 py-2.5 text-xs font-medium text-gray-500">Tutar</th>
                  <th className="text-center px-3 py-2.5 text-xs font-medium text-gray-500">Sheet</th>
                  <th className="text-center px-3 py-2.5 text-xs font-medium text-gray-500"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {reservations.map((r) => (
                  <tr key={r.job_id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-3 py-2.5">
                      <WriteBackEventBadge type={r.event_type} />
                    </td>
                    <td className="px-3 py-2.5 text-xs text-gray-700">{r.hotel_name}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-1.5">
                        <User className="w-3 h-3 text-gray-400" />
                        <span className="text-xs text-gray-800">{r.guest_name || "—"}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-xs text-gray-600">
                      {r.check_in && r.check_out ? `${r.check_in} → ${r.check_out}` : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-gray-600">{r.room_type || "—"}</td>
                    <td className="px-3 py-2.5 text-xs text-right font-medium text-gray-800">
                      {r.amount ? formatPrice(r.amount) : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <WriteBackStatusBadge status={r.writeback_status} />
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      {(r.writeback_status === "failed" || r.writeback_status === "retry") && (
                        <button
                          onClick={() => handleRetry(r.job_id)}
                          disabled={retrying === r.job_id}
                          className="p-1 rounded hover:bg-blue-50 text-blue-500 disabled:opacity-50"
                          title="Yeniden Dene"
                        >
                          <RotateCcw className={`w-3.5 h-3.5 ${retrying === r.job_id ? "animate-spin" : ""}`} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}


// ── Main Page Component ──────────────────────────────────

export default function AgencyAvailabilityPage() {
  const [view, setView] = useState("list"); // list | detail
  const [detailTab, setDetailTab] = useState("grid"); // grid | writeback
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedHotelId, setSelectedHotelId] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [changes, setChanges] = useState([]);
  const [changesLoading, setChangesLoading] = useState(false);

  const [startDate, setStartDate] = useState(getToday());
  const [endDate, setEndDate] = useState(addDays(getToday(), 14));

  const [searchTerm, setSearchTerm] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  // Auto-refresh interval
  const [autoRefresh, setAutoRefresh] = useState(true);

  // ── Fetch Hotels ─────────────────────────────────────

  const fetchHotels = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    setError("");
    try {
      const res = await api.get("/agency/availability");
      setHotels(res.data?.items || []);
    } catch (err) {
      setError(apiErrorMessage(err) || "Müsaitlik verileri yüklenemedi.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // ── Fetch Changes ────────────────────────────────────

  const fetchChanges = useCallback(async () => {
    setChangesLoading(true);
    try {
      const res = await api.get("/agency/availability/changes", { params: { limit: 30 } });
      setChanges(res.data?.items || []);
    } catch {
      // silent fail for changes
    } finally {
      setChangesLoading(false);
    }
  }, []);

  // ── Fetch Hotel Detail ───────────────────────────────

  const fetchDetail = useCallback(async (hotelId, sd, ed) => {
    setDetailLoading(true);
    try {
      const res = await api.get(`/agency/availability/${hotelId}`, {
        params: { start_date: sd, end_date: ed },
      });
      setDetailData(res.data);
    } catch (err) {
      setDetailData(null);
      setError(apiErrorMessage(err) || "Detay yüklenemedi.");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // ── Init ─────────────────────────────────────────────

  useEffect(() => {
    fetchHotels();
    fetchChanges();
  }, [fetchHotels, fetchChanges]);

  // Auto-refresh every 2 minutes
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchHotels(true);
      if (selectedHotelId && view === "detail") {
        fetchDetail(selectedHotelId, startDate, endDate);
      }
    }, 120000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchHotels, selectedHotelId, view, startDate, endDate, fetchDetail]);

  // ── Handlers ─────────────────────────────────────────

  const handleSelectHotel = (hotelId) => {
    setSelectedHotelId(hotelId);
    setView("detail");
    setDetailTab("grid");
    fetchDetail(hotelId, startDate, endDate);
  };

  const handleBack = () => {
    setView("list");
    setDetailData(null);
    setSelectedHotelId(null);
    setDetailTab("grid");
  };

  const handleDateChange = (sd, ed) => {
    setStartDate(sd);
    setEndDate(ed);
    if (selectedHotelId) {
      fetchDetail(selectedHotelId, sd, ed);
    }
  };

  const handleRefresh = () => {
    fetchHotels(true);
    fetchChanges();
    if (selectedHotelId && view === "detail") {
      fetchDetail(selectedHotelId, startDate, endDate);
    }
  };

  // ── Filtered Hotels ──────────────────────────────────

  const filteredHotels = useMemo(() => {
    if (!searchTerm) return hotels;
    const q = searchTerm.toLowerCase();
    return hotels.filter(
      (h) =>
        (h.hotel_name || "").toLowerCase().includes(q) ||
        (h.city || "").toLowerCase().includes(q)
    );
  }, [hotels, searchTerm]);

  // ── Render ───────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6 lg:p-8">
      <div className="max-w-[1400px] mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            {view === "detail" && (
              <button
                onClick={handleBack}
                className="p-2 rounded-lg hover:bg-white border border-gray-200 text-gray-600 transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            )}
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <CalendarDays className="w-6 h-6 text-blue-600" />
                Müsaitlik Takibi
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">
                {view === "list"
                  ? "E-tablolardan otomatik senkronize edilen otel müsaitlikleri"
                  : "Detaylı tarih ve oda tipi bazlı müsaitlik"
                }
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Auto-refresh toggle */}
            <label className="flex items-center gap-2 text-xs text-gray-500 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded text-blue-500 focus:ring-blue-400"
              />
              Otomatik Yenile
            </label>

            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
              Yenile
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Content */}
        {view === "list" ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Hotels List */}
            <div className="lg:col-span-2 space-y-4">
              {/* Search */}
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Otel ara..."
                  className="w-full pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
                />
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                </div>
              ) : filteredHotels.length === 0 ? (
                <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                  <Hotel className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                  <h3 className="text-lg font-medium text-gray-700 mb-1">
                    {hotels.length === 0 ? "Henüz Bağlı Otel Yok" : "Sonuç Bulunamadı"}
                  </h3>
                  <p className="text-sm text-gray-400">
                    {hotels.length === 0
                      ? "Bu acenta hesabına bağlı otel bulunmuyor."
                      : "Arama kriterlerinize uygun otel yok."
                    }
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredHotels.map((h) => (
                    <HotelCard key={h.hotel_id} hotel={h} onSelect={handleSelectHotel} />
                  ))}
                </div>
              )}
            </div>

            {/* Changes Sidebar */}
            <div className="space-y-4">
              <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-4">
                  <Activity className="w-4 h-4 text-blue-600" />
                  Son Güncellemeler
                </h3>
                {changesLoading ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                  </div>
                ) : (
                  <ChangesTimeline changes={changes} />
                )}
              </div>

              {/* Info Box */}
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <h4 className="font-medium text-blue-800 text-sm flex items-center gap-1.5 mb-2">
                  <BarChart3 className="w-4 h-4" />
                  E-Tablo Entegrasyonu
                </h4>
                <p className="text-xs text-blue-600 leading-relaxed">
                  Otellerin paylaştığı müsaitlik e-tabloları otomatik olarak senkronize edilir. 
                  Veriler her 5 dakikada bir güncellenir. Yeşil hücreler müsait odaları, sarılar 
                  azalan stoku, kırmızılar kapalı tarihleri gösterir.
                </p>
              </div>
            </div>
          </div>
        ) : (
          /* Detail View */
          <div className="space-y-4">
            {/* Tab Navigation */}
            <div className="flex items-center gap-1 bg-white rounded-xl border border-gray-200 p-1 w-fit">
              <button
                onClick={() => setDetailTab("grid")}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  detailTab === "grid"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <CalendarDays className="w-4 h-4" />
                Müsaitlik Grid
              </button>
              <button
                onClick={() => setDetailTab("writeback")}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  detailTab === "writeback"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <FileSpreadsheet className="w-4 h-4" />
                Rezervasyonlar & Geri Yazım
              </button>
            </div>

            {/* Tab Content */}
            {detailTab === "grid" ? (
              detailLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                </div>
              ) : (
                <AvailabilityGrid
                  data={detailData}
                  startDate={startDate}
                  endDate={endDate}
                  onDateChange={handleDateChange}
                />
              )
            ) : (
              <WriteBackPanel hotelId={selectedHotelId} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
