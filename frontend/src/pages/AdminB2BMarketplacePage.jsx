import React, { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Info, Loader2, Search, Store, Users } from "lucide-react";

import { api, apiErrorMessage, parseErrorDetails } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import EmptyState from "../components/EmptyState";
import { ErrorCard } from "../components/ErrorCard";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "../components/ui/tooltip";

import PricingPreviewDialog from "../components/b2b/PricingPreviewDialog";

function StatusBadge({ status }) {
  const s = (status || "").toLowerCase();
  if (s === "approved") {
    return (
      <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
        Onaylı
      </Badge>
    );
  }
  if (s === "blocked") {
    return <Badge variant="destructive">Engelli</Badge>;
  }
  return <Badge variant="outline">Beklemede</Badge>;
}

function ProductTypeBadge({ type }) {
  if (!type) return null;
  const t = String(type);
  if (t === "tour") return <Badge variant="secondary">Tur</Badge>;
  if (t === "hotel") return <Badge variant="outline">Otel</Badge>;
  return <Badge variant="outline">{t}</Badge>;
}

export default function AdminB2BMarketplacePage() {
  const [partners, setPartners] = useState([]);
  const [partnersLoading, setPartnersLoading] = useState(false);
  const [partnersError, setPartnersError] = useState("");
  const [partnerSearch, setPartnerSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [selectedPartnerId, setSelectedPartnerId] = useState("");
  const [selectedPartnerName, setSelectedPartnerName] = useState("");

  const [products, setProducts] = useState([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState("");
  const [productsErrorDetails, setProductsErrorDetails] = useState(null);
  const [productSearchInput, setProductSearchInput] = useState("");
  const [debouncedProductSearch, setDebouncedProductSearch] = useState("");
  const [productTypeFilter, setProductTypeFilter] = useState("");
  const [productStatusFilter, setProductStatusFilter] = useState("");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContext, setPreviewContext] = useState(null);

  const [productPage, setProductPage] = useState(1);
  const [productLimit, setProductLimit] = useState(50);
  const [productHasMore, setProductHasMore] = useState(false);
  const productsSeqRef = useRef(0);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedProductSearch(productSearchInput), 300);
    return () => clearTimeout(t);
  }, [productSearchInput]);


  const [savingKey, setSavingKey] = useState("");

  useEffect(() => {
    void loadPartners();
  }, []);

  async function loadPartners() {
    setPartnersLoading(true);
    setPartnersError("");
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      const res = await api.get("/admin/partners", { params });
      const data = res.data || {};
      const items = Array.isArray(data.items) ? data.items : Array.isArray(data) ? data : [];
      setPartners(items);
      // Seçili partner yoksa ilkini otomatik seç
      if (!selectedPartnerId && items.length > 0) {
        setSelectedPartnerId(items[0].id);
        setSelectedPartnerName(items[0].name);
      }
    } catch (e) {
      setPartnersError(apiErrorMessage(e));
    } finally {
      setPartnersLoading(false);
    }
  }

  useEffect(() => {
    if (!selectedPartnerId) {
      setProducts([]);
      setProductsError("");
      return;
    }
    void loadProducts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPartnerId, productTypeFilter, productStatusFilter, debouncedProductSearch, productPage, productLimit]);

  async function loadProducts() {
    if (!selectedPartnerId) return;
    const seq = ++productsSeqRef.current;
    setProductsLoading(true);
    setProductsError("");
    setProductsErrorDetails(null);
    try {
      const params = { page: productPage, limit: productLimit };
      params.partner_id = selectedPartnerId;
      if (productTypeFilter) params.type = productTypeFilter;
      if (productStatusFilter) params.status = productStatusFilter;
      if (debouncedProductSearch) params.q = debouncedProductSearch;
      const res = await api.get("/admin/b2b/marketplace", { params });
      if (seq !== productsSeqRef.current) return;
      const data = res.data || {};
      setProducts(data.items || []);
      setProductHasMore(Boolean(data.has_more));
    } catch (e) {
      if (seq !== productsSeqRef.current) return;
      const msg = apiErrorMessage(e);
      // 404 ya da "Not Found" durumunda boş veri gibi davran, kırmızı hata göstermeyelim
      if (String(msg).toLowerCase().includes("not found") || msg === "Not Found") {
        setProducts([]);
        setProductsError("");
        setProductsErrorDetails(null);
      } else {
        setProductsError(msg);
        setProductsErrorDetails(parseErrorDetails(e));
      }
    } finally {
      if (seq === productsSeqRef.current) {
        setProductsLoading(false);
      }
    }
  }

  const filteredPartners = useMemo(() => {
    const q = partnerSearch.trim().toLowerCase();
    if (!q) return partners;
    return partners.filter((p) => {
      return (
        (p.name || "").toLowerCase().includes(q) ||
        (p.contact_email || "").toLowerCase().includes(q)
      );
    });
  }, [partners, partnerSearch]);

  async function handleToggle(product) {
    if (!selectedPartnerId) return;
    const nextEnabled = !product.is_enabled;
    const prev = { ...product };
    setSavingKey(product.product_id);
    setProducts((prevList) =>
      prevList.map((p) =>
        p.product_id === product.product_id ? { ...p, is_enabled: nextEnabled } : p
      )
    );
    try {
      await api.put("/admin/b2b/marketplace", {
        partner_id: selectedPartnerId,
        product_id: product.product_id,
        is_enabled: nextEnabled,
        commission_rate: product.commission_rate ?? null,
      });
    } catch (e) {
      // rollback
      setProducts((prevList) =>
        prevList.map((p) =>
          p.product_id === product.product_id ? prev : p
        )
      );
      setProductsError(apiErrorMessage(e));
    } finally {
      setSavingKey("");
    }
  }

  async function handleCommissionBlur(product, value) {
    if (!selectedPartnerId) return;
    const trimmed = value.trim();
    const nextCommission = trimmed === "" ? null : Number(trimmed);
    if (Number.isNaN(nextCommission)) return;
    const prev = { ...product };

    setSavingKey(product.product_id + "-commission");
    setProducts((prevList) =>
      prevList.map((p) =>
        p.product_id === product.product_id ? { ...p, commission_rate: nextCommission } : p
      )
    );

    try {
      await api.put("/admin/b2b/marketplace", {
        partner_id: selectedPartnerId,
        product_id: product.product_id,
        is_enabled: product.is_enabled,
        commission_rate: nextCommission,
      });
    } catch (e) {
      // rollback
      setProducts((prevList) =>
        prevList.map((p) =>
          p.product_id === product.product_id ? prev : p
        )
      );
      setProductsError(apiErrorMessage(e));
    } finally {
      setSavingKey("");
    }
  }

  const currentPartnerLabel = selectedPartnerName
    ? `${selectedPartnerName} — Ürün Yetkilendirme`
    : "B2B Marketplace";

  return (
    <TooltipProvider>
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Sol panel: Partner listesi */}
        <div className="md:col-span-4 lg:col-span-3 space-y-3">
          <Card>
            <CardHeader className="pb-2 flex items-center gap-2">
              <Users className="h-4 w-4" />
              <div>
                <CardTitle className="text-sm font-semibold">Partnerler</CardTitle>
                <p className="text-[11px] text-muted-foreground">
                  B2B partner profillerinizi listeleyin ve birini seçerek sağ tarafta ürün yetkilerini yönetin.
                </p>
              </div>
            </CardHeader>
            <CardContent className="pt-2 space-y-2">
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-3 w-3 text-muted-foreground" />
                <Input
                  className="pl-7 h-8 text-xs"
                  placeholder="Partner adı / e-posta filtrele"
                  value={partnerSearch}
                  onChange={(e) => setPartnerSearch(e.target.value)}
                />
              </div>
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <div className="flex items-center gap-1">
                  <span>Durum:</span>
                  <select
                    className="h-7 rounded-md border bg-background px-1 text-[11px]"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                  >
                    <option value="">Tümü</option>
                    <option value="pending">Beklemede</option>
                    <option value="approved">Onaylı</option>
                    <option value="blocked">Engelli</option>
                  </select>
                </div>
                <Button
                  type="button"
                  size="xs"
                  variant="outline"
                  onClick={loadPartners}
                  disabled={partnersLoading}
                >
                  {partnersLoading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}Yenile
                </Button>
              </div>
              <div className="mt-2 max-h-[420px] overflow-y-auto border rounded-xl divide-y">

                {partnersError && (
                  <div className="p-3 text-[11px] text-destructive flex items-start gap-2">
                    <AlertCircle className="h-3 w-3 mt-0.5" />
                    <span>{partnersError}</span>
                  </div>
                )}

                {!partnersError && filteredPartners.length === 0 && !partnersLoading && (
                  <div className="p-4 text-center text-[11px] text-muted-foreground">
                    Henüz partner yok. Önce Partnerler ekranından bir partner oluşturun.
                  </div>
                )}

                {filteredPartners.map((p) => (
                  <div
                    key={p.id}
                    className={`px-3 py-2 text-xs cursor-pointer flex items-center justify-between gap-2 hover:bg-muted/60 ${
                      selectedPartnerId === p.id ? "bg-muted" : ""
                    }`}
                    onClick={() => {
                      setSelectedPartnerId(p.id);
                      setSelectedPartnerName(p.name);
                    }}
                  >
                    <div className="flex flex-col">
                      <span className="font-medium truncate max-w-[160px]">{p.name}</span>
                      <span className="text-[10px] text-muted-foreground truncate max-w-[180px]">
                        {p.contact_email || "-"}
                      </span>
                    </div>
                    <StatusBadge status={p.status} />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sağ panel: Ürün yetkilendirme */}
        <div className="md:col-span-8 lg:col-span-9 space-y-3">
              <div className="text-[11px] font-mono bg-muted rounded px-2 py-1">
                {partnerId || "-"}
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-[11px] text-muted-foreground">Ürün</Label>
              <div className="text-[11px] font-mono bg-muted rounded px-2 py-1">
                {product?.product_id}  b7 {product?.title}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Check-in</Label>
                <Input
                  type="date"
                  className="h-8"
                  value={requestState.checkin}
                  onChange={(e) => handleChange("checkin", e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Check-out</Label>
                <Input
                  type="date"
                  className="h-8"
                  value={requestState.checkout}
                  onChange={(e) => handleChange("checkout", e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Yetişkin</Label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  className="h-8"
                  value={requestState.adults}
                  onChange={(e) => handleChange("adults", e.target.value)}
                />
              </div>
              <div className="space-y-1">

function PricingPreviewDialog({
  open,
  onOpenChange,
  partnerId,
  product,
  requestState,
  setRequestState,
  loading,
  setLoading,
  error,
  setError,
  result,
  setResult,
}) {
                  className="h-7 text-[11px]"

  const breakdown = result?.breakdown;
  const nights = breakdown?.nights;
  const ruleHits = result?.rule_hits || [];
  const notes = result?.notes || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Fiyat Hesaplayıcı</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs mt-2">
          <form onSubmit={onSubmit} className="space-y-2">
            <div className="space-y-1">
              <Label className="text-[11px] text-muted-foreground">Partner</Label>
              <div className="text-[11px] font-mono bg-muted rounded px-2 py-1">
                {partnerId || "-"}
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-[11px] text-muted-foreground">Ürün</Label>
              <div className="text-[11px] font-mono bg-muted rounded px-2 py-1">
                {product?.product_id} · {product?.title}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Check-in</Label>
                <Input
                  type="date"
                  className="h-8"
                  value={requestState.checkin}
                  onChange={(e) => handleChange("checkin", e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Check-out</Label>
                <Input
                  type="date"
                  className="h-8"
                  value={requestState.checkout}
                  onChange={(e) => handleChange("checkout", e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Yetişkin</Label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  className="h-8"
                  value={requestState.adults}
                  onChange={(e) => handleChange("adults", e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Çocuk</Label>
                <Input
                  type="number"
                  min={0}
                  max={10}
                  className="h-8"
                  value={requestState.children}
                  onChange={(e) => handleChange("children", e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Oda</Label>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  className="h-8"
                  value={requestState.rooms}
                  onChange={(e) => handleChange("rooms", e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-[11px] text-muted-foreground">Para birimi</Label>
              <Input
                type="text"
                className="h-8"
                value={requestState.currency}
                onChange={(e) => handleChange("currency", e.target.value.toUpperCase())}
              />
            </div>
            <div className="flex items-center justify-between pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setResult(null);
                  setError("");
                }}
              >
                Temizle
              </Button>
              <Button type="submit" size="sm" disabled={!canSubmit}>
                {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                Hesapla
              </Button>
            </div>
            {error && (
              <div className="mt-2 text-[11px] text-destructive flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                <span>{error}</span>
              </div>
            )}
          </form>

          <div className="space-y-2">
            {!result && !error && (
              <p className="text-[11px] text-muted-foreground">
                Parametreleri doldurup "Hesapla" ile bu partner/ürün için fiyat önizlemesi alabilirsiniz.
              </p>
            )}
            {result && (
              <div className="space-y-2">
                <div className="rounded border bg-muted/40 p-2 space-y-1">
                  <div className="text-[11px] font-semibold">Özet</div>
                  <div className="text-[11px] text-muted-foreground">
                    Gece sayısı: <span className="font-mono">{nights}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Base price: <span className="font-mono">{breakdown.base_price} {result.currency}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Markup: <span className="font-mono">{breakdown.markup_percent}%</span> (
                    <span className="font-mono">{breakdown.markup_amount} {result.currency}</span>)
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Komisyon: <span className="font-mono">{breakdown.commission_rate}%</span> (
                    <span className="font-mono">{breakdown.commission_amount} {result.currency}</span>)
                  </div>
                  <div className="text-[11px] text-muted-foreground font-semibold">
                    Final satış: <span className="font-mono">{breakdown.final_sell_price} {result.currency}</span>
                  </div>
                </div>

                {ruleHits.length > 0 && (
                  <div className="rounded border bg-muted/40 p-2 space-y-1">
                    <div className="text-[11px] font-semibold">Uygulanan kurallar</div>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-muted-foreground">
                      {ruleHits.map((r) => (
                        <li key={r.rule_id}>
                          <span className="font-mono mr-1">{r.rule_id}</span>
                          <span>{r.effect}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {notes.length > 0 && (
                  <div className="rounded border bg-muted/40 p-2 space-y-1">
                    <div className="text-[11px] font-semibold">Notlar</div>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-muted-foreground">
                      {notes.map((n, idx) => (
                        <li key={idx}>{n}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

                <Label className="text-[11px] text-muted-foreground">Çocuk</Label>
                <Input
                  type="number"
                  min={0}
                  max={10}
                  className="h-8"
                  value={requestState.children}
                  onChange={(e) => handleChange("children", e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">Oda</Label>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  className="h-8"
                  value={requestState.rooms}
                  onChange={(e) => handleChange("rooms", e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-[11px] text-muted-foreground">Para birimi</Label>
              <Input
                type="text"
                className="h-8"
                value={requestState.currency}
                onChange={(e) => handleChange("currency", e.target.value.toUpperCase())}
              />
            </div>
            <div className="flex items-center justify-between pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setResult(null);
                  setError("");
                }}
              >
                Temizle
              </Button>
              <Button type="submit" size="sm" disabled={!canSubmit}>
                {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                Hesapla
              </Button>
            </div>
            {error && (
              <div className="mt-2 text-[11px] text-destructive flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                <span>{error}</span>
              </div>
            )}
          </form>

          <div className="space-y-2">
            {!result && !error && (
              <p className="text-[11px] text-muted-foreground">
                Parametreleri doldurup "Hesapla" ile bu partner/ürün için fiyat önizlemesi alabilirsiniz.
              </p>
            )}
            {result && (
              <div className="space-y-2">
                <div className="rounded border bg-muted/40 p-2 space-y-1">
                  <div className="text-[11px] font-semibold">Özet</div>
                  <div className="text-[11px] text-muted-foreground">
                    Gece sayısı: <span className="font-mono">{nights}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Base price: <span className="font-mono">{breakdown.base_price} {result.currency}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Markup: <span className="font-mono">{breakdown.markup_percent}%</span> (
                    <span className="font-mono">{breakdown.markup_amount} {result.currency}</span>)
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Komisyon: <span className="font-mono">{breakdown.commission_rate}%</span> (
                    <span className="font-mono">{breakdown.commission_amount} {result.currency}</span>)
                  </div>
                  <div className="text-[11px] text-muted-foreground font-semibold">
                    Final satış: <span className="font-mono">{breakdown.final_sell_price} {result.currency}</span>
                  </div>
                </div>

                {ruleHits.length > 0 && (
                  <div className="rounded border bg-muted/40 p-2 space-y-1">
                    <div className="text-[11px] font-semibold">Uygulanan kurallar</div>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-muted-foreground">
                      {ruleHits.map((r) => (
                        <li key={r.rule_id}>
                          <span className="font-mono mr-1">{r.rule_id}</span>
                          <span>{r.effect}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {notes.length > 0 && (
                  <div className="rounded border bg-muted/40 p-2 space-y-1">
                    <div className="text-[11px] font-semibold">Notlar</div>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-muted-foreground">
                      {notes.map((n, idx) => (
                        <li key={idx}>{n}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

                  className="h-7 text-[11px]"
                  onClick={loadPartners}
                  disabled={partnersLoading}
                >
                  {partnersLoading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}Yenile
                </Button>
              </div>
              <div className="mt-2 max-h-[420px] overflow-y-auto border rounded-xl divide-y">
                {partnersError && (
                  <div className="p-3 text-[11px] text-destructive flex items-start gap-2">
                    <AlertCircle className="h-3 w-3 mt-0.5" />
                    <span>{partnersError}</span>
                  </div>
                )}

                {!partnersError && filteredPartners.length === 0 && !partnersLoading && (
                  <div className="p-4 text-center text-[11px] text-muted-foreground">
                    Henüz partner yok. Önce Partnerler ekranından bir partner oluşturun.
                  </div>
                )}

                {filteredPartners.map((p) => (
                  <div
                    key={p.id}
                    className={`px-3 py-2 text-xs cursor-pointer flex items-center justify-between gap-2 hover:bg-muted/60 ${
                      selectedPartnerId === p.id ? "bg-muted" : ""
                    }`}
                    onClick={() => {
                      setSelectedPartnerId(p.id);
                      setSelectedPartnerName(p.name);
                    }}
                  >
                    <div className="flex flex-col">
                      <span className="font-medium truncate max-w-[160px]">{p.name}</span>
                      <span className="text-[10px] text-muted-foreground truncate max-w-[180px]">
                        {p.contact_email || "-"}
                      </span>
                    </div>
                    <StatusBadge status={p.status} />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sağ panel: Ürün yetkilendirme */}
        <div className="md:col-span-8 lg:col-span-9 space-y-3">
          <div className="flex items-center gap-2">
            <Store className="h-5 w-5" />
            <div>
              <h1 className="text-lg font-semibold text-foreground">B2B Marketplace</h1>
              <p className="text-xs text-muted-foreground">
                Seçili partner için hangi ürünlerin satılabilir/görünür olduğunu ve ürün bazlı komisyon oranlarını
                yönetin.
              </p>
            </div>
          </div>

          {!selectedPartnerId && (
            <Card>
              <CardContent className="py-10 flex flex-col items-center gap-3 text-center">
                <Store className="h-8 w-8 text-muted-foreground" />
                <p className="font-semibold text-foreground">Partner seçilmedi</p>
                <p className="text-sm text-muted-foreground max-w-sm">
                  Soldaki listeden bir partner seçerek ürün yetkilendirme detaylarını görüntüleyebilirsiniz.
                </p>
              </CardContent>
            </Card>
          )}

          {selectedPartnerId && (
            <Card>
              <CardHeader className="pb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <CardTitle className="text-sm font-medium">{currentPartnerLabel}</CardTitle>
                  <p className="text-xs text-muted-foreground mt-1">
                    Varsayılan kural: Kayıt yoksa ürün kapalı kabul edilir. Yalnızca açtığınız ürünler ilgili
                    partner için listelenir ve satılabilir olur.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2 items-center text-[11px]">
                  <select
                    className="h-8 rounded-md border bg-background px-2 text-[11px]"
                    value={productTypeFilter}
                    onChange={(e) => setProductTypeFilter(e.target.value)}
                  >
                    <option value="">Tüm türler</option>
                    <option value="hotel">Otel</option>
                    <option value="tour">Tur</option>
                  </select>
                  <select
                    className="h-8 rounded-md border bg-background px-2 text-[11px]"
                    value={productStatusFilter}
                    onChange={(e) => setProductStatusFilter(e.target.value)}
                  >
                    <option value="">Tüm durumlar</option>
                    <option value="active">Aktif</option>
                    <option value="passive">Pasif</option>
                  </select>
                  <div className="relative">
                    <Search className="absolute left-2 top-2.5 h-3 w-3 text-muted-foreground" />
                    <Input
                      className="pl-7 h-8 text-[11px] w-48"
                      placeholder="Ad / Kod / Şehir filtrele"
                      value={productSearchInput}
                      onChange={(e) => {
                        setProductPage(1);
                        setProductSearchInput(e.target.value);
                      }}
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
              {productsLoading && products.length === 0 && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Ürünler yükleniyor...
                </div>
              )}

              {!productsLoading && productsError && (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
                  <AlertCircle className="h-4 w-4 mt-0.5" />
                  <span>{productsError}</span>
                </div>
              )}

              {!productsLoading && !productsError && products.length === 0 && (
                <EmptyState
                  title="Görüntülenecek ürün bulunamadı"
                  description="Katalogta hiç ürün olmayabilir veya filtre çok dar olabilir. Filtreleri gevşeterek tekrar deneyin."
                  className="py-12"
                />
              )}

              {!productsLoading && !productsError && products.length > 0 && (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">Ürün</TableHead>
                        <TableHead className="text-xs">Tür</TableHead>
                        <TableHead className="text-xs">Durum</TableHead>
                        <TableHead className="text-xs text-center">Açık mı?</TableHead>
                        <TableHead className="text-xs text-right">
                          <div className="flex items-center justify-end gap-1">
                            <span>Komisyon %</span>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  type="button"
                                  className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-muted-foreground/40 text-[10px] text-muted-foreground hover:bg-muted/40 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                                  aria-label="Komisyon hesaplama açıklaması"
                                >
                                  <Info className="h-3 w-3" />
                                </button>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-[260px] text-[11px] leading-snug">
                                <div className="font-semibold mb-1">Komisyon Hesabı</div>
                                <p>Komisyon, liste marjdan hesaplanır.</p>
                                <p>Liste Marj = Liste Satış − Net (Tedarikçi).</p>
                                <p>İndirimler komisyonu etkilemez; bizim marjımızdan düşer.</p>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        </TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {products.map((p) => (
                        <TableRow key={p.product_id}>
                          <TableCell className="text-xs">
                            <div className="flex flex-col">
                              <span className="font-medium truncate max-w-[260px]">{p.title}</span>
                              <span className="text-[11px] text-muted-foreground font-mono">{p.product_id}</span>
                            </div>
                          </TableCell>
                          <TableCell className="text-xs">
                            <ProductTypeBadge type={p.type} />
                          </TableCell>
                          <TableCell className="text-xs">
                            {p.status === "active" ? (
                              <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                                Aktif
                              </Badge>
                            ) : (
                              <Badge variant="secondary">Pasif</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-xs text-center">
                            <div className="flex items-center justify-center gap-2">
                              <Button
                                type="button"
                                size="sm"
                                variant={p.is_enabled ? "outline" : "secondary"}
                                className="h-7 text-[11px] px-3"
                                disabled={savingKey === p.product_id}
                                onClick={() => handleToggle(p)}
                              >
                                {savingKey === p.product_id
                                  ? "Kaydediliyor..."
                                  : p.is_enabled
                                  ? "Açık (kapat)"
                                  : "Kapalı (aç)"}
                              </Button>
                              <Button
                                size="sm"
                                variant="secondary"
                                className="h-7 text-[11px] px-3"
                                onClick={() => {
                                  const productId = p.product_id ?? p._id ?? p.id;
                                  if (!productId) {
                                    // Ürün id yoksa buton pasif kalmalı; yine de defensive log bırakalım
                                    // eslint-disable-next-line no-console
                                    console.warn("Fiyat Önizleme: product id bulunamadı", p);
                                    return;
                                  }
                                  setPreviewContext({
                                    product_id: productId,
                                    partner_id: selectedPartnerId || null,
                                    check_in: new Date().toISOString().slice(0, 10),
                                    nights: 1,
                                    rooms: 1,
                                    adults: 2,
                                    children: 0,
                                    currency: "EUR",
                                  });
                                  setPreviewOpen(true);
                                }}
                                disabled={! (p.product_id ?? p._id ?? p.id)}
                              >
                                Fiyat Önizleme
                              </Button>
                            </div>
                          </TableCell>
                          <TableCell className="text-xs text-right align-middle">
                            <input
                              type="number"
                              step="0.1"
                              className="h-8 w-20 rounded-md border bg-background px-2 text-right text-[11px]"
                              defaultValue={
                                typeof p.commission_rate === "number" ? String(p.commission_rate) : ""
                              }
                              onBlur={(e) => handleCommissionBlur(p, e.target.value)}
                              placeholder="-"
                              disabled={savingKey === p.product_id + "-commission"}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}

              {/* Pagination controls */}
              {!productsLoading && (
                <div className="flex items-center justify-between mt-3 text-[11px] text-muted-foreground">
                  <span>Sayfa {productPage}</span>
                  <div className="flex items-center gap-2">
                    <select
                      className="h-7 rounded-md border bg-background px-2 text-[11px]"
                      value={productLimit}
                      onChange={(e) => {
                        setProductPage(1);
                        setProductLimit(Number(e.target.value) || 50);
                      }}
                    >
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                      <option value={200}>200</option>
                    </select>
                    <Button
                      type="button"
                      size="xs"
                      variant="outline"
                      disabled={productPage === 1 || productsLoading}
                      onClick={() => setProductPage((p) => Math.max(1, p - 1))}
                    >
                      Önceki
                    </Button>
                    <Button
                      type="button"
                      size="xs"
                      variant="outline"
                      disabled={!productHasMore || productsLoading}
                      onClick={() => setProductPage((p) => p + 1)}
                    >
                      Sonraki
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
        </div>
      </div>

      {productsErrorDetails?.isRetryable && !productsLoading && (
        <div className="mt-3">
          <ErrorCard details={productsErrorDetails} onRetry={loadProducts} />
        </div>
      )}

      {/* Pricing Dialog */}
      <Dialog open={pricingOpen} onOpenChange={setPricingOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-sm">Fiyat Hesaplama</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {pricingProduct && (
              <div className="text-xs text-muted-foreground">
                <div className="font-medium">{pricingProduct.title}</div>
                <div className="font-mono">{pricingProduct.product_id}</div>
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Check-in</Label>
                <Input
                  type="date"
                  className="h-8 text-xs"
                  value={pricingRequest.checkin}
                  onChange={(e) => setPricingRequest(prev => ({ ...prev, checkin: e.target.value }))}
                />
              </div>
              <div>
                <Label className="text-xs">Check-out</Label>
                <Input
                  type="date"
                  className="h-8 text-xs"
                  value={pricingRequest.checkout}
                  onChange={(e) => setPricingRequest(prev => ({ ...prev, checkout: e.target.value }))}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Yetişkin</Label>
                <Input
                  type="number"
                  min="1"
                  className="h-8 text-xs"
                  value={pricingRequest.adults}
                  onChange={(e) => setPricingRequest(prev => ({ ...prev, adults: parseInt(e.target.value) || 1 }))}
                />
              </div>
              <div>
                <Label className="text-xs">Çocuk</Label>
                <Input
                  type="number"
                  min="0"
                  className="h-8 text-xs"
                  value={pricingRequest.children}
                  onChange={(e) => setPricingRequest(prev => ({ ...prev, children: parseInt(e.target.value) || 0 }))}
                />
              </div>
              <div>
                <Label className="text-xs">Oda</Label>
                <Input
                  type="number"
                  min="1"
                  className="h-8 text-xs"
                  value={pricingRequest.rooms}
                  onChange={(e) => setPricingRequest(prev => ({ ...prev, rooms: parseInt(e.target.value) || 1 }))}
                />
              </div>
            </div>

            <div>
              <Label className="text-xs">Para Birimi</Label>
              <select
                className="w-full h-8 rounded-md border bg-background px-2 text-xs"
                value={pricingRequest.currency}
                onChange={(e) => setPricingRequest(prev => ({ ...prev, currency: e.target.value }))}
              >
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
                <option value="TRY">TRY</option>
              </select>
            </div>

            {pricingError && (
              <div className="text-xs text-destructive bg-destructive/10 p-2 rounded">
                {pricingError}
              </div>
            )}

            {pricingResult && (
              <div className="text-xs bg-muted p-3 rounded space-y-1">
                <div className="font-medium">Fiyat Bilgisi:</div>
                <div>Net Fiyat: {pricingResult.net_price} {pricingResult.currency}</div>
                <div>Liste Fiyatı: {pricingResult.list_price} {pricingResult.currency}</div>
                <div>Komisyon: {pricingResult.commission} {pricingResult.currency}</div>
              </div>
            )}

            <div className="flex gap-2 justify-end">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setPricingOpen(false)}
              >
                İptal
              </Button>
              <Button
                size="sm"
                disabled={pricingLoading || !pricingRequest.checkin || !pricingRequest.checkout}
                onClick={handlePricingRequest}
              >
                {pricingLoading ? "Hesaplanıyor..." : "Fiyat Hesapla"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
}
