import React, { useEffect, useMemo, useState } from "react";
import AdminLayout from "../layouts/AdminLayout";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";

function StatusBadge({ status }) {
  if (status === "over_limit") {
    return <Badge variant="destructive">Over limit</Badge>;
  }
  if (status === "near_limit") {
    return <Badge variant="outline">Near limit</Badge>;
  }
  return <Badge variant="secondary">OK</Badge>;
}

function AgingBar({ age0, age31, age61, exposure }) {
  const total = Math.abs(exposure) || 1;
  const p0 = Math.min(100, Math.max(0, (Math.abs(age0) / total) * 100));
  const p31 = Math.min(100, Math.max(0, (Math.abs(age31) / total) * 100));
  const p61 = Math.min(100, Math.max(0, (Math.abs(age61) / total) * 100));

  return (
    <div className="space-y-1">
      <div className="flex h-2 rounded-full overflow-hidden bg-muted">
        <div className="bg-emerald-500" style={{ width: `${p0}%` }} />
        <div className="bg-amber-500" style={{ width: `${p31}%` }} />
        <div className="bg-red-500" style={{ width: `${p61}%` }} />
      </div>
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>0–30d</span>
        <span>31–60d</span>
        <span>61+d</span>
      </div>
    </div>
  );
}

function ExposureTable({ items, filter, statusFilter }) {
  const filtered = useMemo(() => {
    let working = items;

    if (statusFilter && statusFilter !== "all") {
      working = working.filter((it) => it.status === statusFilter);
    }

    if (!filter) return working;
    const f = filter.toLowerCase();
    return working.filter(
      (it) => it.agency_name?.toLowerCase().includes(f) || it.agency_id?.toLowerCase().includes(f)
    );
  }, [items, filter, statusFilter]);

  if (!filtered.length) {
    return (
      <EmptyState
        title="Hiç acente yok"
        description="Bu organizasyon için tanımlı finans hesabı bulunamadı veya filtre çok dar."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs">Agency</TableHead>
            <TableHead className="text-xs text-right">Exposure</TableHead>
            <TableHead className="text-xs text-right">0–30</TableHead>
            <TableHead className="text-xs text-right">31–60</TableHead>
            <TableHead className="text-xs text-right">61+</TableHead>
            <TableHead className="text-xs">Aging</TableHead>
            <TableHead className="text-xs text-right">Limit</TableHead>
            <TableHead className="text-xs">Status</TableHead>
            <TableHead className="text-xs">Terms</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.map((it) => (
            <TableRow key={it.agency_id}>
              <TableCell className="text-xs">
                <div className="flex flex-col">
                  <span className="font-medium truncate max-w-[200px]">{it.agency_name}</span>
                  <span className="text-[10px] text-muted-foreground font-mono">{it.agency_id}</span>
                </div>
              </TableCell>
              <TableCell className="text-xs text-right font-mono">
                {it.exposure.toFixed(2)} {it.currency}
              </TableCell>
              <TableCell className="text-xs text-right font-mono text-emerald-600">
                {it.age_0_30.toFixed(2)}
              </TableCell>
              <TableCell className="text-xs text-right font-mono text-amber-600">
                {it.age_31_60.toFixed(2)}
              </TableCell>
              <TableCell className="text-xs text-right font-mono text-red-600">
                {it.age_61_plus.toFixed(2)}
              </TableCell>
              <TableCell className="align-top">
                <AgingBar
                  age0={it.age_0_30}
                  age31={it.age_31_60}
                  age61={it.age_61_plus}
                  exposure={it.exposure}
                />
              </TableCell>
              <TableCell className="text-xs text-right font-mono">
                {it.credit_limit.toFixed(2)} {it.currency}
              </TableCell>
              <TableCell className="text-xs">
                <StatusBadge status={it.status} />
              </TableCell>
              <TableCell className="text-[10px] text-muted-foreground">
                {it.payment_terms}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function AdminFinanceExposurePageInner() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        setLoading(true);
        setError("");
        const resp = await api.get("/ops/finance/exposure");
        if (cancelled) return;
        setItems(resp.data.items || []);
      } catch (e) {
        if (cancelled) return;
        setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-4">
      <PageHeader
        title="Agency Exposure & Aging"
        description="Acentelerin toplam maruziyeti ve tahsilat yaşlandırmasını tek ekranda gör."
      />

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-sm font-medium">Exposure summary</CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Bu tablo, ledger bazlı hareketlerden hesaplanan exposure ve yaşlandırma
              bucket'larını gösterir.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              className="h-8 w-56 text-xs"
              placeholder="Agency adı veya ID filtrele"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent>
          {loading && items.length === 0 ? (
            <div className="text-xs text-muted-foreground">Yükleniyor...</div>
          ) : error ? (
            <ErrorState title="Exposure yüklenemedi" description={error} />
          ) : (
            <ExposureTable items={items} filter={filter} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function AdminFinanceExposurePage() {
  return (
    <AdminLayout>
      <AdminFinanceExposurePageInner />
    </AdminLayout>
  );
}
