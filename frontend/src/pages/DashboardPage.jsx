import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { ArrowRight, CalendarDays, Ticket, Users, Layers, AlertCircle } from "lucide-react";

import { api, apiErrorMessage, getUser } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";

function StatCard({ title, value, icon: Icon, to, testId }) {
  return (
    <Card className="rounded-2xl shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex items-end justify-between">
        <div className="text-3xl font-semibold text-foreground" data-testid={testId}>
          {value}
        </div>
        {to ? (
          <Button asChild variant="outline" size="sm" className="gap-2">
            <Link to={to}>
              Aç <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const user = getUser();
  const isHotel = (user?.roles || []).includes("hotel_admin") || (user?.roles || []).includes("hotel_staff");
  const isAgency = (user?.roles || []).includes("agency_admin") || (user?.roles || []).includes("agency_agent");


  const [caseCounters, setCaseCounters] = useState({ open: 0, waiting: 0, in_progress: 0 });

  const [resSummary, setResSummary] = useState([]);
  const [sales, setSales] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      setError("");
      try {
        const [a, b, c] = await Promise.all([
          api.get("/reports/reservations-summary"),
          api.get("/reports/sales-summary"),
          api.get("/ops-cases/counters"),
        ]);
        setResSummary(a.data || []);
        setSales(b.data || []);
        setCaseCounters(c.data || { open: 0, waiting: 0, in_progress: 0 });
      } catch (e) {
        const msg = apiErrorMessage(e);
        // "Not Found" durumunu veri yok / rapor devre df olarak yorumlayp
        // dashboard'da krmz hata gstermek yerine sessizce bofa dryoruz.
        if (msg !== "Not Found") {
          const status = e?.response?.status;
          if (status !== 403) setError(msg);
        }
      }
    })();
  }, []);

  const totals = useMemo(() => {
    const map = new Map(resSummary.map((r) => [r.status, r.count]));
    const total = resSummary.reduce((a, r) => a + Number(r.count || 0), 0);
    return {
      total,
      pending: map.get("pending") || 0,
      confirmed: map.get("confirmed") || 0,
      paid: map.get("paid") || 0,
    };
  }, [resSummary]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Dashboard</h2>
          <p className="text-sm text-muted-foreground">
            Rezervasyon ve satış özetini buradan takip edebilirsin.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" data-testid="dash-go-products">
            <Link to="/app/products">Ürünler</Link>
          </Button>
          <Button asChild data-testid="dash-go-reservations">
            <Link to="/app/reservations">Rezervasyonlar</Link>
          </Button>
        </div>
      </div>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="dash-error">
          {error}
        </div>
      ) : null}

      {totals.total === 0 && !error && (
        <div className="rounded-2xl border border-muted px-4 py-3 text-xs text-muted-foreground">
          Son 30 günde rezervasyon verisi bulunamadı. Veriler geldikçe özet kartlar otomatik güncellenecektir.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Toplam Rezervasyon"
          value={totals.total}
          icon={Ticket}
          to={isHotel ? "/app/hotel/bookings" : isAgency ? "/app/agency/bookings" : undefined}
          testId="stat-total"
        />
        <StatCard
          title="Beklemede"
          value={totals.pending}
          icon={CalendarDays}
          to={isHotel ? "/app/hotel/bookings?status=pending" : isAgency ? "/app/agency/bookings?status=pending" : undefined}
          testId="stat-pending"
        />
        <StatCard
          title="Onaylı"
          value={totals.confirmed}
          icon={Ticket}
          to={isHotel ? "/app/hotel/bookings?status=confirmed" : isAgency ? "/app/agency/bookings?status=confirmed" : undefined}
          testId="stat-confirmed"
        />
        <StatCard
          title="Ödendi"
          value={totals.paid}
          icon={Ticket}
          to={isHotel ? "/app/hotel/bookings?status=paid" : isAgency ? "/app/agency/bookings?status=paid" : undefined}
          testId="stat-paid"
        />
      </div>

      {/* Ops case-first summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        <StatCard
          title="Açık Case"
          value={caseCounters.open}
          icon={AlertCircle}
          to="/ops/cases?status=open"
          testId="stat-cases-open"
        />
        <StatCard
          title="Beklemede Case"
          value={caseCounters.waiting}
          icon={AlertCircle}
          to="/ops/cases?status=waiting"
          testId="stat-cases-waiting"
        />
        <StatCard
          title="İşlemde Case"
          value={caseCounters.in_progress}
          icon={AlertCircle}
          to="/ops/cases?status=in_progress"
          testId="stat-cases-inprogress"
        />
      </div>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Son 14 Gün Satış Grafiği</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72" data-testid="sales-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sales} margin={{ left: 8, right: 8 }}>
                <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="revenue" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">
            Not: Gelir hesaplaması rezervasyon total_price üzerinden yapılır (v1).
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="rounded-2xl shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
              <Layers className="h-4 w-4 text-muted-foreground" />
              Ürün Kataloğu
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Tur / konaklama / transfer ürünlerini oluştur.
            <div className="mt-3">
              <Button asChild variant="outline" size="sm">
                <Link to="/app/products">Ürün Ekle</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
              <CalendarDays className="h-4 w-4 text-muted-foreground" />
              Müsaitlik Takvimi
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Kapasite ve fiyatı tarih bazında güncelle.
            <div className="mt-3">
              <Button variant="outline" size="sm" disabled>
                Yakında
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
              <Users className="h-4 w-4 text-muted-foreground" />
              CRM
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Lead ve teklif akışını yönet.
            <div className="mt-3">
              <Button variant="outline" size="sm" disabled>
                Yakında
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2">
              <Ticket className="h-4 w-4 text-muted-foreground" />
              Voucher
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Rezervasyon detayından voucher yazdır.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
