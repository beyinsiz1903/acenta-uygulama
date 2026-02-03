import React, { useEffect, useState, useCallback } from "react";
import { Users, Loader2 } from "lucide-react";

import { fetchPartnerInbox, acceptPartnerRelationship, activatePartnerRelationship } from "../../lib/partnerGraph";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "../../components/ui/table";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { useToast } from "../../hooks/use-toast";

function StatusBadge({ status }) {
  const s = (status || "").toLowerCase();
  if (s === "active") {
    return <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">Aktif</Badge>;
  }
  if (s === "accepted") {
    return <Badge className="bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20">Kabul edildi</Badge>;
  }
  if (s === "invited") {
    return <Badge variant="outline">Davet gf6nderildi</Badge>;
  }
  if (s === "suspended") {
    return <Badge variant="outline" className="border-amber-500/40 text-amber-600 dark:text-amber-400">Askfya ald1ndd1</Badge>;
  }
  if (s === "terminated") {
    return <Badge variant="destructive">Sonlandfrfldf</Badge>;
  }
  return <Badge variant="outline">Bilinmiyor</Badge>;
}

function formatDate(value) {
  if (!value) return "-";
  try {
    const d = new Date(value);
    return d.toLocaleString("tr-TR");
  } catch {
    return value;
  }
}

function shortenId(id) {
  if (!id) return "-";
  if (id.length <= 10) return id;
  return `${id.slice(0, 6)}…${id.slice(-4)}`;
}
async function copyToClipboard(text, toast) {
  try {
    if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      if (toast) {
        toast({ description: "Relationship ID panoya kopyalandı." });
      }
    }
  } catch {
    // sessizce yut; kritik değil
  }
}


