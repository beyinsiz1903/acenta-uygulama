import React, { useState } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, CardElement, useStripe, useElements } from "@stripe/react-stripe-js";

import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import EmptyState from "../../components/EmptyState";
import { createPublicCheckout, apiErrorMessage } from "../../lib/publicBooking";

const STRIPE_PUBLISHABLE_KEY =
  window.STRIPE_PUBLISHABLE_KEY || process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY || "";

const stripePromise = STRIPE_PUBLISHABLE_KEY
  ? loadStripe(STRIPE_PUBLISHABLE_KEY)
  : Promise.resolve(null);

function PublicCheckoutPaymentForm({ clientSecret, bookingCode, onSuccess }) {
  const stripe = useStripe();
  const elements = useElements();

  const [paying, setPaying] = useState(false);
  const [stripeError, setStripeError] = useState("");

  const handlePay = async (e) => {
    e.preventDefault();
    if (!stripe || !elements || !clientSecret) return;

    setPaying(true);
    setStripeError("");

    try {
      const card = elements.getElement(CardElement);
      if (!card) {
        setStripeError("Kart alanı yüklenemedi.");
        setPaying(false);
        return;
      }

      const { error, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
        payment_method: { card },
      });

      if (error) {
        setStripeError(
          error.message ||
            "Ödeme başarısız oldu. Kart bilgilerinizi kontrol edip tekrar deneyin; sorun devam ederse bankanızla görüşün.",
        );
        setPaying(false);
        return;
      }

      if (paymentIntent && paymentIntent.status === "succeeded") {
        onSuccess(bookingCode);
      } else {
        setStripeError("Ödeme henüz tamamlanmadı. Lütfen tekrar deneyin.");
      }
    } catch (err) {
      setStripeError("Ödeme sırasında bir hata oluştu. Lütfen tekrar deneyin.");
    } finally {
      setPaying(false);
    }
  };

  if (!clientSecret) {
    return (
      <p className="text-xs text-red-600">
        Ödeme başlatılamadı. Lütfen daha sonra tekrar deneyin veya destek ile iletişime geçin.
      </p>
    );
  }

  if (!STRIPE_PUBLISHABLE_KEY) {
    return (
      <p className="text-xs text-red-600">
        Stripe yapılandırması eksik. Ödeme formu gösterilemiyor ancak rezervasyon kodunuz:
        <span className="font-mono"> {bookingCode || "(henüz oluşturulmadı)"}</span>.
      </p>
    );
  }

  return (
    <form onSubmit={handlePay} className="space-y-3 mt-3 text-xs">
      <div className="space-y-1">
        <label className="font-medium">Kart Bilgileri</label>
        <div className="border rounded-md px-2 py-2 bg-background">
          <CardElement options={{ hidePostalCode: true }} />
        </div>
      </div>

      {stripeError && <p className="text-xs text-red-600">{stripeError}</p>}

      <Button type="submit" size="sm" disabled={paying || !stripe}>
        {paying ? "Ödeme işleniyor..." : "Ödemeyi Tamamla"}
      </Button>
    </form>
  );
}

