import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { AlertCircle, Clock, CheckCircle2, MessageCircle, TrendingUp, Loader2 } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

/**
 * Env strategy:
 * - Vite: import.meta.env.VITE_BACKEND_URL
 * - CRA fallback: process.env.REACT_APP_BACKEND_URL
 */
const BACKEND_URL =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_BACKEND_URL) ||
  process.env.REACT_APP_BACKEND_URL ||
  "";

/** Token key fallback (projelerde farklı olabiliyor) */
function getAuthToken() {
  return (
    localStorage.getItem("token") ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("jwt") ||
    ""
  );
}

/**
 * Safer date key generator:
 * - Backend by_day date format: YYYY-MM-DD
 * - We generate the same format in local timezone (TR) to avoid UTC shift.
 */
function formatLocalYYYYMMDD(date) {
  // Use Intl to format parts reliably in local time
  const parts = new Intl.DateTimeFormat("en-CA", { // en-CA => YYYY-MM-DD
    timeZone: "Europe/Istanbul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
  return parts; // already YYYY-MM-DD
}

/** Helper: Fill missing days with zeros (keeps order, last N days) */
function fillMissingDays(byDayData = [], days = 7) {
  const map = new Map(byDayData.map((d) => [d.date, d]));
  const filled = [];

  const now = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);

    const dateStr = formatLocalYYYYMMDD(d);
    const existing = map.get(dateStr);

    filled.push(
      existing || { date: dateStr, total: 0, confirmed: 0, cancelled: 0, whatsapp: 0 }
    );
  }

  return filled;
}

/** Small helper */
function pct(x) {
  const v = Number.isFinite(x) ? x : 0;
  return Math.round(v * 100);
}

/** Empty state */
function EmptyState({ title, subtitle }) {
  return (
    <div className="flex items-center justify-center py-14">
      <div className="text-center space-y-2">
        <AlertCircle className="h-10 w-10 text-muted-foreground mx-auto" />
        <p className="text-sm font-medium">{title}</p>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>
    </div>
  );
}

