import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Textarea } from "../components/ui/textarea";

const StatusBadge = ({ s }) => {
  if (!s) return <Badge variant="outline">-</Badge>;
  if (s === "active") return <Badge variant="secondary">active</Badge>;
  if (s === "archived") return <Badge variant="outline">archived</Badge>;
  return <Badge>{s}</Badge>;
};

function ProductForm({ value, onChange, onSave, saving, error }) {
  const v = value || {};
  return (
    <div className="space-y-3">
      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-2 text-xs text-destructive">
          {error}
        </div>
      )}
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Type</div>
          <select
            className="h-9 w-full rounded-md border bg-background px-2 text-sm"
            value={v.type || "hotel"}
            onChange={(e) => onChange({ ...v, type: e.target.value })}
          >
            <option value="hotel">hotel</option>
            <option value="tour">tour</option>
            <option value="transfer">transfer</option>
            <option value="activity">activity</option>
          </select>
        </div>

        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Status</div>
          <select
            className="h-9 w-full rounded-md border bg-background px-2 text-sm"
            value={v.status || "inactive"}
            onChange={(e) => onChange({ ...v, status: e.target.value })}
          >
            <option value="active">active</option>
            <option value="inactive">inactive</option>
            <option value="archived">archived</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Code</div>
          <Input
            value={v.code || ""}
            onChange={(e) => onChange({ ...v, code: e.target.value })}
          />
        </div>
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Currency</div>
          <Input
            value={v.default_currency || "EUR"}
            onChange={(e) =>
              onChange({ ...v, default_currency: (e.target.value || "").toUpperCase() })
            }
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Name (TR)</div>
          <Input
            value={(v.name && v.name.tr) || ""}
            onChange={(e) =>
              onChange({ ...v, name: { ...(v.name || {}), tr: e.target.value } })
            }
          />
        </div>
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Name (EN)</div>
          <Input
            value={(v.name && v.name.en) || ""}
            onChange={(e) =>
              onChange({ ...v, name: { ...(v.name || {}), en: e.target.value } })
            }
          />
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button disabled={saving} onClick={onSave} size="sm">
          {saving ? "Saving..." : "Save"}
        </Button>
      </div>
    </div>
  );
}

