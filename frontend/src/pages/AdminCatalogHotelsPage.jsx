import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Textarea } from "../components/ui/textarea";

const StatusBadge = ({ s }) => {
  if (!s) return <Badge variant="outline">-</Badge>;
  if (s === "active") return <Badge variant="secondary">Aktif</Badge>;
  if (s === "archived") return <Badge variant="outline">Arşivlendi</Badge>;
  return <Badge>{s}</Badge>;
};

function HotelForm({ value, onChange, onSave, saving, error }) {
  const v = value || {};
  const loc = v.location || {};
  return (
    <div className="space-y-3">
      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-2 text-xs text-destructive">
          {error}
        </div>
      )}
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Durum</div>
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
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Varsayılan para birimi</div>
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
          <div className="text-xs text-muted-foreground">Kod</div>
          <Input
            value={v.code || ""}
            onChange={(e) => onChange({ ...v, code: e.target.value })}
          />
        </div>
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Name (TR)</div>
          <Input
            value={(v.name && v.name.tr) || ""}
            onChange={(e) =>
              onChange({ ...v, name: { ...(v.name || {}), tr: e.target.value } })
            }
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Name (EN)</div>
          <Input
            value={(v.name && v.name.en) || ""}
            onChange={(e) =>
              onChange({ ...v, name: { ...(v.name || {}), en: e.target.value } })
            }
          />
        </div>
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">City</div>
          <Input
            value={loc.city || ""}
            onChange={(e) =>
              onChange({
                ...v,
                location: { ...(v.location || {}), city: e.target.value },
              })
            }
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Country</div>
          <Input
            value={loc.country || ""}
            onChange={(e) =>
              onChange({
                ...v,
                location: { ...(v.location || {}), country: e.target.value },
              })
            }
          />
        </div>
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Notes (optional)</div>
          <Textarea
            className="h-9 text-xs"
            value={v.notes || ""}
            onChange={(e) => onChange({ ...v, notes: e.target.value })}
          />
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button disabled={saving} onClick={onSave} size="sm">
          {saving ? "Kaydediliyor..." : "Kaydet"}
        </Button>
      </div>
    </div>
  );
}