export default function AdminPilotDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        setError("");

        const token = getAuthToken();
        if (!BACKEND_URL) throw new Error("BACKEND_URL tanımlı değil (VITE_BACKEND_URL / REACT_APP_BACKEND_URL).");
        if (!token) throw new Error("Token bulunamadı (localStorage: token/access_token/jwt).");

        const resp = await axios.get(`${BACKEND_URL}/api/admin/pilot/summary?days=7`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        setData(resp.data);
      } catch (e) {
        console.error("Pilot summary fetch failed:", e);
        const msg =
          e?.response?.data?.detail ||
          e?.message ||
          "Veri yüklenemedi (bilinmeyen hata)";
        setError(String(msg));
      } finally {
        setLoading(false);
      }
    };

    run();
  }, []);

  const kpis = data?.kpis || {};
  const meta = data?.meta || {};
  const breakdown = data?.breakdown || {};

  const filledByDay = useMemo(() => fillMissingDays(breakdown.by_day || [], 7), [breakdown.by_day]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return <EmptyState title="Dashboard yüklenemedi" subtitle={error} />;
  }

  if (!data) {
    return <EmptyState title="Veri yok" subtitle="API boş response döndü." />;
  }

  const hasBreakdown =
    Array.isArray(breakdown.by_day) ||
    Array.isArray(breakdown.by_hotel) ||
    Array.isArray(breakdown.by_agency);

  // Theme-friendly chart colors via CSS variables (fallbacks included)
  const chartColors = {
    total: "hsl(var(--primary, 222 84% 58%))",
    confirmed: "hsl(var(--success, 142 71% 45%))",
    cancelled: "hsl(var(--warning, 38 92% 50%))",
    whatsapp: "hsl(var(--accent, 262 83% 58%))",
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-foreground">Pilot Dashboard</h1>
          <Badge variant="outline" className="text-xs border-emerald-500/50 text-emerald-700 dark:text-emerald-300">
            Canlı Veri · Son 7 Gün
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground max-w-2xl">
          Syroce Acenta pilotunun ilk 7 günündeki <strong>davranışsal KPI&apos;larını</strong> özetler.
          Veriler gerçek zamanlı olarak hesaplanmaktadır.
        </p>
        {data?.meta && (
          <p className="text-xs text-muted-foreground">
            <strong>{data.meta.activeAgenciesCount}</strong> aktif acenta, <strong>{data.meta.activeHotelsCount}</strong> aktif otel
          </p>
        )}
      </div>

      {/* Üst satır: Aktivasyon & hacim */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Deneme Rezervasyonları</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalRequests}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Toplam talep · Hedef: ≥ 10 (7 günde)
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Acenta başına ortalama <strong>{avgRequestsPerAgency.toFixed(1)}</strong> talep
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">WhatsApp Kullanımı</CardTitle>
            <MessageCircle className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(whatsappShareRate * 100)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Confirmed ekranda <strong>WhatsApp&apos;a Gönder</strong> kullanımı · Hedef: ≥ 70%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Otel Panel Aksiyonu</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-sky-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(hotelPanelActionRate * 100)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Taleplerin panelden <strong>Onayla / Reddet</strong> ile işlem görme oranı · Hedef: ≥ 80%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Orta satır: Hız & güven */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Ortalama Onay Süresi</CardTitle>
            <Clock className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgApprovalMinutes} dk</div>
            <p className="text-xs text-muted-foreground mt-1">
              Talep → Otel onayı ortalama süresi · Hedef: &lt; 120 dk (ideal: &lt; 30 dk)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Mutabakat Ekranı Kullanımı</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-muted-foreground">Acentalar</span>
              <span className="font-semibold">{Math.round(agenciesViewedSettlements * 100)}%</span>
            </div>
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-muted-foreground">Oteller</span>
              <span className="font-semibold">{Math.round(hotelsViewedSettlements * 100)}%</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              En az bir kez <strong>Mutabakat</strong> ekranına giren aktif kullanıcı oranı.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Akış Tamamlama Oranı</CardTitle>
            <AlertCircle className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(flowCompletionRate * 100)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Hızlı Rezervasyon akışını <strong>BookingConfirmed</strong> ile bitirenlerin oranı · Hedef: ≥ 70%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Alt: Yorum / karar matrisi */}
      <Card>
        <CardHeader>
          <CardTitle>Pilot Sonu Yorum Matrisi</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            Bu tablo, ilk 7 gün sonunda <strong>"pilot çalışıyor mu?"</strong> sorusuna net cevap vermek için
            kullanılabilir. Rakamları gerçek verilerle değiştirdiğinizde hangi alana odaklanmanız gerektiği
            hemen ortaya çıkar.
          </p>
          <Separator />
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <p className="font-medium text-foreground">KPI yorumu</p>
              <ul className="list-disc list-inside space-y-1">
                <li>KPI-1 &amp; KPI-2 yüksekse → Acenta ürünü benimsemiş demektir.</li>
                <li>KPI-3 düşükse → Otel UI / bildirim / alışkanlık tarafına odaklanın.</li>
                <li>KPI-4 yüksekse → Otel onay süreçleri yavaş; hız için görüşme yapın.</li>
                <li>KPI-5 açılıyorsa → Mutabakat güven veriyor; parasal ilişki kuruluyor.</li>
                <li>KPI-6 düşükse → Akıştaki sürtünme noktasını (özellikle Adım 2 &amp; 3) inceleyin.</li>
              </ul>
            </div>
            <div className="space-y-1">
              <p className="font-medium text-foreground">Sonraki adım önerileri</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Acenta güçlü, otel zayıfsa → <strong>Gelen Rezervasyonlar</strong> ekranını parlatın.</li>
                <li>Her iki taraf da düşükse → Pilot iletişimi ve onboarding&apos;i gözden geçirin.</li>
                <li>Metrix iyi, ama kullanım azsa → Fiyatlama / ticari model konuşma zamanı gelmiş demektir.</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
