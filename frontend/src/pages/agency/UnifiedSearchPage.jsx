import React, { useState, useMemo, useCallback } from "react";
import {
  Search, Loader2, ArrowUpDown, Filter, Hotel, Plane, Map, Bus, Ticket,
  ChevronRight, AlertTriangle, CheckCircle2, XCircle, ShieldCheck, RefreshCw,
  ArrowLeft, User, Mail, Phone, Building2, CreditCard, Clock, Zap, Star
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from "../../components/ui/dialog";
import { Separator } from "../../components/ui/separator";
import { toast } from "sonner";
import { unifiedSearch, revalidatePrice, executeBooking } from "../../lib/unifiedBooking";

const PRODUCT_TYPES = [
  { value: "hotel", label: "Otel", icon: Hotel },
  { value: "tour", label: "Tur", icon: Map },
  { value: "flight", label: "Ucus", icon: Plane },
  { value: "transfer", label: "Transfer", icon: Bus },
  { value: "activity", label: "Aktivite", icon: Ticket },
];

const SUPPLIER_COLORS = {
  ratehawk: "bg-blue-100 text-blue-800 border-blue-200",
  tbo: "bg-emerald-100 text-emerald-800 border-emerald-200",
  paximum: "bg-amber-100 text-amber-800 border-amber-200",
  wwtatil: "bg-violet-100 text-violet-800 border-violet-200",
};

function getSupplierBadgeClass(code) {
  const key = (code || "").toLowerCase().replace("real_", "");
  return SUPPLIER_COLORS[key] || "bg-gray-100 text-gray-700 border-gray-200";
}

function formatSupplierName(code) {
  return (code || "").replace("real_", "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function formatPrice(amount, currency = "TRY") {
  if (!amount && amount !== 0) return "-";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency }).format(amount);
}

