import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Textarea } from "../components/ui/textarea";

const StatusBadge = ({ s }) => {
  if (!s) return <Badge variant="outline">-</Badge>;
  if (s === "active") return <Badge variant="secondary">aktif</Badge>;
  if (s === "archived") return <Badge variant="outline">arşivlendi</Badge>;
  if (s === "inactive") return <Badge variant="outline">pasif</Badge>;
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
          <div className="text-xs text-muted-foreground">Tür</div>
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
          <div className="text-xs text-muted-foreground">Durum</div>
          <select
            className="h-9 w-full rounded-md border bg-background px-2 text-sm"
            value={v.status || "inactive"}
            onChange={(e) => onChange({ ...v, status: e.target.value })}
          >
            <option value="active">Aktif</option>
            <option value="inactive">Pasif</option>
            <option value="archived">Arşivlendi</option>
          </select>
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
          <div className="text-xs text-muted-foreground">Para birimi</div>
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
          <div className="text-xs text-muted-foreground">Ad (TR)</div>
          <Input
            value={(v.name && v.name.tr) || ""}
            onChange={(e) =>
              onChange({ ...v, name: { ...(v.name || {}), tr: e.target.value } })
            }
          />
        </div>
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">Ad (EN)</div>
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
          {saving ? "Kaydediliyor..." : "Kaydet"}
        </Button>
      </div>
    </div>
  );
}

