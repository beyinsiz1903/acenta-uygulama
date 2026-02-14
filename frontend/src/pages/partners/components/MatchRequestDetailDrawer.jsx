import React, { useMemo, useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "../../../components/ui/sheet";
import { Badge } from "../../../components/ui/badge";
import { Button } from "../../../components/ui/button";
import { fetchB2BEvents } from "../../../lib/b2bEvents";

function statusLabel(status) {
  const s = (status || "").toLowerCase();
  if (s === "pending") return "Beklemede";
  if (s === "approved") return "Onaylandı";
  if (s === "rejected") return "Reddedildi";
  if (s === "completed") return "Tamamlandı";
  return status || "-";
}

function statusBadgeNode(status) {
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

const EVENT_TYPE_LABELS = {
  "listing.created": "Listing oluşturuldu",
  "listing.updated": "Listing güncellendi",
  "match_request.created": "Talep oluşturuldu",
  "match_request.status_changed": "Durum değişti",
};

function ActivityTimeline({ entityId }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!entityId) return;
    setLoading(true);
    setError(false);
    fetchB2BEvents({ entity_id: entityId, limit: 50 })
      .then((data) => setEvents(data.items || []))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [entityId]);

  if (!entityId) return null;

  return (
    <div className="rounded-lg border bg-muted/40 p-3 space-y-2" data-testid="activity-timeline">
      <span className="font-medium text-xs">Aktivite</span>
      {loading ? (
        <p className="text-xs text-muted-foreground">Yükleniyor...</p>
      ) : error ? (
        <p className="text-xs text-destructive">Aktivite yüklenemedi.</p>
      ) : events.length === 0 ? (
        <p className="text-xs text-muted-foreground">Henüz aktivite yok.</p>
      ) : (
        <div className="space-y-1">
          {events.map((evt) => (
            <div key={evt.id} className="flex items-start gap-2 rounded-md border bg-background/80 px-2 py-1.5">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium">
                  {EVENT_TYPE_LABELS[evt.event_type] || evt.event_type}
                </p>
                {evt.payload?.from && evt.payload?.to && (
                  <p className="text-2xs text-muted-foreground">
                    {statusLabel(evt.payload.from)} &rarr; {statusLabel(evt.payload.to)}
                    {evt.payload.requested_price ? ` | ${evt.payload.requested_price} TRY` : ""}
                  </p>
                )}
                {evt.payload?.title && (
                  <p className="text-2xs text-muted-foreground truncate">{evt.payload.title}</p>
                )}
              </div>
              <span className="text-2xs text-muted-foreground whitespace-nowrap">
                {new Date(evt.created_at).toLocaleString("tr-TR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MatchRequestDetailDrawer({
  open,
  onOpenChange,
  request,
  listing,
  onCopyId,
  formatPrice,
}) {
  const hasData = !!request;

  const priceInfo = useMemo(() => {
    if (!request) {
      return {
        requestedPrice: null,
        platformFeeRate: null,
        platformFeeAmount: null,
        providerRate: null,
        providerCommission: null,
        sellerRemain: null,
      };
    }
    const requestedPrice = Number(request.requested_price ?? 0);
    const platformFeeRate = Number(request.platform_fee_rate ?? 0.01);
    const platformFeeAmount =
      request.platform_fee_amount != null
        ? Number(request.platform_fee_amount)
        : requestedPrice * platformFeeRate;

    const providerRate = listing?.provider_commission_rate != null
      ? Number(listing.provider_commission_rate)
      : null;

    let providerCommission = null;
    let sellerRemain = null;
    if (providerRate != null && Number.isFinite(requestedPrice) && requestedPrice > 0) {
      providerCommission = requestedPrice * (providerRate / 100);
      sellerRemain = requestedPrice - platformFeeAmount - providerCommission;
    }

    return {
      requestedPrice,
      platformFeeRate,
      platformFeeAmount,
      providerRate,
      providerCommission,
      sellerRemain,
    };
  }, [request, listing]);

  const history = useMemo(() => {
    const raw = (request && request.status_history) || [];
    const items = Array.isArray(raw) ? [...raw] : [];
    items.sort((a, b) => new Date(b.at || 0) - new Date(a.at || 0));
    return items;
  }, [request]);

  const handleCopy = (value) => {
    if (!value) return;
    onCopyId?.(String(value));
  };

  const fp = (value) => {
    if (!formatPrice) return value ?? "-";
    return formatPrice(value);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-md sm:max-w-lg">
        <SheetHeader className="mb-4">
          <SheetTitle>Talep Detayı</SheetTitle>
          <SheetDescription className="text-xs">
            Talebin durumunu, ilgili listing ve fiyat kırılımını buradan inceleyebilirsiniz.
          </SheetDescription>
        </SheetHeader>

        {!hasData ? (
          <p className="text-xs text-muted-foreground">Herhangi bir talep seçilmedi.</p>
        ) : (
          <div className="flex flex-col gap-4 text-xs">
            {/* Talep özeti */}
            <div className="rounded-lg border bg-muted/40 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">Talep</span>
                <div>{statusBadgeNode(request.status)}</div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">Talep ID</span>
                  <button
                    type="button"
                    className="max-w-[220px] truncate font-mono text-xs underline-offset-2 hover:underline"
                    title="Talep ID'yi kopyala"
                    onClick={() => handleCopy(request.id)}
                  >
                    {request.id}
                  </button>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">Durum</span>
                  <span className="text-xs">{statusLabel(request.status)}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">Satıcı tenant</span>
                  <button
                    type="button"
                    className="max-w-[220px] truncate font-mono text-xs underline-offset-2 hover:underline"
                    title="Satıcı tenant ID'yi kopyala"
                    onClick={() => handleCopy(request.seller_tenant_id)}
                  >
                    {request.seller_tenant_id || "-"}
                  </button>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">Sağlayıcı tenant</span>
                  <button
                    type="button"
                    className="max-w-[220px] truncate font-mono text-xs underline-offset-2 hover:underline"
                    title="Sağlayıcı tenant ID'yi kopyala"
                    onClick={() => handleCopy(request.provider_tenant_id)}
                  >
                    {request.provider_tenant_id || "-"}
                  </button>
                </div>
              </div>
            </div>

            {/* Listing bilgisi */}
            <div className="rounded-lg border bg-muted/40 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">Listing</span>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">Listing ID</span>
                  <button
                    type="button"
                    className="max-w-[220px] truncate font-mono text-xs underline-offset-2 hover:underline"
                    title="Listing ID'yi kopyala"
                    onClick={() => handleCopy(request.listing_id)}
                  >
                    {request.listing_id}
                  </button>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">Başlık</span>
                  <span className="max-w-[220px] truncate text-xs">
                    {listing?.title || "Başlık bulunamadı"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-muted-foreground">Sağlayıcı komisyonu</span>
                  <span className="text-xs">
                    {listing?.provider_commission_rate != null
                      ? `${listing.provider_commission_rate}%`
                      : "—"}
                  </span>
                </div>
              </div>
            </div>

            {/* Fiyat kırılımı */}
            <div className="rounded-lg border bg-muted/40 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">Fiyat kırılımı</span>
                <span className="text-xs text-muted-foreground">(tahmini + kayıtlı)</span>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Talep fiyatı</span>
                  <span className="font-mono text-xs">{fp(priceInfo.requestedPrice)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Platform ücreti ({(priceInfo.platformFeeRate * 100).toFixed(2)}%)</span>
                  <span className="font-mono text-xs">{fp(priceInfo.platformFeeAmount)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Sağlayıcı komisyonu</span>
                  <span className="font-mono text-xs">
                    {priceInfo.providerCommission != null ? fp(priceInfo.providerCommission) : "—"}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Size kalan (tahmini)</span>
                  <span className="font-mono text-xs">
                    {priceInfo.sellerRemain != null ? fp(priceInfo.sellerRemain) : "—"}
                  </span>
                </div>
              </div>
            </div>

            {/* Durum geçmişi */}
            <div className="rounded-lg border bg-muted/40 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">Durum geçmişi</span>
              </div>
              {history.length === 0 ? (
                <p className="text-xs text-muted-foreground">Durum geçmişi bulunamadı.</p>
              ) : (
                <div className="space-y-1">
                  {history.map((h, idx) => (
                    <div
                      key={`${h.status}-${h.at || idx}`}
                      className="flex items-center justify-between gap-2 rounded-md border bg-background/80 px-2 py-1"
                    >
                      <div className="flex items-center gap-2">
                        {statusBadgeNode(h.status)}
                        <span className="text-xs text-muted-foreground">
                          {new Date(h.at || new Date()).toLocaleString("tr-TR")}
                        </span>
                      </div>
                      {h.by_user_id && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          title="İşlemi yapan kullanıcı ID'yi kopyala"
                          onClick={() => handleCopy(h.by_user_id)}
                        >
                          <span className="sr-only">Kopyala</span>
                          <span className="text-2xs">ID</span>
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Aktivite Timeline */}
            <ActivityTimeline entityId={request?.id} />
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
