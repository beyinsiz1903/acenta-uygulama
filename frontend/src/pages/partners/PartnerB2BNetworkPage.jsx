import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Users, Loader2, Link2 } from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "../../components/ui/table";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Textarea } from "../../components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../../components/ui/dialog";
import { useToast } from "../../hooks/use-toast";
import MatchRequestDetailDrawer from "./components/MatchRequestDetailDrawer";
import {
  fetchMyListings,
  createListing,
  updateListing,
  fetchAvailableListings,
  createMatchRequest,
  fetchMyMatchRequests,
  fetchIncomingMatchRequests,
  approveMatchRequest,
  rejectMatchRequest,
  completeMatchRequest,
} from "../../lib/b2bExchange";

function formatTry(value) {
  if (value == null || value === "") return "-";
  try {
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: "TRY",
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
      toast?.({ description: "Kopyalandı" });
      return;
    }
    throw new Error("clipboard_not_available");
  } catch {
    toast?.({ variant: "destructive", description: "Kopyalanamadı" });
  }
}

function statusBadge(status) {
  const s = (status || "").toLowerCase();
  if (s === "pending") return <Badge variant="outline">Beklemede</Badge>;
  if (s === "approved") {
    return (
      <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
        Onaylandı
      </Badge>
    );
  }
  if (s === "rejected") return <Badge variant="destructive">Reddedildi</Badge>;
  if (s === "completed") {
    return (
      <Badge className="bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20">Tamamlandı</Badge>
    );
  }
  return <Badge variant="outline">{status || "-"}</Badge>;
}

function mapCommonErrorMessage(error) {
  const code = error?.raw?.response?.data?.error?.code;
  if (code === "tenant_header_missing") {
    return "Tenant seçimi gerekli. Lütfen geçerli bir tenant ile tekrar deneyin.";
  }
  if (code === "invalid_token" || code === "unauthorized") {
    return "Bu işlemi yapmaya yetkiniz yok. Oturum süreniz dolmuş olabilir.";
  }
  return error?.message || "Beklenmeyen bir hata oluştu.";
}

function mapCreateMatchError(error) {
  const code = error?.raw?.response?.data?.error?.code;
  if (code === "listing_not_found") {
    return "Listing bulunamadı.";
  }
  if (code === "listing_not_active") {
    return "Bu listing artık aktif değil.";
  }
  if (code === "cannot_request_own_listing") {
    return "Kendi listing'iniz için talep oluşturamazsınız.";
  }
  if (code === "not_active_partner") {
    return "Bu listing için aktif bir partner ilişkiniz bulunmuyor.";
  }
  return mapCommonErrorMessage(error);
}

function mapStatusChangeError(error) {
  const code = error?.raw?.response?.data?.error?.code;
  if (code === "invalid_status_transition") {
    return "Bu aşamada bu işlemi yapamazsınız.";
  }
  if (code === "match_request_not_found") {
    return "Talep bulunamadı (yenilemeyi deneyin).";
  }
  return mapCommonErrorMessage(error);
}

function mapListingSaveError(error) {
  const code = error?.raw?.response?.data?.error?.code;
  if (code === "tenant_header_missing") {
    return "Tenant seçimi gerekli. Lütfen geçerli bir tenant ile tekrar deneyin.";
  }
  return error?.message || "Listing kaydedilirken bir hata oluştu.";
}