function VersionsPanel({ productId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [newJson, setNewJson] = useState(
    '{\n  "description": {"tr": "", "en": ""},\n  "amenities": [],\n  "room_type_ids": [],\n  "rate_plan_ids": []\n}'
  );

  const load = async () => {
    if (!productId) return;
    setLoading(true);
    setError("");
    try {
      const r = await api.get(`/admin/catalog/products/${productId}/versions`);
      setItems(r.data.items || []);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId]);

  const createDraft = async () => {
    setError("");
    try {
      const content = JSON.parse(newJson || "{}");
      await api.post(`/admin/catalog/products/${productId}/versions`, { content });
      await load();
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError("Content JSON geçerli değil.");
      } else {
        setError(apiErrorMessage(err));
      }
    }
  };

  const publish = async (versionId) => {
    setError("");
    try {
      await api.post(`/admin/catalog/products/${productId}/versions/${versionId}/publish`);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="font-semibold text-sm">Versions</div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-2 text-xs text-destructive">
          {error}
        </div>
      )}

      <div className="rounded-md border p-3 space-y-2">
        <div className="text-xs text-muted-foreground">
          Create draft version (content JSON)
        </div>
        <Textarea
          className="font-mono text-xs h-40"
          value={newJson}
          onChange={(e) => setNewJson(e.target.value)}
        />
        <div className="flex justify-end">
          <Button size="sm" onClick={createDraft}>
            Create Draft
          </Button>
        </div>
      </div>

      <div className="rounded-md border overflow-hidden">
        <div className="grid grid-cols-5 bg-muted/40 px-2 py-2 text-xs font-semibold">
          <div>Ver</div>
          <div>Status</div>
          <div>Created</div>
          <div>Published</div>
          <div />
        </div>
        <div className="max-h-64 overflow-y-auto text-xs">
          {items.map((v) => (
            <div key={v.version_id} className="grid grid-cols-5 px-2 py-2 border-t items-center">
              <div>{v.version}</div>
              <div>
                <StatusBadge s={v.status} />
              </div>
              <div className="truncate" title={String(v.created_at || "-")}>{
                String(v.created_at || "-").slice(0, 19)
              }</div>
              <div className="truncate" title={String(v.published_at || "-")}>{
                v.published_at ? String(v.published_at).slice(0, 19) : "-"
              }</div>
              <div className="text-right">
                {v.status !== "published" && (
                  <Button
                    size="xs"
                    className="h-7 px-2 text-[11px]"
                    onClick={() => publish(v.version_id)}
                  >
                    Publish
                  </Button>
                )}
              </div>
            </div>
          ))}
          {!items.length && (
            <div className="px-2 py-6 text-xs text-muted-foreground">No versions yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AdminCatalogPage() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);

  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");

  const [loading, setLoading] = useState(false);

  const [draft, setDraft] = useState({
    type: "hotel",
    code: "",
    name: { tr: "", en: "" },
    default_currency: "EUR",
    status: "inactive",
  });
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    setFormError("");
    try {
      const r = await api.get("/admin/catalog/products", {
        params: {
          q: q || undefined,
          type: type || undefined,
          status: status || undefined,
          limit: 50,
        },
      });
      setItems(r.data.items || []);
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const select = async (productId) => {
    setFormError("");
    try {
      const r = await api.get(`/admin/catalog/products/${productId}`);
      setSelected(r.data);
      setDraft(r.data);
    } catch (err) {
      setFormError(apiErrorMessage(err));
    }
  };

  const createNew = () => {
    setSelected(null);
    setFormError("");
    setDraft({
      type: "hotel",
      code: "",
      name: { tr: "", en: "" },
      default_currency: "EUR",
      status: "inactive",
    });
  };

  const save = async () => {
    setSaving(true);
    setFormError("");
    try {
      if (!selected?.product_id) {
        const r = await api.post("/admin/catalog/products", draft);
        await load();
        await select(r.data.product_id);
      } else {
        await api.put(`/admin/catalog/products/${selected.product_id}`, {
          type: draft.type,
          code: draft.code,
          name: draft.name,
          status: draft.status,
          default_currency: draft.default_currency,
        });
        await load();
        await select(selected.product_id);
      }
    } catch (err) {
      setFormError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold">Catalog</div>
          <div className="text-xs text-muted-foreground">
            Products + versioning + publish
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={createNew}>
          New Product
        </Button>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Left: list */}
        <div className="col-span-12 lg:col-span-5 rounded-lg border p-3 space-y-3">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <Input
              placeholder="Search..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <select
              className="h-9 rounded-md border bg-background px-2 text-xs"
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="">All types</option>
              <option value="hotel">hotel</option>
              <option value="tour">tour</option>
              <option value="transfer">transfer</option>
              <option value="activity">activity</option>
            </select>
            <select
              className="h-9 rounded-md border bg-background px-2 text-xs"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="">All status</option>
              <option value="active">active</option>
              <option value="inactive">inactive</option>
              <option value="archived">archived</option>
            </select>
          </div>

          <div className="flex justify-end">
            <Button
              size="sm"
              variant="outline"
              onClick={load}
              disabled={loading}
            >
              {loading ? "Loading..." : "Apply"}
            </Button>
          </div>

          <div className="rounded-md border overflow-hidden text-xs">
            <div className="grid grid-cols-6 bg-muted/40 px-2 py-2 font-semibold">
              <div className="col-span-2">Name</div>
              <div>Code</div>
              <div>Type</div>
              <div>Status</div>
              <div>Pub</div>
            </div>
            <div className="max-h-[60vh] overflow-y-auto">
              {items.map((p) => (
                <button
                  key={p.product_id}
                  type="button"
                  className={`w-full text-left grid grid-cols-6 px-2 py-2 border-t hover:bg-muted/30 ${
                    selected?.product_id === p.product_id ? "bg-muted/40" : ""
                  }`}
                  onClick={() => select(p.product_id)}
                >
                  <div
                    className="col-span-2 truncate"
                    title={p.name_tr || p.name_en || ""}
                  >
                    {p.name_tr || p.name_en || "-"}
                  </div>
                  <div className="truncate">{p.code}</div>
                  <div>{p.type}</div>
                  <div>
                    <StatusBadge s={p.status} />
                  </div>
                  <div>{p.published_version ?? "-"}</div>
                </button>
              ))}
              {!items.length && (
                <div className="px-2 py-6 text-xs text-muted-foreground">
                  No products.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: detail */}
        <div className="col-span-12 lg:col-span-7 rounded-lg border p-3 space-y-4">
          <div className="flex items-center justify-between">
            <div className="font-semibold text-sm">
              {selected ? "Product Detail" : "Create Product"}
            </div>
            {selected?.product_id && (
              <div className="text-[11px] text-muted-foreground">
                ID: <span className="font-mono">{selected.product_id}</span>
              </div>
            )}
          </div>

          <ProductForm
            value={draft}
            onChange={setDraft}
            onSave={save}
            saving={saving}
            error={formError}
          />

          {selected?.product_id && (
            <div className="pt-2 border-t">
              <VersionsPanel productId={selected.product_id} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
