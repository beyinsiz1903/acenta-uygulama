import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card } from "../components/ui/card";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
      {text}
    </div>
  );
}

export default function AdminThemePage() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const [companyName, setCompanyName] = useState("Syroce");
  const [logoUrl, setLogoUrl] = useState("");
  const [faviconUrl, setFaviconUrl] = useState("");
  const [primary, setPrimary] = useState("#2563eb");
  const [primaryFg, setPrimaryFg] = useState("#ffffff");
  const [background, setBackground] = useState("#ffffff");
  const [foreground, setForeground] = useState("#0f172a");
  const [muted, setMuted] = useState("#f1f5f9");
  const [mutedFg, setMutedFg] = useState("#475569");
  const [border, setBorder] = useState("#e2e8f0");
  const [fontFamily, setFontFamily] = useState(
    "Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif",
  );

  const load = async () => {
    setLoading(true);
    setErr("");
    try {
      const res = await api.get("/admin/theme");
      const t = res.data || {};
      const brand = t.brand || {};
      const colors = t.colors || {};
      const typo = t.typography || {};

      setCompanyName(brand.company_name || "Syroce");
      setLogoUrl(brand.logo_url || "");
      setFaviconUrl(brand.favicon_url || "");
      setPrimary(colors.primary || "#2563eb");
      setPrimaryFg(colors.primary_foreground || "#ffffff");
      setBackground(colors.background || "#ffffff");
      setForeground(colors.foreground || "#0f172a");
      setMuted(colors.muted || "#f1f5f9");
      setMutedFg(colors.muted_foreground || "#475569");
      setBorder(colors.border || "#e2e8f0");
      setFontFamily(typo.font_family || fontFamily);
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const save = async () => {
    setErr("");
    setSaving(true);
    try {
      const payload = {
        name: "Default Theme",
        brand: {
          company_name: companyName,
          logo_url: logoUrl || null,
          favicon_url: faviconUrl || null,
        },
        colors: {
          primary,
          primary_foreground: primaryFg,
          background,
          foreground,
          muted,
          muted_foreground: mutedFg,
          border,
        },
        typography: {
          font_family: fontFamily,
        },
      };

      await api.put("/admin/theme", payload);
      await load();
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Tema</h1>
        <p className="text-xs text-muted-foreground">
          Website ve uygulama genelinde kullanılacak marka ve renk temasını yönetin.
        </p>
      </div>

      <Card className="p-3 space-y-3 text-xs">
        <FieldError text={err} />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <div className="space-y-1">
            <Label htmlFor="theme-company-name" className="text-xs">
              Şirket Adı
            </Label>
            <Input
              id="theme-company-name"
              data-testid="theme-company-name"
              className="h-8 text-xs"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Logo URL</Label>
            <Input
              className="h-8 text-xs"
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Favicon URL</Label>
            <Input
              className="h-8 text-xs"
              value={faviconUrl}
              onChange={(e) => setFaviconUrl(e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-2">
          <div className="space-y-1">
            <Label className="text-xs">Primary</Label>
            <div className="flex items-center gap-2">
              <Input
                type="color"
                className="h-8 w-12 p-1"
                value={primary}
                onChange={(e) => setPrimary(e.target.value)}
                data-testid="theme-color-primary"
              />
              <Input
                className="h-8 text-xs font-mono"
                value={primary}
                onChange={(e) => setPrimary(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Primary Foreground</Label>
            <div className="flex items-center gap-2">
              <Input
                type="color"
                className="h-8 w-12 p-1"
                value={primaryFg}
                onChange={(e) => setPrimaryFg(e.target.value)}
              />
              <Input
                className="h-8 text-xs font-mono"
                value={primaryFg}
                onChange={(e) => setPrimaryFg(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Background</Label>
            <div className="flex items-center gap-2">
              <Input
                type="color"
                className="h-8 w-12 p-1"
                value={background}
                onChange={(e) => setBackground(e.target.value)}
              />
              <Input
                className="h-8 text-xs font-mono"
                value={background}
                onChange={(e) => setBackground(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-2">
          <div className="space-y-1">
            <Label className="text-xs">Foreground</Label>
            <div className="flex items-center gap-2">
              <Input
                type="color"
                className="h-8 w-12 p-1"
                value={foreground}
                onChange={(e) => setForeground(e.target.value)}
              />
              <Input
                className="h-8 text-xs font-mono"
                value={foreground}
                onChange={(e) => setForeground(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Muted</Label>
            <div className="flex items-center gap-2">
              <Input
                type="color"
                className="h-8 w-12 p-1"
                value={muted}
                onChange={(e) => setMuted(e.target.value)}
              />
              <Input
                className="h-8 text-xs font-mono"
                value={muted}
                onChange={(e) => setMuted(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Muted Foreground</Label>
            <div className="flex items-center gap-2">
              <Input
                type="color"
                className="h-8 w-12 p-1"
                value={mutedFg}
                onChange={(e) => setMutedFg(e.target.value)}
              />
              <Input
                className="h-8 text-xs font-mono"
                value={mutedFg}
                onChange={(e) => setMutedFg(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-2">
          <div className="space-y-1">
            <Label className="text-xs">Border</Label>
            <div className="flex items-center gap-2">
              <Input
                type="color"
                className="h-8 w-12 p-1"
                value={border}
                onChange={(e) => setBorder(e.target.value)}
              />
              <Input
                className="h-8 text-xs font-mono"
                value={border}
                onChange={(e) => setBorder(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="space-y-1 mt-2">
          <Label className="text-xs">Font Family</Label>
          <Textarea
            className="font-mono text-xs min-h-[60px]"
            value={fontFamily}
            onChange={(e) => setFontFamily(e.target.value)}
          />
        </div>

        <div className="flex justify-end">
          <Button
            size="sm"
            className="h-8 text-xs"
            onClick={save}
            disabled={saving || loading}
            data-testid="theme-save-btn"
          >
            {saving ? "Kaydediliyor..." : "Kaydet"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
