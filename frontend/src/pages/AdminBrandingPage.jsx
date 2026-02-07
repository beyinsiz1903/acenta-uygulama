import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Palette, Image, Building2, Save, RefreshCw } from "lucide-react";

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

  const handleSave = async () => {
    try {
      setSaving(true);
      setSaved(false);
      await api.put("/admin/whitelabel-settings", settings);
      // Apply CSS variable immediately
      if (settings.primary_color) {
        document.documentElement.style.setProperty("--brand-color", settings.primary_color);
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