function ReceivedTable({ items, onAccept, busyId, onCopyId }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs">Relationship</TableHead>
            <TableHead className="text-xs">Karf1 Taraf (Satc4b1cd1 Tenant)</TableHead>
            <TableHead className="text-xs">Durum</TableHead>
            <TableHead className="text-xs">Tarih</TableHead>
            <TableHead className="text-xs text-right">Aksiyon</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((r) => {
            const canAccept = (r.status || "").toLowerCase() === "invited";
            const isBusy = busyId === r.id;
            return (
              <TableRow key={r.id} className="hover:bg-muted/40">
                <TableCell
                  className="text-xs font-mono cursor-pointer hover:underline"
                  title="ID'yi kopyala"
                  onClick={() => onCopyId && onCopyId(r.id)}
                >
                  {shortenId(r.id)}
                </TableCell>
                <TableCell className="text-xs font-mono">{r.seller_tenant_id || "-"}</TableCell>
                <TableCell className="text-xs">
                  <StatusBadge status={r.status} />
                </TableCell>
                <TableCell className="text-xs">{formatDate(r.created_at)}</TableCell>
                <TableCell className="text-xs text-right">
                  {canAccept ? (
                    <Button
                      type="button"
                      size="xs"
                      className="h-7 px-2 text-[11px]"
                      disabled={isBusy}
                      onClick={() => onAccept(r)}
                    >
                      {isBusy && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                      Kabul Et
                    </Button>
                  ) : (
                    <span className="text-[11px] text-muted-foreground">c4b1c5b1lem yok</span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

function SentTable({ items, onActivate, busyId, onCopyId }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs">Relationship</TableHead>
            <TableHead className="text-xs">Karf1 Taraf (Alc4b1cd1 Tenant)</TableHead>
            <TableHead className="text-xs">Durum</TableHead>
            <TableHead className="text-xs">Tarih</TableHead>
            <TableHead className="text-xs text-right">Aksiyon</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((r) => {
            const s = (r.status || "").toLowerCase();
            const canActivate = s === "accepted";
            const isBusy = busyId === r.id;
            return (
              <TableRow key={r.id} className="hover:bg-muted/40">
                <TableCell
                  className="text-xs font-mono cursor-pointer hover:underline"
                  title="ID'yi kopyala"
                  onClick={() => onCopyId && onCopyId(r.id)}
                >
                  {shortenId(r.id)}
                </TableCell>
                <TableCell className="text-xs font-mono">{r.buyer_tenant_id || "-"}</TableCell>
                <TableCell className="text-xs">
                  <StatusBadge status={r.status} />
                </TableCell>
                <TableCell className="text-xs">{formatDate(r.created_at)}</TableCell>
                <TableCell className="text-xs text-right">
                  {canActivate ? (
                    <Button
                      type="button"
                      size="xs"
                      className="h-7 px-2 text-[11px]"
                      disabled={isBusy}
                      onClick={() => onActivate(r)}
                    >
                      {isBusy && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                      Etkinle5ftir
                    </Button>
                  ) : (
                    <span className="text-[11px] text-muted-foreground">c4b1c5b1lem yok</span>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

export default function PartnerInboxPage() {
  const { toast } = useToast();
  const [data, setData] = useState({ invites_received: [], invites_sent: [], active_partners: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyRelationshipId, setBusyRelationshipId] = useState(null);
  const [tab, setTab] = useState("received");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetchPartnerInbox();
      setData({
        invites_received: res.invites_received || [],
        invites_sent: res.invites_sent || [],
        active_partners: res.active_partners || [],
      });
    } catch (e) {
      // apiErrorMessage metni e.message ie7ine gf6mcclfc geliyor
      setError(e?.message || "Bilinmeyen hata");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleAccept = async (rel) => {
    setBusyRelationshipId(rel.id);
    try {
      await acceptPartnerRelationship(rel.id);
      toast({ description: "Davet ba5far31yla kabul edildi." });
      await load();
    } catch (e) {
      toast({ variant: "destructive", description: e?.message || "Davet kabul edilirken hata olu5ftu." });
    } finally {
      setBusyRelationshipId(null);
    }
  };

  const handleActivate = async (rel) => {
    setBusyRelationshipId(rel.id);
    try {
      await activatePartnerRelationship(rel.id);
      toast({ description: "c4b1li5fki ba5far31yla etkinle5ftirildi." });
      await load();
    } catch (e) {
      toast({ variant: "destructive", description: e?.message || "c4b1li5fki etkinle5ftirilirken hata olu5ftu." });
    } finally {
      setBusyRelationshipId(null);
    }
  };

  const handleCopyId = async (id) => {
    await copyToClipboard(id, toast);
  };

  const hasReceived = (data.invites_received || []).length > 0;
  const hasSent = (data.invites_sent || []).length > 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Users className="h-5 w-5" />
        <div>
          <h1 className="text-base font-semibold">Partner Gelen Kutusu</h1>
          <p className="text-xs text-muted-foreground">
            B2B partner davetlerini buradan yf6netin. Gelen ve gf6nderilen davetleri gf6rfcp kabul / etkinle5ftirme
            i5flemlerini yapabilirsiniz.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-sm font-medium">Gelen Kutusu</CardTitle>
            <p className="text-[11px] text-muted-foreground">
              Tenant: <span className="font-mono text-foreground text-[11px]">{data.tenant_id || "-"}</span>
            </p>
          </div>
          {loading && (
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Yfckleniyor...</span>
            </div>
          )}
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-3 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
              {error.includes("401")
                ? "Oturum sfcreniz dolmu5f olabilir. Lfctfen tekrar giri5f yap31n."
                : error.includes("403")
                ? "Bu alana eri5fim yetkiniz yok."
                : error}
            </div>
          )}

          <Tabs value={tab} onValueChange={setTab} className="w-full">
            <TabsList className="grid grid-cols-2 max-w-xs">
              <TabsTrigger value="received">Gelen Davetler</TabsTrigger>
              <TabsTrigger value="sent">Gf6nderilen Davetler</TabsTrigger>
            </TabsList>

            <TabsContent value="received" className="mt-4">
              {!hasReceived && !loading ? (
                <p className="text-xs text-muted-foreground">Henfcz gelen davet yok.</p>
              ) : (
                <ReceivedTable
                  items={data.invites_received || []}
                  onAccept={handleAccept}
                  busyId={busyRelationshipId}
                  onCopyId={handleCopyId}
                />
              )}
            </TabsContent>

            <TabsContent value="sent" className="mt-4">
              {!hasSent && !loading ? (
                <p className="text-xs text-muted-foreground">Henfcz gf6nderilen davet yok.</p>
              ) : (
                <SentTable
                  items={data.invites_sent || []}
                  onActivate={handleActivate}
                  busyId={busyRelationshipId}
                />
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
