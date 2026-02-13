import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Palette, Image, Building2, Save, RefreshCw } from "lucide-react";

function hexToHsl(hex) {
  let r = 0, g = 0, b = 0;
  hex = hex.replace("#", "");
  if (hex.length === 3) {
    r = parseInt(hex[0] + hex[0], 16);
    g = parseInt(hex[1] + hex[1], 16);
    b = parseInt(hex[2] + hex[2], 16);
  } else if (hex.length === 6) {
    r = parseInt(hex.substring(0, 2), 16);
    g = parseInt(hex.substring(2, 4), 16);
    b = parseInt(hex.substring(4, 6), 16);
  }
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h = 0, s = 0, l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
      default: break;
    }
  }
  return `${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`;
}

function applyBrandColor(hexColor) {
  if (!hexColor || !hexColor.startsWith("#")) return;
  const hsl = hexToHsl(hexColor);
  document.documentElement.style.setProperty("--primary", hsl);
  document.documentElement.style.setProperty("--ring", hsl);
  document.documentElement.style.setProperty("--brand-color", hexColor);
}

function relativeLuminance(hex) {
  let r = 0, g = 0, b = 0;
  hex = hex.replace("#", "");
  r = parseInt(hex.substring(0, 2), 16) / 255;
  g = parseInt(hex.substring(2, 4), 16) / 255;
  b = parseInt(hex.substring(4, 6), 16) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function applyForeground(hexColor) {
  if (!hexColor || !hexColor.startsWith("#")) return;
  const lum = relativeLuminance(hexColor);
  const fg = lum > 0.5 ? "224 26% 16%" : "210 40% 98%";
  document.documentElement.style.setProperty("--primary-foreground", fg);
}

const DEFAULT_COLORS = [
  "#3b82f6", "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e",
  "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
  "#06b6d4", "#0ea5e9", "#1e293b", "#64748b",
];

export default function AdminBrandingPage() {
  const [settings, setSettings] = useState({
    company_name: "",
    logo_url: "",
    primary_color: "",
    favicon_url: "",
    support_email: "",
  });
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saved, setSaved] = useState(false);

  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);
      // Try the enterprise endpoint first, fallback to existing whitelabel
      let res;
      try {
        res = await api.get("/admin/whitelabel-settings");
      } catch {
        res = await api.get("/admin/whitelabel");
      }
      const data = res.data || {};
      setSettings({
        company_name: data.company_name || data.brand_name || "",
        logo_url: data.logo_url || "",
        primary_color: data.primary_color || "",
        favicon_url: data.favicon_url || "",
        support_email: data.support_email || "",
      });
    } catch (e) {
      console.error("Failed to load branding settings:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSettings(); }, [loadSettings]);

  // Live preview: apply color immediately when user picks a color
  useEffect(() => {
    if (settings.primary_color && settings.primary_color.startsWith("#") && settings.primary_color.length >= 4) {
      applyBrandColor(settings.primary_color);
      applyForeground(settings.primary_color);
    }
  }, [settings.primary_color]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setSaved(false);
      await api.put("/admin/whitelabel-settings", settings);
      // Apply theme color immediately across the entire app
      if (settings.primary_color) {
        applyBrandColor(settings.primary_color);
        applyForeground(settings.primary_color);
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      alert("Kaydetme hatası: " + (e.response?.data?.error?.message || e.message));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-muted rounded w-1/3"></div>
          <div className="h-40 bg-muted rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl" data-testid="branding-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Palette className="h-6 w-6" />
            White-Label & Branding
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Tenant markalamanızı özelleştirin. Logo, renk ve şirket adı ayarları.
          </p>
        </div>
        <Button onClick={loadSettings} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-1" /> Yenile
        </Button>
      </div>

      <div className="space-y-6">
        {/* Company Name */}
        <div className="rounded-lg border p-4">
          <label className="text-sm font-medium flex items-center gap-2 mb-2">
            <Building2 className="h-4 w-4" /> Şirket Adı
          </label>
          <input
            type="text"
            data-testid="company-name-input"
            value={settings.company_name}
            onChange={(e) => setSettings({ ...settings, company_name: e.target.value })}
            className="w-full rounded-md border px-3 py-2 text-sm bg-background"
            placeholder="Şirket adınız"
          />
        </div>

        {/* Logo URL */}
        <div className="rounded-lg border p-4">
          <label className="text-sm font-medium flex items-center gap-2 mb-2">
            <Image className="h-4 w-4" /> Logo URL
          </label>
          <input
            type="url"
            data-testid="logo-url-input"
            value={settings.logo_url}
            onChange={(e) => setSettings({ ...settings, logo_url: e.target.value })}
            className="w-full rounded-md border px-3 py-2 text-sm bg-background"
            placeholder="https://example.com/logo.png"
          />
          {settings.logo_url && (
            <div className="mt-3 p-3 bg-muted/30 rounded-lg">
              <p className="text-xs text-muted-foreground mb-2">Önizleme:</p>
              <img
                src={settings.logo_url}
                alt="Logo preview"
                data-testid="logo-preview"
                className="h-12 object-contain"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            </div>
          )}
        </div>

        {/* Primary Color */}
        <div className="rounded-lg border p-4">
          <label className="text-sm font-medium flex items-center gap-2 mb-2">
            <Palette className="h-4 w-4" /> Ana Renk
          </label>
          <div className="flex items-center gap-3 mb-3">
            <input
              type="color"
              data-testid="color-picker"
              value={settings.primary_color || "#3b82f6"}
              onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })}
              className="h-10 w-14 rounded cursor-pointer border"
            />
            <input
              type="text"
              data-testid="color-hex-input"
              value={settings.primary_color}
              onChange={(e) => setSettings({ ...settings, primary_color: e.target.value })}
              className="rounded-md border px-3 py-2 text-sm bg-background w-32"
              placeholder="#3b82f6"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_COLORS.map((c) => (
              <button
                key={c}
                onClick={() => setSettings({ ...settings, primary_color: c })}
                className="h-8 w-8 rounded-full border-2 transition-transform hover:scale-110"
                style={{
                  backgroundColor: c,
                  borderColor: settings.primary_color === c ? "white" : "transparent",
                  boxShadow: settings.primary_color === c ? `0 0 0 2px ${c}` : "none",
                }}
                title={c}
              />
            ))}
          </div>
          {settings.primary_color && (
            <div className="mt-3 flex items-center gap-3">
              <div
                className="h-10 px-4 rounded-lg flex items-center text-white text-sm font-medium"
                style={{ backgroundColor: settings.primary_color }}
                data-testid="color-preview"
              >
                Önizleme Butonu
              </div>
              <span className="text-xs text-muted-foreground">Bu renk butonlarda ve vurgularda kullanılır.</span>
            </div>
          )}
        </div>

        {/* Support Email */}
        <div className="rounded-lg border p-4">
          <label className="text-sm font-medium mb-2 block">Destek E-postası</label>
          <input
            type="email"
            data-testid="support-email-input"
            value={settings.support_email}
            onChange={(e) => setSettings({ ...settings, support_email: e.target.value })}
            className="w-full rounded-md border px-3 py-2 text-sm bg-background"
            placeholder="destek@sirket.com"
          />
        </div>

        {/* Save Button */}
        <div className="flex items-center gap-3">
          <Button
            onClick={handleSave}
            disabled={saving}
            data-testid="save-branding-btn"
            className="gap-2"
          >
            <Save className="h-4 w-4" />
            {saving ? "Kaydediliyor..." : "Kaydet"}
          </Button>
          {saved && (
            <span className="text-sm text-green-600 font-medium" data-testid="save-success">
              ✓ Kaydedildi
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
