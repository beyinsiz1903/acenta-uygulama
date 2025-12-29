import React from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "./ui/sheet";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { api, apiErrorMessage } from "../lib/api";
import { Copy, RefreshCw, AlertCircle } from "lucide-react";

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

export function IntegrationDetailDrawer({ open, onOpenChange, integration, onRefresh }) {
  const [syncing, setSyncing] = React.useState(false);
  const [error, setError] = React.useState("");

  if (!integration) {
    return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="right" className="w-full sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>Channel Manager Entegrasyonu</SheetTitle>
          </SheetHeader>
          <div className="py-4 text-sm text-muted-foreground">
            Entegrasyon bilgisi yüklenemedi.
          </div>
        </SheetContent>
      </Sheet>
    );
  }

  const status = integration.status || "not_configured";
  const statusLabel = STATUS_LABELS[status] || status;

  const lastSync = integration.last_sync_at
    ? new Date(integration.last_sync_at).toLocaleString("tr-TR")
    : "-";
  const lastError = integration.last_error || "-";
  const config = integration.config || {};

  async function handleRetrySync() {
    setError("");
    setSyncing(true);
    try {
      await api.post("/hotel/integrations/channel-manager/sync");
      if (onRefresh) {
        await onRefresh();
      }
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setSyncing(false);
    }
  }

  function handleCopyDiagnostic() {
    const lines = [];
    lines.push(`Provider: ${integration.provider || "-"}`);
    lines.push(`Status: ${statusLabel}`);
    lines.push(`Last sync: ${lastSync}`);
    lines.push(`Last error: ${lastError}`);
    if (integration.updated_at) {
      lines.push(`Updated at: ${integration.updated_at}`);
    }
    if (typeof window !== "undefined") {
      const base = process.env.REACT_APP_BACKEND_URL || "";
      if (base) {
        lines.push(`Backend: ${base}`);
      }
    }

    const text = lines.join("\n");

    try {
      if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(text);
      } else {
        const el = document.createElement("textarea");
        el.value = text;
        el.style.position = "fixed";
        el.style.left = "-9999px";
        document.body.appendChild(el);
        el.select();
        document.execCommand("copy");
        document.body.removeChild(el);
      }
    } catch (e) {
      console.error("Copy diagnostic failed", e);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-lg flex flex-col">
        <SheetHeader>
          <SheetTitle>Channel Manager Entegrasyonu</SheetTitle>
          <SheetDescription>
            Kanal yöneticisi bağlantısı burada yönetilir. Credential bilgileri güvenli biçimde
            saklanır ve acenta tarafında hiçbir zaman gösterilmez.
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 mt-0.5" />
              <div>{error}</div>
            </div>
          )}

          <section className="space-y-2">
            <h3 className="text-sm font-medium">Durum & Sağlık</h3>
            <div className="flex items-center gap-2 text-sm">
              <Badge variant={statusVariant(status)}>{statusLabel}</Badge>
              <span className="text-xs text-muted-foreground">
                Provider: {integration.provider || "-"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs text-muted-foreground mt-2">
              <div>
                <div className="font-medium text-foreground mb-1">Son Senkron</div>
                <div>{lastSync}</div>
              </div>
              <div>
                <div className="font-medium text-foreground mb-1">Son Hata</div>
                <div className="break-words">{lastError}</div>
              </div>
            </div>
          </section>

          <section className="space-y-2 text-sm">
            <h3 className="text-sm font-medium">Konfigürasyon Özeti</h3>
            <div className="text-xs text-muted-foreground space-y-1">
              <div>
                <span className="font-medium text-foreground">Mode:</span> {config.mode || "pull"}
              </div>
              <div>
                <span className="font-medium text-foreground">Kanallar:</span>{" "}
                {config.channels && config.channels.length > 0
                  ? config.channels.join(", ")
                  : "-"}
              </div>
              {config.webhook_url && (
                <div>
                  <span className="font-medium text-foreground">Webhook URL:</span>{" "}
                  <span className="break-all">{config.webhook_url}</span>
                </div>
              )}
              {config.notes && (
                <div>
                  <span className="font-medium text-foreground">Notlar:</span>{" "}
                  {config.notes}
                </div>
              )}
            </div>
          </section>

          <section className="space-y-2 text-xs text-muted-foreground">
            <h3 className="text-sm font-medium text-foreground">Güvenlik</h3>
            <p>
              Credentials bilgileri güvenli bir şekilde saklanır (secrets_ref) ve bu ekranda
              gösterilmez. Gerekirse güvenlik ekibi ile iletişime geçebilirsiniz.
            </p>
            {integration.secrets_ref && (
              <p>
                <span className="font-medium text-foreground">Credential versiyon:</span>{" "}
                {integration.secrets_ref.version ?? 0}
              </p>
            )}
          </section>
        </div>

        <div className="pt-3 border-t flex items-center justify-between gap-2 mt-2">
          <div className="text-xs text-muted-foreground">
            Test Connection fonksiyonu FAZ-10.2 ile aktif olacaktır.
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyDiagnostic}
              className="gap-1"
            >
              <Copy className="h-3 w-3" />
              Copy Diagnostic
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetrySync}
              disabled={syncing || status === "not_configured"}
              className="gap-1"
            >
              {syncing && <LoaderMini />}
              Retry Sync
            </Button>
            <Button variant="outline" size="sm" disabled className="gap-1">
              Test Connection
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function LoaderMini() {
  return <RefreshCw className="h-3 w-3 animate-spin" />;
}
