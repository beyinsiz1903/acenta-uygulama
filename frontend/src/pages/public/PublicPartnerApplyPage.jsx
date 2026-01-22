import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { api, apiErrorMessage } from "../../lib/api";
import { useSeo } from "../../hooks/useSeo";

export default function PublicPartnerApplyPage() {
  const [searchParams] = useSearchParams();
  const org = searchParams.get("org") || "";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useSeo({
    title: "Partner Başvuru",
    description: "Syroce ağına partner olarak katılmak için başvuru formu.",
    canonicalPath: "/partners/apply",
    type: "website",
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess(false);

    if (!org) {
      setError("Kuruluş (org) parametresi eksik. Lütfen URL'ye ?org=<organization_id> ekleyin.");
      return;
    }
    if (!name.trim() || !email.trim()) {
      setError("İsim ve e-posta zorunludur.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/public/partners/apply", {
        name: name.trim(),
        email: email.trim(),
        message: message.trim(),
        org,
      });
      setSuccess(true);
      setName("");
      setEmail("");
      setMessage("");
    } catch (e2) {
      setError(apiErrorMessage(e2));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <Card className="w-full max-w-xl p-4 space-y-4">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">Partner Başvuru Formu</h1>
          <p className="text-xs text-muted-foreground">
            Syroce ağına ürünlerinizi veya hizmetlerinizi açmak için aşağıdaki formu doldurun. Ekibimiz
            başvurunuzu inceleyip sizinle iletişime geçecektir.
          </p>
          {!org && (
            <p className="text-[11px] text-red-600">
              Kuruluş (org) parametresi eksik. Lütfen URL'ye ?org=&lt;organization_id&gt; parametresi
              ekleyin.
            </p>
          )}
        </div>

        {error && <p className="text-xs text-red-600">{error}</p>}
        {success && (
          <p className="text-xs text-emerald-600">
            Başvurunuz alındı. Kısa süre içinde ekibimiz sizinle iletişime geçecek.
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div className="space-y-1">
            <Label htmlFor="name">Firma / Partner adı</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Örn: Demo Turizm AŞ"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="email">İletişim e-posta</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="partner@example.com"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="message">Mesaj / Not</Label>
            <Input
              id="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Kısaca iş modelinizi ve beklentinizi paylaşabilirsiniz (opsiyonel)."
            />
          </div>

          <div className="flex justify-end">
            <Button type="submit" size="sm" disabled={submitting}>
              {submitting ? "Gönderiliyor..." : "Başvuruyu Gönder"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