function RatePlansPanel({ productId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState({
    code: "",
    name: { tr: "", en: "" },
    board: "BB",
    currency: "EUR",
    base_net_price: 0,
    status: "active",
    payment_type: "postpay",
  });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    if (!productId) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.get(`/admin/catalog/rate-plans`, {
        params: { product_id: productId },
      });
      setItems(res.data || []);
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

  const save = async () => {
    if (!productId) return;
    setSaving(true);
    setError("");
    try {
      await api.post(`/admin/catalog/rate-plans`, {
        ...draft,
        product_id: productId,
      });
      setDraft({
        code: "",
        name: { tr: "", en: "" },
        board: "BB",
        currency: "EUR",
        base_net_price: 0,
        status: "active",
        payment_type: "postpay",
      });
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">Rate planlar</div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          {loading ? "Yükleniyor..." : "Yenile"}
        </Button>
      </div>
      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-2 text-xs text-destructive">
          {error === "Not Found" ? "Otel kataloğu verileri alınırken bir hata oluştu. Lütfen daha sonra tekrar deneyin." : error}
        </div>
      )}
      <div className="rounded-md border overflow-hidden text-xs">
        <div className="grid grid-cols-6 bg-muted/40 px-2 py-2 font-semibold">
          <div>Code</div>
          <div>Name</div>
          <div>Board</div>
          <div>Currency</div>
          <div className="text-right">Net</div>
          <div>Status</div>
        </div>
        <div className="max-h-56 overflow-y-auto">
          {items.map((rp) => (
            <div key={rp.rate_plan_id} className="grid grid-cols-6 px-2 py-2 border-t items-center">
              <div className="truncate">{rp.code}</div>
              <div className="truncate">{(rp.name && (rp.name.tr || rp.name.en)) || "-"}</div>
              <div>{rp.board}</div>
              <div>{rp.currency || "EUR"}</div>
              <div className="text-right">{(rp.base_net_price ?? 0).toFixed(2)}</div>
              <div>
                <StatusBadge s={rp.status || "active"} />
              </div>
            </div>
          ))}
          {!items.length && (
            <div className="px-2 py-4 text-xs text-muted-foreground">Henüz rate plan tanımlı değil.</div>
          )}
        </div>
      </div>

      <div className="rounded-md border p-3 space-y-2">
        <div className="text-xs font-semibold">New rate plan</div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Code</div>
            <Input
              value={draft.code}
              onChange={(e) => setDraft({ ...draft, code: e.target.value })}
            />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Board</div>
            <select
              className="h-8 rounded-md border bg-background px-2 text-xs"
              value={draft.board}
              onChange={(e) => setDraft({ ...draft, board: e.target.value })}
            >
              <option value="RO">RO</option>
              <option value="BB">BB</option>
              <option value="HB">HB</option>
              <option value="FB">FB</option>
              <option value="AI">AI</option>
            </select>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Name (TR)</div>
            <Input
              value={draft.name.tr}
              onChange={(e) => setDraft({ ...draft, name: { ...draft.name, tr: e.target.value } })}
            />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Name (EN)</div>
            <Input
              value={draft.name.en}
              onChange={(e) => setDraft({ ...draft, name: { ...draft.name, en: e.target.value } })}
            />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Base net price (EUR)</div>
            <Input
              type="number"
              min={0}
              step="0.01"
              value={draft.base_net_price}
              onChange={(e) =>
                setDraft({ ...draft, base_net_price: Number(e.target.value) || 0 })
              }
            />
          </div>
        </div>
        <div className="flex justify-end">
          <Button size="sm" onClick={save} disabled={saving}>
            {saving ? "Saving..." : "Create"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function AdminCatalogHotelsPage() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [draft, setDraft] = useState({
    type: "hotel",
    code: "",
    name: { tr: "", en: "" },
    default_currency: "EUR",
    status: "inactive",
    location: { city: "", country: "" },
  });

  const load = async () => {
    setLoading(true);
    setFormError("");
    try {
      const res = await api.get("/admin/catalog/products", {
        params: {
          q: q || undefined,
          type: "hotel",
          status: status || undefined,
          limit: 50,
        },
      });
      setItems(res.data.items || []);
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
      setDraft({
        ...r.data,
        type: "hotel",
        location: r.data.location || { city: "", country: "" },
      });
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
      location: { city: "", country: "" },
    });
  };

  const save = async () => {
    setSaving(true);
    setFormError("");
    try {
      // Simple client-side guard for required hotel fields
      if (!draft.name?.tr && !draft.name?.en) {
        throw new Error("Name (TR veya EN) zorunlu.");
      }
      if (!draft.location?.city || !draft.location?.country) {
        throw new Error("City ve Country zorunlu.");
      }

      if (!selected?.product_id) {
        const r = await api.post("/admin/catalog/products", draft);
        await load();
        await select(r.data.product_id);
      } else {
        await api.put(`/admin/catalog/products/${selected.product_id}`, {
          type: "hotel",
          code: draft.code,
          name: draft.name,
          status: draft.status,
          default_currency: draft.default_currency,
          location: draft.location,
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
          <div className="text-lg font-semibold">Catalog / Hotels</div>
          <div className="text-xs text-muted-foreground">
            Hotel products + basic rate plans
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={createNew}>
          New Hotel
        </Button>
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-5 rounded-lg border p-3 space-y-3">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <Input
              placeholder="Search by name..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
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
            <Button
              size="sm"
              variant="outline"
              onClick={load}
              disabled={loading}
            >
              {loading ? "Loading..." : "Apply"}
            </Button>
          </div>

          <div className="rounded-md border overflow-hidden text-xs mt-2">
            <div className="grid grid-cols-6 bg-muted/40 px-2 py-2 font-semibold">
              <div className="col-span-2">Name</div>
              <div>City</div>
              <div>Country</div>
              <div>Status</div>
              <div>Code</div>
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
                  <div className="truncate">{p.location?.city || "-"}</div>
                  <div className="truncate">{p.location?.country || "-"}</div>
                  <div>
                    <StatusBadge s={p.status} />
                  </div>
                  <div className="truncate">{p.code}</div>
                </button>
              ))}
              {!items.length && (
                <div className="px-2 py-6 text-xs text-muted-foreground">
                  Henüz otel kaydı yok.
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-7 rounded-lg border p-3 space-y-4">
          <div className="flex items-center justify-between">
            <div className="font-semibold text-sm">
              {selected ? "Hotel Detail" : "Create Hotel"}
            </div>
            {selected?.product_id && (
              <div className="text-xs text-muted-foreground">
                ID: <span className="font-mono">{selected.product_id}</span>
              </div>
            )}
          </div>

          <HotelForm
            value={draft}
            onChange={setDraft}
            onSave={save}
            saving={saving}
            error={formError === "Not Found" ? "" : formError}
          />

          {selected?.product_id && (
            <div className="pt-3 border-t mt-3">
              <RatePlansPanel productId={selected.product_id} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
