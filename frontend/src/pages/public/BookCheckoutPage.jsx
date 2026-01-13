import React, { useState } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, CardElement, useStripe, useElements } from "@stripe/react-stripe-js";

import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { createPublicCheckout, apiErrorMessage } from "../../lib/publicBooking";

const STRIPE_PUBLISHABLE_KEY = window.STRIPE_PUBLISHABLE_KEY || process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY || "";
const stripePromise = STRIPE_PUBLISHABLE_KEY ? loadStripe(STRIPE_PUBLISHABLE_KEY) : Promise.resolve(null);

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
        setStripeError(error.message || "Ödeme başarısız oldu. Lütfen tekrar deneyin.");
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
        Stripe yapılandırması eksik. Ödeme formu gösterilemiyor ancak rezervasyon kodunuz:{  const { productId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const org = searchParams.get("org") || "";
  const quoteId = searchParams.get("quote_id") || "";

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

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
    setResult(null);

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
      };

      const res = await createPublicCheckout(body);
      if (!res.ok) {
        if (res.reason === "provider_unavailable") {
          setError("Ödeme sağlayıcısına şu anda ulaşılamıyor. Lütfen daha sonra tekrar deneyin.");
        } else {
          setError("Checkout tamamlanamadı. Lütfen tekrar deneyin.");
        }
        return;
      }

      setResult(res);

      const qp = new URLSearchParams();
      if (res.booking_code) qp.set("booking_code", res.booking_code);
      navigate(`/book/complete?${qp.toString()}`);
    } catch (e2) {
      const status = e2?.response?.status;
      const detail = e2?.response?.data?.detail;
      if (status === 404 && (detail === "QUOTE_NOT_FOUND" || detail === "Quote not found or expired")) {
        setError("Teklifin süresi doldu. Lütfen yeni bir teklif alın.");
      } else {
        setError(apiErrorMessage(e2));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <Card className="w-full max-w-lg p-4 space-y-3">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Checkout (v1)</h1>
          <p className="text-xs text-muted-foreground">
            Bu adımda misafir bilgilerini alıyor ve backend üzerinden public checkout isteği gönderiyoruz.
            Stripe kart formu bir sonraki iterasyonda eklenecek.
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
            <span className="font-medium">Quote ID:</span> <span className="font-mono break-all">{quoteId || "(henüz oluşturulmadı)"}</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 text-xs mt-2">
          <div className="space-y-1">
            <label className="font-medium">Ad Soyad</label>
            <input
              type="text"
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
              className="w-full rounded-md border px-2 py-1"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </div>

          {error && <div className="text-xs text-red-600">{error}</div>}

          {result && (
            <div className="text-xs space-y-1 border-t pt-2 mt-2">
              <div>
                <span className="font-medium">Booking ID:</span> <span className="font-mono">{result.booking_id}</span>
              </div>
              <div>
                <span className="font-medium">Booking code:</span> <span className="font-mono">{result.booking_code}</span>
              </div>
              <div>
                <span className="font-medium">Payment Intent:</span>{" "}
                <span className="font-mono break-all">{result.payment_intent_id}</span>
              </div>
              <div>
                <span className="font-medium">Client secret:</span>{" "}
                <span className="font-mono break-all">{result.client_secret}</span>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="submit" size="sm" disabled={!org || !quoteId || loading}>
              {loading ? "Checkout işlemi..." : "Checkout"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}