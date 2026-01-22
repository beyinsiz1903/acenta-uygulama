import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Loader2, AlertCircle } from "lucide-react";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive">
      <AlertCircle className="h-4 w-4 mt-0.5" />
      <div>{text}</div>
    </div>
  );
}

function ContractsTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [code, setCode] = useState("");
  const [status, setStatus] = useState("draft");
  const [supplierId, setSupplierId] = useState("");
  const [agencyId, setAgencyId] = useState("");
  const [channelId, setChannelId] = useState("");
  const [markets, setMarkets] = useState("");
  const [productIds, setProductIds] = useState("");

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await api.get("/admin/pricing/contracts");
      setItems(res.data || []);
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const create = async () => {
    setErr("");
    try {
      await api.post("/admin/pricing/contracts", {
        code,
        status,
        supplier_id: supplierId || null,
        agency_id: agencyId || null,
        channel_id: channelId || null,
        markets: markets
          .split(",")
          .map((m) => m.trim().toUpperCase())
          .filter(Boolean),
        product_ids: productIds
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean),
      });
      setCode("");
      setSupplierId("");
      setAgencyId("");
      setChannelId("");
      setMarkets("");
      setProductIds("");
      await load();
    } catch (e) {
      setErr(apiErrorMessage(e));
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">Contracts</div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          {loading && <Loader2 className="h-3 w-3 animate-spin" />}
          Yenile
        </Button>
      </div>

      <FieldError text={err} />

      <div className="rounded-md border p-3 space-y-2 text-[11px]">
        <div className="grid grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Code</Label>
            <Input
              className="h-8 text-xs"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="CONTRACT_SUP1_AG1"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Status</Label>
            <select
              className="h-8 w-full rounded-md border bg-background px-2 text-xs"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="draft">draft</option>
              <option value="active">active</option>
              <option value="archived">archived</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Supplier ID</Label>
            <Input className="h-8 text-xs" value={supplierId} onChange={(e) => setSupplierId(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Agency ID</Label>
            <Input className="h-8 text-xs" value={agencyId} onChange={(e) => setAgencyId(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Channel ID</Label>
            <Input className="h-8 text-xs" value={channelId} onChange={(e) => setChannelId(e.target.value)} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Markets (comma-separated)</Label>
            <Input
              className="h-8 text-xs"
              value={markets}
              onChange={(e) => setMarkets(e.target.value)}
              placeholder="TR,DE"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Product IDs (comma-separated)</Label>
            <Input
              className="h-8 text-xs"
              value={productIds}
              onChange={(e) => setProductIds(e.target.value)}
              placeholder="prod_1,prod_2"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button size="sm" className="h-8 text-xs" onClick={create} disabled={loading}>
            Sözleşme Oluştur
          </Button>
        </div>
      </div>

      <div className="rounded-md border overflow-hidden text-[11px]">
        <div className="grid grid-cols-7 bg-muted/40 px-2 py-2 font-semibold">
          <div>Code</div>
          <div>Supplier</div>
          <div>Agency</div>
          <div>Channel</div>
          <div>Markets</div>
          <div>Status</div>
          <div>Created</div>
        </div>
        <div className="max-h-64 overflow-y-auto">
          {items.map((c) => (
            <div key={c.contract_id} className="grid grid-cols-7 border-t px-2 py-2">
              <div className="font-mono truncate" title={c.code}>{c.code}</div>
              <div className="truncate" title={c.supplier_id || ""}>{c.supplier_id || "-"}</div>
              <div className="truncate" title={c.agency_id || ""}>{c.agency_id || "-"}</div>
              <div className="truncate" title={c.channel_id || ""}>{c.channel_id || "-"}</div>
              <div className="truncate" title={(c.markets || []).join(", ")}>{(c.markets || []).join(", ") || "-"}</div>
              <div><Badge variant={c.status === "active" ? "secondary" : "outline"}>{c.status}</Badge></div>
              <div>{c.created_at ? String(c.created_at).slice(0, 19) : "-"}</div>
            </div>
          ))}
          {!items.length && (
            <div className="px-2 py-3 text-[11px] text-muted-foreground">No contracts.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function RateGridsTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [contractId, setContractId] = useState("");
  const [productId, setProductId] = useState("");
  const [ratePlanId, setRatePlanId] = useState("");
  const [roomTypeId, setRoomTypeId] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [rowsJson, setRowsJson] = useState(
    '[\n  {"valid_from":"2025-06-01","valid_to":"2025-06-30","min_los":1,"max_los":14,"occupancy":2,"board":"BB","base_net":100}\n]'
  );

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await api.get("/admin/pricing/rate-grids", {
        params: {
          product_id: productId || undefined,
          rate_plan_id: ratePlanId || undefined,
        },
      });
      setItems(res.data || []);
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const create = async () => {
    setErr("");
    try {
      const rows = JSON.parse(rowsJson || "[]");
      await api.post("/admin/pricing/rate-grids", {
        contract_id: contractId,
        product_id: productId,
        rate_plan_id: ratePlanId,
        room_type_id: roomTypeId || null,
        currency,
        status: "active",
        rows,
      });
      await load();
    } catch (e) {
      if (e instanceof SyntaxError) setErr("Rows JSON geçerli değil.");
      else setErr(apiErrorMessage(e));
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">Rate tabloları</div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          {loading && <Loader2 className="h-3 w-3 animate-spin" />}
          Yenile
        </Button>
      </div>

      <FieldError text={err} />

      <div className="rounded-md border p-3 space-y-2 text-[11px]">
        <div className="grid grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Contract ID</Label>
            <Input className="h-8 text-xs" value={contractId} onChange={(e) => setContractId(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Product ID</Label>
            <Input className="h-8 text-xs" value={productId} onChange={(e) => setProductId(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Rate Plan ID</Label>
            <Input className="h-8 text-xs" value={ratePlanId} onChange={(e) => setRatePlanId(e.target.value)} />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Room Type ID</Label>
            <Input className="h-8 text-xs" value={roomTypeId} onChange={(e) => setRoomTypeId(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Currency</Label>
            <Input className="h-8 text-xs" value={currency} onChange={(e) => setCurrency(e.target.value)} />
          </div>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px]">Rows (JSON)</Label>
          <Textarea
            className="font-mono text-[11px] min-h-[100px]"
            value={rowsJson}
            onChange={(e) => setRowsJson(e.target.value)}
          />
        </div>

        <div className="flex justify-end">
          <Button size="sm" className="h-8 text-xs" onClick={create} disabled={loading}>
            Grid Oluştur
          </Button>
        </div>
      </div>

      <div className="rounded-md border overflow-hidden text-[11px]">
        <div className="grid grid-cols-5 bg-muted/40 px-2 py-2 font-semibold">
          <div>Product</div>
          <div>Rate Plan</div>
          <div>Room</div>
          <div>Currency</div>
          <div>Rows</div>
        </div>
        <div className="max-h-64 overflow-y-auto">
          {items.map((g) => (
            <div key={g.grid_id} className="grid grid-cols-5 border-t px-2 py-2">
              <div className="truncate" title={g.product_id}>{g.product_id}</div>
              <div className="truncate" title={g.rate_plan_id}>{g.rate_plan_id}</div>
              <div className="truncate" title={g.room_type_id || ""}>{g.room_type_id || "-"}</div>
              <div>{g.currency}</div>
              <div>{g.rows?.length ?? 0} rows</div>
            </div>
          ))}
          {!items.length && (
            <div className="px-2 py-3 text-[11px] text-muted-foreground">No grids.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function RulesTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [code, setCode] = useState("");
  const [status, setStatus] = useState("draft");
  const [priority, setPriority] = useState(100);
  const [scopeJson, setScopeJson] = useState(
    '{"markets":["DE"],"product_ids":[],"rate_plan_ids":[]}'
  );
  const [actionJson, setActionJson] = useState(
    '{"type":"markup","mode":"percent","value":10}'
  );

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await api.get("/admin/pricing/rules");
      setItems(res.data || []);
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const create = async () => {
    setErr("");
    try {
      const scope = JSON.parse(scopeJson || "{}");
      const action = JSON.parse(actionJson || "{}");
      await api.post("/admin/pricing/rules", {
        code,
        status,
        priority: Number(priority || 0),
        scope,
        action,
      });
      setCode("");
      await load();
    } catch (e) {
      if (e instanceof SyntaxError) setErr("Scope/Action JSON geçerli değil.");
      else setErr(apiErrorMessage(e));
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">Rules</div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          {loading && <Loader2 className="h-3 w-3 animate-spin" />}
          Yenile
        </Button>
      </div>

      <FieldError text={err} />

      <div className="rounded-md border p-3 space-y-2 text-[11px]">
        <div className="grid grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Code</Label>
            <Input
              className="h-8 text-xs"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="RULE_DE_SUMMER"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Status</Label>
            <select
              className="h-8 w-full rounded-md border bg-background px-2 text-xs"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="draft">draft</option>
              <option value="active">active</option>
              <option value="archived">archived</option>
            </select>
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Priority</Label>
            <Input
              type="number"
              className="h-8 text-xs"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Scope (JSON)</Label>
            <Textarea
              className="font-mono text-[11px] min-h-[100px]"
              value={scopeJson}
              onChange={(e) => setScopeJson(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Action (JSON)</Label>
            <Textarea
              className="font-mono text-[11px] min-h-[100px]"
              value={actionJson}
              onChange={(e) => setActionJson(e.target.value)}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button size="sm" className="h-8 text-xs" onClick={create} disabled={loading}>
            Create Rule
          </Button>
        </div>
      </div>

      <div className="rounded-md border overflow-hidden text-[11px]">
        <div className="grid grid-cols-5 bg-muted/40 px-2 py-2 font-semibold">
          <div>Code</div>
          <div>Status</div>
          <div>Priority</div>
          <div>Scope</div>
          <div>Action</div>
        </div>
        <div className="max-h-64 overflow-y-auto">
          {items.map((r) => (
            <div key={r.rule_id} className="grid grid-cols-5 border-t px-2 py-2">
              <div className="font-mono truncate" title={r.code}>{r.code}</div>
              <div>{r.status}</div>
              <div>{r.priority}</div>
              <div className="truncate" title={JSON.stringify(r.scope)}>
                {JSON.stringify(r.scope).slice(0, 40)}...
              </div>
              <div className="truncate" title={JSON.stringify(r.action)}>
                {JSON.stringify(r.action).slice(0, 40)}...
              </div>
            </div>
          ))}
          {!items.length && (
            <div className="px-2 py-3 text-[11px] text-muted-foreground">No rules.</div>
          )}
        </div>
      </div>
    </div>
  );
}
function parseDateSafe(value) {
  if (!value) return null;
  try {
    const s = String(value).slice(0, 10);
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    let d;
    if (m) {
      const y = Number(m[1]);
      const mo = Number(m[2]) - 1;
      const da = Number(m[3]);
      d = new Date(y, mo, da);
    } else {
      d = new Date(value);
    }
    if (Number.isNaN(d.getTime())) return null;
    d.setHours(0, 0, 0, 0);
    return d;
  } catch {
    return null;
  }
}

function classifyValidity(validity, now) {
  if (!validity || !validity.from) return "no_validity";
  const from = parseDateSafe(validity.from);
  const to = validity.to ? parseDateSafe(validity.to) : null;
  if (!from) return "no_validity";

  if (now < from) return "upcoming";
  if (!to) return "active_now";
  if (now >= from && now < to) return "active_now";
  return "expired";
}

function markupLevel(action) {
  if (!action || typeof action.value === "undefined" || action.value === null) {
    return "na";
  }
  const v = Number(action.value);
  if (!Number.isFinite(v)) return "na";
  if (v >= 20) return "high";
  if (v >= 10) return "medium";
  if (v >= 0) return "low";
  return "na";
}

function ValidityRangeBadge({ kind }) {
  if (!kind) return null;
  let label = "";
  let cls = "border text-[9px] px-1.5 py-0.5 rounded-full";

  if (kind === "active_now") {
    label = "ACTIVE NOW";
    cls += " bg-emerald-100 text-emerald-800 border-emerald-200";
  } else if (kind === "upcoming") {
    label = "UPCOMING";
    cls += " bg-sky-100 text-sky-800 border-sky-200";
  } else if (kind === "expired") {
    label = "EXPIRED";
    cls += " bg-slate-100 text-slate-700 border-slate-200";
  } else {
    label = "NO VALIDITY";
    cls += " bg-amber-100 text-amber-800 border-amber-200";
  }

  return <span className={cls}>{label}</span>;
}

function shortJson(obj, n = 40) {
  try {
    const s = JSON.stringify(obj ?? {});
    return s.length > n ? `${s.slice(0, n)}...` : s;
  } catch {
    return "{}";
  }
}


function MarkupLevelBadge({ level }) {
  if (!level) return null;
  let label = "";
  let cls = "border text-[9px] px-1.5 py-0.5 rounded-full";

  if (level === "high") {
    label = "HIGH";
    cls += " bg-amber-100 text-amber-900 border-amber-200";
  } else if (level === "medium") {
    label = "MEDIUM";
    cls += " bg-blue-100 text-blue-900 border-blue-200";
  } else if (level === "low") {
    label = "LOW";
    cls += " bg-emerald-100 text-emerald-900 border-emerald-200";
  } else {
    label = "N/A";
    cls += " bg-slate-100 text-slate-700 border-slate-200";
  }

  return <span className={cls}>{label}</span>;
}



function SimpleRulesTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const [priority, setPriority] = useState(100);
  const [agencyId, setAgencyId] = useState("");
  const [productId, setProductId] = useState("");
  const [productType, setProductType] = useState("hotel");
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [value, setValue] = useState("10");
  const [notes, setNotes] = useState("");

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await api.get("/admin/pricing/rules/simple");
      setItems(res.data || []);
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const toDate = (value) => {
    if (!value) return null;
    try {
      return value.slice(0, 10);
    } catch {
      return null;
    }
  };

  const create = async () => {
    setErr("");
    setSaving(true);
    try {
      const from = toDate(validFrom);
      const to = toDate(validTo);
      if (!from || !to) {
        setErr("Geçerlilik başlangıç ve bitiş tarihleri zorunludur.");
        setSaving(false);
        return;
      }

      const payload = {
        priority: Number(priority || 0),
        scope: {
          agency_id: agencyId || null,
          product_id: productId || null,
          product_type: productType || null,
        },
        validity: {
          from,
          to,
        },
        action: {
          type: "markup_percent",
          value: Number(value) || 0,
        },
        notes: notes || null,
      };

      await api.post("/admin/pricing/rules/simple", payload);
      setAgencyId("");
      setProductId("");
      setProductType("hotel");
      setValidFrom("");
      setValidTo("");
      setValue("10");
      setNotes("");
      await load();
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const toggleStatus = async (rule) => {
    setErr("");
    setSaving(true);
    try {
      const nextStatus = rule.status === "active" ? "inactive" : "active";
      await api.put(`/admin/pricing/rules/${rule.rule_id}`, {
        status: nextStatus,
      });
      await load();
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">Simple Rules (markup %)</div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          {loading && <Loader2 className="h-3 w-3 animate-spin" />}
          Yenile
        </Button>
      </div>

      <FieldError text={err} />

      <div className="rounded-md border p-3 space-y-2 text-[11px]">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Priority</Label>
            <Input
              type="number"
              className="h-8 text-xs"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Agency ID (opsiyonel)</Label>
            <Input
              className="h-8 text-xs"
              value={agencyId}
              onChange={(e) => setAgencyId(e.target.value)}
              placeholder="agency_1"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Product ID (opsiyonel)</Label>
            <Input
              className="h-8 text-xs"
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              placeholder="product_1"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Product Type</Label>
            <select
              className="h-8 w-full rounded-md border bg-background px-2 text-xs"
              value={productType}
              onChange={(e) => setProductType(e.target.value)}
            >
              <option value="hotel">hotel</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <div className="space-y-1">
            <Label className="text-[11px]">Geçerlilik Başlangıç</Label>
            <Input
              type="date"
              className="h-8 text-xs"
              value={validFrom}
              onChange={(e) => setValidFrom(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Geçerlilik Bitiş</Label>
            <Input
              type="date"
              className="h-8 text-xs"
              value={validTo}
              onChange={(e) => setValidTo(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Markup %</Label>
            <Input
              type="number"
              className="h-8 text-xs"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="10"
            />
          </div>
        </div>

        <div className="space-y-1">
          <Label className="text-[11px]">Notlar</Label>
          <Textarea
            className="font-sans text-[11px] min-h-[60px]"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Örn: B2B portal için genel %10 markup"
          />
        </div>

        <div className="flex justify-end">
          <Button size="sm" className="h-8 text-xs" onClick={create} disabled={saving}>
            {saving && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
            Kural Oluştur
          </Button>
        </div>
      </div>

      <div className="rounded-md border overflow-hidden text-[11px]">
        <div className="grid grid-cols-8 bg-muted/40 px-2 py-2 font-semibold">
          <div>ID</div>
          <div>Name</div>
          <div>Status</div>
          <div>Priority</div>
          <div>Scope</div>
          <div>Action</div>
          <div>Geçerlilik</div>
          <div>Range</div>
        </div>
        <div className="max-h-64 overflow-y-auto">
          {items.map((r) => {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const validityKind = classifyValidity(r.validity, today);
            const level = markupLevel(r.action);

            const ruleName = (r.notes && String(r.notes).trim()) ||
              (typeof r.priority !== "undefined" ? `priority=${r.priority}` : "");

            let rowBg = "";
            if (validityKind === "active_now") rowBg = "bg-emerald-50";
            else if (validityKind === "upcoming") rowBg = "bg-sky-50";
            else if (validityKind === "expired") rowBg = "bg-slate-50 opacity-80";
            else rowBg = "bg-amber-50";

            const cls = [
              "grid grid-cols-8 border-t px-2 py-2 items-center",
              rowBg,
            ]
              .filter(Boolean)
              .join(" ");

            const dimClass = r.status !== "active" ? "opacity-70" : "";

            return (
              <div
                key={r.rule_id}
                className={cls}
                data-testid={`simple-rule-row-${r.rule_id}`}
              >
                <div className={`font-mono truncate ${dimClass}`} title={r.rule_id}>
                  {r.rule_id}
                </div>
                <div className={`truncate text-[11px] ${dimClass}`} title={ruleName || ""}>
                  {ruleName || <span className="text-muted-foreground">(no name)</span>}
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={r.status === "active" ? "secondary" : "outline"}>{r.status}</Badge>
                  <Button
                    size="xs"
                    variant="outline"
                    className="h-6 text-[10px]"
                    onClick={() => toggleStatus(r)}
                    disabled={saving}
                  >
                    {r.status === "active" ? "Pasifleştir" : "Aktifleştir"}
                  </Button>
                </div>
                <div className={dimClass}>{r.priority}</div>
                <div className={`truncate ${dimClass}`} title={JSON.stringify(r.scope)}>
                  {shortJson(r.scope)}
                </div>
                <div className={`truncate ${dimClass}`} title={JSON.stringify(r.action)}>
                  {shortJson(r.action)}
                </div>
                <div className={`truncate ${dimClass}`} title={JSON.stringify(r.validity)}>
                  {r.validity?.from} → {r.validity?.to}
                </div>
                <div className="flex flex-col gap-1 text-[10px]">
                  <div data-testid={`validity-badge-${r.rule_id}`}>
                    <ValidityRangeBadge kind={validityKind} />
                  </div>
                  <div data-testid={`markup-badge-${r.rule_id}`}>
                    <MarkupLevelBadge level={level} />
                  </div>
                </div>
              </div>
            );
          })}
          {!items.length && (
            <div className="px-2 py-3 text-[11px] text-muted-foreground">Henüz simple rule yok.</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AdminPricingPage() {
  const [activeTab, setActiveTab] = useState("contracts");

  const tabs = [
    { key: "contracts", label: "Contracts" },
    { key: "grids", label: "Rate Grids" },
    { key: "rules", label: "Rules (v2)" },
    { key: "simple_rules", label: "Simple Rules" },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold">Pricing</div>
          <div className="text-[11px] text-muted-foreground">
            Contracts + rate grids + rules (v2 skeleton)
          </div>
        </div>
      </div>

      <div className="flex gap-2 border-b pb-2 text-[11px]">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setActiveTab(t.key)}
            className={`rounded-md px-2 py-1 border ${
              activeTab === t.key
                ? "border-primary text-primary"
                : "border-muted text-muted-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "contracts" && <ContractsTab />}
      {activeTab === "grids" && <RateGridsTab />}
      {activeTab === "rules" && <RulesTab />}
      {activeTab === "simple_rules" && <SimpleRulesTab />}
    </div>
  );
}
