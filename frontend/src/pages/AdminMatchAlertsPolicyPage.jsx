import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { Switch } from "../components/ui/switch";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Loader2, AlertCircle } from "lucide-react";

export default function AdminMatchAlertsPolicyPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [runLoading, setRunLoading] = useState(false);
  const [policy, setPolicy] = useState({
    enabled: true,
    threshold_not_arrived_rate: 0.5,
    threshold_repeat_not_arrived_7: 3,
    min_matches_total: 5,
    cooldown_hours: 24,
    email_recipients: [],
    webhook_url: null,
  });
  const [recipientsInput, setRecipientsInput] = useState("");
  const [runParams, setRunParams] = useState({ days: 30, min_total: 5 });
  const [runResult, setRunResult] = useState(null);
  const [deliveries, setDeliveries] = useState([]);
  const [deliveriesLoading, setDeliveriesLoading] = useState(false);
  const [deliveriesFilter, setDeliveriesFilter] = useState({ status: "all", channel: "all", match_id: "" });
  const [riskProfile, setRiskProfile] = useState({
    rate_threshold: 0.5,
    repeat_threshold_7: 3,
    mode: "rate_or_repeat",
    updated_at: null,
    updated_by_email: null,
  });
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewHighRiskCount, setPreviewHighRiskCount] = useState(null);

  const loadPolicy = async () => {
    try {
      setLoading(true);
      setError("");
      const resp = await api.get("/admin/match-alerts/policy");
      const p = resp.data?.policy || {};
      setPolicy(p);
      setRecipientsInput((p.email_recipients || []).join(", "));
    } catch (e) {
      console.error("Match alerts policy fetch failed", e);
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };
  const loadDeliveries = async () => {
    try {
      setDeliveriesLoading(true);
      const resp = await api.get("/admin/match-alerts/deliveries", {
        params: {
          limit: 50,
          status: deliveriesFilter.status,
          match_id: deliveriesFilter.match_id || undefined,
          channel: deliveriesFilter.channel && deliveriesFilter.channel !== "all" ? deliveriesFilter.channel : undefined,
        },
      });
      setDeliveries(resp.data?.items || []);
    } catch (e) {
      console.error("Match alerts deliveries fetch failed", e);
      // Hata zaten üstteki error alanında gösterilebilir; burada swallow edebiliriz.
    } finally {
      setDeliveriesLoading(false);
    }
  };

  useEffect(() => {
    loadPolicy();
    loadDeliveries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError("");
      const recipients = recipientsInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

      const payload = {
        ...policy,
        email_recipients: recipients.length ? recipients : null,
      };

      await api.put("/admin/match-alerts/policy", payload);
      await loadPolicy();
    } catch (e) {
      console.error("Match alerts policy save failed", e);
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setRunResult(null);
    await loadPolicy();
  };

  const handleDryRun = async () => {
    try {
      setRunLoading(true);
      setError("");
      setRunResult(null);
      const resp = await api.post("/admin/match-alerts/run", null, {
        params: {
          days: runParams.days,
          min_total: runParams.min_total,
          dry_run: 1,
        },
      });
      setRunResult(resp.data || null);
    } catch (e) {
      console.error("Match alerts dry run failed", e);
      setError(apiErrorMessage(e));
    } finally {
      setRunLoading(false);
    }
  };

  if (loading) {
    return (
      <div
        className="flex items-center justify-center h-96"
        data-testid="admin-match-alerts-policy-page"
      >
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-match-alerts-policy-page">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Match Alerts Policy</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Match, konaklama gerçekleştiği anlamına gelmez; sadece acenta–otel eşleşmesi (pair) için risk sinyallerini
          özetler. Bu sayfa, yüksek riskli eşleşmeler için email alert davranışını kontrol etmenizi sağlar. Webhook
          entegrasyonları v1 ile gelecektir.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-destructive text-sm">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Policy</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="text-sm font-medium">Alerting aktif</div>
              <p className="text-xs text-muted-foreground">
                Enabled kapalıysa, hiçbir eşleşme için email alert üretilmez.
              </p>
            </div>
            <Switch
              checked={policy.enabled}
              onCheckedChange={(val) => setPolicy((prev) => ({ ...prev, enabled: Boolean(val) }))}
              data-testid="match-alerts-enabled"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1">
              <label htmlFor="threshold-rate" className="text-sm font-medium">
                Not-arrived / cancel rate eşiği
              </label>
              <Input
                id="threshold-rate"
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={policy.threshold_not_arrived_rate}
                onChange={(e) =>
                  setPolicy((prev) => ({
                    ...prev,
                    threshold_not_arrived_rate: parseFloat(e.target.value || "0"),
                  }))
                }
                data-testid="match-alerts-threshold-rate"
              />
              <p className="text-xs text-muted-foreground">
                0–1 arası oran. Örneğin 0.5 → %50 ve üzeri iptal/not-arrived oranı için alert üret.
              </p>
            </div>

            <div className="space-y-1">
              <label htmlFor="min-matches" className="text-sm font-medium">
                Minimum eşleşme sayısı
              </label>
              <Input
                id="min-matches"
                type="number"
                min="1"
                value={policy.min_matches_total}
                onChange={(e) =>
                  setPolicy((prev) => ({
                    ...prev,
                    min_matches_total: parseInt(e.target.value || "1", 10),
                  }))
                }
                data-testid="match-alerts-min-matches"
              />
              <p className="text-xs text-muted-foreground">
                Belirtilen dönem içinde toplam eşleşme sayısı bu değerden küçükse alert üretilmez.
              </p>
            </div>

            <div className="space-y-1">
              <label htmlFor="cooldown-hours" className="text-sm font-medium">
                Cooldown (saat)
              </label>
              <Input
                id="cooldown-hours"
                type="number"
                min="1"
                max="168"
                value={policy.cooldown_hours}
                onChange={(e) =>
                  setPolicy((prev) => ({
                    ...prev,
                    cooldown_hours: parseInt(e.target.value || "1", 10),
                  }))
                }
                data-testid="match-alerts-cooldown"
              />
              <p className="text-xs text-muted-foreground">
                Aynı match ve config için yeni alert üretmeden önce beklenecek minimum süre.
              </p>
            </div>

            <div className="space-y-1">
              <label htmlFor="recipients" className="text-sm font-medium">
                Email recipients
              </label>
              <Input
                id="recipients"
                placeholder="alerts@acenta.test, ops@acenta.test"
                value={recipientsInput}
                onChange={(e) => setRecipientsInput(e.target.value)}
                data-testid="match-alerts-recipients"
              />
              <p className="text-xs text-muted-foreground">
                Virgülle ayrılmış email listesi. Boş bırakırsan varsayılan olarak kendi email adresin kullanılır.
              </p>
            </div>

            <div className="space-y-1">
              <label htmlFor="repeat-threshold" className="text-sm font-medium">
                Repeat not-arrived (v1 placeholder)
              </label>
              <Input
                id="repeat-threshold"
                type="number"
                min="0"
                value={policy.threshold_repeat_not_arrived_7}
                onChange={(e) =>
                  setPolicy((prev) => ({
                    ...prev,
                    threshold_repeat_not_arrived_7: parseInt(e.target.value || "0", 10),
                  }))
                }
              />
              <p className="text-xs text-muted-foreground">
                Şimdilik sadece config olarak saklanır; v1 ile aktif hale gelecektir.
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label htmlFor="webhook-url" className="text-sm font-medium">
                  Webhook URL
                </label>
                <div className="flex items-center gap-2 text-xs">
                  <span>Enable webhook</span>
                  <Switch
                    checked={policy.webhook_enabled}
                    onCheckedChange={(val) =>
                      setPolicy((prev) => ({ ...prev, webhook_enabled: Boolean(val) }))
                    }
                    data-testid="match-alerts-webhook-enabled"
                  />
                </div>
              </div>
              <Input
                id="webhook-url"
                value={policy.webhook_url || ""}
                onChange={(e) =>
                  setPolicy((prev) => ({
                    ...prev,
                    webhook_url: e.target.value,
                  }))
                }
                placeholder="https://hooks.slack.com/..."
                data-testid="match-alerts-webhook-url"
              />
              <p className="text-xs text-muted-foreground">
                Webhook URL boş veya disabled ise webhook gönderilmez. Örn: Slack/Discord/Teams incoming webhook.
              </p>
            </div>

            <div className="space-y-1">
              <label htmlFor="webhook-secret" className="text-sm font-medium">
                Webhook Secret (opsiyonel)
              </label>
              <Input
                id="webhook-secret"
                type="password"
                value={policy.webhook_secret || ""}
                onChange={(e) =>
                  setPolicy((prev) => ({
                    ...prev,
                    webhook_secret: e.target.value || null,
                  }))
                }
                placeholder="İmza için gizli anahtar"
                data-testid="match-alerts-webhook-secret"
              />
              <p className="text-xs text-muted-foreground">
                Belirtilirse, payload imzalanır ve X-Syroce-Signature header&apos;ında sha256=hmac_hex olarak gönderilir.
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={async () => {
                  try {
                    setSaving(true);
                    setError("");
                    const resp = await api.post("/admin/match-alerts/webhook-test", {
                      webhook_url: policy.webhook_url,
                      webhook_secret: policy.webhook_secret,
                    });
                    const data = resp.data || {};
                    alert(
                      `Webhook test ok: status=${data.http_status} snippet=${(data.snippet || "").slice(
                        0,
                        80
                      )}`
                    );
                  } catch (e) {
                    console.error("Match alerts webhook test failed", e);
                    setError(apiErrorMessage(e));
                  } finally {
                    setSaving(false);
                  }
                }}
                data-testid="match-alerts-webhook-test"
              >
                Test Webhook
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-3 mt-4">
            <Button
              onClick={handleSave}
              disabled={saving}
              data-testid="match-alerts-save"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Kaydediliyor...
                </>
              ) : (
                "Kaydet"
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleReset}
              data-testid="match-alerts-reset"
            >
              Varsayılanlara dön
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dry Run</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">
              Dry run ile mevcut policy’e göre hangi eşleşmelerin alert tetikleyeceğini görebilirsin. Gerçek email
              gönderimi yapılmaz.
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={async () => {
                if (!window.confirm("Dry run değil. Email gönderilecek. Devam?")) return;
                try {
                  setRunLoading(true);
                  setError("");
                  const resp = await api.post("/admin/match-alerts/run", null, {
                    params: {
                      days: runParams.days,
                      min_total: runParams.min_total,
                      dry_run: 0,
                    },
                  });
                  const data = resp.data || {};
                  // Basit feedback
                  alert(
                    `Run Now tamamlandı. Sent: ${data.sent_count || 0}, Failed: ${
                      data.failed_count || 0
                    }`
                  );
                  // Son alertler listesini yenilemek için aşağıda deliveries fetch çağrısı yapılacak
                  await loadDeliveries();
                } catch (e) {
                  console.error("Match alerts run-now failed", e);
                  setError(apiErrorMessage(e));
                } finally {
                  setRunLoading(false);
                }
              }}
              data-testid="match-alerts-run-now"
            >
              Run Now (Send Emails)
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">
            Dry run ile mevcut policy’e göre hangi eşleşmelerin alert tetikleyeceğini görebilirsin. Gerçek email
            gönderimi yapılmaz.
          </p>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-1">
              <label htmlFor="run-days" className="text-sm font-medium">
                Gün (days)
              </label>
              <Input
                id="run-days"
                type="number"
                min="1"
                max="365"
                value={runParams.days}
                onChange={(e) =>
                  setRunParams((prev) => ({ ...prev, days: parseInt(e.target.value || "1", 10) }))
                }
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="run-min-total" className="text-sm font-medium">
                Min matches
              </label>
              <Input
                id="run-min-total"
                type="number"
                min="1"
                value={runParams.min_total}
                onChange={(e) =>
                  setRunParams((prev) => ({ ...prev, min_total: parseInt(e.target.value || "1", 10) }))
                }
              />
            </div>
          </div>

          <Button
            type="button"
            onClick={handleDryRun}
            disabled={runLoading}
            data-testid="match-alerts-dry-run"
          >
            {runLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Çalıştırılıyor...
              </>
            ) : (
              "Dry Run Çalıştır"
            )}
          </Button>

          {runResult && (
            <div className="mt-4 space-y-2" data-testid="match-alerts-dry-table">
              <div className="text-sm">
                <span className="font-medium">Evaluated:</span> {runResult.evaluated_count} ·
                <span className="font-medium ml-2">Triggered:</span> {runResult.triggered_count} ·
                <span className="font-medium ml-2">Sent:</span> {runResult.sent_count} ·
                <span className="font-medium ml-2">Failed:</span> {runResult.failed_count}
              </div>

              {(!runResult.items || runResult.items.length === 0) ? (
                <p className="text-sm text-muted-foreground">
                  Bu parametrelerle alert tetikleyen eşleşme bulunamadı.
                </p>
              ) : (
                <div className="overflow-x-auto mt-2">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-xs text-muted-foreground">
                        <th className="py-1 pr-2">Match ID</th>
                        <th className="py-1 pr-2">Acenta</th>
                        <th className="py-1 pr-2">Otel</th>
                        <th className="py-1 pr-2 text-right">Toplam</th>
                        <th className="py-1 pr-2 text-right">Cancel rate</th>
                        <th className="py-1 pr-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {runResult.items.slice(0, 20).map((item) => (
                        <tr key={item.match_id} className="border-b last:border-0">
                          <td className="py-1 pr-2 font-mono text-xs">{item.match_id}</td>
                          <td className="py-1 pr-2">{item.agency_name || item.agency_id}</td>
                          <td className="py-1 pr-2">{item.hotel_name || item.hotel_id}</td>
                          <td className="py-1 pr-2 text-right">{item.total_bookings}</td>
                          <td className="py-1 pr-2 text-right">{(item.cancel_rate * 100).toFixed(1)}%</td>
                          <td className="py-1 pr-2">{item.action_status || "none"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Son Alertler</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4" data-testid="match-alerts-deliveries-table">
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <div className="space-y-1">
              <label className="text-xs font-medium" htmlFor="deliveries-status">
                Status
              </label>
              <select
                id="deliveries-status"
                className="border rounded px-2 py-1 text-sm bg-background"
                value={deliveriesFilter.status}
                onChange={(e) =>
                  setDeliveriesFilter((prev) => ({ ...prev, status: e.target.value }))
                }
                data-testid="match-alerts-deliveries-status"
              >
                <option value="all">All</option>
                <option value="sent">Sent</option>
                <option value="failed">Failed</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium" htmlFor="deliveries-channel">
                Channel
              </label>
              <select
                id="deliveries-channel"
                className="border rounded px-2 py-1 text-sm bg-background"
                value={deliveriesFilter.channel || "all"}
                onChange={(e) =>
                  setDeliveriesFilter((prev) => ({ ...prev, channel: e.target.value }))
                }
                data-testid="match-alerts-deliveries-channel"
              >
                <option value="all">All</option>
                <option value="email">Email</option>
                <option value="webhook">Webhook</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium" htmlFor="deliveries-matchid">
                Match ID
              </label>
              <Input
                id="deliveries-matchid"
                placeholder="agency__hotel"
                value={deliveriesFilter.match_id}
                onChange={(e) =>
                  setDeliveriesFilter((prev) => ({ ...prev, match_id: e.target.value }))
                }
                className="h-8 text-xs"
                data-testid="match-alerts-deliveries-matchid"
              />
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={loadDeliveries}
              data-testid="match-alerts-deliveries-refresh"
            >
              Yenile
            </Button>
          </div>

          {deliveriesLoading ? (
            <p className="text-sm text-muted-foreground">Yükleniyor...</p>
          ) : deliveries.length === 0 ? (
            <p className="text-sm text-muted-foreground">Kayıtlı alert teslimatı bulunamadı.</p>
          ) : (
            <div className="overflow-x-auto mt-2">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="py-1 pr-2">Sent At</th>
                    <th className="py-1 pr-2">Match ID</th>
                    <th className="py-1 pr-2">Status</th>
                    <th className="py-1 pr-2">Channel</th>
                    <th className="py-1 pr-2">Error</th>
                    <th className="py-1 pr-2">Fingerprint</th>
                  </tr>
                </thead>
                <tbody>
                  {deliveries.map((d) => {
                    const fp = d.fingerprint || "";
                    const fpShort = fp.length > 12 ? `${fp.slice(0, 12)}…` : fp;
                    const status = d.status || "sent";
                    const statusClass =
                      status === "failed"
                        ? "text-red-600"
                        : "text-emerald-600";
                    return (
                      <tr key={`${d.match_id}-${d.sent_at}-${d.channel}`} className="border-b last:border-0">
                        <td className="py-1 pr-2 text-xs">
                          {d.sent_at ? new Date(d.sent_at).toLocaleString() : "-"}
                        </td>
                        <td className="py-1 pr-2 font-mono text-xs">{d.match_id}</td>
                        <td className="py-1 pr-2 text-xs">
                          <span className={statusClass}>{status}</span>
                        </td>
                        <td className="py-1 pr-2 text-xs">{d.channel}</td>
                        <td className="py-1 pr-2 text-xs max-w-[200px] truncate">
                          {d.error || "—"}
                        </td>
                        <td className="py-1 pr-2 text-xs font-mono">{fpShort}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
