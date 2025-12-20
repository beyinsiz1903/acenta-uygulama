import React, { useEffect, useState } from "react";
import { Loader2, AlertCircle } from "lucide-react";

import { api, apiErrorMessage, getUser } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { IntegrationDetailDrawer } from "../components/IntegrationDetailDrawer";

const PROVIDERS = [
  { value: "channex", label: "Channex" },
  { value: "siteminder", label: "SiteMinder" },
  { value: "cloudbeds", label: "Cloudbeds" },
  { value: "hotelrunner", label: "HotelRunner" },
  { value: "custom", label: "Custom" },
];

const STATUS_LABELS = {
  not_configured: "Not Configured",
  configured: "Configured",
  connected: "Connected",
  error: "Error",
  disabled: "Disabled",
};

function statusVariant(status) {
  switch (status) {
    case "connected":
      return "default";
    case "configured":
      return "secondary";
    case "error":
      return "destructive";
    case "disabled":
      return "outline";
    case "not_configured":
    default:
      return "outline";
  }
}

export default function HotelIntegrationsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const user = getUser();

  const [provider, setProvider] = useState("");
  const [status, setStatus] = useState("not_configured");
  const [lastSyncAt, setLastSyncAt] = useState(null);
  const [lastError, setLastError] = useState(null);
  const [integration, setIntegration] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    load();
    // eslint-disable-next-line
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/hotel/integrations");
      const items = resp.data?.items || [];
      const cm = items[0] || null;

      if (cm) {
        setIntegration(cm);
        setProvider(cm.provider || "");
        setStatus(cm.status || "not_configured");
        setLastSyncAt(cm.last_sync_at || null);
        setLastError(cm.last_error || null);
      }
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setError("");

    if (status !== "not_configured" && !provider) {
      setError("Lütfen önce bir provider seçin.");
      return;
    }

    setSaving(true);
    try {
      await api.put("/hotel/integrations/channel-manager", {
        provider: provider || null,
        status,
        config: {
          mode: "pull",
          channels: [],
        },
      });
      await load();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <Card className="rounded-2xl border bg-card shadow-sm">
          <CardContent className="p-10 flex flex-col items-center justify-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <div className="text-sm text-muted-foreground">Entegrasyon bilgileri yükleniyor...</div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Entegrasyonlar</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Kanal yöneticisi bağlantınızı buradan yönetin. Credential bilgileri güvenli bir şekilde
          saklanır ve acenta tarafında gösterilmez.
        </p>
      </div>

      <Card className="rounded-2xl border bg-card shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base font-semibold">Channel Manager</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Channex, SiteMinder, Cloudbeds, HotelRunner veya özel entegrasyonlar için temel yapılandırma.
            </p>
          </div>
          <Badge variant={statusVariant(status)}>{STATUS_LABELS[status] || status}</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 mt-0.5" />
              <div>{error}</div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Provider
              </div>
              <Select value={provider} onValueChange={setProvider}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Seçiniz" />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Durum
              </div>
              <Select value={status} onValueChange={setStatus}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="not_configured">Not Configured</SelectItem>
                  <SelectItem value="configured">Configured</SelectItem>
                  <SelectItem value="connected">Connected</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                  <SelectItem value="disabled">Disabled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-muted-foreground">
            <div>
              <div className="font-medium mb-1">Son Senkron</div>
              <div>{lastSyncAt ? new Date(lastSyncAt).toLocaleString("tr-TR") : "-"}</div>
            </div>
            <div>
              <div className="font-medium mb-1">Son Hata</div>
              <div>{lastError || "-"}</div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="text-xs text-muted-foreground">
              Test bağlantı ve credential yönetimi bir sonraki fazda eklenecektir.
            </div>
            <div className="flex gap-2">
              <Button variant="outline" type="button" onClick={() => setDrawerOpen(true)}>
                Detay
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Kaydediliyor..." : "Kaydet"}
      <IntegrationDetailDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        integration={integration}
        onRefresh={load}
      />

              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