export default function PartnerB2BNetworkPage() {
  const { toast } = useToast();

  const [mode, setMode] = useState("seller"); // "seller" | "provider"

  // Seller state
  const [availableListings, setAvailableListings] = useState([]);
  const [availableLoading, setAvailableLoading] = useState(false);
  const [availableError, setAvailableError] = useState("");

  const [myRequests, setMyRequests] = useState([]);
  const [myRequestsLoading, setMyRequestsLoading] = useState(false);
  const [myRequestsError, setMyRequestsError] = useState("");

  const [requestModalOpen, setRequestModalOpen] = useState(false);
  const [selectedListing, setSelectedListing] = useState(null);
  const [requestedPrice, setRequestedPrice] = useState("");
  const [requestSubmitting, setRequestSubmitting] = useState(false);
  const [requestError, setRequestError] = useState("");

  // Provider state
  const [myListings, setMyListings] = useState([]);
  const [myListingsLoading, setMyListingsLoading] = useState(false);
  const [myListingsError, setMyListingsError] = useState("");

  const [incomingRequests, setIncomingRequests] = useState([]);
  const [incomingLoading, setIncomingLoading] = useState(false);
  const [incomingError, setIncomingError] = useState("");

  const [listingModalOpen, setListingModalOpen] = useState(false);
  const [editingListing, setEditingListing] = useState(null);
  const [listingForm, setListingForm] = useState({
    title: "",
    base_price: "",
    provider_commission_rate: "",
    description: "",
    category: "",
    status: "active",
  });
  const [listingSubmitting, setListingSubmitting] = useState(false);
  const [listingModalError, setListingModalError] = useState("");

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailRequest, setDetailRequest] = useState(null);
  const [detailListing, setDetailListing] = useState(null);
  const [sellerStatusFilter, setSellerStatusFilter] = useState("all");
  const [providerStatusFilter, setProviderStatusFilter] = useState("all");


  const [busyMatchId, setBusyMatchId] = useState(null);
  const [busyMatchAction, setBusyMatchAction] = useState(null);

  // Derived maps
  const listingTitleById = useMemo(() => {
    const map = {};
    (myListings || []).forEach((l) => {
      if (l?.id) map[l.id] = l.title || l.id;
    });
    (availableListings || []).forEach((l) => {
      if (l?.id && !map[l.id]) map[l.id] = l.title || l.id;
    });
    return map;
  }, [myListings, availableListings]);

  const sortedAvailableListings = useMemo(() => {
    const items = Array.isArray(availableListings) ? [...availableListings] : [];
    return items.sort(
      (a, b) => new Date(b.created_at || b.updated_at || 0) - new Date(a.created_at || a.updated_at || 0),
    );
  }, [availableListings]);

  const sortedMyListings = useMemo(() => {
    const items = Array.isArray(myListings) ? [...myListings] : [];
    return items.sort(
      (a, b) => new Date(b.created_at || b.updated_at || 0) - new Date(a.created_at || a.updated_at || 0),
    );
  }, [myListings]);

  const sortedMyRequests = useMemo(() => {
    const items = Array.isArray(myRequests) ? [...myRequests] : [];
    items.sort(
      (a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0),
    );
    if (sellerStatusFilter === "all") return items;
    return items.filter((r) => (r.status || "").toLowerCase() === sellerStatusFilter);
  }, [myRequests, sellerStatusFilter]);

  const sortedIncomingRequests = useMemo(() => {
    const items = Array.isArray(incomingRequests) ? [...incomingRequests] : [];
    items.sort(
      (a, b) => new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0),
    );
    if (providerStatusFilter === "all") return items;
    return items.filter((r) => (r.status || "").toLowerCase() === providerStatusFilter);
  }, [incomingRequests, providerStatusFilter]);

  const loadAvailableListings = useCallback(async () => {
    setAvailableLoading(true);
    setAvailableError("");
    try {
      const items = await fetchAvailableListings();
      setAvailableListings(Array.isArray(items) ? items : []);
    } catch (err) {
      setAvailableError(mapCommonErrorMessage(err));
      setAvailableListings([]);
    } finally {
      setAvailableLoading(false);
    }
  }, []);

  const loadMyRequests = useCallback(async () => {
    setMyRequestsLoading(true);
    setMyRequestsError("");
    try {
      const items = await fetchMyMatchRequests();
      setMyRequests(Array.isArray(items) ? items : []);
    } catch (err) {
      setMyRequestsError(mapCommonErrorMessage(err));
      setMyRequests([]);
    } finally {
      setMyRequestsLoading(false);
    }
  }, []);

  const loadMyListings = useCallback(async () => {
    setMyListingsLoading(true);
    setMyListingsError("");
    try {
      const items = await fetchMyListings();
      setMyListings(Array.isArray(items) ? items : []);
    } catch (err) {
      setMyListingsError(mapCommonErrorMessage(err));
      setMyListings([]);
    } finally {
      setMyListingsLoading(false);
    }
  }, []);

  const loadIncomingRequests = useCallback(async () => {
    setIncomingLoading(true);
    setIncomingError("");
    try {
      const items = await fetchIncomingMatchRequests();
      setIncomingRequests(Array.isArray(items) ? items : []);
    } catch (err) {
      setIncomingError(mapCommonErrorMessage(err));
      setIncomingRequests([]);
    } finally {
      setIncomingLoading(false);
    }
  }, []);

  // Initial load per mode
  useEffect(() => {
    if (mode === "seller") {
      void loadAvailableListings();
      void loadMyRequests();
    } else {
      void loadMyListings();
      void loadIncomingRequests();
    }
  }, [mode, loadAvailableListings, loadMyRequests, loadMyListings, loadIncomingRequests]);

  const openRequestModal = (listing) => {
    setSelectedListing(listing);
    setRequestedPrice(String(listing?.base_price ?? ""));
    setRequestError("");
    setRequestModalOpen(true);
  };

  const closeRequestModal = () => {
    if (requestSubmitting) return;
    setRequestModalOpen(false);
    setSelectedListing(null);
    setRequestedPrice("");
    setRequestError("");
  };

  const handleSubmitRequest = async (e) => {
    e.preventDefault();
    if (!selectedListing) return;
    const priceNumber = Number(requestedPrice);
    if (!Number.isFinite(priceNumber) || priceNumber <= 0) {
      setRequestError("Talep fiyatı pozitif bir sayı olmalıdır.");
      return;
    }
    setRequestSubmitting(true);
    setRequestError("");
    try {
      await createMatchRequest({
        listing_id: selectedListing.id,
        requested_price: priceNumber,
      });
      toast({ description: "Talep gönderildi." });
      setRequestModalOpen(false);
      setSelectedListing(null);
      setRequestedPrice("");
      // Mutasyon sonrası refresh standardı
      void loadAvailableListings();
      void loadMyRequests();
    } catch (err) {
      setRequestError(mapCreateMatchError(err));
    } finally {
      setRequestSubmitting(false);
    }
  };

  const startNewListing = () => {
    setEditingListing(null);
    setListingForm({
      title: "",
      base_price: "",
      provider_commission_rate: "",
      description: "",
      category: "",
      status: "active",
    });
    setListingModalError("");
    setListingModalOpen(true);
  };

  const startEditListing = (listing) => {
    setEditingListing(listing);
    setListingForm({
      title: listing.title || "",
      base_price: String(listing.base_price ?? ""),
      provider_commission_rate: String(listing.provider_commission_rate ?? ""),
      description: listing.description || "",
      category: listing.category || "",
      status: listing.status || "active",
    });
    setListingModalError("");
    setListingModalOpen(true);
  };

  const closeListingModal = () => {
    if (listingSubmitting) return;
    setListingModalOpen(false);
    setEditingListing(null);
  };

  const handleSaveListing = async (e) => {
    e.preventDefault();
    const basePriceNumber = Number(listingForm.base_price);
    const rateNumber = Number(listingForm.provider_commission_rate);
    if (!Number.isFinite(basePriceNumber) || basePriceNumber <= 0) {
      setListingModalError("Taban fiyat pozitif bir sayı olmalıdır.");
      return;
    }
    if (!Number.isFinite(rateNumber) || rateNumber < 0 || rateNumber > 100) {
      setListingModalError("Komisyon oranı 0 ile 100 arasında olmalıdır.");
      return;
    }

    const payload = {
      title: listingForm.title,
      base_price: basePriceNumber,
      provider_commission_rate: rateNumber,
      description: listingForm.description || undefined,
      category: listingForm.category || undefined,
      status: listingForm.status || "active",
    };

    setListingSubmitting(true);
    setListingModalError("");
    try {
      if (editingListing?.id) {
        await updateListing(editingListing.id, payload);
      } else {
        await createListing(payload);
      }
      toast({ description: "Listing kaydedildi." });
      setListingModalOpen(false);
      setEditingListing(null);
      // Mutasyon sonrası refresh standardı
      void loadMyListings();
    } catch (err) {
      setListingModalError(mapListingSaveError(err));
    } finally {
      setListingSubmitting(false);
    }
  };

  const handleMatchAction = async (match, action) => {
    setBusyMatchId(match.id);
    setBusyMatchAction(action);
    try {
      if (action === "approve") {
        await approveMatchRequest(match.id);
      } else if (action === "reject") {
        await rejectMatchRequest(match.id);
      } else if (action === "complete") {
        await completeMatchRequest(match.id);
      }
      toast({ description: "Talep durumu güncellendi." });
      // Mutasyon sonrası refresh standardı
      void loadIncomingRequests();
    } catch (err) {
      toast({ variant: "destructive", description: mapStatusChangeError(err) });
    } finally {
      setBusyMatchId(null);
      setBusyMatchAction(null);
    }
  };

  const sellerHasListings = (availableListings || []).length > 0;
  const sellerHasRequests = (myRequests || []).length > 0;
  const providerHasListings = (myListings || []).length > 0;
  const providerHasIncoming = (incomingRequests || []).length > 0;

  const openDetailForRequest = (req, mode) => {
    setDetailRequest(req);
    if (mode === "seller") {
      const fromAvailable = (availableListings || []).find((l) => l.id === req.listing_id);
      setDetailListing(fromAvailable || null);
    } else {
      const fromMy = (myListings || []).find((l) => l.id === req.listing_id);
      setDetailListing(fromMy || null);
    }
    setDetailOpen(true);
  };

  const closeDetail = () => {
    setDetailOpen(false);
    setDetailRequest(null);
    setDetailListing(null);
  };

  const computeBreakdown = () => {
    const price = Number(requestedPrice);
    if (!Number.isFinite(price) || price <= 0 || !selectedListing) {
      return { platformFee: 0, providerCommission: 0, sellerRemain: 0 };
    }
    const platformFee = price * 0.01;
    const providerCommission = price * (Number(selectedListing.provider_commission_rate || 0) / 100);
    const sellerRemain = price - platformFee - providerCommission;
    return { platformFee, providerCommission, sellerRemain };
  };

  const breakdown = computeBreakdown();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Users className="h-5 w-5" />
        <div>
          <h1 className="text-base font-semibold">B2B Ağ</h1>
          <p className="text-xs text-muted-foreground">
            Aktif partner ilişkileriniz üzerinden listing yayınlayın veya diğer sağlayıcıların listinglerine talep
            gönderin.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-xs">
            <Link2 className="h-4 w-4" />
            <CardTitle className="text-sm font-medium">Mod</CardTitle>
          </div>
          <div className="inline-flex rounded-md border bg-background p-0.5 text-[11px]">
            <button
              type="button"
              className={`px-3 py-1 rounded-sm ${
                mode === "seller" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
              }`}
              onClick={() => setMode("seller")}
            >
              Satıcı
            </button>
            <button
              type="button"
              className={`px-3 py-1 rounded-sm ${
                mode === "provider" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
              }`}
              onClick={() => setMode("provider")}
            >
              Sağlayıcı
            </button>
          </div>
        </CardHeader>
      </Card>

      {mode === "seller" ? (
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-sm font-medium">Müsait Listingler</CardTitle>
                <p className="text-[11px] text-muted-foreground">
                  Aktif partner ilişkileriniz olan sağlayıcıların yayınladığı listingler.
                </p>
              </div>
              {availableLoading && (
                <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>Yükleniyor…</span>
                </div>
              )}
            </CardHeader>
            <CardContent className="text-xs">
              {availableError && (
                <p className="mb-2 text-[11px] text-destructive">{availableError}</p>
              )}
              {!availableLoading && !sellerHasListings && !availableError && (
                <p className="text-[11px] text-muted-foreground">
                  Henüz müsait tur yok. Aktif partner ilişkiniz yoksa burada liste göremezsiniz.
                </p>
              )}
              {sellerHasListings && (
                <>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[11px] text-muted-foreground">Sadece duruma göre filtreleyin.</p>
                    <select
                      className="h-7 rounded-md border bg-background px-2 text-[11px]"
                      value={sellerStatusFilter}
                      onChange={(e) => setSellerStatusFilter(e.target.value)}
                    >
                      <option value="all">Tüm durumlar</option>
                      <option value="pending">Beklemede</option>
                      <option value="approved">Onaylandı</option>
                      <option value="rejected">Reddedildi</option>
                      <option value="completed">Tamamlandı</option>
                    </select>
                  </div>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-xs">Listing ID</TableHead>
                          <TableHead className="text-xs">Başlık</TableHead>
                          <TableHead className="text-xs">Kategori</TableHead>
                          <TableHead className="text-xs">Taban Fiyat</TableHead>
                          <TableHead className="text-xs">Sağlayıcı Komisyonu</TableHead>
                          <TableHead className="text-xs">Durum</TableHead>
                          <TableHead className="text-xs text-right">Aksiyon</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sortedAvailableListings.map((l) => (
                          <TableRow key={l.id} className="hover:bg-muted/40">
                            <TableCell
                              className="text-xs font-mono cursor-pointer hover:underline"
                              title="ID'yi kopyala"
                              onClick={() => copyToClipboard(l.id, toast)}
                            >
                              {shortenId(l.id)}
                            </TableCell>
                            <TableCell className="text-xs">{l.title || "-"}</TableCell>
                            <TableCell className="text-xs">{l.category || "-"}</TableCell>
                            <TableCell className="text-xs">{formatTry(l.base_price)}</TableCell>
                            <TableCell className="text-xs">{`${l.provider_commission_rate ?? 0}%`}</TableCell>
                            <TableCell className="text-xs">
                              <Badge variant={l.status === "active" ? "outline" : "secondary"}>{l.status}</Badge>
                            </TableCell>
                            <TableCell className="text-xs text-right">
                              <Button
                                type="button"
                                size="xs"
                                className="h-7 px-2 text-[11px]"
                                onClick={() => openRequestModal(l)}
                              >
                                Talep Gönder
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-sm font-medium">Taleplerim</CardTitle>
                <p className="text-[11px] text-muted-foreground">
                  Diğer sağlayıcıların listingleri için gönderdiğiniz talepler.
                </p>
              </div>
              {myRequestsLoading && (
                <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>Yükleniyor…</span>
                </div>
              )}
            </CardHeader>
            <CardContent className="text-xs">
              {myRequestsError && (
                <p className="mb-2 text-[11px] text-destructive">{myRequestsError}</p>
              )}
              {!myRequestsLoading && !sellerHasRequests && !myRequestsError && (
                <p className="text-[11px] text-muted-foreground">Henüz talep oluşturmadınız.</p>
              )}
              {sellerHasRequests && (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">Talep ID</TableHead>
                        <TableHead className="text-xs">Listing ID</TableHead>
                        <TableHead className="text-xs">Sağlayıcı Tenant</TableHead>
                        <TableHead className="text-xs">Talep Fiyatı</TableHead>
                        <TableHead className="text-xs">Platform Ücreti</TableHead>
                        <TableHead className="text-xs">Durum</TableHead>
                        <TableHead className="text-xs text-right">Aksiyon</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sortedMyRequests.map((r) => (
                        <TableRow key={r.id} className="hover:bg-muted/40">
                          <TableCell
                            className="text-xs font-mono cursor-pointer hover:underline"
                            title="ID'yi kopyala"
                            onClick={() => copyToClipboard(r.id, toast)}
                          >
                            {shortenId(r.id)}
                          </TableCell>
                          <TableCell className="text-xs font-mono">{shortenId(r.listing_id)}</TableCell>
                          <TableCell className="text-xs font-mono">{r.provider_tenant_id}</TableCell>
                          <TableCell className="text-xs">{formatTry(r.requested_price)}</TableCell>
                          <TableCell className="text-xs">
                            {r.platform_fee_amount ? formatTry(r.platform_fee_amount) : "-"}
                          </TableCell>
                          <TableCell className="text-xs">{statusBadge(r.status)}</TableCell>
                          <TableCell className="text-xs text-right">
                            <Button
                              type="button"
                              size="xs"
                              variant="outline"
                              className="h-7 px-2 text-[11px]"
                              onClick={() => openDetailForRequest(r, "seller")}
                            >
                              Detay
                            </Button>
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
      ) : (
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-sm font-medium">Listinglerim</CardTitle>
                <p className="text-[11px] text-muted-foreground">
                  B2B ağınızda diğer acentelere açtığınız listingler.
                </p>
              </div>
              <div className="flex items-center gap-2">
                {myListingsLoading && (
                  <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span>Yükleniyor…</span>
                  </div>
                )}
                <Button type="button" size="xs" className="h-7 px-2 text-[11px]" onClick={startNewListing}>
                  Yeni Listing
                </Button>
              </div>
            </CardHeader>
            <CardContent className="text-xs">
              {myListingsError && (
                <p className="mb-2 text-[11px] text-destructive">{myListingsError}</p>
              )}
              {!myListingsLoading && !providerHasListings && !myListingsError && (
                <p className="text-[11px] text-muted-foreground">
                  Henüz tur listelemediniz. &quot;Yeni Listing&quot; ile başlayın.
                </p>
              )}
              {providerHasListings && (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">Listing ID</TableHead>
                        <TableHead className="text-xs">Başlık</TableHead>
                        <TableHead className="text-xs">Kategori</TableHead>
                        <TableHead className="text-xs">Taban Fiyat</TableHead>
                        <TableHead className="text-xs">Komisyon Oranı</TableHead>
                        <TableHead className="text-xs">Durum</TableHead>
                        <TableHead className="text-xs text-right">Aksiyon</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sortedMyListings.map((l) => (
                        <TableRow key={l.id} className="hover:bg-muted/40">
                          <TableCell
                            className="text-xs font-mono cursor-pointer hover:underline"
                            title="ID'yi kopyala"
                            onClick={() => copyToClipboard(l.id, toast)}
                          >
                            {shortenId(l.id)}
                          </TableCell>
                          <TableCell className="text-xs">{l.title || "-"}</TableCell>
                          <TableCell className="text-xs">{l.category || "-"}</TableCell>
                          <TableCell className="text-xs">{formatTry(l.base_price)}</TableCell>
                          <TableCell className="text-xs">{`${l.provider_commission_rate ?? 0}%`}</TableCell>
                          <TableCell className="text-xs">
                            <Badge variant={l.status === "active" ? "outline" : "secondary"}>{l.status}</Badge>
                          </TableCell>
                          <TableCell className="text-xs text-right">
                            <Button
                              type="button"
                              size="xs"
                              className="h-7 px-2 text-[11px]"
                              onClick={() => startEditListing(l)}
                            >
                              Düzenle
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-sm font-medium">Gelen Talepler</CardTitle>
                <p className="text-[11px] text-muted-foreground">
                  Diğer acentelerin listinglerinize gönderdiği talepler.
                </p>
              </div>
              {incomingLoading && (
                <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>Yükleniyor…</span>
                </div>
              )}
            </CardHeader>
            <CardContent className="text-xs">
              {incomingError && (
                <p className="mb-2 text-[11px] text-destructive">{incomingError}</p>
              )}
              {!incomingLoading && !providerHasIncoming && !incomingError && (
                <p className="text-[11px] text-muted-foreground">Henüz gelen talep yok.</p>
              )}
              {providerHasIncoming && (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-xs">Talep ID</TableHead>
                        <TableHead className="text-xs">Listing</TableHead>
                        <TableHead className="text-xs">Satıcı Tenant</TableHead>
                        <TableHead className="text-xs">Talep Fiyatı</TableHead>
                        <TableHead className="text-xs">Platform Ücreti</TableHead>
                        <TableHead className="text-xs">Durum</TableHead>
                        <TableHead className="text-xs text-right">Aksiyon</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sortedIncomingRequests.map((r) => {
                        const canApproveOrReject = (r.status || "").toLowerCase() === "pending";
                        const canComplete = (r.status || "").toLowerCase() === "approved";
                        const isBusy = busyMatchId === r.id;
                        return (
                          <TableRow key={r.id} className="hover:bg-muted/40">
                            <TableCell
                              className="text-xs font-mono cursor-pointer hover:underline"
                              title="ID'yi kopyala"
                              onClick={() => copyToClipboard(r.id, toast)}
                            >
                              {shortenId(r.id)}
                            </TableCell>
                            <TableCell className="text-xs">
                              <span className="font-mono">{shortenId(r.listing_id)}</span>
                              {listingTitleById[r.listing_id] && (
                                <span className="ml-1 text-[11px] text-muted-foreground truncate inline-block max-w-[140px]">
                                  {listingTitleById[r.listing_id]}
                                </span>
                              )}
                            </TableCell>
                            <TableCell className="text-xs font-mono">{r.seller_tenant_id}</TableCell>
                            <TableCell className="text-xs">{formatTry(r.requested_price)}</TableCell>
                            <TableCell className="text-xs">
                              {r.platform_fee_amount ? formatTry(r.platform_fee_amount) : "-"}
                            </TableCell>
                            <TableCell className="text-xs">{statusBadge(r.status)}</TableCell>
                            <TableCell className="text-xs text-right space-x-1">
                              {canApproveOrReject && (
                                <>
                                  <Button
                                    type="button"
                                    size="xs"
                                    className="h-7 px-2 text-[11px]"
                                    disabled={isBusy}
                                    onClick={() => handleMatchAction(r, "approve")}
                                  >
                                    {isBusy && busyMatchAction === "approve" && (
                                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                    )}
                                    Onayla
                                  </Button>
                                  <Button
                                    type="button"
                                    size="xs"
                                    variant="outline"
                                    className="h-7 px-2 text-[11px]"
                                    disabled={isBusy}
                                    onClick={() => handleMatchAction(r, "reject")}
                                  >
                                    {isBusy && busyMatchAction === "reject" && (
                                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                    )}
                                    Reddet
                                  </Button>
                                </>
                              )}
                              {canComplete && (
                                <Button
                                  type="button"
                                  size="xs"
                                  variant="outline"
                                  className="h-7 px-2 text-[11px]"
                                  disabled={isBusy}
                                  onClick={() => handleMatchAction(r, "complete")}
                                >
                                  {isBusy && busyMatchAction === "complete" && (
                                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                  )}
                                  Tamamla
                                </Button>
                              )}
                              {!canApproveOrReject && !canComplete && (
                                <span className="text-[11px] text-muted-foreground">İşlem yok</span>
                              )}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <Dialog open={requestModalOpen} onOpenChange={(open) => !requestSubmitting && setRequestModalOpen(open)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Talep gönder</DialogTitle>
            <DialogDescription className="text-xs">
              Seçili listing için talep fiyatı belirleyin. Aşağıdaki kırılım bilgilendirme amaçlıdır (tahmini).
            </DialogDescription>
          </DialogHeader>

          {selectedListing && (
            <form onSubmit={handleSubmitRequest} className="space-y-3 text-xs">
              <div className="space-y-0.5">
                <div className="font-medium truncate">{selectedListing.title || "Listing"}</div>
                <div className="text-[11px] text-muted-foreground">
                  ID: <span className="font-mono">{selectedListing.id}</span>
                </div>
                <div className="text-[11px] text-muted-foreground">
                  Taban fiyat: <span className="font-mono">{formatTry(selectedListing.base_price)}</span>
                </div>
                <div className="text-[11px] text-muted-foreground">
                  Sağlayıcı komisyonu: {selectedListing.provider_commission_rate}%
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-medium" htmlFor="requested-price">
                  Talep fiyatı (TRY)
                </label>
                <Input
                  id="requested-price"
                  type="number"
                  min="0"
                  step="0.01"
                  value={requestedPrice}
                  onChange={(e) => setRequestedPrice(e.target.value)}
                  className="h-8 text-xs"
                />
              </div>

              <div className="rounded-md border bg-muted/40 px-3 py-2 space-y-1">
                <div className="text-[11px] font-medium">Fiyat kırılımı (tahmini)</div>
                <div className="flex items-center justify-between text-[11px]">
                  <span>Platform ücreti (1%)</span>
                  <span className="font-mono">{formatTry(breakdown.platformFee)}</span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span>Sağlayıcı komisyonu ({selectedListing.provider_commission_rate}%)</span>
                  <span className="font-mono">{formatTry(breakdown.providerCommission)}</span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span>Size kalan (tahmini)</span>
                  <span className="font-mono">{formatTry(breakdown.sellerRemain)}</span>
                </div>
              </div>

              {requestError && (
                <p className="text-[11px] text-destructive">{requestError}</p>
              )}

              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={requestSubmitting}
                  onClick={closeRequestModal}
                >
                  Vazgeç
                </Button>
                <Button type="submit" size="sm" disabled={requestSubmitting}>
                  {requestSubmitting && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                  Talep Gönder
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={listingModalOpen} onOpenChange={(open) => !listingSubmitting && setListingModalOpen(open)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingListing ? "Listing düzenle" : "Yeni listing"}</DialogTitle>
            <DialogDescription className="text-xs">
              B2B ağınızda diğer acentelerin göreceği yeni bir listing oluşturun veya mevcut bir listingi güncelleyin.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSaveListing} className="space-y-3 text-xs">
            <div className="space-y-1">
              <label className="text-[11px] font-medium" htmlFor="listing-title">
                Başlık
              </label>
              <Input
                id="listing-title"
                value={listingForm.title}
                onChange={(e) => setListingForm((f) => ({ ...f, title: e.target.value }))}
                className="h-8 text-xs"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-medium" htmlFor="listing-category">
                Kategori (opsiyonel)
              </label>
              <Input
                id="listing-category"
                value={listingForm.category}
                onChange={(e) => setListingForm((f) => ({ ...f, category: e.target.value }))}
                className="h-8 text-xs"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-[11px] font-medium" htmlFor="listing-base-price">
                  Taban fiyat (TRY)
                </label>
                <Input
                  id="listing-base-price"
                  type="number"
                  min="0"
                  step="0.01"
                  value={listingForm.base_price}
                  onChange={(e) => setListingForm((f) => ({ ...f, base_price: e.target.value }))}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] font-medium" htmlFor="listing-commission">
                  Sağlayıcı komisyonu (%)
                </label>
                <Input
                  id="listing-commission"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={listingForm.provider_commission_rate}
                  onChange={(e) => setListingForm((f) => ({ ...f, provider_commission_rate: e.target.value }))}
                  className="h-8 text-xs"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-medium" htmlFor="listing-description">
                Açıklama (opsiyonel)
              </label>
              <Textarea
                id="listing-description"
                value={listingForm.description}
                onChange={(e) => setListingForm((f) => ({ ...f, description: e.target.value }))}
                className="h-20 text-xs"
              />
            </div>

            <div className="space-y-1">
              <span className="text-[11px] font-medium">Durum</span>
              <div className="inline-flex rounded-md border bg-background p-0.5 text-[11px]">
                <button
                  type="button"
                  className={`px-3 py-1 rounded-sm ${
                    listingForm.status === "active"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground"
                  }`}
                  onClick={() => setListingForm((f) => ({ ...f, status: "active" }))}
                >
                  Aktif
                </button>
                <button
                  type="button"

      <MatchRequestDetailDrawer
        open={detailOpen}
        onOpenChange={(open) => {
          if (!open) closeDetail();
          else setDetailOpen(true);
        }}
        request={detailRequest}
        listing={detailListing}
        onCopyId={(value) => copyToClipboard(value, toast)}
        formatPrice={formatTry}
      />

                  className={`px-3 py-1 rounded-sm ${
                    listingForm.status === "inactive"
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground"
                  }`}
                  onClick={() => setListingForm((f) => ({ ...f, status: "inactive" }))}
                >
                  Pasif
                </button>
              </div>
            </div>

            {listingModalError && (
              <p className="text-[11px] text-destructive">{listingModalError}</p>
            )}

            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={listingSubmitting}
                onClick={closeListingModal}
              >
                Vazgeç
              </Button>
              <Button type="submit" size="sm" disabled={listingSubmitting}>
                {listingSubmitting && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                Kaydet
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <MatchRequestDetailDrawer
        open={detailOpen}
        onClose={closeDetail}
        request={detailRequest}
        listing={detailListing}
      />
    </div>
  );
}
