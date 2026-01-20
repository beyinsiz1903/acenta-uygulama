import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, Building2 } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "../components/ui/sheet";
import { Label } from "../components/ui/label";

function RiskBadge({ status }) {
  if (status === "over_limit") {
    return <Badge variant="destructive">Limit aşıldı</Badge>;
  }
  if (status === "near_limit") {
    return <Badge variant="secondary">Limite yakın</Badge>;
  }
  return <Badge variant="outline">Normal</Badge>;
}

function StatusBadge({ status }) {
  if (status === "disabled") {
    return <Badge variant="secondary">Pasif</Badge>;
  }
  return <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">Aktif</Badge>;
}

function formatAmount(value, currency) {
  if (value == null) return "-";
  const num = Number(value);
  if (Number.isNaN(num)) return "-";
  return `${num.toFixed(2)} ${currency || "EUR"}`;
}

export default function AdminB2BAgenciesSummaryPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");

  const [selected, setSelected] = useState(null); // { id, name, ... }
  const [sheetOpen, setSheetOpen] = useState(false);
  const [sheetTab, setSheetTab] = useState("credit"); // "credit" | "embed"
  const [creditForm, setCreditForm] = useState({ limit: "", soft_limit: "", payment_terms: "NET14", status: "active" });
  const [creditSaving, setCreditSaving] = useState(false);
  const [creditError, setCreditError] = useState("");

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        setLoading(true);
        setError("");
        const resp = await api.get("/admin/b2b/agencies/summary");
        if (cancelled) return;
        setItems(resp.data?.items || []);
      } catch (err) {
        if (cancelled) return;
        setError(apiErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    let data = items;
    if (riskFilter !== "all") {
      data = data.filter((it) => it.risk_status === riskFilter);
    }
    if (filter) {
      const f = filter.toLowerCase();
      data = data.filter((it) => {
        const name = (it.name || "").toLowerCase();
        const id = (it.id || "").toLowerCase();
        return name.includes(f) || id.includes(f);
      });
    }
    return data;
  }, [items, filter, riskFilter]);

  function openSheetForAgency(agency, tab = "credit") {
    setSelected(agency);
    setSheetTab(tab);
    setCreditError("");
    // Kredi formunu mevcut özet değerlerle doldur
    setCreditForm({
      limit: agency.credit_limit != null ? String(agency.credit_limit) : "",
      soft_limit: agency.soft_limit != null ? String(agency.soft_limit) : "",
      payment_terms: agency.payment_terms || "NET14",
      status: agency.status === "disabled" ? "suspended" : "active",
    });
    setSheetOpen(true);
  }

  const backendBase =
    (typeof window !== "undefined" &&
      (window.__ACENTA_BACKEND_URL__ || window.importMetaEnvBackendUrl || process.env.REACT_APP_BACKEND_URL)) ||
    "";

  function buildEmbedUrl(agency) {
    // Faz 1: basit partner parametresi ile book sayfas31
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const base = origin || backendBase || "";
    const url = `${base.replace(/\/$/, "")}/book?partner=${encodeURIComponent(agency.id)}`;
    return url;
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-foreground">B2B Acenteler – Finans Özeti</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Her acentenin kredi limiti, maruziyeti ve risk durumunu tek ekranda gör.
        </p>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-sm font-medium">Finans Özeti</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Veriler, finans hesapları (ledger) ve kredi profillerinden okunur. Sadece okuma amaçlıdır.
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="inline-flex rounded-lg bg-muted p-1 text-[11px] text-muted-foreground">
              <button
                type="button"
                className={`px-2 py-1 rounded-md ${riskFilter === "all" ? "bg-background text-foreground shadow" : ""}`}
                onClick={() => setRiskFilter("all")}
              >
                Tümü
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded-md ${
                  riskFilter === "near_limit" ? "bg-background text-foreground shadow" : ""
                }`}
                onClick={() => setRiskFilter("near_limit")}
              >
                Limite yakın
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded-md ${
                  riskFilter === "over_limit" ? "bg-background text-foreground shadow" : ""
                }`}
                onClick={() => setRiskFilter("over_limit")}
              >
                Limit aşıldı
              </button>
            </div>
            <Input
              className="h-8 w-56 text-xs"
              placeholder="Acenta adı veya ID filtrele"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent>
          {loading && items.length === 0 ? (
            <div className="text-xs text-muted-foreground">Yükleniyor...</div>
          ) : error ? (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 mt-0.5" />
              <div>{error}</div>
            </div>
          ) : filtered.length === 0 ? (
            <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
              <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
                <Building2 className="h-8 w-8 text-muted-foreground" />
              </div>
              <div className="text-center max-w-md">
                <p className="font-semibold text-foreground">Görüntülenecek acente bulunamadı</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Filtreyi genişleterek veya kredi profili tanımlayarak bu listeyi doldurabilirsiniz.
                </p>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Acenta</TableHead>
                    <TableHead className="text-xs">Durum</TableHead>
                    <TableHead className="text-xs text-right">Maruziyet (Exposure)</TableHead>
                    <TableHead className="text-xs text-right">Kredi Limiti</TableHead>
                    <TableHead className="text-xs text-right">Soft Limit</TableHead>
                    <TableHead className="text-xs">Risk Durumu</TableHead>
                    <TableHead className="text-xs">Ödeme Şartı</TableHead>
                    <TableHead className="text-xs">Üst Acenta</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((it) => (
                    <TableRow key={it.id}>
                      <TableCell className="text-xs">
                        <div className="flex flex-col">
                          <span className="font-medium truncate max-w-[220px]">{it.name}</span>
                          <span className="text-[10px] text-muted-foreground font-mono">{it.id}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs">
                        <StatusBadge status={it.status} />
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {formatAmount(it.exposure, it.currency)}
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {formatAmount(it.credit_limit, it.currency)}
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {formatAmount(it.soft_limit, it.currency)}
                      </TableCell>
                      <TableCell className="text-xs">
                        <RiskBadge status={it.risk_status} />
                      </TableCell>
                      <TableCell className="text-[11px] text-muted-foreground">
                        {it.payment_terms || "-"}
                      </TableCell>
                      <TableCell className="text-[11px] text-muted-foreground font-mono">
                        {it.parent_agency_id || "-"}
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
