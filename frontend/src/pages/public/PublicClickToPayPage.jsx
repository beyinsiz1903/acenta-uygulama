import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, CardElement, useStripe, useElements } from "@stripe/react-stripe-js";

import { api, apiErrorMessage } from "../../lib/api";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import ErrorState from "../../components/ErrorState";
import EmptyState from "../../components/EmptyState";

// In a real deployment, this would come from environment/config. For this
// preview implementation we rely on Stripe.js auto-detection via backend
// client_secret only. We keep the publishable key nullable to allow
// Server-side confirmation experiments later.

const STRIPE_PUBLISHABLE_KEY = window.STRIPE_PUBLISHABLE_KEY || "";

const stripePromise = STRIPE_PUBLISHABLE_KEY ? loadStripe(STRIPE_PUBLISHABLE_KEY) : Promise.resolve(null);

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

function ClickToPayForm({ token, tokenData }) {
  const stripe = useStripe();
  const elements = useElements();

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setSubmitting(true);
    setError("");

    try {
      const cardElement = elements.getElement(CardElement);
      if (!cardElement) {
        setError("Kart alanı yüklenemedi.");
        setSubmitting(false);
        return;
      }

      const { error: stripeError, paymentIntent } = await stripe.confirmCardPayment(
        tokenData.client_secret,
        {
          payment_method: {
            card: cardElement,
          },
        }
      );

      if (stripeError) {
        setError(stripeError.message || "Ödeme başarısız oldu.");
        setSubmitting(false);
        return;
      }

      if (paymentIntent && paymentIntent.status === "succeeded") {
        setSuccess(true);
      } else {
        setError("Ödeme henüz tamamlanmadı. Lütfen tekrar deneyin.");
      }
    } catch (e) {
      setError("Ödeme sırasında bir hata oluştu.");
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="space-y-2 text-center">
        <h1 className="text-xl font-semibold">Ödeme başarıyla tamamlandı</h1>
        <p className="text-sm text-muted-foreground">Teşekkür ederiz. Rezervasyon tahsilatınız güncellenecektir.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1">
        <label className="text-xs font-medium text-muted-foreground">Kart Bilgileri</label>
        <div className="border rounded-md px-3 py-2 bg-background">
          <CardElement options={{ hidePostalCode: true }} />
        </div>
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <Button type="submit" className="w-full" disabled={submitting || !stripe}>
        {submitting ? "Ödeme işleniyor..." : "Ödemeyi Tamamla"}
      </Button>
    </form>
  );
}

export default function PublicClickToPayPage() {
  const { token } = useParams();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [tokenData, setTokenData] = useState(null);

  useEffect(() => {
    if (!token) return;

    async function loadToken() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/public/pay/${token}`);
        setTokenData(res.data || null);
      } catch (e) {
        setError(apiErrorMessage(e));
        setTokenData(null);
      } finally {
        setLoading(false);
      }
    }

    loadToken();
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <Card className="w-full max-w-md p-4 space-y-4">
        {loading ? (
          <div className="text-sm text-muted-foreground">Ödeme linki kontrol ediliyor...</div>
        ) : error ? (
          <ErrorState title="Ödeme linki geçerli değil" description={error} />
        ) : !tokenData ? (
          <EmptyState
            title="Ödeme linki bulunamadı"
            description="Bu ödeme linki hatalı veya süresi dolmuş olabilir. Lütfen operasyon ekibiyle iletişime geçin."
          />
        ) : (
          <>
            <div className="space-y-1">
              <h1 className="text-lg font-semibold">Ödeme Yap</h1>
              <p className="text-xs text-muted-foreground">
                Rezervasyon kodu <span className="font-mono">{tokenData.booking_code}</span> için aşağıdaki tutarı
                ödüyorsunuz.
              </p>
              <p className="text-base font-semibold">
                {formatAmount(tokenData.amount_cents, tokenData.currency)}
              </p>
            </div>

            {STRIPE_PUBLISHABLE_KEY ? (
              <Elements stripe={stripePromise} options={{ clientSecret: tokenData.client_secret }}>
                <ClickToPayForm token={token} tokenData={tokenData} />
              </Elements>
            ) : (
              <p className="text-xs text-red-600">
                Stripe publishable key yapılandırılmadığı için ödeme formu gösterilemiyor.
              </p>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
