import React, { useEffect, useMemo, useState } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerDescription } from "../components/ui/drawer";
import { TableBody, TableCell, TableHead, TableHeader, TableRow, Table } from "../components/ui/table";
import { Button } from "../components/ui/button";

function StatusBadge({ status }) {
  if (status === "over_limit") {
    return <Badge variant="destructive">Limit aşıldı</Badge>;
  }
  if (status === "near_limit") {
    return <Badge variant="outline">Limite yakın</Badge>;
  }
  return <Badge variant="secondary">Uygun</Badge>;
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

function ExposureTable({ items, filter, statusFilter, onRowClick }) {
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
            <TableRow
              key={it.agency_id}
              className="cursor-pointer hover:bg-muted/50"
              onClick={() => onRowClick && onRowClick(it)}
            >
              <TableCell className="text-xs">
                <div className="flex flex-col">
                  <span className="font-medium truncate max-w-[200px]">{it.agency_name}</span>
                  <span className="text-[10px] text-muted-foreground font-mono">{it.agency_id}</span>
                </div>
              </TableCell>
              <TableCell className="text-xs text-right font-mono">
                {(it.exposure || 0).toFixed(2)} {it.currency}
              </TableCell>
              <TableCell className="text-xs text-right font-mono text-emerald-600">
                {(it.age_0_30 || 0).toFixed(2)}
              </TableCell>
              <TableCell className="text-xs text-right font-mono text-amber-600">
                {(it.age_31_60 || 0).toFixed(2)}
              </TableCell>
              <TableCell className="text-xs text-right font-mono text-red-600">
                {(it.age_61_plus || 0).toFixed(2)}
              </TableCell>
              <TableCell className="align-top">
                <AgingBar
                  age0={it.age_0_30 || 0}
                  age31={it.age_31_60 || 0}
                  age61={it.age_61_plus || 0}
                  exposure={it.exposure || 0}
                />
              </TableCell>
              <TableCell className="text-xs text-right font-mono">
                {(it.credit_limit || 0).toFixed(2)} {it.currency}
              </TableCell>
              <TableCell className="text-xs">
                <StatusBadge status={it.status} />
              </TableCell>
              <TableCell className="text-[10px] text-muted-foreground">
                {it.payment_terms}
              </TableCell>

function ExposureDrilldownDrawer({ open, onOpenChange, agency }) {
  const [bucket, setBucket] = useState("all");
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!open || !agency) return;
    let cancelled = false;
    const run = async () => {
      try {
        setLoading(true);
        setError("");
        setEntries([]);
        const params = new URLSearchParams();
        if (bucket) params.set("bucket", bucket);
        params.set("limit", "200");
        const res = await api.get(`/ops/finance/exposure/${agency.agency_id}/entries?${params.toString()}`);
        if (cancelled) return;
        setEntries(res.data?.items || []);
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
  }, [open, agency?.agency_id, bucket]);

  const filteredEntries = useMemo(() => {
    if (!search) return entries;
    const f = search.toLowerCase();
    return entries.filter((e) => {
      const fields = [e.booking_id, e.source_id, e.note].filter(Boolean).join(" ").toLowerCase();
      return fields.includes(f);
    });
  }, [entries, search]);

  const currency = agency?.currency || "";

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent>
        <DrawerHeader className="border-b pb-3">
          <DrawerTitle className="flex flex-col gap-1">
            <span className="text-sm font-semibold">
              {agency?.agency_name || "Seçili acente"}
            </span>
            <span className="text-[11px] text-muted-foreground font-mono">{agency?.agency_id}</span>
          </DrawerTitle>
          <DrawerDescription className="text-xs">
            Ledger bazlı hareketleri ve aging bucket&apos;lar[D[D[D[D[D[Dını acente seviyesinde inceleyin.
          </DrawerDescription>
        </DrawerHeader>
        <div className="p-4 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="inline-flex rounded-lg bg-muted p-1 text-[11px] text-muted-foreground">
              {["all", "0_30", "31_60", "61_plus"].map((b) => (
                <button
                  key={b}
                  type="button"
                  className={`px-2 py-1 rounded-md ${bucket === b ? "bg-background text-foreground shadow" : ""}`}
                  onClick={() => setBucket(b)}
                >
                  {b === "all" && "Tümü"}
                  {b === "0_30" && "0-30"}
                  {b === "31_60" && "31-60"}
                  {b === "61_plus" && "61+"}
                </button>
              ))}
            </div>
            <Input
              className="h-8 w-full sm:w-64 text-xs"
              placeholder="Booking ID / kaynak / not ara"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {loading && entries.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">Yükleniyor...</div>
          ) : error ? (
            <div className="space-y-2">
              <div className="text-xs text-destructive">{error}</div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="text-xs"
                onClick={() => {
                  // trigger refetch by toggling bucket
                  setBucket((prev) => (prev === "all" ? "0_30" : "all"));
                }}
              >
                Tekrar dene
              </Button>
            </div>
          ) : filteredEntries.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">
              Bu bucket için ledger kaydı bulunamadı.
            </div>
          ) : (
            <div className="overflow-x-auto max-h-[420px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-[11px]">Posted At</TableHead>
                    <TableHead className="text-[11px] text-right">Age (gün)</TableHead>
                    <TableHead className="text-[11px] text-right">Tutar</TableHead>
                    <TableHead className="text-[11px]">Yön</TableHead>
                    <TableHead className="text-[11px]">Kaynak</TableHead>
                    <TableHead className="text-[11px]">Booking</TableHead>
                    <TableHead className="text-[11px]">Not</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredEntries.map((e) => (
                    <TableRow key={e.ledger_entry_id} className="text-xs align-top">
                      <TableCell>{new Date(e.posted_at).toLocaleString()}</TableCell>
                      <TableCell className="text-right font-mono">{e.age_days}</TableCell>
                      <TableCell className="text-right font-mono">
                        {e.direction === "credit" ? "-" : "+"}
                        {e.amount.toFixed(2)} {currency}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-[10px]">
                          {e.direction} · {e.source_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-[11px]">
                        {e.source_id || "-"}
                      </TableCell>
                      <TableCell className="font-mono text-[11px]">
                        {e.booking_id ? (
                          <a
                            href={`/ops/bookings/${e.booking_id}`}
                            className="text-primary hover:underline"
                            target="_blank"
                            rel="noreferrer"
                          >
                            {e.booking_id}
                          </a>
                        ) : (
                          "-"
                        )}
                      </TableCell>
                      <TableCell className="max-w-[180px] truncate" title={e.note}>
                        {e.note || "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  );
}

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
  const [statusFilter, setStatusFilter] = useState("all");

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
              bucket&apos;larını gösterir.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-lg bg-muted p-1 text-[11px] text-muted-foreground">
              <button
                type="button"
                className={`px-2 py-1 rounded-md ${
                  statusFilter === "all" ? "bg-background text-foreground shadow" : ""
                }`}
                onClick={() => setStatusFilter("all")}
              >
                Tümü
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded-md ${
                  statusFilter === "near_limit" ? "bg-background text-foreground shadow" : ""
                }`}
                onClick={() => setStatusFilter("near_limit")}
              >
                Limite yakın
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded-md ${
                  statusFilter === "over_limit" ? "bg-background text-foreground shadow" : ""
                }`}
                onClick={() => setStatusFilter("over_limit")}
              >
                Limit aşıldı
              </button>
            </div>
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
            <ExposureTable items={items} filter={filter} statusFilter={statusFilter} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function AdminFinanceExposurePage() {
  return <AdminFinanceExposurePageInner />;
}
