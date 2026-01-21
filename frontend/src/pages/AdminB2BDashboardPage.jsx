import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, Activity, ShieldAlert, Users } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";

function formatAmount(value, currency = "EUR") {
  if (value == null) return "-";
  const num = Number(value);
  if (Number.isNaN(num)) return "-";
  return `${num.toFixed(2)} ${currency}`;
}

function RiskBadge({ status }) {
  if (status === "over_limit") {
    return <Badge variant="destructive">Limit aşıldı</Badge>;
  }
  if (status === "near_limit") {
    return <Badge variant="secondary">Limite yakın</Badge>;
  }
  return <Badge variant="outline">Normal</Badge>;
}

export default function AdminB2BDashboardPage() {
  const [agencies, setAgencies] = useState([]);
  const [funnelItems, setFunnelItems] = useState([]);
  const [announcements, setAnnouncements] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const [agRes, fnRes, annRes] = await Promise.all([
          api.get("/admin/b2b/agencies/summary"),
          api.get("/admin/b2b/funnel/summary"),
          api.get("/admin/b2b/announcements"),
        ]);
        if (cancelled) return;
        setAgencies(agRes.data?.items || []);
        setFunnelItems(fnRes.data?.items || []);
        setAnnouncements(annRes.data?.items || []);
      } catch (e) {
        if (cancelled) return;
        setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const funnelByPartner = useMemo(() => {
    const map = {};
    (funnelItems || []).forEach((row) => {
      if (row && row.partner) map[row.partner] = row;
    });
    return map;
  }, [funnelItems]);

  const summary = useMemo(() => {
    const total = agencies.length;
    let active = 0;
    let disabled = 0;
    let nearLimit = 0;
    let overLimit = 0;
    let totalExposure = 0;
    let totalLimit = 0;

    agencies.forEach((a) => {
      if (a.status === "disabled") disabled += 1;
      else active += 1;
      if (a.risk_status === "near_limit") nearLimit += 1;
      if (a.risk_status === "over_limit") overLimit += 1;
      if (typeof a.exposure === "number") totalExposure += a.exposure;
      if (typeof a.credit_limit === "number") totalLimit += a.credit_limit;
    });

    let funnelQuotes = 0;
    let funnelAmountCents = 0;
    funnelItems.forEach((f) => {
      funnelQuotes += f.total_quotes || 0;
      funnelAmountCents += f.total_amount_cents || 0;
    });

    const activeAnnouncements = announcements.filter((a) => a.is_active).length;

    return {
      total,
      active,
      disabled,
      nearLimit,
      overLimit,
      totalExposure,
      totalLimit,
      funnelQuotes,
      funnelAmountCents,
      activeAnnouncements,
    };
  }, [agencies, funnelItems, announcements]);

  const riskyAgencies = useMemo(() => {
    const list = agencies
      .map((a) => {
        const funnel = funnelByPartner[a.id] || null;
        return {
          ...a,
          funnel_quotes: funnel ? funnel.total_quotes : 0,
          funnel_amount_cents: funnel ? funnel.total_amount_cents : 0,
        };
      })
      .filter((a) => a.risk_status === "near_limit" || a.risk_status === "over_limit")
      .sort((a, b) => (b.funnel_amount_cents || 0) - (a.funnel_amount_cents || 0));

    return list.slice(0, 5);
  }, [agencies, funnelByPartner]);

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground">B2B Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          B2B acenta portföyünüzün finansal durumu, funnel trafiği ve duyuru aktivitesine hızlı bakış.
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 mt-0.5" />
          <div>{error}</div>
        </div>
      )}

      {/* KPI kartları */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Users className="h-4 w-4" /> B2B Acenta Sayısı
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div className="text-2xl font-bold">{summary.total}</div>
            <div className="text-xs text-muted-foreground">
              Aktif: {summary.active} · Pasif: {summary.disabled}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <ShieldAlert className="h-4 w-4" /> Kredi Riski
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div className="text-2xl font-bold">{summary.overLimit}</div>
            <div className="text-xs text-muted-foreground">
              Limit aşıldı: {summary.overLimit} · Limite yakın: {summary.nearLimit}
            </div>
            <div className="mt-1 text-[11px] text-muted-foreground">
              Toplam Limit: {formatAmount(summary.totalLimit)} · Toplam Exposure: {formatAmount(summary.totalExposure)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Activity className="h-4 w-4" /> B2B Funnel & Duyurular
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div className="text-2xl font-bold">{summary.funnelQuotes}</div>
            <div className="text-xs text-muted-foreground">
              Son 30 günde partner kanalından gelen teklif adedi.
            </div>
            <div className="mt-1 text-[11px] text-muted-foreground">
              Toplam teklif tutarı: {formatAmount(summary.funnelAmountCents / 100)}
            </div>
            <div className="mt-1 text-[11px] text-muted-foreground">
              Aktif duyuru sayısı: {summary.activeAnnouncements}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Riskli acentalar tablosu */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Riskli & Aktif B2B Acentalar</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && agencies.length === 0 ? (
            <p className="text-xs text-muted-foreground">Yükleniyor...</p>
          ) : riskyAgencies.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Şu anda limiti aşan veya limite yakın acenta bulunmuyor.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Acenta</TableHead>
                    <TableHead className="text-xs">Durum</TableHead>
                    <TableHead className="text-xs">Risk</TableHead>
                    <TableHead className="text-xs text-right">Exposure</TableHead>
                    <TableHead className="text-xs text-right">Kredi Limiti</TableHead>
                    <TableHead className="text-xs text-right">B2B Funnel (Teklif)</TableHead>
                    <TableHead className="text-xs text-right">B2B Funnel (Tutar)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {riskyAgencies.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="text-xs">
                        <div className="flex flex-col">
                          <span className="font-medium truncate max-w-[220px]">{a.name}</span>
                          <span className="text-[10px] text-muted-foreground font-mono">{a.id}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs">
                        {a.status === "disabled" ? (
                          <Badge variant="secondary">Pasif</Badge>
                        ) : (
                          <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                            Aktif
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs">
                        <RiskBadge status={a.risk_status} />
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {formatAmount(a.exposure, a.currency)}
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {formatAmount(a.credit_limit, a.currency)}
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {a.funnel_quotes || 0}
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {formatAmount((a.funnel_amount_cents || 0) / 100, "EUR")}
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
