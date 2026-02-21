import React, { useCallback, useEffect, useState, useMemo } from "react";
import {
  Building2, Hotel, DollarSign, Image, Plus, Trash2, Edit, Search,
  FileText, Percent, Tag, Calendar, Save, X, CheckCircle2, AlertTriangle,
  Layers, Star, Eye
} from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "../components/ui/dialog";
import EmptyState from "../components/EmptyState";

/* ─────── Tabs ─────── */
function TabButton({ active, onClick, icon: Icon, label, count }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-all ${
        active
          ? "bg-primary text-primary-foreground shadow-sm"
          : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
      {count > 0 && (
        <span className={`ml-1 flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-2xs font-bold ${
          active ? "bg-white/20 text-primary-foreground" : "bg-muted text-muted-foreground"
        }`}>
          {count}
        </span>
      )}
    </button>
  );
}

/* ─────── Pricing Contract Form ─────── */
function PricingContractForm({ open, onOpenChange, agencies, hotels, existingData, onSaved }) {
  const [agencyId, setAgencyId] = useState("");
  const [hotelId, setHotelId] = useState("");
  const [markupPercent, setMarkupPercent] = useState("");
  const [discountPercent, setDiscountPercent] = useState("");
  const [fixedCommission, setFixedCommission] = useState("");
  const [currency, setCurrency] = useState("TRY");
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open && existingData) {
      setAgencyId(existingData.agency_id || "");
      setHotelId(existingData.hotel_id || "");
      setMarkupPercent(existingData.markup_percent != null ? String(existingData.markup_percent) : "");
      setDiscountPercent(existingData.discount_percent != null ? String(existingData.discount_percent) : "");
      setFixedCommission(existingData.fixed_commission != null ? String(existingData.fixed_commission) : "");
      setCurrency(existingData.currency || "TRY");
      setValidFrom(existingData.valid_from || "");
      setValidTo(existingData.valid_to || "");
      setIsActive(existingData.is_active !== false);
    } else if (open) {
      setAgencyId("");
      setHotelId("");
      setMarkupPercent("");
      setDiscountPercent("");
      setFixedCommission("");
      setCurrency("TRY");
      setValidFrom("");
      setValidTo("");
      setIsActive(true);
    }
    setError("");
  }, [open, existingData]);

  async function save() {
    if (!agencyId || !hotelId) {
      setError("Acenta ve otel seçimi zorunludur.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const payload = {
        agency_id: agencyId,
        hotel_id: hotelId,
        currency,
        is_active: isActive,
      };
      if (markupPercent) payload.markup_percent = parseFloat(markupPercent);
      if (discountPercent) payload.discount_percent = parseFloat(discountPercent);
      if (fixedCommission) payload.fixed_commission = parseFloat(fixedCommission);
      if (validFrom) payload.valid_from = validFrom;
      if (validTo) payload.valid_to = validTo;

      await api.post("/admin/agency-contracts/pricing", payload);
      onSaved?.();
      onOpenChange(false);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <DollarSign className="h-5 w-5 text-primary" />
            {existingData ? "Fiyat Sözleşmesi Düzenle" : "Yeni Fiyat Sözleşmesi"}
          </DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Acenta *</Label>
            <Select value={agencyId} onValueChange={setAgencyId} disabled={!!existingData}>
              <SelectTrigger data-testid="contract-agency">
                <SelectValue placeholder="Acenta seç..." />
              </SelectTrigger>
              <SelectContent>
                {agencies.map((a) => (
                  <SelectItem key={a.id || a._id} value={a.id || a._id}>{a.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Otel *</Label>
            <Select value={hotelId} onValueChange={setHotelId} disabled={!!existingData}>
              <SelectTrigger data-testid="contract-hotel">
                <SelectValue placeholder="Otel seç..." />
              </SelectTrigger>
              <SelectContent>
                {hotels.map((h) => (
                  <SelectItem key={h.id || h._id} value={h.id || h._id}>{h.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Markup (%)</Label>
            <Input
              type="number" step="0.1" value={markupPercent}
              onChange={(e) => setMarkupPercent(e.target.value)}
              placeholder="Örn: 10"
              data-testid="contract-markup"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">İndirim (%)</Label>
            <Input
              type="number" step="0.1" value={discountPercent}
              onChange={(e) => setDiscountPercent(e.target.value)}
              placeholder="Örn: 5"
              data-testid="contract-discount"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Sabit Komisyon</Label>
            <Input
              type="number" step="0.01" value={fixedCommission}
              onChange={(e) => setFixedCommission(e.target.value)}
              placeholder="Örn: 150.00"
              data-testid="contract-commission"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Para Birimi</Label>
            <Select value={currency} onValueChange={setCurrency}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="TRY">TRY (₺)</SelectItem>
                <SelectItem value="EUR">EUR (€)</SelectItem>
                <SelectItem value="USD">USD ($)</SelectItem>
                <SelectItem value="GBP">GBP (£)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Geçerlilik Başlangıcı</Label>
            <Input type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Geçerlilik Bitişi</Label>
            <Input type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} />
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <input
              type="checkbox" id="pricing-active" checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            <Label htmlFor="pricing-active" className="text-xs font-medium text-muted-foreground cursor-pointer">
              Aktif
            </Label>
          </div>
        </div>
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600 flex items-center gap-1.5">
            <AlertTriangle className="h-3 w-3 shrink-0" /> {error}
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Vazgeç</Button>
          <Button onClick={save} disabled={loading} className="gap-1.5">
            <Save className="h-3.5 w-3.5" />
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ─────── Content Override Form ─────── */
function ContentOverrideForm({ open, onOpenChange, agencies, hotels, existingData, onSaved }) {
  const [agencyId, setAgencyId] = useState("");
  const [hotelId, setHotelId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [imagesText, setImagesText] = useState("");
  const [starRating, setStarRating] = useState("");
  const [customTags, setCustomTags] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open && existingData) {
      setAgencyId(existingData.agency_id || "");
      setHotelId(existingData.hotel_id || "");
      setDisplayName(existingData.display_name || "");
      setDescription(existingData.description || "");
      setImagesText((existingData.images || []).join("\n"));
      setStarRating(existingData.star_rating != null ? String(existingData.star_rating) : "");
      setCustomTags((existingData.custom_tags || []).join(", "));
      setIsActive(existingData.is_active !== false);
    } else if (open) {
      setAgencyId(""); setHotelId(""); setDisplayName(""); setDescription("");
      setImagesText(""); setStarRating(""); setCustomTags(""); setIsActive(true);
    }
    setError("");
  }, [open, existingData]);

  async function save() {
    if (!agencyId || !hotelId) {
      setError("Acenta ve otel seçimi zorunludur.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const payload = {
        agency_id: agencyId,
        hotel_id: hotelId,
        is_active: isActive,
      };
      if (displayName) payload.display_name = displayName;
      if (description) payload.description = description;
      if (imagesText.trim()) payload.images = imagesText.split("\n").map(s => s.trim()).filter(Boolean);
      if (starRating) payload.star_rating = parseInt(starRating);
      if (customTags.trim()) payload.custom_tags = customTags.split(",").map(s => s.trim()).filter(Boolean);

      await api.post("/admin/agency-contracts/content", payload);
      onSaved?.();
      onOpenChange(false);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <Image className="h-5 w-5 text-primary" />
            {existingData ? "İçerik Özelleştirmesi Düzenle" : "Yeni İçerik Özelleştirmesi"}
          </DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Acenta *</Label>
            <Select value={agencyId} onValueChange={setAgencyId} disabled={!!existingData}>
              <SelectTrigger data-testid="content-agency">
                <SelectValue placeholder="Acenta seç..." />
              </SelectTrigger>
              <SelectContent>
                {agencies.map((a) => (
                  <SelectItem key={a.id || a._id} value={a.id || a._id}>{a.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Otel *</Label>
            <Select value={hotelId} onValueChange={setHotelId} disabled={!!existingData}>
              <SelectTrigger data-testid="content-hotel">
                <SelectValue placeholder="Otel seç..." />
              </SelectTrigger>
              <SelectContent>
                {hotels.map((h) => (
                  <SelectItem key={h.id || h._id} value={h.id || h._id}>{h.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 col-span-2">
            <Label className="text-xs font-medium text-muted-foreground">Görünen Otel Adı</Label>
            <Input
              value={displayName} onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Acenta için özel otel adı"
              data-testid="content-display-name"
            />
          </div>
          <div className="space-y-2 col-span-2">
            <Label className="text-xs font-medium text-muted-foreground">Açıklama</Label>
            <textarea
              value={description} onChange={(e) => setDescription(e.target.value)}
              placeholder="Acenta için özel otel açıklaması..."
              className="flex min-h-[80px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              data-testid="content-description"
            />
          </div>
          <div className="space-y-2 col-span-2">
            <Label className="text-xs font-medium text-muted-foreground">Görseller (her satıra bir URL)</Label>
            <textarea
              value={imagesText} onChange={(e) => setImagesText(e.target.value)}
              placeholder={"https://example.com/image1.jpg\nhttps://example.com/image2.jpg"}
              className="flex min-h-[80px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none font-mono text-xs"
              data-testid="content-images"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Yıldız Puanı</Label>
            <Select value={starRating} onValueChange={setStarRating}>
              <SelectTrigger><SelectValue placeholder="Seç..." /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">Varsayılan</SelectItem>
                <SelectItem value="1">1 ★</SelectItem>
                <SelectItem value="2">2 ★★</SelectItem>
                <SelectItem value="3">3 ★★★</SelectItem>
                <SelectItem value="4">4 ★★★★</SelectItem>
                <SelectItem value="5">5 ★★★★★</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground">Özel Etiketler (virgülle ayırın)</Label>
            <Input
              value={customTags} onChange={(e) => setCustomTags(e.target.value)}
              placeholder="VIP, Premium, Özel Fiyat"
              data-testid="content-tags"
            />
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <input
              type="checkbox" id="content-active" checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            <Label htmlFor="content-active" className="text-xs font-medium text-muted-foreground cursor-pointer">
              Aktif
            </Label>
          </div>
        </div>
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600 flex items-center gap-1.5">
            <AlertTriangle className="h-3 w-3 shrink-0" /> {error}
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Vazgeç</Button>
          <Button onClick={save} disabled={loading} className="gap-1.5">
            <Save className="h-3.5 w-3.5" />
            {loading ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ═══════════════════════ MAIN PAGE ═══════════════════════ */
export default function AdminAgencyContractsPage() {
  const [tab, setTab] = useState("pricing");
  const [agencies, setAgencies] = useState([]);
  const [hotels, setHotels] = useState([]);

  const [pricingContracts, setPricingContracts] = useState([]);
  const [contentOverrides, setContentOverrides] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [filterAgency, setFilterAgency] = useState("all");
  const [filterHotel, setFilterHotel] = useState("all");

  // Forms
  const [pricingFormOpen, setPricingFormOpen] = useState(false);
  const [contentFormOpen, setContentFormOpen] = useState(false);
  const [editData, setEditData] = useState(null);

  // Load agencies and hotels on mount
  useEffect(() => {
    (async () => {
      try {
        const [ag, ht] = await Promise.all([
          api.get("/admin/agencies"),
          api.get("/admin/hotels/"),
        ]);
        setAgencies(ag.data || []);
        setHotels(ht.data || []);
      } catch (e) {
        console.warn("Could not load agencies/hotels:", e);
      }
    })();
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const pParams = {};
      const cParams = {};
      if (filterAgency && filterAgency !== "all") {
        pParams.agency_id = filterAgency;
        cParams.agency_id = filterAgency;
      }
      if (filterHotel && filterHotel !== "all") {
        pParams.hotel_id = filterHotel;
        cParams.hotel_id = filterHotel;
      }
      const [p, c] = await Promise.all([
        api.get("/admin/agency-contracts/pricing", { params: pParams }),
        api.get("/admin/agency-contracts/content", { params: cParams }),
      ]);
      setPricingContracts(p.data || []);
      setContentOverrides(c.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [filterAgency, filterHotel]);

  useEffect(() => { loadData(); }, [loadData]);

  // Name resolution helpers
  const agencyMap = useMemo(() => {
    const m = {};
    agencies.forEach((a) => { m[a.id || a._id] = a.name; });
    return m;
  }, [agencies]);

  const hotelMap = useMemo(() => {
    const m = {};
    hotels.forEach((h) => { m[h.id || h._id] = h.name; });
    return m;
  }, [hotels]);

  async function deletePricing(contractId) {
    if (!window.confirm("Bu fiyat sözleşmesini silmek istediğinizden emin misiniz?")) return;
    try {
      await api.delete(`/admin/agency-contracts/pricing/${contractId}`);
      loadData();
    } catch (e) {
      alert(apiErrorMessage(e));
    }
  }

  function editPricing(item) {
    setEditData(item);
    setPricingFormOpen(true);
  }

  function editContent(item) {
    setEditData(item);
    setContentFormOpen(true);
  }

  return (
    <div className="space-y-5">
      {/* ── Page Header ── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Acenta Sözleşmeleri
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground/70 font-medium">
            Acenta özel fiyatlandırma ve içerik yönetimi
          </p>
        </div>
        <Button
          onClick={() => {
            setEditData(null);
            if (tab === "pricing") setPricingFormOpen(true);
            else setContentFormOpen(true);
          }}
          size="sm"
          className="gap-1.5 text-xs font-medium h-9"
          data-testid="contract-new"
        >
          <Plus className="h-3.5 w-3.5" />
          {tab === "pricing" ? "Yeni Fiyat Sözleşmesi" : "Yeni İçerik Özelleştirmesi"}
        </Button>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 rounded-lg bg-muted/30 p-1 border border-border/40 w-fit">
        <TabButton
          active={tab === "pricing"}
          onClick={() => setTab("pricing")}
          icon={DollarSign}
          label="Fiyatlandırma"
          count={pricingContracts.length}
        />
        <TabButton
          active={tab === "content"}
          onClick={() => setTab("content")}
          icon={Image}
          label="İçerik Özelleştirmeleri"
          count={contentOverrides.length}
        />
      </div>

      {/* ── Filters ── */}
      <Card className="rounded-xl shadow-sm border-border/60">
        <CardHeader className="pb-3 px-5 pt-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5">
            <div className="md:col-span-5">
              <Select value={filterAgency} onValueChange={setFilterAgency}>
                <SelectTrigger className="h-9 text-xs" data-testid="filter-agency">
                  <SelectValue placeholder="Tüm acentalar" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tüm Acentalar</SelectItem>
                  {agencies.map((a) => (
                    <SelectItem key={a.id || a._id} value={a.id || a._id}>{a.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-4">
              <Select value={filterHotel} onValueChange={setFilterHotel}>
                <SelectTrigger className="h-9 text-xs" data-testid="filter-hotel">
                  <SelectValue placeholder="Tüm oteller" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tüm Oteller</SelectItem>
                  {hotels.map((h) => (
                    <SelectItem key={h.id || h._id} value={h.id || h._id}>{h.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-3">
              <Button variant="outline" onClick={loadData} className="w-full h-9 gap-1.5 text-xs font-medium">
                <Search className="h-3 w-3" />
                Filtrele
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="px-5 pb-5">
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-600 mb-3 flex items-center gap-1.5">
              <AlertTriangle className="h-3 w-3 shrink-0" /> {error}
            </div>
          )}

          {/* ── Pricing Tab ── */}
          {tab === "pricing" && (
            <div className="overflow-x-auto rounded-lg border border-border/40">
              <Table data-testid="pricing-table">
                <TableHeader>
                  <TableRow className="bg-muted/30 hover:bg-muted/30">
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Acenta</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Otel</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Markup</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">İndirim</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Komisyon</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Geçerlilik</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Durum</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9 text-right">İşlem</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={8} className="py-12 text-center">
                        <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                          Yükleniyor...
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : pricingContracts.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="py-8">
                        <EmptyState
                          title="Henüz fiyat sözleşmesi yok"
                          description="Farklı acenteler için özel fiyatlandırma oluşturabilirsiniz."
                          action={
                            <Button onClick={() => { setEditData(null); setPricingFormOpen(true); }} size="sm" className="text-xs gap-1.5">
                              <Plus className="h-3 w-3" /> İlk sözleşmeyi oluştur
                            </Button>
                          }
                        />
                      </TableCell>
                    </TableRow>
                  ) : (
                    pricingContracts.map((c) => (
                      <TableRow key={c._id || c.id} className="hover:bg-muted/20 transition-colors">
                        <TableCell className="text-sm font-medium text-foreground py-3">
                          <div className="flex items-center gap-1.5">
                            <Building2 className="h-3.5 w-3.5 text-muted-foreground/50" />
                            {agencyMap[c.agency_id] || c.agency_id}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-foreground/80 py-3">
                          <div className="flex items-center gap-1.5">
                            <Hotel className="h-3.5 w-3.5 text-muted-foreground/50" />
                            {hotelMap[c.hotel_id] || c.hotel_id}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm py-3">
                          {c.markup_percent != null ? (
                            <span className="inline-flex items-center gap-1 text-amber-700 bg-amber-50 px-2 py-0.5 rounded text-xs font-semibold">
                              +%{c.markup_percent}
                            </span>
                          ) : "—"}
                        </TableCell>
                        <TableCell className="text-sm py-3">
                          {c.discount_percent != null ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded text-xs font-semibold">
                              -%{c.discount_percent}
                            </span>
                          ) : "—"}
                        </TableCell>
                        <TableCell className="text-sm py-3">
                          {c.fixed_commission != null ? (
                            <span className="text-xs font-medium">{c.fixed_commission} {c.currency}</span>
                          ) : "—"}
                        </TableCell>
                        <TableCell className="text-2xs text-muted-foreground py-3">
                          {c.valid_from || c.valid_to ? (
                            <span>{c.valid_from || "∞"} → {c.valid_to || "∞"}</span>
                          ) : "Süresiz"}
                        </TableCell>
                        <TableCell className="py-3">
                          {c.is_active !== false ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full text-2xs font-semibold">
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Aktif
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-slate-500 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-full text-2xs font-semibold">
                              <span className="h-1.5 w-1.5 rounded-full bg-slate-400" /> Pasif
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right py-3">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost" size="sm"
                              className="h-7 w-7 p-0 text-primary hover:text-primary"
                              onClick={() => editPricing(c)}
                              data-testid={`pricing-edit-${c._id || c.id}`}
                            >
                              <Edit className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost" size="sm"
                              className="h-7 w-7 p-0 text-rose-500 hover:text-rose-700"
                              onClick={() => deletePricing(c._id || c.id)}
                              data-testid={`pricing-del-${c._id || c.id}`}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}

          {/* ── Content Tab ── */}
          {tab === "content" && (
            <div className="overflow-x-auto rounded-lg border border-border/40">
              <Table data-testid="content-table">
                <TableHeader>
                  <TableRow className="bg-muted/30 hover:bg-muted/30">
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Acenta</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Otel</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Özel İsim</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Görseller</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Yıldız</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Etiketler</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9">Durum</TableHead>
                    <TableHead className="text-2xs font-semibold uppercase tracking-wider text-muted-foreground/70 h-9 text-right">İşlem</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={8} className="py-12 text-center">
                        <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                          Yükleniyor...
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : contentOverrides.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="py-8">
                        <EmptyState
                          title="Henüz içerik özelleştirmesi yok"
                          description="Farklı acenteler için özel otel görselleri ve içerikleri belirleyebilirsiniz."
                          action={
                            <Button onClick={() => { setEditData(null); setContentFormOpen(true); }} size="sm" className="text-xs gap-1.5">
                              <Plus className="h-3 w-3" /> İlk özelleştirmeyi oluştur
                            </Button>
                          }
                        />
                      </TableCell>
                    </TableRow>
                  ) : (
                    contentOverrides.map((c) => (
                      <TableRow key={c._id || c.id} className="hover:bg-muted/20 transition-colors">
                        <TableCell className="text-sm font-medium text-foreground py-3">
                          <div className="flex items-center gap-1.5">
                            <Building2 className="h-3.5 w-3.5 text-muted-foreground/50" />
                            {agencyMap[c.agency_id] || c.agency_id}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-foreground/80 py-3">
                          <div className="flex items-center gap-1.5">
                            <Hotel className="h-3.5 w-3.5 text-muted-foreground/50" />
                            {hotelMap[c.hotel_id] || c.hotel_id}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm py-3">
                          {c.display_name || <span className="text-muted-foreground/50">—</span>}
                        </TableCell>
                        <TableCell className="py-3">
                          {(c.images || []).length > 0 ? (
                            <span className="inline-flex items-center gap-1 text-primary bg-primary/5 px-2 py-0.5 rounded text-2xs font-semibold">
                              <Image className="h-3 w-3" /> {c.images.length} görsel
                            </span>
                          ) : "—"}
                        </TableCell>
                        <TableCell className="py-3">
                          {c.star_rating != null ? (
                            <span className="inline-flex items-center gap-0.5 text-amber-600">
                              {Array.from({ length: c.star_rating }, (_, i) => (
                                <Star key={i} className="h-3 w-3 fill-amber-400 text-amber-400" />
                              ))}
                            </span>
                          ) : "—"}
                        </TableCell>
                        <TableCell className="py-3">
                          <div className="flex flex-wrap gap-1">
                            {(c.custom_tags || []).map((t, i) => (
                              <span key={i} className="inline-flex items-center px-1.5 py-0.5 rounded bg-primary/5 text-primary text-2xs font-medium">
                                {t}
                              </span>
                            ))}
                            {(c.custom_tags || []).length === 0 && "—"}
                          </div>
                        </TableCell>
                        <TableCell className="py-3">
                          {c.is_active !== false ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full text-2xs font-semibold">
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Aktif
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-slate-500 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-full text-2xs font-semibold">
                              <span className="h-1.5 w-1.5 rounded-full bg-slate-400" /> Pasif
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right py-3">
                          <Button
                            variant="ghost" size="sm"
                            className="h-7 w-7 p-0 text-primary hover:text-primary"
                            onClick={() => editContent(c)}
                            data-testid={`content-edit-${c._id || c.id}`}
                          >
                            <Edit className="h-3.5 w-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Forms ── */}
      <PricingContractForm
        open={pricingFormOpen}
        onOpenChange={setPricingFormOpen}
        agencies={agencies}
        hotels={hotels}
        existingData={editData}
        onSaved={loadData}
      />
      <ContentOverrideForm
        open={contentFormOpen}
        onOpenChange={setContentFormOpen}
        agencies={agencies}
        hotels={hotels}
        existingData={editData}
        onSaved={loadData}
      />
    </div>
  );
}
