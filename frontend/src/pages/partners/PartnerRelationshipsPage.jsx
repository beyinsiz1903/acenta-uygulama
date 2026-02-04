import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Users, Loader2, Filter } from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "../../components/ui/table";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { useToast } from "../../hooks/use-toast";
import { fetchRelationships } from "../../lib/partnerGraph";

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
      toast?.({ description: "ID panoya kopyalandı." });
    }
  } catch {
    // kritik değil
  }
}

export default function PartnerRelationshipsPage() {
  const { toast } = useToast();

  const [statusFilter, setStatusFilter] = useState([]); // invited/accepted/active/suspended/terminated
  const [role, setRole] = useState("any"); // any | seller | buyer

  const [items, setItems] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const hasNext = !!nextCursor;

  const statusOptions = [
    { value: "invited", label: "Davet" },
    { value: "accepted", label: "Kabul edildi" },
    { value: "active", label: "Aktif" },
    { value: "suspended", label: "Askıya alındı" },
    { value: "terminated", label: "Sonlandırıldı" },
  ];

  const toggleStatus = (value) => {
    setStatusFilter((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    );
  };

  const effectiveStatuses = useMemo(() => statusFilter, [statusFilter]);

  const loadFirstPage = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetchRelationships({
        statuses: effectiveStatuses,
        role,
        limit: 50,
        cursor: undefined,
      });
      setItems(res.items || []);
      setNextCursor(res.next_cursor || null);
    } catch (e) {
      const code = e?.raw?.response?.data?.error?.code;
      let msg = e?.message || "Partner ilişkileri yüklenirken bir hata oluştu.";
      if (code === "invalid_status") {
        msg = "Durum filtresi geçersiz. Lütfen sadece izin verilen statüleri seçin.";
      } else if (code === "invalid_role") {
        msg = "Rol filtresi geçersiz.";
      } else if (code === "invalid_cursor") {
        msg = "Sayfalama bilgisi geçersiz. Lütfen sayfayı yenileyin.";
      } else if (code === "tenant_header_missing") {
        msg = "Tenant seçimi gerekli. Lütfen geçerli bir tenant ile tekrar deneyin.";
      } else if (code === "invalid_token") {
        msg = "Oturum süreniz dolmuş olabilir. Lütfen tekrar giriş yapın.";
      }
      setError(msg);
      setItems([]);
      setNextCursor(null);
    } finally {
      setLoading(false);
    }
  }, [effectiveStatuses, role]);

  const loadMore = useCallback(async () => {
    if (!nextCursor) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetchRelationships({
        statuses: effectiveStatuses,
        role,
        limit: 50,
        cursor: nextCursor,
      });
      setItems((prev) => [...prev, ...(res.items || [])]);
      setNextCursor(res.next_cursor || null);
    } catch (e) {
      const msg = e?.message || "Ekstra sayfa yüklenirken bir hata oluştu.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [effectiveStatuses, role, nextCursor]);

  useEffect(() => {
    void loadFirstPage();
  }, [loadFirstPage]);

  const derivedItems = useMemo(() => {
    // V1: current tenant id backend'ten gelmediği için sadece role filtresine göre label türetiyoruz.
    return items.map((it) => {
      let roleLabel = "";
      if (role === "seller") {
        roleLabel = "Ben Satıcıyım";
      } else if (role === "buyer") {
        roleLabel = "Ben Alıcıyım";
      } else {
        roleLabel = ""; // any iken karışık olabilir
      }
      return {
        ...it,
        _role_label: roleLabel,
      };
    });
  }, [items, role]);

  const handleCopyId = async (id) => {
    if (!id) return;
    await copyToClipboard(id, toast);
  };

  const handleCopyTenant = async (tenantId) => {
    if (!tenantId) return;
    await copyToClipboard(tenantId, toast);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Users className="h-5 w-5" />
        <div>
          <h1 className="text-base font-semibold">Partner İlişkileri</h1>
          <p className="text-xs text-muted-foreground">
            Bu ekranda tüm B2B partner ilişkilerinizi görebilirsiniz. Davet, kabul ve aktif ilişkileri filtreleyin.
          </p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-sm font-medium">Filtreler</CardTitle>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
            <div className="flex flex-col gap-1">
              <span className="font-medium flex items-center gap-1">
                <Filter className="h-3 w-3" /> Durum
              </span>
              <div className="flex flex-wrap gap-1">
                {statusOptions.map((opt) => {
                  const active = statusFilter.includes(opt.value);
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => toggleStatus(opt.value)}
                      className={`h-6 rounded-full border px-2 text-[11px] ${
                        active
                          ? "bg-primary text-primary-foreground border-primary"
                          : "text-muted-foreground"
                      }`}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[11px] font-medium">Rol</span>
              <div className="inline-flex rounded-md border bg-background p-0.5 text-[11px]">
                <button
                  type="button"
                  className={`px-2 py-1 rounded-sm ${
                    role === "any" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                  }`}
                  onClick={() => setRole("any")}
                >
                  Tümü
                </button>
                <button
                  type="button"
                  className={`px-2 py-1 rounded-sm ${
                    role === "seller" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                  }`}
                  onClick={() => setRole("seller")}
                >
                  Ben satıcıyım
                </button>
                <button
                  type="button"
                  className={`px-2 py-1 rounded-sm ${
                    role === "buyer" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                  }`}
                  onClick={() => setRole("buyer")}
                >
                  Ben alıcıyım
                </button>
              </div>
            </div>

            <div className="flex gap-2 mt-2 sm:mt-5">
              <Button type="button" size="sm" disabled={loading} onClick={loadFirstPage}>
                {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                Uygula
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={loading && !items.length}
                onClick={() => {
                  setStatusFilter([]);
                  setRole("any");
                  setItems([]);
                  setNextCursor(null);
                  setError("");
                  void loadFirstPage();
                }}
              >
                Temizle
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mt-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2 flex items-center justify-between">
          <CardTitle className="text-sm font-medium">İlişki listesi</CardTitle>
          {loading && (
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>Yükleniyor…</span>
            </div>
          )}
        </CardHeader>
        <CardContent className="text-xs">
          {derivedItems.length === 0 && !loading ? (
            <p className="text-xs text-muted-foreground">Henüz partner ilişkisi bulunmuyor.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Relationship ID</TableHead>
                    <TableHead className="text-xs">Rol</TableHead>
                    <TableHead className="text-xs">Satıcı Tenant</TableHead>
                    <TableHead className="text-xs">Alıcı Tenant</TableHead>
                    <TableHead className="text-xs">Durum</TableHead>
                    <TableHead className="text-xs">Davet</TableHead>
                    <TableHead className="text-xs">Kabul</TableHead>
                    <TableHead className="text-xs">Aktif</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {derivedItems.map((it) => (
                    <TableRow key={it.id} className="hover:bg-muted/40">
                      <TableCell
                        className="text-xs font-mono cursor-pointer hover:underline"
                        title="Relationship ID'yi kopyala"
                        onClick={() => handleCopyId(it.id)}
                      >
                        {shortenId(it.id)}
                      </TableCell>
                      <TableCell className="text-xs">{it._role_label || ""}</TableCell>
                      <TableCell
                        className="text-xs font-mono cursor-pointer hover:underline"
                        title="Satıcı tenant ID'yi kopyala"
                        onClick={() => handleCopyTenant(it.seller_tenant_id)}
                      >
                        {it.seller_tenant_id || <span className="text-muted-foreground">-</span>}
                      </TableCell>
                      <TableCell
                        className="text-xs font-mono cursor-pointer hover:underline"
                        title="Alıcı tenant ID'yi kopyala"
                        onClick={() => handleCopyTenant(it.buyer_tenant_id)}
                      >
                        {it.buyer_tenant_id || <span className="text-muted-foreground">-</span>}
                      </TableCell>
                      <TableCell className="text-xs">
                        <Badge variant="outline">{it.status}</Badge>
                      </TableCell>
                      <TableCell className="text-xs">{formatDate(it.invited_at)}</TableCell>
                      <TableCell className="text-xs">{formatDate(it.accepted_at)}</TableCell>
                      <TableCell className="text-xs">{formatDate(it.activated_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <div className="mt-3 flex justify-end">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={!hasNext || loading}
              onClick={loadMore}
            >
              {loading && hasNext && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              Daha fazla yükle
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
