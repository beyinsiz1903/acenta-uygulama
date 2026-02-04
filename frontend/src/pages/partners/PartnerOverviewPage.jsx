import React, { useEffect, useState } from "react";
import { Users, Receipt, Link2 } from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { apiErrorMessage } from "../../lib/api";
import { fetchPartnerNotificationsSummary, fetchRelationships } from "../../lib/partnerGraph";
import { fetchSettlementStatement } from "../../lib/settlements";
import { Link } from "react-router-dom";

function formatDate(value) {
  if (!value) return "-";
  try {
    const d = new Date(value);
    return d.toLocaleString("tr-TR");
  } catch {
    return value;
  }
}

export default function PartnerOverviewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [summary, setSummary] = useState(null);
  const [relationships, setRelationships] = useState([]);
  const [statementInfo, setStatementInfo] = useState({ totalCount: 0, currencies: [] });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const now = new Date();
        const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

        const [summaryRes, relRes, stmtRes] = await Promise.all([
          fetchPartnerNotificationsSummary().catch((err) => {
            throw err;
          }),
          fetchRelationships({ role: "any", limit: 5 }).catch((err) => {
            throw err;
          }),
          fetchSettlementStatement({
            month,
            perspective: "seller",
            limit: 5,
          }).catch((err) => {
            throw err;
          }),
        ]);

        if (cancelled) return;

        setSummary(summaryRes || null);
        setRelationships(Array.isArray(relRes?.items) ? relRes.items.slice(0, 5) : []);

        const stmtCount = stmtRes?.totals?.count || 0;
        const currencies = Array.isArray(stmtRes?.currency_breakdown)
          ? stmtRes.currency_breakdown.slice(0, 2)
          : [];

        setStatementInfo({ totalCount: stmtCount, currencies });
      } catch (err) {
        if (cancelled) return;
        const code = err?.raw?.response?.data?.error?.code;
        let msg = apiErrorMessage(err);
        if (code === "tenant_header_missing") {
          msg = "Tenant seçimi gerekli. Partner modülü için geçerli bir tenant ile tekrar deneyin.";
        }
        setError(msg || "Partner genel bakış yüklenirken bir hata oluştu.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  const invitesReceived = summary?.counts?.invites_received ?? 0;
  const activePartners = summary?.counts?.active_partners ?? 0;

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h2 className="text-base font-semibold">Partners  Genel Bakış</h2>
        <p className="text-xs text-muted-foreground">
          Partner ekosisteminize genel bir bakış: bekleyen davetler, aktif ilişkiler ve mutabakat durumu.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs">
              <Users className="h-4 w-4" />
              <CardTitle className="text-sm font-medium">Bekleyen Davetler</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{invitesReceived}</div>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Partner ağınızdan size gelen ve henüz aksiyon alınmamış davetler.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs">
              <Users className="h-4 w-4" />
              <CardTitle className="text-sm font-medium">Aktif Partnerler</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{activePartners}</div>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Aktif durumda olan B2B partner ilişkilerinizin sayısı.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs">
              <Receipt className="h-4 w-4" />
              <CardTitle className="text-sm font-medium">Bu Ay Mutabakat</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="text-xs space-y-1">
            <div className="text-lg font-semibold">Toplam kayıt: {statementInfo.totalCount}</div>
            {statementInfo.currencies.length > 0 ? (
              <div className="space-y-0.5 text-[11px] text-muted-foreground">
                {statementInfo.currencies.map((c) => (
                  <div key={c.currency} className="flex items-center justify-between">
                    <span>{c.currency}</span>
                    <span>{c.count} kayıt</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[11px] text-muted-foreground">Bu ay için mutabakat özeti bulunamadı.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs">
            <Link2 className="h-4 w-4" />
            <CardTitle className="text-sm font-medium">Son İlişkiler</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="text-xs">
          {loading && !relationships.length ? (
            <p className="text-xs text-muted-foreground">Yükleniyor…</p>
          ) : relationships.length === 0 ? (
            <p className="text-xs text-muted-foreground">Henüz partner ilişkisi bulunmuyor.</p>
          ) : (
            <div className="space-y-1">
              {relationships.map((r) => (
                <div
                  key={r.id}
                  className="flex items-center justify-between rounded-md border bg-muted/40 px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="text-[11px] font-mono truncate">{r.id}</div>
                    <div className="text-[11px] text-muted-foreground">
                      Oluşturma: {formatDate(r.created_at)}
                    </div>
                  </div>
                  <Badge variant="outline" className="text-[10px]">
                    {r.status || "-"}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
