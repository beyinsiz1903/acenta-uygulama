import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import EmptyState from "../../components/EmptyState";
import { getPublicBookingSummary, requestMyBookingLink, createMyBookingToken, apiErrorMessage } from "../../lib/publicBooking";

function formatAmount(amountCents, currency) {
  const amount = (amountCents || 0) / 100;
  try {
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: currency || "EUR",
      minimumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency || "EUR"}`;
  }
}

export default function BookCompletePage() {
  const [searchParams] = useSearchParams();

  const normalizeParam = (value) => {
    if (value == null) return "";
    const trimmed = value.trim();
    if (!trimmed || trimmed === "undefined" || trimmed === "null") return "";
    return trimmed;
  };

  const bookingCode = normalizeParam(searchParams.get("booking_code"));
  const org = normalizeParam(searchParams.get("org"));
  const partner = normalizeParam(searchParams.get("partner"));

  const isE2E =
    typeof window !== "undefined" && window.location.search && window.location.search.includes("e2e=1");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [email, setEmail] = useState("");
  const [linkRequestLoading, setLinkRequestLoading] = useState(false);
  const [linkRequestError, setLinkRequestError] = useState("");
  const [linkRequestMessage, setLinkRequestMessage] = useState("");
  const [instantToken, setInstantToken] = useState("");

  useEffect(() => {
    if (!bookingCode || !org) return;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getPublicBookingSummary({ org, booking_code: bookingCode });
        setSummary(data.booking || null);
      } catch (e) {
        setError(apiErrorMessage(e));
        setSummary(null);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [bookingCode, org]);

  useEffect(() => {
    if (!bookingCode || !org) return;

    async function loadInstantToken() {
      try {
        const data = await createMyBookingToken({ org, booking_code: bookingCode });
        if (data && data.token) {
          setInstantToken(data.token);
        }
      } catch (e) {
        // Silent fail; instant access is "nice to have" only
        console.error("Instant MyBooking token error", e);
      }
    }

    loadInstantToken();
  }, [bookingCode, org]);

  const navigate = useNavigate();
  const statusBadge = summary?.status || "PENDING_PAYMENT";

  const qpBackToSearch = new URLSearchParams();
  if (org) qpBackToSearch.set("org", org);

  const handleViewBooking = () => {
    if (instantToken) {
      navigate(`/my-booking/${instantToken}`);
    } else {
      navigate("/my-booking");
    }
  };

  if (!bookingCode || !org) {
    return (
      <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
        <Card className="w-full max-w-lg p-4 space-y-3">
          <EmptyState
            title={"Rezervasyon bilgisi bulunamad\u0131"}
            description={"Ba\u011flant\u0131 eksik veya hatal\u0131. L\u00fctfen rezervasyon sayfas\u0131n\u0131 yeniden a\u00e7\u0131n."}
            action={
              <div className="flex flex-col sm:flex-row gap-2 justify-center">
                <Button
                  size="sm"
                  onClick={() => {
                    const qs = qpBackToSearch.toString();
                    navigate(qs ? `/book?${qs}` : "/book");
                  }}
                >
                  {"Geri d\u00f6n"}
                </Button>
              </div>
            }
          />
          {isE2E && (
            <div data-testid="e2e-guard" className="mt-2 text-2xs text-muted-foreground">
              GUARD_RENDERED: missing booking_code
            </div>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <Card className="w-full max-w-lg p-4 space-y-3 text-center">
        <h1 className="text-lg font-semibold">Rezervasyonunuz alındı</h1>
        <p className="text-xs text-muted-foreground">
          Bu sayfa, ödeme akışı tamamlandığında rezervasyon özetini gösterir. Şu anda backend checkout akışının
          iskeleti test ediliyor.
        </p>
        <p className="text-xs text-muted-foreground">
          Rezervasyonunuz oluşturuldu. Ödeme tamamlanana kadar durum <span className="font-mono">PENDING_PAYMENT</span>
          olabilir.
        </p>

        <div className="text-xs space-y-1">
          <div>
            <span className="font-medium">Booking code:</span>{" "}
            <span className="font-mono">{bookingCode || "(başarılı checkout sonrasında doldurulacak)"}</span>
          </div>
        </div>

        {loading && <p className="text-xs text-muted-foreground">Rezervasyon özeti yükleniyor...</p>}
        {!loading && error && (
          <p className="text-xs text-red-600">
            Özet getirilemedi. Lütfen rezervasyonunuzu My Booking üzerinden kontrol edin. ({error})
          </p>
        )}

        {!loading && !error && summary && (
          <div className="mt-3 space-y-2 text-xs text-left">
            <div className="flex items-center justify-between">
              <div className="font-medium">Durum</div>
              <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium">
                {statusBadge}
              </span>
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Ürün</div>
              <div className="font-medium">{summary.product?.title || "Rezervasyonunuz"}</div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="text-xs text-muted-foreground">Giriş / Çıkış</div>
                <div>
                  {summary.date_from || "-"} → {summary.date_to || "-"}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Gece</div>
                <div>{summary.nights ?? "-"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Kişi / Oda</div>
                <div>
                  {summary.pax?.adults || 0} yetişkin, {summary.pax?.children || 0} çocuk, {summary.pax?.rooms || 1} oda
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Tutar</div>
                <div>
                  {formatAmount(summary.price?.amount_cents, summary.price?.currency)}
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="pt-2 flex justify-center">
          <Button
            size="sm"
            variant="outline"
            onClick={handleViewBooking}
          >
            {instantToken ? "Hemen Görüntüle" : "Rezervasyonumu Görüntüle"}
          </Button>
        </div>

        <div className="mt-4 border-t pt-3 text-left text-xs space-y-2">
          <div className="font-medium">E-posta ile rezervasyon linki gönder</div>
          <p className="text-xs text-muted-foreground">
            E-posta adresinizi girdiğinizde, bu rezervasyonla eşleşen bir kayıt bulunursa birkaç dakika
            içinde My Booking bağlantısı e-posta ile göndereceğiz.
          </p>
          <div className="flex flex-col sm:flex-row gap-2 items-center">
            <input
              type="email"
              className="w-full rounded-md border px-2 py-1 text-xs"
              placeholder="ornek@misafir.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Button
              size="sm"
              disabled={!email || linkRequestLoading || !bookingCode}
              onClick={async () => {
                setLinkRequestError("");
                setLinkRequestMessage("");
                try {
                  setLinkRequestLoading(true);
                  await requestMyBookingLink({
                    email,
                    booking_code: bookingCode,
                  });
                  setLinkRequestMessage(
                    "Eğer bu e-posta ile eşleşen bir rezervasyon bulunursa, birkaç dakika içinde bağlantı gönderilecektir.",
                  );
                } catch (e) {
                  setLinkRequestError(apiErrorMessage(e));
                } finally {
                  setLinkRequestLoading(false);
                }
              }}
            >
              {linkRequestLoading ? "Gönderiliyor..." : "Link gönder"}
            </Button>
          </div>
          {linkRequestMessage && <p className="text-xs text-green-700">{linkRequestMessage}</p>}
          {linkRequestError && <p className="text-xs text-red-600">{linkRequestError}</p>}
        </div>
      </Card>
    </div>
  );
}