// ===================== SEARCH FORM =====================
function SearchForm({ onSearch, loading }) {
  const [productType, setProductType] = useState("hotel");
  const [destination, setDestination] = useState("");
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!destination.trim()) {
      toast.error("Lutfen destinasyon giriniz");
      return;
    }
    onSearch({
      product_type: productType,
      destination: destination.trim(),
      check_in: checkIn || undefined,
      check_out: checkOut || undefined,
      adults,
      children,
      currency: "TRY",
    });
  };

  return (
    <Card data-testid="unified-search-form">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Search className="h-5 w-5 text-primary" />
          Coklu Supplier Arama
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Product type tabs */}
          <div>
            <Label className="text-xs font-medium text-muted-foreground mb-2 block">Urun Tipi</Label>
            <Tabs value={productType} onValueChange={setProductType}>
              <TabsList className="grid grid-cols-5 w-full">
                {PRODUCT_TYPES.map((pt) => (
                  <TabsTrigger
                    key={pt.value}
                    value={pt.value}
                    data-testid={`product-type-${pt.value}`}
                    className="flex items-center gap-1.5 text-xs"
                  >
                    <pt.icon className="h-3.5 w-3.5" />
                    {pt.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>

          {/* Search fields */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <Label htmlFor="destination" className="text-xs font-medium">Destinasyon</Label>
              <Input
                id="destination"
                data-testid="search-destination"
                placeholder="orn: Antalya"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="checkIn" className="text-xs font-medium">Giris Tarihi</Label>
              <Input
                id="checkIn"
                data-testid="search-checkin"
                type="date"
                value={checkIn}
                onChange={(e) => setCheckIn(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="checkOut" className="text-xs font-medium">Cikis Tarihi</Label>
              <Input
                id="checkOut"
                data-testid="search-checkout"
                type="date"
                value={checkOut}
                onChange={(e) => setCheckOut(e.target.value)}
                className="mt-1"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs font-medium">Yetiskin</Label>
                <Select value={String(adults)} onValueChange={(v) => setAdults(Number(v))}>
                  <SelectTrigger data-testid="search-adults" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[1,2,3,4,5,6].map(n => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs font-medium">Cocuk</Label>
                <Select value={String(children)} onValueChange={(v) => setChildren(Number(v))}>
                  <SelectTrigger data-testid="search-children" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[0,1,2,3,4].map(n => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <Button
            type="submit"
            disabled={loading}
            data-testid="search-submit-btn"
            className="w-full sm:w-auto"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Search className="h-4 w-4 mr-2" />}
            {loading ? "Aranıyor..." : "Supplier'larda Ara"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ===================== SEARCH RESULTS TABLE =====================
function SearchResultsTable({ items, searchMeta, onSelect, sortField, sortDir, onSort }) {
  if (!items || items.length === 0) return null;

  const handleSort = (field) => {
    onSort(field, sortField === field && sortDir === "asc" ? "desc" : "asc");
  };

  const SortHeader = ({ field, children }) => (
    <TableHead
      className="cursor-pointer select-none hover:bg-muted/50 transition-colors"
      onClick={() => handleSort(field)}
    >
      <span className="flex items-center gap-1">
        {children}
        <ArrowUpDown className="h-3 w-3 text-muted-foreground" />
      </span>
    </TableHead>
  );

  return (
    <Card data-testid="search-results-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">
            Arama Sonuclari ({items.length} sonuc)
          </CardTitle>
          {searchMeta && (
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {searchMeta.search_duration_ms}ms
              </span>
              <span>{searchMeta.suppliers_queried?.length || 0} supplier</span>
              {searchMeta.suppliers_failed?.length > 0 && (
                <Badge variant="destructive" className="text-[10px]">
                  {searchMeta.suppliers_failed.length} basarisiz
                </Badge>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="border rounded-lg overflow-auto max-h-[55vh]" data-testid="search-results-table">
          <Table>
            <TableHeader className="sticky top-0 bg-white dark:bg-background z-10">
              <TableRow>
                <SortHeader field="supplier_code">Supplier</SortHeader>
                <SortHeader field="name">Urun</SortHeader>
                <TableHead>Tip</TableHead>
                <SortHeader field="supplier_price">Supplier Fiyat</SortHeader>
                <SortHeader field="sell_price">Satis Fiyati</SortHeader>
                <TableHead>Musaitlik</TableHead>
                <TableHead>Iptal</TableHead>
                <TableHead className="text-right">Islem</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item, idx) => (
                <TableRow
                  key={item.item_id || idx}
                  className="hover:bg-muted/30 transition-colors cursor-pointer"
                  data-testid={`search-result-row-${idx}`}
                  onClick={() => onSelect(item)}
                >
                  <TableCell>
                    <Badge variant="outline" className={`text-[10px] font-medium ${getSupplierBadgeClass(item.supplier_code)}`}>
                      {formatSupplierName(item.supplier_code)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="max-w-[200px]">
                      <p className="font-medium text-sm truncate">{item.name || "-"}</p>
                      {item.description && (
                        <p className="text-xs text-muted-foreground truncate">{item.description}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="text-[10px]">
                      {item.product_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {formatPrice(item.supplier_price, item.currency)}
                  </TableCell>
                  <TableCell className="font-mono text-sm font-semibold">
                    {formatPrice(item.sell_price, item.currency)}
                  </TableCell>
                  <TableCell>
                    {item.available ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="text-xs text-muted-foreground truncate max-w-[100px] block">
                      {item.cancellation_policy || "Bilgi yok"}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="default"
                      data-testid={`select-item-btn-${idx}`}
                      onClick={(e) => { e.stopPropagation(); onSelect(item); }}
                      className="text-xs h-7"
                    >
                      Sec
                      <ChevronRight className="h-3 w-3 ml-1" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

// ===================== PRICE COMPARISON =====================
function PriceComparisonPanel({ items, onSelect }) {
  // Group by name (fuzzy match by name)
  const groups = useMemo(() => {
    const map = {};
    (items || []).forEach((item) => {
      const key = (item.name || "unknown").toLowerCase().trim();
      if (!map[key]) map[key] = { name: item.name, items: [] };
      map[key].items.push(item);
    });
    return Object.values(map).filter(g => g.items.length > 1).sort((a, b) => b.items.length - a.items.length);
  }, [items]);

  if (groups.length === 0) {
    return (
      <Card className="border-dashed" data-testid="no-comparison-card">
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          <Filter className="h-8 w-8 mx-auto mb-2 opacity-40" />
          Karsılastırılabilir urun bulunamadı. Farkli supplier'lardan benzer urunler oldugunda burada goruntulenir.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="price-comparison-panel">
      <h3 className="text-sm font-semibold flex items-center gap-2">
        <ArrowUpDown className="h-4 w-4 text-primary" />
        Supplier Karsılastırması ({groups.length} grup)
      </h3>
      {groups.slice(0, 5).map((group, gIdx) => (
        <Card key={gIdx} data-testid={`comparison-group-${gIdx}`}>
          <CardHeader className="py-3 pb-2">
            <CardTitle className="text-sm">{group.name}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Supplier</TableHead>
                  <TableHead className="text-xs">Fiyat</TableHead>
                  <TableHead className="text-xs">Iptal</TableHead>
                  <TableHead className="text-xs text-right">Islem</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {group.items
                  .sort((a, b) => (a.supplier_price || 0) - (b.supplier_price || 0))
                  .map((item, iIdx) => (
                    <TableRow key={iIdx}>
                      <TableCell>
                        <Badge variant="outline" className={`text-[10px] ${getSupplierBadgeClass(item.supplier_code)}`}>
                          {formatSupplierName(item.supplier_code)}
                        </Badge>
                        {iIdx === 0 && (
                          <Badge className="ml-1 text-[9px] bg-green-100 text-green-800 border-green-200">
                            En Ucuz
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm font-semibold">
                        {formatPrice(item.supplier_price, item.currency)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {item.cancellation_policy || "-"}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          size="sm"
                          variant={iIdx === 0 ? "default" : "outline"}
                          className="text-xs h-7"
                          data-testid={`compare-select-${gIdx}-${iIdx}`}
                          onClick={() => onSelect(item)}
                        >
                          Sec
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ===================== BOOKING FLOW =====================
function BookingFlow({ selectedItem, onBack, onComplete }) {
  const [step, setStep] = useState(1); // 1=travellers, 2=billing, 3=revalidate, 4=confirm, 5=result
  const [loading, setLoading] = useState(false);
  const [revalResult, setRevalResult] = useState(null);
  const [bookingResult, setBookingResult] = useState(null);
  const [showDriftDialog, setShowDriftDialog] = useState(false);
  const [showFallbackDialog, setShowFallbackDialog] = useState(false);

  const [travellers, setTravellers] = useState([{
    title: "Mr", first_name: "", last_name: "", email: "", phone: "", type: "adult", is_lead: true,
  }]);
  const [contact, setContact] = useState({ email: "", phone: "", name: "" });
  const [billing, setBilling] = useState({ company_name: "", tax_id: "", address: "", city: "" });

  const updateTraveller = (idx, field, value) => {
    setTravellers(prev => prev.map((t, i) => i === idx ? { ...t, [field]: value } : t));
  };

  const addTraveller = () => {
    setTravellers(prev => [...prev, {
      title: "Mr", first_name: "", last_name: "", email: "", phone: "", type: "adult", is_lead: false,
    }]);
  };

  const removeTraveller = (idx) => {
    if (travellers.length <= 1) return;
    setTravellers(prev => prev.filter((_, i) => i !== idx));
  };

  // Step 3: Price Revalidation
  const handleRevalidate = async () => {
    setLoading(true);
    try {
      const result = await revalidatePrice({
        supplier_code: selectedItem.supplier_code,
        supplier_item_id: selectedItem.supplier_item_id,
        original_price: selectedItem.supplier_price,
        currency: selectedItem.currency || "TRY",
        product_type: selectedItem.product_type,
      });
      setRevalResult(result);

      const driftPct = Math.abs(result.price_drift_pct || 0);

      if (!result.can_proceed) {
        // >10% drift - abort
        toast.error("Fiyat farki cok yuksek! Rezervasyon iptal edildi.");
        setStep(3);
      } else if (result.requires_approval || driftPct >= 5) {
        // 5-10% drift - show approval dialog
        setShowDriftDialog(true);
      } else if (driftPct >= 2) {
        // 2-5% drift - warning, auto proceed
        toast.warning(`Fiyat ${driftPct.toFixed(1)}% degisti. Devam ediliyor.`);
        setStep(4);
      } else {
        // <2% - silent
        setStep(4);
      }
    } catch (err) {
      toast.error("Fiyat dogrulama hatasi: " + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Step 4: Execute Booking
  const handleBook = async () => {
    setLoading(true);
    try {
      const result = await executeBooking({
        supplier_code: selectedItem.supplier_code,
        supplier_item_id: selectedItem.supplier_item_id,
        product_type: selectedItem.product_type,
        travellers,
        contact,
        billing,
        expected_price: revalResult?.current_price || selectedItem.supplier_price,
        currency: selectedItem.currency || "TRY",
      });
      setBookingResult(result);

      if (result.fallback_used) {
        setShowFallbackDialog(true);
      }

      if (result.status === "confirmed") {
        toast.success("Rezervasyon onaylandı!");
        setStep(5);
      } else if (result.status === "aborted") {
        toast.error("Rezervasyon iptal edildi: " + (result.reason || "Bilinmeyen hata"));
      } else {
        toast.error("Rezervasyon basarisiz: " + (result.error || "Tum supplier'lar basarisiz"));
        setStep(5);
      }
    } catch (err) {
      toast.error("Rezervasyon hatasi: " + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Step indicators
  const steps = [
    { num: 1, label: "Yolcular" },
    { num: 2, label: "Fatura" },
    { num: 3, label: "Fiyat Kontrol" },
    { num: 4, label: "Onay" },
    { num: 5, label: "Sonuc" },
  ];

  return (
    <div className="space-y-6" data-testid="booking-flow">
      {/* Step bar */}
      <div className="flex items-center gap-2 flex-wrap" data-testid="booking-step-bar">
        {steps.map((s, idx) => (
          <React.Fragment key={s.num}>
            <div className="flex items-center gap-1.5">
              <div className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold border transition-colors ${
                s.num === step ? "bg-primary text-primary-foreground border-primary" :
                s.num < step ? "bg-green-100 text-green-700 border-green-300" :
                "bg-muted text-muted-foreground border-border"
              }`}>
                {s.num < step ? <CheckCircle2 className="h-3.5 w-3.5" /> : s.num}
              </div>
              <span className={`text-xs font-medium ${s.num === step ? "text-foreground" : "text-muted-foreground"}`}>
                {s.label}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div className={`flex-1 h-px min-w-[16px] ${s.num < step ? "bg-green-300" : "bg-border"}`} />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Selected item summary */}
      <Card className="bg-muted/30">
        <CardContent className="py-3 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <Badge variant="outline" className={getSupplierBadgeClass(selectedItem.supplier_code)}>
              {formatSupplierName(selectedItem.supplier_code)}
            </Badge>
            <span className="font-medium text-sm">{selectedItem.name}</span>
            <Badge variant="secondary" className="text-[10px]">{selectedItem.product_type}</Badge>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono font-semibold text-lg">
              {formatPrice(selectedItem.supplier_price, selectedItem.currency)}
            </span>
            <Button variant="ghost" size="sm" onClick={onBack} data-testid="booking-back-btn">
              <ArrowLeft className="h-4 w-4 mr-1" /> Geri
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* STEP 1: Traveller details */}
      {step === 1 && (
        <Card data-testid="step-travellers">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <User className="h-4 w-4 text-primary" /> Yolcu Bilgileri
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {travellers.map((t, idx) => (
              <div key={idx} className="border rounded-lg p-4 space-y-3" data-testid={`traveller-form-${idx}`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    {t.is_lead ? "Ana Yolcu" : `Yolcu ${idx + 1}`}
                  </span>
                  {!t.is_lead && (
                    <Button variant="ghost" size="sm" className="text-xs text-red-600" onClick={() => removeTraveller(idx)}>
                      Kaldir
                    </Button>
                  )}
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <Label className="text-xs">Unvan</Label>
                    <Select value={t.title} onValueChange={(v) => updateTraveller(idx, "title", v)}>
                      <SelectTrigger className="mt-1" data-testid={`traveller-title-${idx}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Mr">Mr</SelectItem>
                        <SelectItem value="Mrs">Mrs</SelectItem>
                        <SelectItem value="Ms">Ms</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">Ad *</Label>
                    <Input
                      className="mt-1"
                      data-testid={`traveller-fname-${idx}`}
                      value={t.first_name}
                      onChange={(e) => updateTraveller(idx, "first_name", e.target.value)}
                      placeholder="Ad"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Soyad *</Label>
                    <Input
                      className="mt-1"
                      data-testid={`traveller-lname-${idx}`}
                      value={t.last_name}
                      onChange={(e) => updateTraveller(idx, "last_name", e.target.value)}
                      placeholder="Soyad"
                    />
                  </div>
                </div>
              </div>
            ))}
            <Button variant="outline" size="sm" onClick={addTraveller} data-testid="add-traveller-btn">
              + Yolcu Ekle
            </Button>

            <Separator />

            <div>
              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Mail className="h-4 w-4 text-primary" /> Iletisim Bilgileri
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <Label className="text-xs">Ad Soyad</Label>
                  <Input
                    className="mt-1"
                    data-testid="contact-name"
                    value={contact.name}
                    onChange={(e) => setContact(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Ad Soyad"
                  />
                </div>
                <div>
                  <Label className="text-xs">E-posta *</Label>
                  <Input
                    className="mt-1"
                    type="email"
                    data-testid="contact-email"
                    value={contact.email}
                    onChange={(e) => setContact(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="ornek@email.com"
                  />
                </div>
                <div>
                  <Label className="text-xs">Telefon *</Label>
                  <Input
                    className="mt-1"
                    data-testid="contact-phone"
                    value={contact.phone}
                    onChange={(e) => setContact(prev => ({ ...prev, phone: e.target.value }))}
                    placeholder="+90 5XX XXX XXXX"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <Button onClick={() => setStep(2)} data-testid="to-billing-btn">
                Devam <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* STEP 2: Billing */}
      {step === 2 && (
        <Card data-testid="step-billing">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Building2 className="h-4 w-4 text-primary" /> Fatura Bilgileri
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Firma Adi</Label>
                <Input
                  className="mt-1"
                  data-testid="billing-company"
                  value={billing.company_name}
                  onChange={(e) => setBilling(prev => ({ ...prev, company_name: e.target.value }))}
                  placeholder="Firma Adi"
                />
              </div>
              <div>
                <Label className="text-xs">Vergi No</Label>
                <Input
                  className="mt-1"
                  data-testid="billing-taxid"
                  value={billing.tax_id}
                  onChange={(e) => setBilling(prev => ({ ...prev, tax_id: e.target.value }))}
                  placeholder="Vergi No"
                />
              </div>
              <div>
                <Label className="text-xs">Adres</Label>
                <Input
                  className="mt-1"
                  data-testid="billing-address"
                  value={billing.address}
                  onChange={(e) => setBilling(prev => ({ ...prev, address: e.target.value }))}
                  placeholder="Adres"
                />
              </div>
              <div>
                <Label className="text-xs">Sehir</Label>
                <Input
                  className="mt-1"
                  data-testid="billing-city"
                  value={billing.city}
                  onChange={(e) => setBilling(prev => ({ ...prev, city: e.target.value }))}
                  placeholder="Sehir"
                />
              </div>
            </div>
            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(1)} data-testid="back-to-travellers-btn">
                <ArrowLeft className="h-4 w-4 mr-1" /> Geri
              </Button>
              <Button onClick={() => { setStep(3); handleRevalidate(); }} data-testid="to-revalidate-btn">
                Fiyat Kontrolu <ShieldCheck className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* STEP 3: Price Revalidation */}
      {step === 3 && (
        <Card data-testid="step-revalidation">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" /> Fiyat Dogrulama
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
                <span className="ml-2 text-sm text-muted-foreground">Fiyat kontrol ediliyor...</span>
              </div>
            )}
            {!loading && revalResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-[10px] text-muted-foreground">Orijinal Fiyat</p>
                    <p className="font-mono font-semibold">{formatPrice(revalResult.original_price)}</p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-[10px] text-muted-foreground">Guncel Fiyat</p>
                    <p className="font-mono font-semibold">{formatPrice(revalResult.current_price)}</p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-[10px] text-muted-foreground">Fiyat Farki</p>
                    <p className={`font-mono font-semibold ${revalResult.price_drift_pct > 0 ? "text-red-600" : revalResult.price_drift_pct < 0 ? "text-green-600" : ""}`}>
                      {revalResult.price_drift_pct > 0 ? "+" : ""}{(revalResult.price_drift_pct || 0).toFixed(2)}%
                    </p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-[10px] text-muted-foreground">Durum</p>
                    {revalResult.can_proceed ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600 mx-auto mt-1" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500 mx-auto mt-1" />
                    )}
                  </div>
                </div>
                {!revalResult.can_proceed && (
                  <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm flex items-center gap-2" data-testid="revalidation-abort">
                    <XCircle className="h-4 w-4 shrink-0" />
                    {revalResult.abort_reason || "Fiyat farki cok yuksek. Rezervasyon yapılamaz."}
                  </div>
                )}
                <div className="flex justify-between">
                  <Button variant="outline" onClick={() => setStep(2)}>
                    <ArrowLeft className="h-4 w-4 mr-1" /> Geri
                  </Button>
                  {revalResult.can_proceed && (
                    <Button onClick={() => setStep(4)} data-testid="to-confirm-btn">
                      Onayla ve Rezerve Et <CreditCard className="h-4 w-4 ml-1" />
                    </Button>
                  )}
                  {!revalResult.can_proceed && (
                    <Button variant="outline" onClick={onBack} data-testid="return-search-btn">
                      Aramaya Don
                    </Button>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* STEP 4: Confirm booking */}
      {step === 4 && (
        <Card data-testid="step-confirm">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-primary" /> Rezervasyon Onayi
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-muted/30 p-4 rounded-lg space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Urun</span>
                <span className="font-medium">{selectedItem.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Supplier</span>
                <Badge variant="outline" className={getSupplierBadgeClass(selectedItem.supplier_code)}>
                  {formatSupplierName(selectedItem.supplier_code)}
                </Badge>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Yolcu Sayisi</span>
                <span>{travellers.length} kisi</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Ana Yolcu</span>
                <span>{travellers[0]?.first_name} {travellers[0]?.last_name}</span>
              </div>
              <Separator />
              <div className="flex justify-between text-base font-semibold">
                <span>Toplam Tutar</span>
                <span className="font-mono">
                  {formatPrice(revalResult?.current_price || selectedItem.supplier_price, selectedItem.currency)}
                </span>
              </div>
            </div>

            <div className="p-3 bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-400 rounded-lg text-xs flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>
                Onayladıgınızda rezervasyon dogrudan supplier'a iletilecektir.
                Birincil supplier basarisiz olursa otomatik fallback zinciri devreye girecektir.
              </span>
            </div>

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep(3)} data-testid="back-to-reval-btn">
                <ArrowLeft className="h-4 w-4 mr-1" /> Geri
              </Button>
              <Button onClick={handleBook} disabled={loading} data-testid="confirm-booking-btn">
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Zap className="h-4 w-4 mr-2" />}
                {loading ? "Rezerve ediliyor..." : "Rezervasyonu Onayla"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* STEP 5: Result */}
      {step === 5 && bookingResult && (
        <Card data-testid="step-result">
          <CardContent className="py-8 text-center space-y-4">
            {bookingResult.status === "confirmed" ? (
              <>
                <CheckCircle2 className="h-16 w-16 text-green-600 mx-auto" />
                <h2 className="text-xl font-bold">Rezervasyon Onaylandi!</h2>
                <div className="space-y-2 text-sm">
                  <p>Rezervasyon No: <span className="font-mono font-semibold" data-testid="booking-id">{bookingResult.internal_booking_id}</span></p>
                  <p>Supplier: <Badge variant="outline" className={getSupplierBadgeClass(bookingResult.supplier_code)}>{formatSupplierName(bookingResult.supplier_code)}</Badge></p>
                  {bookingResult.confirmation_code && (
                    <p>Onay Kodu: <span className="font-mono" data-testid="confirmation-code">{bookingResult.confirmation_code}</span></p>
                  )}
                  <p>Tutar: <span className="font-mono font-semibold">{formatPrice(bookingResult.confirmed_price || bookingResult.booked_price, bookingResult.currency)}</span></p>
                  <p className="text-muted-foreground text-xs">Sure: {bookingResult.duration_ms}ms</p>
                </div>
                {bookingResult.fallback_used && (
                  <div className="p-3 bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-400 rounded-lg text-xs mx-auto max-w-md" data-testid="fallback-info">
                    <RefreshCw className="h-4 w-4 inline mr-1" />
                    Fallback kullanildi. Orijinal supplier: {formatSupplierName(bookingResult.original_supplier)}
                    {" -> "}Kullanilan: {formatSupplierName(bookingResult.supplier_code)}
                  </div>
                )}
              </>
            ) : (
              <>
                <XCircle className="h-16 w-16 text-red-500 mx-auto" />
                <h2 className="text-xl font-bold">Rezervasyon Basarisiz</h2>
                <p className="text-sm text-muted-foreground" data-testid="booking-error">
                  {bookingResult.error || bookingResult.reason || "Tum supplier'lar basarisiz oldu"}
                </p>
              </>
            )}
            <Button onClick={onBack} variant="outline" data-testid="new-search-btn" className="mt-4">
              Yeni Arama Yap
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Price Drift Approval Dialog */}
      <Dialog open={showDriftDialog} onOpenChange={setShowDriftDialog}>
        <DialogContent data-testid="price-drift-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              Fiyat Degisimi Tespit Edildi
            </DialogTitle>
            <DialogDescription>
              Arama yapıldıgından bu yana fiyat degisikligi tespit edildi.
            </DialogDescription>
          </DialogHeader>
          {revalResult && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <p className="text-xs text-muted-foreground">Orijinal</p>
                  <p className="font-mono font-semibold">{formatPrice(revalResult.original_price)}</p>
                </div>
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <p className="text-xs text-muted-foreground">Guncel</p>
                  <p className="font-mono font-semibold">{formatPrice(revalResult.current_price)}</p>
                </div>
              </div>
              <p className="text-sm text-center">
                Fark: <span className="font-semibold text-amber-600">%{Math.abs(revalResult.price_drift_pct || 0).toFixed(2)}</span>
              </p>
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => { setShowDriftDialog(false); setStep(1); }} data-testid="drift-cancel-btn">
              Iptal Et
            </Button>
            <Button onClick={() => { setShowDriftDialog(false); setStep(4); }} data-testid="drift-accept-btn">
              Yeni Fiyati Kabul Et
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Fallback Info Dialog */}
      <Dialog open={showFallbackDialog} onOpenChange={setShowFallbackDialog}>
        <DialogContent data-testid="fallback-dialog">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-amber-600" />
              Fallback Supplier Kullanildi
            </DialogTitle>
            <DialogDescription>
              Birincil supplier basarisiz oldugu icin alternatif supplier'dan rezervasyon yapildi.
            </DialogDescription>
          </DialogHeader>
          {bookingResult && (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Orijinal Supplier</span>
                <Badge variant="outline">{formatSupplierName(bookingResult.original_supplier)}</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Kullanilan Supplier</span>
                <Badge variant="outline" className={getSupplierBadgeClass(bookingResult.supplier_code)}>
                  {formatSupplierName(bookingResult.supplier_code)}
                </Badge>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setShowFallbackDialog(false)} data-testid="fallback-ok-btn">Tamam</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ===================== MAIN PAGE =====================
export default function UnifiedSearchPage() {
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState(null);
  const [searchMeta, setSearchMeta] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [viewMode, setViewMode] = useState("results"); // results | compare
  const [sortField, setSortField] = useState("supplier_price");
  const [sortDir, setSortDir] = useState("asc");
  const [filterSupplier, setFilterSupplier] = useState("all");

  const handleSearch = useCallback(async (params) => {
    setSearchLoading(true);
    setSearchResults(null);
    setSearchMeta(null);
    setSelectedItem(null);
    try {
      const data = await unifiedSearch(params);
      setSearchResults(data.items || []);
      setSearchMeta({
        request_id: data.request_id,
        product_type: data.product_type,
        total: data.total,
        suppliers_queried: data.suppliers_queried,
        suppliers_failed: data.suppliers_failed,
        search_duration_ms: data.search_duration_ms,
      });
      if (data.items?.length > 0) {
        toast.success(`${data.items.length} sonuc bulundu (${data.search_duration_ms}ms)`);
      } else {
        toast.info("Sonuc bulunamadi. Farkli parametrelerle tekrar deneyin.");
      }
    } catch (err) {
      toast.error("Arama hatasi: " + (err?.response?.data?.detail || err.message));
    } finally {
      setSearchLoading(false);
    }
  }, []);

  // Sort and filter results
  const filteredResults = useMemo(() => {
    if (!searchResults) return [];
    let items = [...searchResults];
    if (filterSupplier !== "all") {
      items = items.filter(i => i.supplier_code === filterSupplier);
    }
    items.sort((a, b) => {
      const aVal = a[sortField] ?? 0;
      const bVal = b[sortField] ?? 0;
      if (typeof aVal === "string") return sortDir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      return sortDir === "asc" ? aVal - bVal : bVal - aVal;
    });
    return items;
  }, [searchResults, filterSupplier, sortField, sortDir]);

  const availableSuppliers = useMemo(() => {
    if (!searchResults) return [];
    return [...new Set(searchResults.map(i => i.supplier_code))];
  }, [searchResults]);

  // If an item is selected, show booking flow
  if (selectedItem) {
    return (
      <div className="space-y-6" data-testid="unified-search-page">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Unified Booking</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Coklu supplier uzerinden guvenli rezervasyon
          </p>
        </div>
        <BookingFlow
          selectedItem={selectedItem}
          onBack={() => setSelectedItem(null)}
          onComplete={() => { setSelectedItem(null); setSearchResults(null); }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="unified-search-page">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Coklu Supplier Arama</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Tum tedarikçilerden tek seferde arama yapın, karsılastırın ve rezerve edin
        </p>
      </div>

      <SearchForm onSearch={handleSearch} loading={searchLoading} />

      {/* Results section */}
      {searchResults && searchResults.length > 0 && (
        <div className="space-y-4">
          {/* Toolbar */}
          <div className="flex items-center gap-3 flex-wrap">
            <Tabs value={viewMode} onValueChange={setViewMode}>
              <TabsList>
                <TabsTrigger value="results" data-testid="view-results-tab">
                  Tum Sonuclar
                </TabsTrigger>
                <TabsTrigger value="compare" data-testid="view-compare-tab">
                  Karsılastır
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <Select value={filterSupplier} onValueChange={setFilterSupplier}>
              <SelectTrigger className="w-[180px]" data-testid="filter-supplier">
                <Filter className="h-3 w-3 mr-1" />
                <SelectValue placeholder="Supplier filtrele" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tum Supplier'lar</SelectItem>
                {availableSuppliers.map(s => (
                  <SelectItem key={s} value={s}>{formatSupplierName(s)}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <span className="text-xs text-muted-foreground ml-auto">
              {filteredResults.length} / {searchResults.length} sonuc
            </span>
          </div>

          {viewMode === "results" ? (
            <SearchResultsTable
              items={filteredResults}
              searchMeta={searchMeta}
              onSelect={setSelectedItem}
              sortField={sortField}
              sortDir={sortDir}
              onSort={(field, dir) => { setSortField(field); setSortDir(dir); }}
            />
          ) : (
            <PriceComparisonPanel items={filteredResults} onSelect={setSelectedItem} />
          )}
        </div>
      )}

      {searchResults && searchResults.length === 0 && !searchLoading && (
        <Card className="border-dashed" data-testid="no-results-card">
          <CardContent className="py-12 text-center">
            <Search className="h-10 w-10 mx-auto mb-3 text-muted-foreground opacity-40" />
            <p className="text-muted-foreground text-sm">
              Sonuc bulunamadı. Farkli parametrelerle tekrar deneyin.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
