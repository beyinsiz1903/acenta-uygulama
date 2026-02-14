import React, { useEffect, useState } from "react";
import { AlertCircle, Loader2, Tag } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Card } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
      <AlertCircle className="h-4 w-4 mt-0.5" />
      <div>{text}</div>
    </div>
  );
}

export default function AdminCampaignsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [channels, setChannels] = useState(["B2C"]);
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [couponCodes, setCouponCodes] = useState("");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await api.get("/admin/campaigns");
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

  const resetForm = () => {
    setName("");
    setSlug("");
    setDescription("");
    setChannels(["B2C"]);
    setValidFrom("");
    setValidTo("");
    setCouponCodes("");
  };

  const toISO = (value) => {
    if (!value) return null;
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    return d.toISOString();
  };

  const handleChannelToggle = (value) => {
    setChannels((prev) => {
      if (prev.includes(value)) {
        return prev.filter((x) => x !== value);
      }
      return [...prev, value];
    });
  };

  const create = async () => {
    setErr("");
    if (!name.trim() || !slug.trim()) {
      setErr("Kampanya adı ve slug alanları zorunludur.");
      return;
    }

    setCreating(true);
    try {
      const payload = {
        name: name.trim(),
        slug: slug.trim(),
        description,
        channels: channels.length ? channels : ["B2C"],
        valid_from: toISO(validFrom),
        valid_to: toISO(validTo),
        coupon_codes: couponCodes
          .split(",")
          .map((c) => c.trim().toUpperCase())
          .filter(Boolean),
      };

      await api.post("/admin/campaigns", payload);
      resetForm();
      await load();
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setCreating(false);
    }
  };

  const toggleActive = async (campaign) => {
    setErr("");
    const next = !campaign.active;
    try {
      await api.patch(`/admin/campaigns/${campaign.id}`, { active: next });
      await load();
    } catch (e) {
      setErr(apiErrorMessage(e));
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold flex items-center gap-2">
          <Tag className="h-4 w-4" /> Kampanyalar
        </h1>
        <p className="text-xs text-muted-foreground">
          Kuponları gruplayarak B2B/B2C kampanyaları oluşturun, tarih aralığına ve kanallara göre yönetin.
        </p>
      </div>

      <Card className="p-3 space-y-3 text-xs">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Yeni Kampanya</div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Alanlar:</span>
            <span>Ad, Slug, Kanal, Tarih, Kupon Kodları</span>
          </div>
        </div>

        <FieldError text={err} />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label className="text-xs">Ad</Label>
            <Input
              className="h-8 text-xs"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Örn: Yaz Fırsatları 2025"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Slug</Label>
            <Input
              className="h-8 text-xs"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="yaz-firsatlari-2025"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Kanallar</Label>
            <div className="flex gap-2 text-xs">
              <button
                type="button"
                className={`px-2 py-1 rounded-md border ${
                  channels.includes("B2C") ? "bg-background text-foreground shadow" : "bg-muted"
                }`}
                onClick={() => handleChannelToggle("B2C")}
              >
                B2C
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded-md border ${
                  channels.includes("B2B") ? "bg-background text-foreground shadow" : "bg-muted"
                }`}
                onClick={() => handleChannelToggle("B2B")}
              >
                B2B
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <div className="space-y-1 md:col-span-2">
            <Label className="text-xs">Açıklama</Label>
            <Input
              className="h-8 text-xs"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Kampanya açıklaması (landing sayfada görünecek)."
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Kupon Kodları</Label>
            <Input
              className="h-8 text-xs"
              value={couponCodes}
              onChange={(e) => setCouponCodes(e.target.value)}
              placeholder="YAZ2025, ILKALI50"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label className="text-xs">Başlangıç</Label>
            <Input
              type="datetime-local"
              className="h-8 text-xs"
              value={validFrom}
              onChange={(e) => setValidFrom(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Bitiş</Label>
            <Input
              type="datetime-local"
              className="h-8 text-xs"
              value={validTo}
              onChange={(e) => setValidTo(e.target.value)}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button size="sm" className="h-8 text-xs" onClick={create} disabled={creating}>
            {creating && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
            Kampanya Oluştur
          </Button>
        </div>
      </Card>

      <Card className="p-3 space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Mevcut Kampanyalar</div>
          <Button size="sm" variant="outline" onClick={load} disabled={loading}>
            {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
            Yenile
          </Button>
        </div>

        <div className="mt-2 rounded-md border overflow-hidden">
          <div className="grid grid-cols-7 bg-muted/40 px-2 py-2 font-semibold">
            <div>Ad</div>
            <div>Slug</div>
            <div>Kanallar</div>
            <div>Kuponlar</div>
            <div>Başlangıç</div>
            <div>Bitiş</div>
            <div>Durum</div>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {items.map((c) => (
              <div key={c.id} className="grid grid-cols-7 border-t px-2 py-2 items-center">
                <div className="truncate" title={c.name}>
                  {c.name}
                </div>
                <div className="font-mono text-xs truncate" title={c.slug}>
                  {c.slug}
                </div>
                <div className="flex flex-wrap gap-1">
                  {(c.channels || []).map((ch) => (
                    <Badge key={ch} variant="secondary">
                      {ch}
                    </Badge>
                  ))}
                </div>
                <div className="flex flex-wrap gap-1">
                  {(c.coupon_codes || []).map((code) => (
                    <Badge key={code} variant="outline" className="font-mono">
                      {code}
                    </Badge>
                  ))}
                </div>
                <div>{c.valid_from ? String(c.valid_from).slice(0, 16) : "-"}</div>
                <div>{c.valid_to ? String(c.valid_to).slice(0, 16) : "-"}</div>
                <div className="flex items-center gap-2">
                  <Badge variant={c.active ? "secondary" : "outline"}>{c.active ? "Aktif" : "Pasif"}</Badge>
                  <Button
                    size="xs"
                    variant="outline"
                    className="h-6 px-2 text-2xs"
                    onClick={() => toggleActive(c)}
                  >
                    {c.active ? "Pasifleştir" : "Aktifleştir"}
                  </Button>
                </div>
              </div>
            ))}
            {!items.length && !loading && (
              <div className="px-2 py-3 text-xs text-muted-foreground">Henüz kampanya yok.</div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
