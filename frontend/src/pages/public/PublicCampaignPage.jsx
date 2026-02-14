import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";

import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import EmptyState from "../../components/EmptyState";
import { api, apiErrorMessage } from "../../lib/api";
import { useSeo } from "../../hooks/useSeo";

export default function PublicCampaignPage() {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const org = searchParams.get("org") || "";

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [campaign, setCampaign] = useState(null);

  useSeo({
    title: campaign?.name || "Kampanya",
    description: campaign?.description || "",
    canonicalPath: slug ? `/campaigns/${slug}` : "/campaigns",
    type: "website",
  });

  useEffect(() => {
    if (!slug || !org) return;

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/public/campaigns/${slug}`, { params: { org } });
        if (cancelled) return;
        setCampaign(res.data || null);
      } catch (e) {
        if (cancelled) return;
        setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [slug, org]);

  const handleStartBooking = () => {
    const qp = new URLSearchParams();
    if (org) qp.set("org", org);
    const qs = qp.toString();
    navigate(qs ? `/book?${qs}` : "/book");
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <Card className="w-full max-w-2xl p-4 space-y-4">
        {!org && (
          <p className="text-xs text-red-600">
            Kuruluş (org) parametresi eksik. Lütfen URL&apos;ye ?org=&lt;organization_id&gt; parametresi ekleyin.
          </p>
        )}

        {loading && <p className="text-xs text-muted-foreground">Kampanya yükleniyor...</p>}

        {error && !loading && (
          <EmptyState
            title="Kampanya bulunamadı"
            description={error}
            action={
              <div className="flex justify-center">
                <Button size="sm" onClick={handleStartBooking}>
                  Rezervasyon ara
                </Button>
              </div>
            }
          />
        )}

        {campaign && !error && (
          <>
            <div className="space-y-2">
              <h1 className="text-xl font-semibold text-foreground">{campaign.name}</h1>
              {campaign.description && (
                <p className="text-sm text-muted-foreground whitespace-pre-line">{campaign.description}</p>
              )}
            </div>

            {Array.isArray(campaign.coupon_codes) && campaign.coupon_codes.length > 0 && (
              <div className="space-y-1 text-xs">
                <div className="font-medium">Kampanya kupon kodları</div>
                <div className="flex flex-wrap gap-2">
                  {campaign.coupon_codes.map((code) => (
                    <span
                      key={code}
                      className="inline-flex items-center rounded-md border bg-muted px-2 py-1 font-mono text-xs"
                    >
                      {code}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  Rezervasyon adımında bu kodları kullanarak indiriminizi uygulayabilirsiniz.
                </p>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button size="sm" onClick={handleStartBooking}>
                Rezervasyon Başlat
              </Button>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