export default function BookCheckoutPage() {
  const { productId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const normalizeParam = (value) => {
    if (value == null) return "";
    const trimmed = value.trim();
    if (!trimmed || trimmed === "undefined" || trimmed === "null") return "";
    return trimmed;
  };

  const org = normalizeParam(searchParams.get("org"));
  const partner = normalizeParam(searchParams.get("partner"));
  const quoteId = normalizeParam(searchParams.get("quote_id"));

  const isE2E =
    typeof window !== "undefined" && window.location.search && window.location.search.includes("e2e=1");

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [clientSecret, setClientSecret] = useState("");
  const [providerError, setProviderError] = useState(null);
  const [showProviderDetails, setShowProviderDetails] = useState(false);
  const [couponCode, setCouponCode] = useState("");
  const [couponResult, setCouponResult] = useState(null);

  const getIdempotencyKey = () => {
    const keyName = `public_checkout_idem_${quoteId}`;
    const existing = window.sessionStorage.getItem(keyName);
    if (existing) return existing;
    const generated = `idem_${Math.random().toString(36).slice(2, 12)}`;
    window.sessionStorage.setItem(keyName, generated);
    return generated;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!org || !quoteId) return;

    setLoading(true);
    setError("");
    setShowProviderDetails(false);
    setProviderError(null);
    setResult(null);
    setCouponResult(null);

    try {
      const body = {
        org,
        quote_id: quoteId,
        guest: {
          full_name: fullName,
          email,
          phone,
        },
        payment: { method: "stripe" },
        idempotency_key: getIdempotencyKey(),
        coupon: couponCode.trim() || undefined,
      };

      const res = await createPublicCheckout(body);
      if (res.coupon) {
        setCouponResult(res.coupon);
      } else {
        setCouponResult(null);
      }
      if (!res.ok) {
        if (res.reason === "provider_unavailable") {
          setProviderError(res.provider_error || null);
          setError(
            "Ödeme sağlayıcısına şu anda ulaşılamıyor. Lütfen birkaç dakika sonra tekrar deneyin. Teklifinizin süresi dolarsa yeniden teklif oluşturmanız gerekebilir.",
          );
        } else {
          setError(
            "Ödeme işlemi tamamlanamadı. Kartınızdan çekim yapılmamıştır. Lütfen birkaç dakika sonra tekrar deneyin; sorun devam ederse bankanız veya destek ekibimizle iletişime geçin.",
          );
        }
        return;
      }

      setResult(res);
      setClientSecret(res.client_secret || "");
      setProviderError(null);
    } catch (e2) {
      const status = e2?.status ?? e2?.response?.status;
      const code = e2?.code;
      const detail = e2?.raw?.response?.data?.detail || e2?.response?.data?.detail;

      if (
        status === 404 &&
        (code === "QUOTE_NOT_FOUND" || detail === "QUOTE_NOT_FOUND" || detail === "Quote not found or expired")
      ) {
        setError("Teklifin süresi doldu. Lütfen yeni bir teklif alın.");
      } else if (status === 404 && detail === "NOT_FOUND" && quoteId) {
        setError("Teklif bulunamadı veya süresi doldu. Lütfen yeni bir teklif alın.");
      } else if (status === 429 || code === "RATE_LIMITED") {
        setError("Çok fazla istek atıldı, lütfen 1 dakika sonra tekrar deneyin.");
      } else {
        const msg = apiErrorMessage(e2.raw || e2) || e2.message;
        setError(
          msg ||
            "Ödeme sırasında beklenmeyen bir hata oluştu. Kartınızdan çekim yapılmamıştır; lütfen tekrar deneyin veya destek ile iletişime geçin.",
        );
      }
    } finally {
      setLoading(false);
    }
  };

  if (!org || !quoteId) {
    const qpBackToSearch = new URLSearchParams();
    if (org) qpBackToSearch.set("org", org);

    return (
      <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
        <Card className="w-full max-w-lg p-4 space-y-3">
          <EmptyState
            title={"Teklif bilgisi bulunamad\u0131"}
            description={"Ba\u011flant\u0131 eksik veya hatal\u0131. L\u00fctfen teklif ba\u011flant\u0131s\u0131n\u0131 yeniden a\u00e7\u0131n."}
            action={
              <div className="flex justify-center">
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
              GUARD_RENDERED: missing org/quote_id
            </div>
          )}
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <Card className="w-full max-w-lg p-4 space-y-3">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Ödeme ve Rezervasyon Tamamlama</h1>
          <p className="text-xs text-muted-foreground">
            Bu adımda misafir bilgilerinizi alıyor ve kartınızdan güvenli bir şekilde ödeme alarak rezervasyonunuzu
            tamamlıyoruz.
          </p>
        </div>

        <div className="text-xs space-y-1">
          <div>
            <span className="font-medium">Product ID:</span> <span className="font-mono break-all">{productId}</span>
          </div>
          <div>
            <span className="font-medium">Org:</span> <span className="font-mono break-all">{org || "-"}</span>
          </div>
          <div>
            <span className="font-medium">Quote ID:</span>{" "}
            <span className="font-mono break-all">{quoteId || "(henüz oluşturulmadı)"}</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs mt-2">
          <div className="space-y-1">
            <label className="font-medium">Kupon Kodu (varsa)</label>
            <input
              type="text"
              className="w-full rounded-md border px-2 py-1 uppercase"
              value={couponCode}
              onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
              placeholder="Örn: YAZ2025"
            />
          </div>

          <div className="space-y-1">
            <label className="font-medium">Ad Soyad</label>
            <input
              type="text"
              data-testid="checkout-name"
              className="w-full rounded-md border px-2 py-1"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1">
            <label className="font-medium">E-posta</label>
            <input
              type="email"
              data-testid="checkout-email"
              className="w-full rounded-md border px-2 py-1"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1">
            <label className="font-medium">Telefon</label>
            <input
              type="tel"
              data-testid="checkout-phone"
              className="w-full rounded-md border px-2 py-1"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>

          {error && (
          <div className="text-xs text-red-600 space-y-1">
            <p>{error}</p>
            {providerError && (
              <button
                type="button"
                className="text-xs underline"
                onClick={() => setShowProviderDetails((v) => !v)}
              >
                {showProviderDetails ? "Detayı gizle" : "Detay"}
              </button>
            )}
            {showProviderDetails && providerError && (
              <pre className="text-2xs bg-slate-100 rounded p-2 overflow-x-auto">
                {JSON.stringify(
                  {
                    code: providerError?.code,
                    type: providerError?.type,
                    message: providerError?.message,
                  },
                  null,
                  2,
                )}
              </pre>
            )}
          </div>
        )}

          {result && (
            <div className="text-xs space-y-1 border-t pt-2 mt-2">
              <div>
                <span className="font-medium">Booking ID:</span>{" "}
                <span className="font-mono">{result.booking_id}</span>
              </div>
              <div>
                <span className="font-medium">Booking code:</span>{" "}
                <span className="font-mono">{result.booking_code}</span>
              </div>
              <div>
                <span className="font-medium">Payment Intent:</span>{" "}
                <span className="font-mono break-all">{result.payment_intent_id}</span>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="submit" size="sm" disabled={!org || !quoteId || loading}>
              {loading ? "Checkout işlemi..." : "Checkout"}
            </Button>
          </div>
        </form>

        {couponResult && (
          <div className="mt-4 border-t pt-3 space-y-1 text-xs">
            <div className="flex items-center justify-between">
              <div className="font-medium">Kupon</div>
              <div className="text-xs text-muted-foreground">
                Kod: <span className="font-mono">{couponResult.code}</span>
              </div>
            </div>
            <div className="text-xs">
              Durum: <span className="font-mono">{couponResult.status}</span>
              {couponResult.reason && ` • ${couponResult.reason}`}
            </div>
            {couponResult.status === "APPLIED" && (
              <div className="text-xs">
                İndirim: {couponResult.amount_cents / 100} {couponResult.currency}
              </div>
            )}
          </div>
        )}

        {result && (
          <div className="mt-4 border-t pt-3 space-y-2 text-xs">
            {providerError && !error && (
              <div className="text-xs text-red-600 space-y-1">
                <p>Ödeme sırasında bir hata oluştu. Lütfen tekrar deneyin.</p>
                <button
                  type="button"
                  className="text-xs underline"
                  onClick={() => setShowProviderDetails((v) => !v)}
                >
                  {showProviderDetails ? "Detayı gizle" : "Detay"}
                </button>
                {showProviderDetails && (
                  <pre className="text-2xs bg-slate-100 rounded p-2 overflow-x-auto">
                    {JSON.stringify(
                      {
                        code: providerError?.code,
                        type: providerError?.type,
                        message: providerError?.message,
                      },
                      null,
                      2,
                    )}
                  </pre>
                )}
              </div>
            )}
            <div className="font-medium">Ödeme</div>
            {clientSecret ? (
              STRIPE_PUBLISHABLE_KEY ? (
                <Elements stripe={stripePromise} options={{ clientSecret }}>
                  <PublicCheckoutPaymentForm
                    clientSecret={clientSecret}
                    bookingCode={result.booking_code}
                    onSuccess={(code) => {
                      const qp = new URLSearchParams();
                      if (code) qp.set("booking_code", code);
                      navigate(`/book/complete?${qp.toString()}`);
                    }}
                  />
                </Elements>
              ) : (
                <p className="text-xs text-red-600">
                  Stripe yapılandırması eksik. Ödeme formu gösterilemiyor ancak rezervasyon kodunuz:
                  <span className="font-mono"> {result.booking_code}</span>.
                </p>
              )
            ) : (
              <p className="text-xs text-red-600">
                Ödeme başlatılamadı. Lütfen daha sonra tekrar deneyin veya destek ile iletişime geçin.
              </p>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
