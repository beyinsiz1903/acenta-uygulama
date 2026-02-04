import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Users, Loader2, Filter } from "lucide-react";

import { fetchPartnerInbox } from "../../lib/partnerGraph";
import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "../../components/ui/table";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { useToast } from "../../hooks/use-toast";

function StatusBadge({ status }) {
  const s = (status || "").toLowerCase();
  if (s === "invited") {
    return <Badge variant="outline">Davet gönderildi</Badge>;
  }
  if (s === "accepted") {
    return <Badge className="bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20">Kabul edildi</Badge>;
  }
  if (s === "active") {
    return <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">Aktif</Badge>;
  }
  if (s === "suspended") {
    return <Badge variant="outline" className="border-amber-500/40 text-amber-600 dark:text-amber-400">Askıya alındı</Badge>;
  }
  if (s === "terminated") {
    return <Badge variant="destructive">Sonlandırıldı</Badge>;
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
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      toast?.({ description: "Relationship ID panoya kopyalandı." });
    }
  } catch {
    // kritik değil
  }
}

export default function PartnerInvitesPage() {
  const { toast } = useToast();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [roleFilter, setRoleFilter] = useState("all"); // all | received | sent

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetchPartnerInbox();
      const received = Array.isArray(res.invites_received) ? res.invites_received : [];
      const sent = Array.isArray(res.invites_sent) ? res.invites_sent : [];

      const normalised = [
        ...received.map((r) => {
          const createdAt = r.invited_at || r.created_at || null;
          return {
            id: r.id,
            direction: "received",
            role: "buyer", // ben alıcıyım, karşı taraf satıcı
            role_label: "Bana gelen davet",
            counterparty_tenant_id: r.seller_tenant_id || null,
            status: r.status || "invited",
            created_at: createdAt,
          };
        }),
        ...sent.map((r) => {
          const createdAt = r.invited_at || r.created_at || null;
          return {
            id: r.id,
            direction: "sent",
            role: "seller",
            role_label: "Benim gönderdiğim davet",
            counterparty_tenant_id: r.buyer_tenant_id || null,
            status: r.status || "invited",
            created_at: createdAt,
          };
        }),
      ];

      // created_at desc için sıralayalım
      normalised.sort((a, b) => {
        const da = a.created_at ? new Date(a.created_at).getTime() : 0;
        const db = b.created_at ? new Date(b.created_at).getTime() : 0;
        return db - da;
      });

      setItems(normalised);
    } catch (e) {
      setError(e?.message || "Davetler yüklenirken bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredItems = useMemo(() => {
    if (roleFilter === "received") {
      return items.filter((it) => it.direction === "received");
    }
    if (roleFilter === "sent") {
      return items.filter((it) => it.direction === "sent");
    }
    return items;
  }, [items, roleFilter]);

  const handleCopyId = async (id) => {
    if (!id) return;
    await copyToClipboard(id, toast);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Users className="h-5 w-5" />
        <div>
          <h1 className="text-base font-semibold">Partner Davetleri</h1>
          <p className="text-xs text-muted-foreground">
            Bu ekranda aldığınız ve gönderdiğiniz B2B partner davetlerini görebilirsiniz. Aktif partnerler sonraki
            sürümde eklenecek.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-sm font-medium">Davet listesi</CardTitle>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
            <div className="inline-flex items-center gap-1">
              <Filter className="h-3 w-3" />
              <span>Rol:</span>
              <select
                className="h-7 rounded-md border bg-background px-2 text-[11px]"
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
              >
                <option value="all">Tümü</option>
                <option value="received">Bana gelen</option>
                <option value="sent">Benim gönderdiğim</option>
              </select>
            </div>
            <Button type="button" variant="outline" size="xs" onClick={load} disabled={loading}>
              {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              Yenile
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-3 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
              {error}
            </div>
          )}

          {!loading && filteredItems.length === 0 && !error ? (
            <p className="text-xs text-muted-foreground">
              Henüz herhangi bir partner daveti bulunmuyor. Keşfet &amp; Davet Et ekranından yeni davetler gönderebilirsiniz.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Relationship ID</TableHead>
                    <TableHead className="text-xs">Yön</TableHead>
                    <TableHead className="text-xs">Karşı taraf Tenant</TableHead>
                    <TableHead className="text-xs">Durum</TableHead>
                    <TableHead className="text-xs">Tarih</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredItems.map((it) => (
                    <TableRow key={it.id} className="hover:bg-muted/40">
                      <TableCell
                        className="text-xs font-mono cursor-pointer hover:underline"
                        title="ID'yi kopyala"
                        onClick={() => handleCopyId(it.id)}
                      >
                        {shortenId(it.id)}
                      </TableCell>
                      <TableCell className="text-xs">
                        {it.direction === "received" ? "Bana gelen davet" : "Benim gönderdiğim davet"}
                      </TableCell>
                      <TableCell className="text-xs font-mono">
                        {it.counterparty_tenant_id || <span className="text-muted-foreground">-</span>}
                      </TableCell>
                      <TableCell className="text-xs">
                        <StatusBadge status={it.status} />
                      </TableCell>
                      <TableCell className="text-xs">{formatDate(it.created_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
