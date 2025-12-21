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
      {/* Header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-foreground">Pilot Dashboard</h1>
          <Badge variant="outline" className="text-xs">
            Canlı Veri · Son 7 Gün
          </Badge>
        </div>

        <p className="text-sm text-muted-foreground max-w-2xl">
          Pilot KPI'larını ve detaylı breakdown'ları görüntüleyin.
        </p>

        <p className="text-xs text-muted-foreground">
          <strong>{meta.activeAgenciesCount ?? 0}</strong> aktif acenta ·{" "}
          <strong>{meta.activeHotelsCount ?? 0}</strong> aktif otel ·{" "}
          <strong>{meta.whatsappClickedCount ?? 0}</strong> WhatsApp click
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Deneme Rezervasyonları</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{kpis.totalRequests ?? 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Acenta başına ortalama <strong>{Number(kpis.avgRequestsPerAgency ?? 0).toFixed(1)}</strong> talep
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">WhatsApp Kullanımı</CardTitle>
            <MessageCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pct(kpis.whatsappShareRate)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Toplam rezervasyonlarda WhatsApp paylaşım oranı
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Otel Panel Aksiyonu</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pct(kpis.hotelPanelActionRate)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Otel aksiyon alma oranı (onay + iptal)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Ortalama Onay Süresi</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Number(kpis.avgApprovalMinutes ?? 0)} dk</div>
            <p className="text-xs text-muted-foreground mt-1">Talep → Otel onayı ortalama süresi</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Akış Tamamlama</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pct(kpis.flowCompletionRate)}%</div>
            <p className="text-xs text-muted-foreground mt-1">Onaylı rezervasyon oranı</p>
          </CardContent>
        </Card>

        {/* Optional extra meta card */}
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Confirmed Bazlı WhatsApp</CardTitle>
            <MessageCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pct(meta.whatsappShareRateConfirmed)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Confirmed booking'lerde WhatsApp oranı (secondary)
            </p>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {!hasBreakdown ? (
        <EmptyState title="Breakdown verisi yok" subtitle="API breakdown alanı dönmüyor veya boş." />
      ) : (
        <div className="space-y-6">
          {/* Daily Trend */}
          <Card>
            <CardHeader>
              <CardTitle>Günlük Rezervasyon Trendi</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={filledByDay}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="total" stroke={chartColors.total} name="Toplam" strokeWidth={2} />
                  <Line type="monotone" dataKey="confirmed" stroke={chartColors.confirmed} name="Onaylı" strokeWidth={2} />
                  <Line type="monotone" dataKey="cancelled" stroke={chartColors.cancelled} name="İptal" strokeWidth={2} />
                  <Line type="monotone" dataKey="whatsapp" stroke={chartColors.whatsapp} name="WhatsApp" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
              <p className="mt-3 text-xs text-muted-foreground">
                Not: Günler zero-fill ile 7 gün sabit gösterilir.
              </p>
            </CardContent>
          </Card>

          {/* Hotel Performance */}
          <Card>
            <CardHeader>
              <CardTitle>Otel Bazlı Performans</CardTitle>
            </CardHeader>
            <CardContent>
              {Array.isArray(breakdown.by_hotel) && breakdown.by_hotel.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={breakdown.by_hotel}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="hotel_name"
                        tick={{ fontSize: 12 }}
                        interval={0}
                        angle={-10}
                        height={50}
                      />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="confirmed" fill={chartColors.confirmed} name="Onaylı" />
                      <Bar dataKey="cancelled" fill={chartColors.cancelled} name="İptal" />
                    </BarChart>
                  </ResponsiveContainer>

                  <div className="mt-4 grid gap-2 md:grid-cols-3 text-sm text-muted-foreground">
                    <div>
                      <span className="font-medium text-foreground">Action Rate:</span>{" "}
                      {pct(breakdown.by_hotel[0]?.action_rate)}%
                    </div>
                    <div>
                      <span className="font-medium text-foreground">Avg Approval:</span>{" "}
                      {Number(breakdown.by_hotel[0]?.avg_approval_minutes ?? 0)} dk
                    </div>
                    <div>
                      <span className="font-medium text-foreground">Action Count:</span>{" "}
                      {Number(breakdown.by_hotel[0]?.action_count ?? 0)}
                    </div>
                  </div>
                </>
              ) : (
                <EmptyState title="Otel breakdown boş" subtitle="Bu aralıkta otel bazlı veri yok." />
              )}
            </CardContent>
          </Card>

          {/* Agency Table */}
          <Card>
            <CardHeader>
              <CardTitle>Acenta Bazlı Performans</CardTitle>
            </CardHeader>
            <CardContent>
              {Array.isArray(breakdown.by_agency) && breakdown.by_agency.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Acenta</TableHead>
                      <TableHead>Toplam</TableHead>
                      <TableHead>Onaylı</TableHead>
                      <TableHead>Conversion</TableHead>
                      <TableHead>WhatsApp</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {breakdown.by_agency.map((a) => (
                      <TableRow key={a.agency_id}>
                        <TableCell className="font-medium">{a.agency_name}</TableCell>
                        <TableCell>{a.total}</TableCell>
                        <TableCell>{a.confirmed}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{pct(a.conversion_rate)}%</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{pct(a.whatsapp_rate)}%</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <EmptyState title="Acenta breakdown boş" subtitle="Bu aralıkta acenta bazlı veri yok." />
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
