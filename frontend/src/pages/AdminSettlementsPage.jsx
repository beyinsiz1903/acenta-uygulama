import React, { useMemo, useState } from "react";
import { Save, Download, RefreshCw, AlertCircle, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { api, apiErrorMessage } from "../lib/api";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { toast } from "sonner";

function formatCents(amount, currency) {
  const value = (Number(amount || 0) || 0) / 100;
  const cur = currency || "EUR";
  return `${value.toFixed(2)} ${cur}`;
}

function SettlementStatusSummary({ items }) {
  const { totalGross, totalAgency, totalPlatform, currencies } = useMemo(() => {
    const byCur = new Map();
    for (const it of items || []) {
      const cur = it.currency || "EUR";
      const row = byCur.get(cur) || { gross: 0, agency: 0, platform: 0 };
      row.gross += Number(it.gross_cents || 0);
      row.agency += Number(it.agency_cut_cents || 0);
      row.platform += Number(it.platform_cut_cents || 0);
      byCur.set(cur, row);
    }
    const curList = Array.from(byCur.entries()).map(([cur, row]) => ({
      currency: cur,
      gross: row.gross,
      agency: row.agency,
      platform: row.platform,
    }));
    const totalGross = curList.reduce((s, r) => s + r.gross, 0);
    const totalAgency = curList.reduce((s, r) => s + r.agency, 0);
    const totalPlatform = curList.reduce((s, r) => s + r.platform, 0);
    return { totalGross, totalAgency, totalPlatform, currencies: curList };
  }, [items]);

  if (!items || items.length === 0) {
    return (
      <Card className="border-dashed bg-muted/20">
        <CardHeader>
          <CardTitle className="text-sm">Mutabakat özeti</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          Seçilen tarih aralığına göre bir ödeme kaydı bulunamadı. Filtreleri genişletmeyi deneyin.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Mutabakat özeti</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Toplam tahsilat (brüt)</div>
            <div className="text-base font-semibold">
              {formatCents(totalGross, currencies[0]?.currency)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Acenta payfi</div>
            <div className="text-base font-semibold">
              {formatCents(totalAgency, currencies[0]?.currency)}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Platform payı</div>
            <div className="text-base font-semibold">
              {formatCents(totalPlatform, currencies[0]?.currency)}
            </div>
          </div>
        </div>
        {currencies.length > 1 && (
          <div className="pt-2 border-t mt-2 space-y-1">
            <div className="text-xs font-medium text-muted-foreground">Para birimi bazında dağılım</div>
            <div className="space-y-1">
              {currencies.map((c) => (
                <div key={c.currency} className="flex items-center justify-between text-xs">
                  <div className="font-mono">{c.currency}</div>
                  <div className="flex items-center gap-3">
                    <span>Brüt: {formatCents(c.gross, c.currency)}</span>
                    <span>Acenta: {formatCents(c.agency, c.currency)}</span>
                    <span>Platform: {formatCents(c.platform, c.currency)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Filters({ dateFrom, dateTo, agencyId, onChange, loading, onSubmit, onDownloadCsv }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <div className="space-y-1">
          <CardTitle className="text-sm flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filtreler
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Tarih aralığı ve opsiyonel acenta filtresiyle B2B tahsilat mutabakatına ulaşın.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onSubmit} disabled={loading}>
            <RefreshCw className="h-3 w-3 mr-1" /> Yükle
          </Button>
          <Button size="sm" onClick={onDownloadCsv} disabled={loading}>
            <Download className="h-3 w-3 mr-1" /> CSV
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Başlangıç tarihi</div>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => onChange({ dateFrom: e.target.value })}
              className="h-9 text-xs"
            />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Bitiş tarihi</div>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => onChange({ dateTo: e.target.value })}
              className="h-9 text-xs"
            />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Acenta ID (opsiyonel)</div>
            <Input
              value={agencyId}
              onChange={(e) => onChange({ agencyId: e.target.value })}
              placeholder="agency uuid veya kod"
              className="h-9 text-xs"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminSettlementsPage() {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [agencyId, setAgencyId] = useState("");

  const { data: settlementData, isLoading: loading, error: fetchError, refetch } = useQuery({
    queryKey: ["admin", "settlements", dateFrom, dateTo, agencyId],
    queryFn: async () => {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (agencyId) params.agency_id = agencyId;
      const resp = await api.get("/admin/settlements", { params });
      return resp.data || {};
    },
    staleTime: 30_000,
    onSuccess: (data) => {
      if (!dateFrom && data.date_from) setDateFrom(data.date_from.slice(0, 10));
      if (!dateTo && data.date_to) setDateTo(data.date_to.slice(0, 10));
    },
  });
  const items = settlementData?.items || [];
  const error = fetchError ? apiErrorMessage(fetchError) : "";

  async function onDownloadCsv() {
    try {
      const params = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (agencyId) params.agency_id = agencyId;
      const resp = await api.get("/admin/settlements", {
        params: { ...params, format: "csv" },
        responseType: "blob",
      });
      const blob = new Blob([resp.data], { type: "text/csv;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "settlements.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(apiErrorMessage(e));
    }
  }

  const onFilterChange = (patch) => {
    if (Object.prototype.hasOwnProperty.call(patch, "dateFrom")) setDateFrom(patch.dateFrom);
    if (Object.prototype.hasOwnProperty.call(patch, "dateTo")) setDateTo(patch.dateTo);
    if (Object.prototype.hasOwnProperty.call(patch, "agencyId")) setAgencyId(patch.agencyId);
  };

  const onSubmitFilters = () => {
    refetch();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mutabakat Tablosu"
        subtitle="Ödeme işlemleri üzerinden hesaplanan brüt tutar, acente payı ve platform payı listesi."
      />

      {error && !loading && (
        <ErrorState
          title="Mutabakat listesi yüklenemedi"
          description={error}
          onRetry={() => refetch()}
          className="max-w-xl"
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] gap-4">
        <div className="space-y-4">
          <Filters
            dateFrom={dateFrom}
            dateTo={dateTo}
            agencyId={agencyId}
            onChange={onFilterChange}
            loading={loading}
            onSubmit={onSubmitFilters}
            onDownloadCsv={onDownloadCsv}
          />

          <Card className="min-h-[320px]">
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-sm">İşlem satırları</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Ödeme işlemleri, acente ve rezervasyon bilgileriyle birlikte görüntülenen satırlar.
                </p>
              </div>
              <div className="text-xs text-muted-foreground flex flex-col items-end">
                <span>{items.length} satr</span>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto border-t">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Tarih</TableHead>
                      <TableHead className="text-xs">Booking</TableHead>
                      <TableHead className="text-xs">Acenta</TableHead>
                      <TableHead className="text-xs">Para Birimi</TableHead>
                      <TableHead className="text-xs text-right">Brüt</TableHead>
                      <TableHead className="text-xs text-right">Acenta payı</TableHead>
                      <TableHead className="text-xs text-right">Platform payı</TableHead>
                      <TableHead className="text-xs">Ödeme kanalı</TableHead>
                      <TableHead className="text-xs">Kaynak</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      <TableRow>
                        <TableCell colSpan={9} className="py-10 text-center text-sm text-muted-foreground">
                          Yükleniyor...
                        </TableCell>
                      </TableRow>
                    ) : items.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={9} className="py-10">
                          <EmptyState
                            title="Kayıt yok"
                            description="Seçilen tarih aralığı ve filtrelere göre işlem kaydı bulunamadı."
                          />
                        </TableCell>
                      </TableRow>
                    ) : (
                      items.map((it) => (
                        <TableRow key={it.tx_id} className="hover:bg-accent/40">
                          <TableCell className="text-xs">
                            {it.date ? new Date(it.date).toLocaleString() : "-"}
                          </TableCell>
                          <TableCell className="text-xs">
                            <div className="font-mono truncate max-w-[140px]">{it.booking_code || it.booking_id}</div>
                          </TableCell>
                          <TableCell className="text-xs font-mono truncate max-w-[120px]">
                            {it.agency_id || "-"}
                          </TableCell>
                          <TableCell className="text-xs">{it.currency || "EUR"}</TableCell>
                          <TableCell className="text-xs text-right">
                            {formatCents(it.gross_cents, it.currency)}
                          </TableCell>
                          <TableCell className="text-xs text-right">
                            {formatCents(it.agency_cut_cents, it.currency)}
                          </TableCell>
                          <TableCell className="text-xs text-right">
                            {formatCents(it.platform_cut_cents, it.currency)}
                          </TableCell>
                          <TableCell className="text-xs">{it.payment_method || "-"}</TableCell>
                          <TableCell className="text-xs">{it.channel || "-"}</TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <SettlementStatusSummary items={items} />
          <Card className="border-dashed bg-muted/20">
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Save className="h-4 w-4" /> Kullanım notları
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground space-y-2">
              <p>
                Bu ekran, Agentis seviyesinde bir B2B tahsilat mutabakatı sağlar: her bir ödeme işlemi için brüt
                tutar, acenta payı ve platform payı görünür.
              </p>
              <ul className="list-disc list-inside space-y-1">
                <li>
                  Muhasebe: Ödeme işlemlerinin detaylı dökümünü ve hesaplamalarını bu sayfadan takip edebilirsiniz.
                </li>
                <li>
                  Bilgi: Mutabakat sayfasının kullanım verileri
                  yönetim panelinde izlenebilir.
                </li>
                <li>
                  CSV dışa aktarım: Muhasebe ekibine Excel/ERP import için aynı veri setini götürmek içindir.
                </li>
              </ul>            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
