import React, { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock3, RefreshCw } from "lucide-react";

import { getBillingHistory } from "../../lib/billing";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";

function formatTimelineDate(value) {
  if (!value) {
    return "Az önce";
  }

  try {
    return new Intl.DateTimeFormat("tr-TR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return String(value);
  }
}

function getToneUi(tone) {
  if (tone === "success") {
    return {
      icon: CheckCircle2,
      wrapperClass: "border-emerald-200 bg-emerald-50/80",
      iconClass: "border-emerald-200 bg-emerald-100 text-emerald-700",
      eyebrowClass: "text-emerald-700",
    };
  }

  if (tone === "warning") {
    return {
      icon: AlertTriangle,
      wrapperClass: "border-amber-200 bg-amber-50/80",
      iconClass: "border-amber-200 bg-amber-100 text-amber-700",
      eyebrowClass: "text-amber-700",
    };
  }

  return {
    icon: Clock3,
    wrapperClass: "border-sky-200 bg-sky-50/75",
    iconClass: "border-sky-200 bg-sky-100 text-sky-700",
    eyebrowClass: "text-sky-700",
  };
}

export const BillingHistoryTimeline = ({ refreshKey }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadHistory = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getBillingHistory();
      setItems(Array.isArray(data?.items) ? data.items : []);
    } catch (err) {
      setError(err?.message || "Faturalama geçmişi alınamadı.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory, refreshKey]);

  return (
    <Card className="rounded-[28px] border-border/60 bg-card/85" data-testid="billing-history-card">
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle data-testid="billing-history-title">Faturalama Geçmişi</CardTitle>
          <CardDescription data-testid="billing-history-description">
            Plan değişiklikleri, tahsilatlar ve ödeme uyarılarını tek akışta görün.
          </CardDescription>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void loadHistory()}
          disabled={loading}
          className="rounded-2xl"
          data-testid="billing-history-refresh-button"
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Geçmişi Yenile
        </Button>
      </CardHeader>

      <CardContent>
        {loading && !items.length ? (
          <div className="rounded-3xl border border-dashed border-border/70 bg-background/50 px-5 py-8 text-sm text-muted-foreground" data-testid="billing-history-loading">
            Faturalama olayları yükleniyor...
          </div>
        ) : null}

        {!loading && error ? (
          <div className="rounded-3xl border border-destructive/30 bg-destructive/5 px-5 py-4 text-sm text-destructive" data-testid="billing-history-error">
            {error}
          </div>
        ) : null}

        {!loading && !error && !items.length ? (
          <div className="rounded-3xl border border-dashed border-border/70 bg-background/50 px-5 py-8 text-sm text-muted-foreground" data-testid="billing-history-empty">
            Henüz gösterilecek bir faturalama olayı oluşmadı.
          </div>
        ) : null}

        {!loading && !error && items.length ? (
          <div className="space-y-4" data-testid="billing-history-list">
            {items.map((item) => {
              const toneUi = getToneUi(item.tone);
              const Icon = toneUi.icon;

              return (
                <article
                  key={item.id}
                  className={`grid gap-4 rounded-[24px] border px-5 py-4 sm:grid-cols-[auto_1fr] ${toneUi.wrapperClass}`}
                  data-testid={`billing-history-item-${item.id}`}
                >
                  <div
                    className={`flex h-11 w-11 items-center justify-center rounded-2xl border ${toneUi.iconClass}`}
                    data-testid={`billing-history-item-icon-${item.id}`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>

                  <div className="space-y-2">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className={`text-xs font-semibold uppercase tracking-[0.18em] ${toneUi.eyebrowClass}`} data-testid={`billing-history-item-tone-${item.id}`}>
                          {item.actor_type === "system" ? "Sistem Olayı" : "Kullanıcı İşlemi"}
                        </p>
                        <h3 className="mt-1 text-base font-semibold text-foreground" data-testid={`billing-history-item-title-${item.id}`}>
                          {item.title}
                        </h3>
                      </div>
                      <p className="text-sm text-muted-foreground" data-testid={`billing-history-item-date-${item.id}`}>
                        {formatTimelineDate(item.occurred_at)}
                      </p>
                    </div>

                    <p className="text-sm leading-6 text-foreground/85" data-testid={`billing-history-item-description-${item.id}`}>
                      {item.description}
                    </p>

                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground" data-testid={`billing-history-item-actor-${item.id}`}>
                      {item.actor_label}
                    </p>
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
};