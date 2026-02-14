import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Calendar, Filter, Loader2, Receipt } from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "../../components/ui/table";
import { useToast } from "../../hooks/use-toast";
import { fetchSettlementStatement } from "../../lib/settlements";

function formatDate(value) {
  if (!value) return "-";
  try {
    const d = new Date(value);
    return d.toLocaleString("tr-TR");
  } catch {
    return value;
  }
}

function formatAmount(value, currency) {
  if (value == null || value === "") return "-";
  if (!currency) return String(value);
  try {
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(Number(value));
  } catch {
    return String(value);
  }
}


function shortenId(id) {
  if (!id) return "-";
  if (id.length <= 10) return id;
  return `${id.slice(0, 6)}…${id.slice(-4)}`;
}

async function copyToClipboard(text, toast) {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      toast?.({ description: "ID panoya kopyalandı." });
    }
  } catch {
    // kritik değil
  }
}

export default function PartnerStatementsPage() {
  const { toast } = useToast();

  const now = new Date();
  const defaultMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  const [month, setMonth] = useState(defaultMonth);
  const [perspective, setPerspective] = useState("seller");
  const [statusFilter, setStatusFilter] = useState([]); // array of strings
  const [counterpartyTenantId, setCounterpartyTenantId] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [items, setItems] = useState([]);
  const [totals, setTotals] = useState(null);
  const [currencyBreakdown, setCurrencyBreakdown] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);

  const hasNext = !!nextCursor;

  const statusOptions = [
    { value: "open", label: "Açık" },
    { value: "approved", label: "Onaylandı" },
    { value: "paid", label: "Ödendi" },
    { value: "void", label: "İptal" },
  ];

  const toggleStatus = (value) => {
    setStatusFilter((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    );
  };

  const effectiveStatuses = useMemo(() => statusFilter, [statusFilter]);

  const loadFirstPage = useCallback(async () => {
    if (!month) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetchSettlementStatement({
        month,
        perspective,
        statuses: effectiveStatuses,
        counterpartyTenantId: counterpartyTenantId || undefined,
        cursor: undefined,
        limit: 50,
      });
      setItems(res.items || []);
      setTotals(res.totals || null);
      setCurrencyBreakdown(res.currency_breakdown || []);
      setNextCursor(res.page?.next_cursor || null);
    } catch (e) {
      const code = e?.raw?.response?.data?.error?.code;
      let msg = e?.message || "Mutabakat ekstresi yüklenirken bir hata oluştu.";
      if (code === "invalid_month") {
        msg = "Ay formatı geçersiz. Örn: 2026-02.";
      } else if (code === "statement_too_large") {
        msg = "Bu filtreyle çok fazla kayıt var (max 500). Lütfen filtreleri daraltın.";
      } else if (code === "invalid_cursor") {
        msg = "Sayfalama bilgisi geçersiz. Lütfen sayfayı yenileyin.";
      } else if (code === "tenant_header_missing") {
        msg = "Tenant seçimi gerekli. Lütfen geçerli bir tenant ile tekrar deneyin.";
      } else if (code === "invalid_token") {
        msg = "Oturum süreniz dolmuş olabilir. Lütfen tekrar giriş yapın.";
      }
      setError(msg);
      setItems([]);
      setTotals(null);
      setCurrencyBreakdown([]);
      setNextCursor(null);
    } finally {
      setLoading(false);
    }
  }, [month, perspective, effectiveStatuses, counterpartyTenantId]);

  const loadMore = useCallback(async () => {
    if (!nextCursor || !month) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetchSettlementStatement({
        month,
        perspective,
        statuses: effectiveStatuses,
        counterpartyTenantId: counterpartyTenantId || undefined,
        cursor: nextCursor,
        limit: 50,
      });
      setItems((prev) => [...prev, ...(res.items || [])]);
      // totals ve currency_breakdown backend kontratına göre tüm filtre aralığı için
      // olduğundan, ilk sayfadan gelen değerleri koruyoruz.
      setNextCursor(res.page?.next_cursor || null);
    } catch (e) {
      const msg = e?.message || "Ekstra sayfa yüklenirken bir hata oluştu.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [month, perspective, effectiveStatuses, counterpartyTenantId, nextCursor]);

  useEffect(() => {
    void loadFirstPage();
  }, [loadFirstPage]);

  const handleApplyFilters = async (e) => {
    e.preventDefault();
    await loadFirstPage();
  };

  const handleResetFilters = () => {
    setMonth(defaultMonth);
    setPerspective("seller");
    setStatusFilter([]);
    setCounterpartyTenantId("");
    setItems([]);
    setNextCursor(null);
    setTotals(null);
    setCurrencyBreakdown([]);
  };

  const derivedItems = useMemo(() => {
    return items.map((it) => {
      const counterparty =
        perspective === "seller" ? it.buyer_tenant_id : it.seller_tenant_id;
      return { ...it, counterparty_tenant_id: counterparty };
    });
  }, [items, perspective]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Receipt className="h-5 w-5" />
        <div>
          <h1 className="text-base font-semibold">Mutabakat Ekstresi</h1>
          <p className="text-xs text-muted-foreground">
            B2B partner ağınızdaki settlement kayıtlarını ay, perspektif ve duruma göre
            görüntüleyin.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-xs">
            <Calendar className="h-4 w-4" />
            <CardTitle className="text-sm font-medium">Filtreler</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleApplyFilters}
            className="flex flex-col gap-3 text-xs md:flex-row md:flex-wrap md:items-end"
          >
            <div className="flex flex-col gap-1 w-full md:w-auto">
              <label htmlFor="month" className="text-xs font-medium">
                Ay (YYYY-MM)
              </label>
              <Input
                id="month"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
                className="h-8 text-xs max-w-[120px]"
                placeholder="2026-02"
              />
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium">Perspektif</span>
              <div className="inline-flex rounded-md border bg-background p-0.5 text-xs">
                <button
                  type="button"
                  className={`px-2 py-1 rounded-sm ${
                    perspective === "seller"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground"
                  }`}
                  onClick={() => setPerspective("seller")}
                >
                  Satıcı
                </button>
                <button
                  type="button"
                  className={`px-2 py-1 rounded-sm ${
                    perspective === "buyer"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground"
                  }`}
                  onClick={() => setPerspective("buyer")}
                >
                  Alıcı
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium flex items-center gap-1">
                <Filter className="h-3 w-3" /> Durum
              </span>
              <div className="flex flex-wrap gap-1">
                {statusOptions.map((opt) => {
                  const active = statusFilter.includes(opt.value);
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => toggleStatus(opt.value)}
                      className={`h-6 rounded-full border px-2 text-xs ${
                        active
                          ? "bg-primary text-primary-foreground border-primary"
                          : "text-muted-foreground"
                      }`}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col gap-1 w-full md:w-60">
              <label htmlFor="counterparty" className="text-xs font-medium">
                Karşı Tenant ID (opsiyonel)
              </label>
              <Input
                id="counterparty"
                value={counterpartyTenantId}
                onChange={(e) => setCounterpartyTenantId(e.target.value)}
                className="h-8 text-xs"
                placeholder="buyer/seller tenant id"
              />
            </div>

            <div className="flex gap-2 mt-2 md:mt-0">
              <Button type="submit" size="sm" disabled={loading}>
                {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                Uygula
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={handleResetFilters}>
                Temizle
              </Button>
            </div>
          </form>

          {error && (
            <div className="mt-3 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Totals & currency breakdown */}
      {totals && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium">Toplam kayıt</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-semibold">{totals.count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium">Brüt toplam</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-semibold">{formatAmount(totals.gross_total, totals.currency)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium">Komisyon toplamı</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-semibold">{formatAmount(totals.commission_total, totals.currency)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium">Net toplam</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-lg font-semibold">{formatAmount(totals.net_total, totals.currency)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {currencyBreakdown && currencyBreakdown.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Para birimi bazında özet</CardTitle>
          </CardHeader>
          <CardContent className="text-xs">
            <div className="flex flex-wrap gap-2">
              {currencyBreakdown.map((c) => (
                <div
                  key={c.currency}
                  className="rounded-md border bg-muted/40 px-3 py-2 space-y-1 min-w-[140px]"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{c.currency}</span>
                    <Badge variant="outline" className="text-2xs">
                      {c.count} kayıt
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground space-y-0.5">
                    <div>Brüt: {formatAmount(c.gross_total, c.currency)}</div>
                    <div>Komisyon: {formatAmount(c.commission_total, c.currency)}</div>
                    <div>Net: {formatAmount(c.net_total, c.currency)}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Items table */}
      <Card>
        <CardHeader className="pb-2 flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Kayıtlar</CardTitle>
          {loading && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Yükleniyor…</span>
            </div>
          )}
        </CardHeader>
        <CardContent className="text-xs">
          {derivedItems.length === 0 && !loading ? (
            <p className="text-xs text-muted-foreground">
              Bu filtreler ile gösterilecek mutabakat kaydı bulunamadı.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Tarih</TableHead>
                    <TableHead className="text-xs">Booking ID</TableHead>
                    <TableHead className="text-xs">Settlement ID</TableHead>
                    <TableHead className="text-xs">Karşı Tenant</TableHead>
                    <TableHead className="text-xs">Para</TableHead>
                    <TableHead className="text-xs">Brüt</TableHead>
                    <TableHead className="text-xs">Komisyon</TableHead>
                    <TableHead className="text-xs">Net</TableHead>
                    <TableHead className="text-xs">Durum</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {derivedItems.map((it) => (
                    <TableRow key={it.settlement_id} className="hover:bg-muted/40">
                      <TableCell className="text-xs">{formatDate(it.created_at)}</TableCell>
                      <TableCell
                        className="text-xs font-mono cursor-pointer hover:underline"
                        title="Booking ID'yi kopyala"
                        onClick={() => it.booking_id && copyToClipboard(it.booking_id, toast)}
                      >
                        {shortenId(it.booking_id)}
                      </TableCell>
                      <TableCell
                        className="text-xs font-mono cursor-pointer hover:underline"
                        title="Settlement ID'yi kopyala"
                        onClick={() => it.settlement_id && copyToClipboard(it.settlement_id, toast)}
                      >
                        {shortenId(it.settlement_id)}
                      </TableCell>
                      <TableCell
                        className="text-xs font-mono cursor-pointer hover:underline"
                        title="Karşı tenant ID'yi kopyala"
                        onClick={() => it.counterparty_tenant_id && copyToClipboard(it.counterparty_tenant_id, toast)}
                      >
                        {it.counterparty_tenant_id || <span className="text-muted-foreground">-</span>}
                      </TableCell>
                      <TableCell className="text-xs">{it.currency || "-"}</TableCell>
                      <TableCell className="text-xs">{formatAmount(it.gross_amount, it.currency)}</TableCell>
                      <TableCell className="text-xs">{formatAmount(it.commission_amount, it.currency)}</TableCell>
                      <TableCell className="text-xs">{formatAmount(it.net_amount, it.currency)}</TableCell>
                      <TableCell className="text-xs">
                        <Badge variant="outline">{it.status || "-"}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <div className="mt-3 flex justify-end">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={!hasNext || loading}
              onClick={loadMore}
            >
              {loading && hasNext && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              Daha fazla yükle
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