function VersionsPanel({ productId, productStatus }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [roomTypes, setRoomTypes] = useState([]);
  const [ratePlans, setRatePlans] = useState([]);
  const [selectedRoomTypeIds, setSelectedRoomTypeIds] = useState([]);
  const [selectedRatePlanIds, setSelectedRatePlanIds] = useState([]);

  const [newJson, setNewJson] = useState(
    '{\n  "description": {"tr": "", "en": ""},\n  "amenities": [],\n  "room_type_ids": [],\n  "rate_plan_ids": []\n}'
  );

  const load = async () => {
    if (!productId) return;
    setLoading(true);
    setError("");
    try {
      const [verRes, roomRes, rateRes] = await Promise.all([
        api.get(`/admin/catalog/products/${productId}/versions`),
        api.get(`/admin/catalog/room-types`, { params: { product_id: productId } }),
        api.get(`/admin/catalog/rate-plans`, { params: { product_id: productId } }),
      ]);
      setItems(verRes.data.items || []);
      setRoomTypes(roomRes.data || []);
      setRatePlans(rateRes.data || []);
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

  const toggleRoomType = (id) => {
    setSelectedRoomTypeIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleRatePlan = (id) => {
    setSelectedRatePlanIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const createDraft = async () => {
    setError("");
    try {
      const content = JSON.parse(newJson || "{}");
      content.room_type_ids = selectedRoomTypeIds;
      content.rate_plan_ids = selectedRatePlanIds;
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
        <div className="font-semibold text-sm">Versiyonlar</div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          {loading ? "Yükleniyor..." : "Yenile"}
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 p-2 text-xs text-destructive">
          {error}
        </div>
      )}

      <div className="rounded-md border p-3 space-y-2">
        <div className="text-xs text-muted-foreground">
          Taslak versiyon oluştur (JSON içerik).
          <span className="font-medium">Not:</span> JSON içindeki
          <code className="mx-1 rounded bg-muted px-1">room_type_ids</code> ve
          <code className="mx-1 rounded bg-muted px-1">rate_plan_ids</code> alanları, aşağıdaki seçimlerinizle
          her zaman overwrite edilir.
        </div>
        <Textarea
          className="font-mono text-xs h-40"
          value={newJson}
          onChange={(e) => setNewJson(e.target.value)}
        />
        <div className="flex justify-end">
          <Button size="sm" onClick={createDraft}>
            Taslak oluştur
          </Button>
        </div>
      </div>
      <div className="rounded-md border p-3 space-y-3">
        <div className="text-[11px] font-semibold">Bağlı oda tipleri</div>
        <div className="text-[11px] text-muted-foreground">
          Aşağıdan seçtiğiniz room type ve rate plan ID&apos;leri, draft içeriğinde
          <code className="mx-1 rounded bg-muted px-1">room_type_ids</code> ve
          <code className="mx-1 rounded bg-muted px-1">rate_plan_ids</code> alanlarına otomatik eklenecektir.
        </div>
        <div className="grid grid-cols-2 gap-3 text-[11px]">
          <div className="space-y-1">
            <div className="font-medium">Oda tipleri</div>
            <div className="max-h-32 overflow-y-auto space-y-1">
              {roomTypes.map((rt) => (
                <label key={rt.room_type_id} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="h-3 w-3"
                    checked={selectedRoomTypeIds.includes(rt.room_type_id)}
                    onChange={() => toggleRoomType(rt.room_type_id)}
                  />
                  <span className="truncate">
                    {rt.code} – {(rt.name && (rt.name.tr || rt.name.en)) || "(isim yok)"}
                  </span>
                </label>
              ))}
              {!roomTypes.length && (
                <div className="text-[11px] text-muted-foreground">Henüz room type yok.</div>
              )}
            </div>
          </div>
          <div className="space-y-1">
            <div className="font-medium">Rate planlar</div>
            <div className="max-h-32 overflow-y-auto space-y-1">
              {ratePlans.map((rp) => (
                <label key={rp.rate_plan_id} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="h-3 w-3"
                    checked={selectedRatePlanIds.includes(rp.rate_plan_id)}
                    onChange={() => toggleRatePlan(rp.rate_plan_id)}
                  />
                  <span className="truncate">
                    {rp.code} – {(rp.name && (rp.name.tr || rp.name.en)) || "(isim yok)"}
                  </span>
                </label>
              ))}
              {!ratePlans.length && (
                <div className="text-[11px] text-muted-foreground">Henüz rate plan yok.</div>
              )}
            </div>
          </div>
        </div>
      </div>


      <div className="rounded-md border overflow-hidden">
        <div className="grid grid-cols-5 bg-muted/40 px-2 py-2 text-xs font-semibold">
          <div>Sürüm</div>
          <div>Durum</div>
          <div>Oluşturulma</div>
          <div>Yayınlanma</div>
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
                    disabled={productStatus !== "active"}
                    title={
                      productStatus !== "active"
                        ? "Yayınlamak için ürün status=active olmalı."
                        : undefined
                    }
                  >
                    Publish
                  </Button>
                )}
              </div>
            </div>
          ))}
          {!items.length && (
            <div className="px-2 py-6 text-xs text-muted-foreground">Henüz versiyon yok.</div>
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
          <div className="text-lg font-semibold">Katalog</div>
          <div className="text-xs text-muted-foreground">
            Ürün listesi, versiyonlama ve yayınlama ekranı.
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={createNew}>
          Yeni ürün
        </Button>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Left: list */}
        <div className="col-span-12 lg:col-span-5 rounded-lg border p-3 space-y-3">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <Input
              placeholder="Ara..."
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <select
              className="h-9 rounded-md border bg-background px-2 text-xs"
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="">Tüm türler</option>
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
              <option value="">Tüm durumlar</option>
              <option value="active">Aktif</option>
              <option value="inactive">Pasif</option>
              <option value="archived">Arşivlendi</option>
            </select>
          </div>

          <div className="flex justify-end">
            <Button
              size="sm"
              variant="outline"
              onClick={load}
              disabled={loading}
            >
              {loading ? "Yükleniyor..." : "Uygula"}
            </Button>
          </div>

          <div className="rounded-md border overflow-hidden text-xs">
            <div className="grid grid-cols-6 bg-muted/40 px-2 py-2 font-semibold">
              <div className="col-span-2">Ad</div>
              <div>Kod</div>
              <div>Tür</div>
              <div>Durum</div>
              <div>Yay. ver.</div>
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
                  Ürün bulunamadı.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: detail */}
        <div className="col-span-12 lg:col-span-7 rounded-lg border p-3 space-y-4">
          <div className="flex items-center justify-between">
            <div className="font-semibold text-sm">
              {selected ? "Ürün detayı" : "Ürün oluştur"}
            </div>
            {selected && selected.status !== "active" && (
              <div className="ml-4 rounded-md border border-amber-400/60 bg-amber-50 px-2 py-1 text-[11px] text-amber-900">
                Product inactive c bb publish disabled
              </div>
            )}
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
              <VersionsPanel productId={selected.product_id} productStatus={selected.status} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
