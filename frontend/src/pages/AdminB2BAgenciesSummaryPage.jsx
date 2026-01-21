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

  const [funnelByPartner, setFunnelByPartner] = useState({}); // { [partnerId]: { total_quotes, total_amount_cents, ... } }

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        setLoading(true);
        setError("");
        const resp = await api.get("/admin/b2b/agencies/summary");
        if (cancelled) return;
        setItems(resp.data?.items || []);

        // Partner funnel özetini de oku (opsiyonel, hata durumda sessizce geç)
        try {
          const funnelResp = await api.get("/admin/b2b/funnel/summary");
          if (!cancelled) {
            const byPartner = {};
            (funnelResp.data?.items || []).forEach((row) => {
              if (row && row.partner) {
                byPartner[row.partner] = row;
              }
            });
            setFunnelByPartner(byPartner);
          }
        } catch (_funnelErr) {
          if (!cancelled) {
            setFunnelByPartner({});
          }
        }
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
    // Faz 1: basit partner + org parametresi ile public book sayfas31
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const base = origin || backendBase || "";
    const qs = new URLSearchParams();
    if (agency.organization_id) {
      qs.set("org", agency.organization_id);
    }
    qs.set("partner", agency.id);
    const url = `${base.replace(/\/$/, "")}/book?${qs.toString()}`;
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

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right" className="w-full max-w-md">
          <SheetHeader>
            <SheetTitle>B2B Acenta Detayı</SheetTitle>
            <SheetDescription>
              Kredi profili ve embed edilebilir bayi iframe bilgisi.
            </SheetDescription>
          </SheetHeader>

          {selected && (
            <div className="mt-4 space-y-4">
              <div className="space-y-1 text-sm">
                <div className="font-medium">{selected.name}</div>
                <div className="text-[11px] text-muted-foreground font-mono">{selected.id}</div>
              </div>

              <div className="inline-flex rounded-lg bg-muted p-1 text-[11px] text-muted-foreground">
                <button
                  type="button"
                  className={`px-2 py-1 rounded-md ${
                    sheetTab === "credit" ? "bg-background text-foreground shadow" : ""
                  }`}
                  onClick={() => setSheetTab("credit")}
                >
                  Kredi Profili
                </button>
                <button
                  type="button"
                  className={`px-2 py-1 rounded-md ${
                    sheetTab === "embed" ? "bg-background text-foreground shadow" : ""
                  }`}
                  onClick={() => setSheetTab("embed")}
                >
                  Bayi iframe
                </button>
              </div>

              {sheetTab === "credit" && (
                <div className="space-y-4">
                  <p className="text-xs text-muted-foreground">
                    Limit ve ödeme şartı değişiklikleri doğrudan kredi profilini günceller. Soft limit, uyarı eşiği
                    olarak kullanılır.
                  </p>

                  {creditError && (
                    <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
                      <AlertCircle className="h-4 w-4 mt-0.5" />
                      <div>{creditError}</div>
                    </div>
                  )}

                  <div className="space-y-3">
                    <div className="space-y-1">
                      <Label htmlFor="limit">Kredi Limiti</Label>
                      <Input
                        id="limit"
                        type="number"
                        min={0}
                        value={creditForm.limit}
                        onChange={(e) =>
                          setCreditForm((prev) => ({ ...prev, limit: e.target.value }))
                        }
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="soft_limit">Soft Limit</Label>
                      <Input
                        id="soft_limit"
                        type="number"
                        min={0}
                        value={creditForm.soft_limit}
                        onChange={(e) =>
                          setCreditForm((prev) => ({ ...prev, soft_limit: e.target.value }))
                        }
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="payment_terms">Ödeme Şartı</Label>
                      <select
                        id="payment_terms"
                        className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                        value={creditForm.payment_terms}
                        onChange={(e) =>
                          setCreditForm((prev) => ({ ...prev, payment_terms: e.target.value }))
                        }
                      >
                        <option value="PREPAY">PREPAY</option>
                        <option value="NET7">NET7</option>
                        <option value="NET14">NET14</option>
                        <option value="NET30">NET30</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor="status">Kredi Profili Durumu</Label>
                      <select
                        id="status"
                        className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                        value={creditForm.status}
                        onChange={(e) =>
                          setCreditForm((prev) => ({ ...prev, status: e.target.value }))
                        }
                      >
                        <option value="active">Aktif</option>
                        <option value="suspended">Askıda</option>
                      </select>
                    </div>
                  </div>

                  <SheetFooter className="mt-4">
                    <Button
                      type="button"
                      onClick={async () => {
                        if (!selected) return;
                        setCreditError("");
                        const limitNum = Number(creditForm.limit || 0);
                        const softNum = creditForm.soft_limit ? Number(creditForm.soft_limit) : null;
                        if (Number.isNaN(limitNum) || limitNum < 0) {
                          setCreditError("Limit 0 veya üzeri sayısal bir değer olmalıdır.");
                          return;
                        }
                        if (softNum != null && (Number.isNaN(softNum) || softNum < 0)) {
                          setCreditError("Soft limit 0 veya üzeri sayısal bir değer olmalıdır.");
                          return;
                        }
                        setCreditSaving(true);
                        try {
                          await api.put(`/ops/finance/credit-profiles/${selected.id}`, {
                            limit: limitNum,
                            soft_limit: softNum,
                            payment_terms: creditForm.payment_terms,
                            status: creditForm.status,
                          });
                          // Listeyi tazele
                          const resp = await api.get("/admin/b2b/agencies/summary");
                          setItems(resp.data?.items || []);
                          setSheetOpen(false);
                        } catch (err) {
                          setCreditError(apiErrorMessage(err));
                        } finally {
                          setCreditSaving(false);
                        }
                      }}
                      disabled={creditSaving}
                      className="gap-2"
                    >
                      {creditSaving ? "Kaydediliyor..." : "Kaydet"}
                    </Button>
                  </SheetFooter>
                </div>
              )}

              {sheetTab === "embed" && (
                <div className="space-y-3">
                  <p className="text-xs text-muted-foreground">
                    Bu snippet, ilgili acentenin embed edilebilir rezervasyon iframe&apos;ini kendi web sitenize
                    yerleştirmeniz için bir örnektir. İlk fazda yalnızca temel partner parametresi taşır.
                  </p>
                  <div className="space-y-1 text-xs">
                    <div className="font-medium">Iframe URL</div>
                    <code className="block rounded-md bg-muted px-2 py-1 text-[11px] whitespace-pre-wrap break-all">
                      {buildEmbedUrl(selected)}
                    </code>
                  </div>
                  <div className="space-y-1 text-xs">
                    <div className="font-medium">Örnek iframe kodu</div>
                    <code className="block rounded-md bg-muted px-2 py-2 text-[11px] whitespace-pre overflow-x-auto">
                      {`<iframe\n  src="${buildEmbedUrl(selected)}"\n  width="100%"\n  height="800"\n  style="border:0;"\n  loading="lazy"\n></iframe>`}
                    </code>
                  </div>
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>

                  {filtered.map((it) => (
                    <TableRow
                      key={it.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => openSheetForAgency(it, "credit")}
                    >
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
