import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, ClipboardCopy, RefreshCw, Search } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";

import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "../components/ui/sheet";

const ACTION_OPTIONS = [
  "booking.confirm",
  "booking.cancel",
  "booking.note",
  "booking.guest_note",
  "booking.cancel_request",
  "stop_sell.create",
  "stop_sell.update",
  "stop_sell.delete",
  "allocation.create",
  "allocation.update",
  "allocation.delete",
  "link.create",
  "link.update",
];

const TARGET_OPTIONS = [
  "booking",
  "stop_sell",
  "allocation",
  "agency_hotel_link",
];

function relativeTime(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  const diffMs = Date.now() - d.getTime();
  const sec = Math.floor(diffMs / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 48) return `${hr}h`;
  const day = Math.floor(hr / 24);
  return `${day}d`;
}

export default function AdminAuditLogsPage() {
  const [action, setAction] = useState("");
  const [targetType, setTargetType] = useState("");
  const [targetId, setTargetId] = useState("");
  const [actorEmail, setActorEmail] = useState("");
  const [range, setRange] = useState("24h");
  const [limit, setLimit] = useState(200);

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selected, setSelected] = useState(null);
  const [open, setOpen] = useState(false);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const params = { limit: Number(limit || 200) };
      if (action) params.action = action;
      if (targetType) params.target_type = targetType;
      if (targetId) params.target_id = targetId;
      if (actorEmail) params.actor_email = actorEmail;
      if (range) params.range = range;

      const resp = await api.get("/audit/logs", { params });
      setItems(resp.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const diffCount = (it) => {
    const diff = it?.diff || {};
    return Object.keys(diff).length;
  };

  const sorted = useMemo(() => {
    return [...(items || [])].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );
  }, [items]);

  async function openDetail(row) {
    // we already have full doc in list, but keep it simple
    setSelected(row);
    setOpen(true);
  }

  async function copyJson() {
    if (!selected) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(selected, null, 2));
    } catch {
      // fallback
      const textarea = document.createElement("textarea");
      textarea.value = JSON.stringify(selected, null, 2);
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Audit Logs</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Kritik operasyonları 30 saniyede bulun: kim ne yaptı?
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Yenile
          </Button>
        </div>
      </div>

      <div className="rounded-2xl border bg-card shadow-sm p-4">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <div className="grid gap-1 md:col-span-2">
            <div className="text-xs text-muted-foreground">Action</div>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={action}
              onChange={(e) => setAction(e.target.value)}
            >
              <option value="">Tümü</option>
              {ACTION_OPTIONS.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>

          <div className="grid gap-1 md:col-span-1">
            <div className="text-xs text-muted-foreground">Target Type</div>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={targetType}
              onChange={(e) => setTargetType(e.target.value)}
            >
              <option value="">Tümü</option>
              {TARGET_OPTIONS.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div className="grid gap-1 md:col-span-1">
            <div className="text-xs text-muted-foreground">Target ID</div>
            <Input value={targetId} onChange={(e) => setTargetId(e.target.value)} placeholder="uuid" />
          </div>

          <div className="grid gap-1 md:col-span-1">
            <div className="text-xs text-muted-foreground">Actor email</div>
            <Input value={actorEmail} onChange={(e) => setActorEmail(e.target.value)} placeholder="mail" />
          </div>

          <div className="grid gap-1 md:col-span-1">
            <div className="text-xs text-muted-foreground">Range</div>
            <select
              className="h-10 rounded-md border bg-background px-3 text-sm"
              value={range}
              onChange={(e) => setRange(e.target.value)}
            >
              <option value="">Tümü</option>
              <option value="24h">son 24 saat</option>
              <option value="7d">son 7 gün</option>
            </select>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2">
          <Button onClick={load} disabled={loading}>
            <Search className="h-4 w-4 mr-2" />
            Filtrele
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setAction("");
              setTargetType("");
              setTargetId("");
              setActorEmail("");
              setRange("24h");
              setLimit(200);
              setTimeout(load, 0);
            }}
            disabled={loading}
          >
            Sıfırla
          </Button>

          <div className="ml-auto flex items-center gap-2">
            <div className="text-xs text-muted-foreground">Limit</div>
            <Input
              className="w-24"
              type="number"
              min={1}
              max={500}
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
            />
          </div>
        </div>

        {error ? (
          <div className="mt-3 rounded-xl border border-destructive/50 bg-destructive/5 p-3 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
            <div className="text-sm text-foreground">{error}</div>
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl border bg-card shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Target</TableHead>
              <TableHead>Origin</TableHead>
              <TableHead>Diff</TableHead>
              <TableHead className="text-right">Detay</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : sorted.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-10 text-center text-sm text-muted-foreground">
                  Kayıt yok.
                </TableCell>
              </TableRow>
            ) : (
              sorted.map((it) => (
                <TableRow key={it.id} className="hover:bg-accent/40">
                  <TableCell title={it.created_at} className="font-mono text-xs">
                    {relativeTime(it.created_at)}
                  </TableCell>
                  <TableCell>
                    <div className="text-sm font-medium">{it.actor?.email || "-"}</div>
                    <div className="text-xs text-muted-foreground">{(it.actor?.roles || []).join(", ")}</div>
                  </TableCell>
                  <TableCell className="text-sm">
                    <Badge variant="secondary">{it.action}</Badge>
                  </TableCell>
                  <TableCell className="text-sm">
                    <div className="font-medium">{it.target?.type}</div>
                    <div className="text-xs text-muted-foreground font-mono">{it.target?.id}</div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    <div className="font-mono">{it.origin?.path}</div>
                    <div>{it.origin?.ip}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={diffCount(it) ? "default" : "secondary"}>
                      {diffCount(it)} alan
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="outline" size="sm" onClick={() => openDetail(it)}>
                      Aç
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Audit Detay</SheetTitle>
          </SheetHeader>

          {selected ? (
            <div className="mt-4 space-y-6">
              <div className="rounded-xl border bg-muted/30 p-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-xs text-muted-foreground">Action</div>
                    <div className="font-mono">{selected.action}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Created</div>
                    <div className="font-mono">{selected.created_at}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Actor</div>
                    <div className="font-mono">{selected.actor?.email || "-"}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Roles</div>
                    <div className="font-mono">{(selected.actor?.roles || []).join(", ")}</div>
                  </div>
                </div>

                <div className="mt-3 flex justify-end">
                  <Button variant="outline" onClick={copyJson}>
                    <ClipboardCopy className="h-4 w-4 mr-2" />
                    Copy as JSON
                  </Button>
                </div>
              </div>

              <div>
                <div className="text-sm font-semibold">Origin</div>
                <pre className="mt-2 text-xs rounded-xl border bg-background p-3 overflow-x-auto">
{JSON.stringify(selected.origin || {}, null, 2)}
                </pre>
              </div>

              <div>
                <div className="text-sm font-semibold">Diff</div>
                <pre className="mt-2 text-xs rounded-xl border bg-background p-3 overflow-x-auto">
{JSON.stringify(selected.diff || {}, null, 2)}
                </pre>
              </div>

              <div>
                <div className="text-sm font-semibold">Meta</div>
                <pre className="mt-2 text-xs rounded-xl border bg-background p-3 overflow-x-auto">
{JSON.stringify(selected.meta || {}, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="mt-6 text-sm text-muted-foreground">Seçim yok.</div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
