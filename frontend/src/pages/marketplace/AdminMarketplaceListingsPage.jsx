import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { Badge } from "../../components/ui/badge";
import { AlertCircle, Loader2, Pencil, Upload, Archive } from "lucide-react";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
      <AlertCircle className="mt-0.5 h-4 w-4" />
      <div>{text}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  const value = status || "draft";
  if (value === "published") return <Badge className="bg-emerald-500 text-white">Published</Badge>;
  if (value === "archived") return <Badge variant="outline">Archived</Badge>;
  return <Badge variant="outline">Draft</Badge>;
}

function useTenantKey() {
  const STORAGE_KEY = "marketplace:tenantKey";
  const [tenantKey, setTenantKey] = useState(() => {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem(STORAGE_KEY) || "";
  });

  const saveTenantKey = (value) => {
    setTenantKey(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, value || "");
    }
  };

  return { tenantKey, saveTenantKey };
}

function ListingFormDialog({ open, onOpenChange, initial, onSaved, tenantKey }) {
  const isEdit = Boolean(initial && initial.id);
  const [title, setTitle] = useState(initial?.title || "");
  const [description, setDescription] = useState(initial?.description || "");
  const [category, setCategory] = useState(initial?.category || "");
  const [basePrice, setBasePrice] = useState(initial?.base_price || initial?.price || "100.00");
  const [tags, setTags] = useState((initial?.tags || []).join(", "));
  const [pricingHintText, setPricingHintText] = useState(
    initial?.pricing_hint ? JSON.stringify(initial.pricing_hint, null, 2) : ""
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setTitle(initial?.title || "");
      setDescription(initial?.description || "");
      setCategory(initial?.category || "");
      setBasePrice(initial?.base_price || initial?.price || "100.00");
      setTags((initial?.tags || []).join(", "));
      setPricingHintText(initial?.pricing_hint ? JSON.stringify(initial.pricing_hint, null, 2) : "");
      setError("");
    }
  }, [open, initial]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title || !basePrice) {
      setError("Title ve base_price zorunludur.");
      return;
    }

    let pricingHint = undefined;
    if (pricingHintText.trim()) {
      try {
        pricingHint = JSON.parse(pricingHintText);
      } catch (err) {
        setError("pricing_hint JSON formatında olmalıdır.");
        return;
      }
    }

    const payload = {
      title: title.trim(),
      description: description.trim() || null,
      category: category.trim() || null,
      currency: "TRY",
      base_price: String(basePrice).trim(),
      pricing_hint: pricingHint,
      tags: tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    };

    setSaving(true);
    setError("");
    try {
      const headers = tenantKey ? { "X-Tenant-Key": tenantKey } : {};
      if (isEdit) {
        await api.patch(`/marketplace/listings/${initial.id}`, payload, { headers });
      } else {
        await api.post("/marketplace/listings", payload, { headers });
      }
      if (onSaved) onSaved();
      onOpenChange(false);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-base">
            {isEdit ? "Listing Düzenle" : "Yeni Listing"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <FieldError text={error} />
          <div className="space-y-1">
            <Label className="text-xs">Title</Label>
            <Input
              className="h-8 text-xs"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Örn. Antalya Otel Portföyü"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Description</Label>
            <textarea
              className="min-h-[60px] w-full rounded-md border bg-background p-2 text-xs"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Kısa açıklama (opsiyonel)"
            />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1">
              <Label className="text-xs">Category</Label>
              <Input
                className="h-8 text-xs"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="hotel / tour / transfer"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Base Price</Label>
              <Input
                className="h-8 text-xs"
                value={basePrice}
                onChange={(e) => setBasePrice(e.target.value)}
                placeholder="100.00"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Tags (virgülle)</Label>
              <Input
                className="h-8 text-xs"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="otel, antalya, deniz"
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Pricing Hint (JSON, opsiyonel)</Label>
            <textarea
              className="min-h-[60px] w-full rounded-md border bg-background p-2 text-xs font-mono"
              value={pricingHintText}
              onChange={(e) => setPricingHintText(e.target.value)}
              placeholder='{"recommended_markup_pct": 10}'
            />
          </div>
          <DialogFooter className="mt-2 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => onOpenChange(false)}
            >
              Vazgeç
            </Button>
            <Button type="submit" size="sm" className="h-8 text-xs" disabled={saving}>
              {saving && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              {isEdit ? "Kaydet" : "Oluştur"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminMarketplaceListingsPage() {
  const { tenantKey, saveTenantKey } = useTenantKey();
  const [statusFilter, setStatusFilter] = useState("all");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [busyActionId, setBusyActionId] = useState(null);

  const headers = useMemo(() => {
    const h = {};
    if (tenantKey) h["X-Tenant-Key"] = tenantKey;
    return h;
  }, [tenantKey]);

  const load = async () => {
    if (!tenantKey) return;
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (statusFilter !== "all") params.status = statusFilter;
      const res = await api.get("/marketplace/listings", { headers, params });
      setItems(res.data || []);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tenantKey) {
      void load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantKey, statusFilter]);

  const handlePublish = async (listing) => {
    setBusyActionId(listing.id);
    try {
      await api.post(`/marketplace/listings/${listing.id}/publish`, null, { headers });
      await load();
    } catch (err) {
      // eslint-disable-next-line no-alert
      alert(apiErrorMessage(err));
    } finally {
      setBusyActionId(null);
    }
  };

  const handleArchive = async (listing) => {
    setBusyActionId(listing.id);
    try {
      await api.post(`/marketplace/listings/${listing.id}/archive`, null, { headers });
      await load();
    } catch (err) {
      // eslint-disable-next-line no-alert
      alert(apiErrorMessage(err));
    } finally {
      setBusyActionId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-lg font-semibold">Marketplace Listings</div>
          <div className="max-w-xl text-xs text-muted-foreground">
            Tenant bazlı marketplace ürünleri. Bu ekrandan kendi tenantiniz için draft/published/archived listingleri
            yönetebilirsiniz.
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs"
            onClick={() => {
              if (tenantKey) void load();
            }}
            disabled={loading || !tenantKey}
          >
            {loading && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}Yenile
          </Button>
          <Button
            size="sm"
            className="h-8 text-xs"
            onClick={() => {
              setSelected(null);
              setCreateOpen(true);
            }}
            disabled={!tenantKey}
          >
            Yeni Listing
          </Button>
        </div>
      </div>

      {/* Tenant key selector */}
      <div className="rounded-md border bg-white p-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="space-y-1">
            <Label className="text-xs">Tenant Key</Label>
            <Input
              className="h-8 text-xs min-w-[200px]"
              value={tenantKey}
              onChange={(e) => saveTenantKey(e.target.value)}
              placeholder="seller-tenant"
            />
          </div>
          {!tenantKey && (
            <div className="text-xs text-destructive flex items-center gap-1">
              <AlertCircle className="h-4 w-4" />
              <span>Listingleri görmek için önce bir tenant key girin.</span>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Label className="text-xs">Status</Label>
          <select
            className="h-8 rounded-md border bg-background px-2 text-xs"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </div>

      <div className="rounded-md border overflow-hidden">
        <Table className="text-xs">
          <TableHeader>
            <TableRow className="bg-muted/40">
              <TableHead>Title</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Price</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell colSpan={6} className="py-6 text-center text-muted-foreground">
                  <Loader2 className="mr-2 inline-block h-4 w-4 animate-spin" /> Yükleniyor...
                </TableCell>
              </TableRow>
            )}
            {!loading && items.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-6 text-center text-muted-foreground">
                  Henüz listing bulunmuyor.
                </TableCell>
              </TableRow>
            )}
            {!loading &&
              items.map((l) => (
                <TableRow key={l.id}>
                  <TableCell>{l.title}</TableCell>
                  <TableCell>{l.category || <span className="text-muted-foreground">-</span>}</TableCell>
                  <TableCell>
                    <span className="font-mono">
                      {l.base_price || l.price} {l.currency || "TRY"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={l.status} />
                  </TableCell>
                  <TableCell>{l.updated_at || "-"}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        type="button"
                        size="icon"
                        variant="outline"
                        className="h-7 w-7"
                        onClick={() => {
                          setSelected(l);
                          setEditOpen(true);
                        }}
                      >
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button
                        type="button"
                        size="icon"
                        variant="outline"
                        className="h-7 w-7 text-emerald-600 border-emerald-500/40"
                        disabled={busyActionId === l.id || l.status === "published"}
                        onClick={() => handlePublish(l)}
                      >
                        {busyActionId === l.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Upload className="h-3 w-3" />
                        )}
                      </Button>
                      <Button
                        type="button"
                        size="icon"
                        variant="outline"
                        className="h-7 w-7 text-destructive border-destructive/40"
                        disabled={busyActionId === l.id || l.status === "archived"}
                        onClick={() => handleArchive(l)}
                      >
                        {busyActionId === l.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Archive className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>

      <ListingFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        initial={null}
        onSaved={load}
        tenantKey={tenantKey}
      />
      <ListingFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        initial={selected}
        onSaved={load}
        tenantKey={tenantKey}
      />
    </div>
  );
}
