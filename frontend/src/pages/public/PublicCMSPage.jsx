import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { Card } from "../../components/ui/card";
import { api, apiErrorMessage } from "../../lib/api";
import { useSeo } from "../../hooks/useSeo";

export default function PublicCMSPage() {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();

  const org = searchParams.get("org") || "";

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(null);

  useSeo({
    title: page?.seo_title || page?.title || "Sayfa",
    description: page?.seo_description || "",
    canonicalPath: slug ? `/p/${slug}` : "/p",
    type: "website",
  });

  useEffect(() => {
    if (!slug || !org) return;

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/public/cms/pages/${slug}`, { params: { org } });
        if (cancelled) return;
        setPage(res.data || null);
      } catch (e) {
        if (cancelled) return;
        setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [slug, org]);

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <Card className="w-full max-w-2xl p-4 space-y-4">
        {!org && (
          <p className="text-xs text-red-600">
            Kuruluş (org) parametresi eksik. Lütfen URL&apos;ye ?org=&lt;organization_id&gt; parametresi ekleyin.
          </p>
        )}

        {loading && <p className="text-xs text-muted-foreground">Sayfa yükleniyor...</p>}

        {error && !loading && (
          <p className="text-xs text-red-600">{error}</p>
        )}

        {page && !error && (
          <>
            <div className="space-y-1">
              <h1 className="text-xl font-semibold text-foreground">{page.title}</h1>
            </div>
            <div className="text-sm text-muted-foreground whitespace-pre-line">{page.body}</div>
          </>
        )}
      </Card>
    </div>
  );
}
