import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Search, Users, Loader2 } from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Button } from "../../components/ui/button";
import { Textarea } from "../../components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../../components/ui/dialog";
import { useToast } from "../../hooks/use-toast";
import { searchTenants, invitePartnerBySlug } from "../../lib/partnerGraph";

function useDebouncedValue(value, delay) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = window.setTimeout(() => {
      setDebounced(value);
    }, delay);
    return () => window.clearTimeout(id);
  }, [value, delay]);

  return debounced;
}

export default function PartnerDiscoveryPage() {
  const { toast } = useToast();
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebouncedValue(query, 350);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);

  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteTarget, setInviteTarget] = useState(null);
  const [note, setNote] = useState("");
  const [inviteLoading, setInviteLoading] = useState(false);

  const minLengthMet = useMemo(() => debouncedQuery.trim().length >= 2, [debouncedQuery]);

  const load = useCallback(async () => {
    const q = debouncedQuery.trim();
    setError("");

    if (q.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const data = await searchTenants(q);
      setResults(Array.isArray(data) ? data.slice(0, 20) : []);
    } catch (e) {
      const msg = e?.message || "Arama sırasında bir hata oluştu.";
      setError(msg);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleOpenInvite = (tenant) => {
    setInviteTarget(tenant);
    setNote("");
    setInviteOpen(true);
  };

  const handleSendInvite = async (e) => {
    e.preventDefault();
    if (!inviteTarget?.slug) return;

    setInviteLoading(true);
    setError("");
    try {
      await invitePartnerBySlug(inviteTarget.slug, note);
      toast({ description: "Davet gönderildi." });
      setInviteOpen(false);
      // Inbox'a yönlendir
      if (typeof window !== "undefined") {
        window.location.href = "/app/partners/inbox";
      }
    } catch (err) {
      const code = err?.raw?.response?.data?.error?.code;
      let msg = err?.message || "Davet gönderilemedi. Tekrar deneyin.";
      if (code === "cannot_invite_self") {
        msg = "Kendinize davet gönderemezsiniz.";
      } else if (code === "tenant_not_found") {
        msg = "Tenant bulunamadı.";
      } else if (code === "tenant_inactive") {
        msg = "Tenant pasif, davet gönderilemez.";
      } else if (code === "insufficient_permissions") {
        msg = "Bu işlem için yetkiniz yok.";
      }
      toast({ variant: "destructive", description: msg });
    } finally {
      setInviteLoading(false);
    }
  };

  const showInitialHint = !debouncedQuery && !loading && results.length === 0 && !error;
  const showNoResults = minLengthMet && !loading && results.length === 0 && !error;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Users className="h-5 w-5" />
        <div>
          <h1 className="text-base font-semibold">Partner Keşfet</h1>
          <p className="text-xs text-muted-foreground">
            Diğer acenteleri arayın ve partnerlik daveti gönderin.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Tenant arama</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Tenant ara (slug veya isim)…"
                className="pl-8 h-8 text-xs"
              />
            </div>
            {loading && (
              <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>Aranıyor…</span>
              </div>
            )}
          </div>

          {query && query.trim().length < 2 && (
            <p className="text-[11px] text-muted-foreground">Arama için en az 2 karakter girin.</p>
          )}

          {error && (
            <p className="text-[11px] text-destructive">{error}</p>
          )}

          {showInitialHint && (
            <p className="text-[11px] text-muted-foreground">Bir tenant arayarak davet gönderebilirsin.</p>
          )}

          {showNoResults && (
            <p className="text-[11px] text-muted-foreground">Sonuç bulunamadı.</p>
          )}

          {results.length > 0 && (
            <div className="mt-2 space-y-1 max-h-80 overflow-y-auto">
              {results.map((t) => (
                <div
                  key={t.tenant_id || t.slug}
                  className="flex items-center justify-between rounded-md border bg-muted/40 px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="truncate text-xs font-medium">{t.name || t.slug}</div>
                    <div className="text-[11px] text-muted-foreground truncate font-mono">{t.slug}</div>
                  </div>
                  <Button
                    type="button"
                    size="xs"
                    className="h-7 px-3 text-[11px]"
                    onClick={() => handleOpenInvite(t)}
                  >
                    Davet Et
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={inviteOpen} onOpenChange={(open) => !inviteLoading && setInviteOpen(open)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Partner daveti gönder</DialogTitle>
            <DialogDescription className="text-xs">
              Seçili tenant’a B2B partnerlik daveti göndereceksiniz.
            </DialogDescription>
          </DialogHeader>

          {inviteTarget && (
            <form onSubmit={handleSendInvite} className="space-y-3 text-xs">
              <div className="space-y-0.5">
                <div className="font-medium truncate">{inviteTarget.name || inviteTarget.slug}</div>
                <div className="text-[11px] text-muted-foreground font-mono truncate">{inviteTarget.slug}</div>
              </div>

              <div className="space-y-1">
                <label className="text-[11px] font-medium" htmlFor="invite-note">
                  Not (opsiyonel)
                </label>
                <Textarea
                  id="invite-note"
                  value={note}
                  onChange={(e) => {
                    const v = e.target.value || "";
                    if (v.length <= 280) setNote(v);
                  }}
                  className="h-24 text-xs"
                  placeholder="Opsiyonel: bu davet için kısa bir not ekleyebilirsiniz (maks. 280 karakter)."
                />
                <div className="text-[10px] text-muted-foreground text-right">{note.length}/280</div>
              </div>

              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setInviteOpen(false)}
                  disabled={inviteLoading}
                >
                  Vazgeç
                </Button>
                <Button type="submit" size="sm" disabled={inviteLoading}>
                  {inviteLoading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                  Gönder
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
