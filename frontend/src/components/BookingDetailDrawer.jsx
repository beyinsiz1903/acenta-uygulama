import React, { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter } from "./ui/sheet";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { toast } from "sonner";
import { buildBookingCopyText } from "../utils/buildBookingCopyText";
import { api, apiErrorMessage } from "../lib/api";
import { FinanceSummaryCard } from "./FinanceSummaryCard";

function StatusBadge({ status_tr, status }) {
  if (!status_tr && !status) return null;
  const tone = (status || "").toLowerCase();
  let variant = "outline";
  if (tone === "confirmed") variant = "default";
  if (tone === "completed") variant = "secondary";
  if (tone === "cancelled") variant = "destructive";

  return <Badge variant={variant}>{status_tr || status}</Badge>;
}

export function BookingDetailDrawer({ bookingId, mode = "agency", open, onOpenChange }) {
  const [booking, setBooking] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [voucherEmailDialogOpen, setVoucherEmailDialogOpen] = useState(false);
  const [voucherEmail, setVoucherEmail] = useState("");
  const [voucherEmailSending, setVoucherEmailSending] = useState(false);
  const [voucherToken, setVoucherToken] = useState(null);
  const [voucherLoading, setVoucherLoading] = useState(false);

  useEffect(() => {
    if (!open || !bookingId) {
      setError("");
      return;
    }

    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const base = mode === "hotel" ? "/hotel/bookings" : "/agency/bookings";
        const resp = await api.get(`${base}/${bookingId}`);
        if (!cancelled) setBooking(resp.data || null);
      } catch (e) {
        if (!cancelled) {
          setError(apiErrorMessage(e));
          setBooking(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [open, bookingId, mode]);

  const handleOpenChange = (next) => {
    if (!next) {
      setBooking(null);
      setError("");
      setVoucherToken(null);
      setVoucherLoading(false);
    }
    onOpenChange?.(next);
  };

  const handleCopy = async () => {
    if (!booking) return;
    const text = buildBookingCopyText(booking);
    if (!text) return;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }
      toast.success("Rezervasyon bilgisi kopyalandı");
    } catch {
      toast.error("Kopyalama başarısız oldu");
    }
  };

  const ensureVoucherToken = async () => {
    // legacy public voucher token flow; kept for compatibility if used elsewhere
    if (!bookingId) return null;
    if (voucherToken) return voucherToken;

    setVoucherLoading(true);
    try {
      const resp = await api.post(`/voucher/${bookingId}/generate`);
      const token = resp?.data?.token;
      if (token) {
        setVoucherToken(token);
        return token;
      }
      throw new Error("TOKEN_MISSING");
    } catch (e) {
      toast.error(apiErrorMessage(e) || "Voucher oluşturulamadı");
      return null;
    } finally {
      setVoucherLoading(false);
    }
  };

  const handleOpenVoucherPdfDirect = async () => {
    if (!booking) return;
    const id = booking.id || booking._id || booking.booking_id || bookingId;
    if (!id) return;

    try {
      const resp = await api.get(`/bookings/${id}/voucher.pdf`, { responseType: "blob" });
      const blob = new Blob([resp.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e) {
      toast.error(apiErrorMessage(e) || "Voucher PDF açılamadı");
    }
  };

  const getBackendBaseUrl = () => {
    // CRA: process.env.REACT_APP_BACKEND_URL, Vite: import.meta.env.VITE_BACKEND_URL
    if (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_BACKEND_URL) {
      return import.meta.env.VITE_BACKEND_URL;
    }
    if (process.env.REACT_APP_BACKEND_URL) {
      return process.env.REACT_APP_BACKEND_URL;
    }
    // Fallback: relative (aynı origin). Public voucher endpoint yine çalışır.
    return "";
  };

  const handleCopyVoucherLink = async () => {
    const token = await ensureVoucherToken();
    if (!token) return;
    const base = getBackendBaseUrl();
    const url = `${base}/api/voucher/public/${token}?format=html`;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(url);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = url;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }
      toast.success("Voucher linki kopyalandı");
    } catch {
      toast.error("Voucher linki kopyalanamadı");
    }
  };

  const handleOpenVoucherPdf = async () => {
    const token = await ensureVoucherToken();
    if (!token) return;
    const base = getBackendBaseUrl();
    const url = `${base}/api/voucher/public/${token}?format=pdf`;
    try {
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      toast.error("PDF açılamadı");
    }
  };

  const titleHotel = booking?.hotel_name || "Rezervasyon Detayı";
  const subtitleParts = [];
  if (booking?.guest_name) subtitleParts.push(booking.guest_name);
  if (booking?.check_in_date && booking?.check_out_date) {
    subtitleParts.push(`${booking.check_in_date} → ${booking.check_out_date}`);
  }

  const subtitle = subtitleParts.join(" • ");

  const customer = booking?.customer || null;
  const snap = booking?.catalog_snapshot || null;
  const isPublic = booking?.source === "public_booking";

  const infoRows = [
    ["Oda / Room", booking?.room_type],
    ["Pansiyon / Board", booking?.board_type],
    ["Pax", booking ? `${booking.adults ?? "-"} / ${booking.children ?? 0}` : null],
    [
      "Tutar / Total",
      booking?.total_amount != null
        ? `${Number(booking.total_amount).toLocaleString("tr-TR", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
          })} ${booking.currency || ""}`.trim()
        : null,
    ],
    ["Durum / Status", `${booking?.status_tr || ""}${booking?.status_en ? ` / ${booking.status_en}` : ""}`],
    ["Booking ID", booking?.code],
    [
      "Kaynak / Source",
      booking?.source === "public_booking"
        ? "Public Booking"
        : booking?.source,
    ],
    ["Ödeme / Payment", booking?.payment_status],
    ["Oluşturma / Created", booking?.created_at],
    ["Onay Zamanı / Confirmed At", booking?.confirmed_at],
    ["Özel İstekler / Special Requests", booking?.special_requests],
  ];

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl flex flex-col">
        <SheetHeader className="space-y-2 pb-4 border-b">
          <div className="flex items-start justify-between gap-3">
            <div>
              <SheetTitle className="text-xl font-semibold">{titleHotel}</SheetTitle>
              {subtitle && (
                <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
              )}
            </div>
            <StatusBadge status_tr={booking?.status_tr} status={booking?.status} />
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {loading && (
            <p className="text-sm text-muted-foreground px-1">Yükleniyor...</p>
          )}

          {!loading && error && (
            <p className="text-sm text-destructive px-1">{error}</p>
          )}

          {!loading && !error && booking && (
            <div className="space-y-4">
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">
                    Özet / Summary
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                    {infoRows.map(([label, value]) => (
                      <div key={label} className="flex flex-col">
                        <span className="text-xs text-muted-foreground uppercase tracking-wide">
                          {label}
                        </span>
                        <span className="text-foreground">
                          {value === null || value === undefined || value === "" ? "-" : value}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Finansal Özet Kartı */}
                {booking && (
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">
                      Finans
                    </h3>
                    <FinanceSummaryCard
                      gross={booking.gross_amount ?? booking.total_amount ?? 0}
                      commissionPercent={booking.commission_value_snapshot ?? booking.commission_percent ?? 0}
                      commissionAmount={booking.commission_amount ?? 0}
                      netToHotel={booking.net_amount ?? 0}
                      paymentStatus={booking.payment_status || "unpaid"}
                      onStatusChange={(next) => {
                        setBooking((prev) => (prev ? { ...prev, payment_status: next } : prev));
                      }}
                      onSave={async () => {
                        if (!booking) return;
                        try {
                          const id = booking.id || booking._id || booking.booking_id || bookingId;
                          const resp = await api.post(`/bookings/${id}/payment-status`, {
                            status: booking.payment_status || "unpaid",
                          });
                          const updated = resp.data || {};
                          setBooking((prev) => (prev ? { ...prev, payment_status: updated.payment_status } : prev));
                          toast.success("Ödeme durumu güncellendi");
                        } catch (e) {
                          toast.error(apiErrorMessage(e) || "Ödeme durumu güncellenemedi");
                        }
                      }}
                      onDownloadPdf={handleOpenVoucherPdfDirect}
                      onDownloadVoucher={async () => {
                        if (!booking) return;
                        try {
                          const id = booking.id || booking._id || booking.booking_id || bookingId;
                          const url = `${api.defaults.baseURL}/bookings/${id}/voucher.pdf`;
                          window.open(url, "_blank", "noopener,noreferrer");
                        } catch (e) {
                          toast.error("Voucher indirilemedi");
                        }
                      }}
                      onSendVoucherEmail={() => {
                        setVoucherEmail(booking?.guest?.email || "");
                        setVoucherEmailDialogOpen(true);
                      }}
                    />
                  </div>
                )}
              </div>

              {/* Müşteri Bloğu */}
              {customer ? (
                <div className="mt-4 rounded-md border p-3">
                  <div className="text-sm font-medium mb-2">Müşteri</div>
                  <div className="text-sm space-y-1">
                    <div>
                      <span className="text-muted-foreground">Ad Soyad:</span>{" "}
                      <span>{customer?.name || "-"}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Telefon:</span>{" "}
                      <span>{customer?.phone || "-"}</span>
                    </div>
                    {customer?.email ? (
                      <div>
                        <span className="text-muted-foreground">E-posta:</span>{" "}
                        <span>{customer.email}</span>
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}

              {/* Katalog Snapshot Bloğu (sadece public) */}
              {isPublic ? (
                <div className="mt-3 rounded-md border p-3">
                  <div className="text-sm font-medium mb-2">Katalog Snapshot</div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <div>Min nights: {snap?.min_nights ?? "-"}</div>
                    <div>Komisyon: %{snap?.commission?.value ?? "-"}</div>
                    <div>Markup: %{snap?.pricing_policy?.markup_percent ?? "-"}</div>
                  </div>
                </div>
              ) : null}

              <Separator />

              <div className="text-xs text-muted-foreground">
                <p>
                  Bu görünüm, voucher ve email metinleri için normalize edilmiş{' '}
                  rezervasyon özetidir.
                </p>
              </div>
            </div>
          )}
        </div>

        <SheetFooter className="gap-2 border-t pt-3 flex flex-row items-center justify-between">
          <div className="text-xs text-muted-foreground">
            {booking?.code && <span>PNR: {booking.code}</span>}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleCopy} disabled={!booking}>
              Bilgileri Kopyala
            </Button>

            {mode === "hotel" && booking?.source === "public_booking" && (
              <Button
                variant="outline"
                onClick={() => {
                  const key = booking.id || booking.booking_id || booking._id;
                  if (!key) return;
                  window.open(`/app/hotel/bookings/${key}/print`, "_blank", "noopener,noreferrer");
                }}
                disabled={!booking}
              >
                Yazdır
              </Button>
            )}

            {mode === "hotel" && (
              <>
                <Button
                  variant="outline"
                  onClick={async () => {
                    if (!booking) return;
                    try {
                      const resp = await api.post(`/bookings/${booking.id || booking.code || booking._id}/mark-paid`);
                      const updated = resp.data || {};
                      toast.success("Ödeme alındı olarak işaretlendi");
                      setBooking((prev) => ({ ...(prev || {}), payment: updated.payment }));
                    } catch (e) {
                      toast.error("Ödeme alındı işaretlenemedi");
                    }
                  }}
                  disabled={!booking}
                >
                  Ödeme Alındı
                </Button>

                <Button
                  variant="outline"
                  onClick={async () => {
                    if (!booking) return;
                    try {
                      const resp = await api.get(`/bookings/${booking.id || booking.code || booking._id}/payment-instructions`);
                      const data = resp.data || {};
                      const p = data.payment || {};
                      const off = data.offline || {};
                      const parts = [];
                      if (off.iban) parts.push(`IBAN: ${off.iban}`);
                      if (off.account_holder) parts.push(`Alıcı: ${off.account_holder}`);
                      if (off.bank_name) parts.push(`Banka: ${off.bank_name}`);
                      if (p.reference_code) parts.push(`Açıklama: ${p.reference_code}`);
                      if (p.amount) parts.push(`Tutar: ${p.amount} ${p.currency || ""}`);
                      const text = parts.join(" | ");
                      if (navigator.clipboard && text) {
                        await navigator.clipboard.writeText(text);
                        toast.success("Ödeme talimatı panoya kopyalandı");
                      } else {
                        toast.success("Ödeme talimatını kopyalamak için metni seçebilirsiniz");
                      }
                    } catch (e) {
                      toast.error("Ödeme talimatı alınamadı");
                    }
                  }}
                  disabled={!booking}
                >
                  Ödeme Bilgilerini Kopyala
                </Button>
              </>
            )}

            <Button
              variant="outline"
              onClick={handleCopyVoucherLink}
              disabled={!booking || voucherLoading}
            >
              {voucherLoading ? "Voucher oluşturuluyor..." : "Voucher Linkini Kopyala"}
            </Button>
            <Button
              variant="outline"
              onClick={handleCopyVoucherLink}
              disabled={!booking || voucherLoading}
            >
              {voucherLoading ? "Voucher oluşturuluyor..." : "Voucher Linkini Kopyala"}
            </Button>

            <Button
              variant="outline"
              onClick={handleOpenVoucherPdfDirect}
              disabled={!booking || (booking.status !== "confirmed")}
            >
              Voucher PDF
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
