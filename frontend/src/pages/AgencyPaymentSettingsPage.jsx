import React, { useEffect, useState } from "react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/card";
import { toast } from "sonner";

export default function AgencyPaymentSettingsPage() {
  const user = getUser();
  const isAdmin = (user?.roles || []).includes("agency_admin");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [info, setInfo] = useState("");
  const [form, setForm] = useState({
    enabled: false,
    account_name: "",
    bank_name: "",
    iban: "",
    swift: "",
    currency: "TRY",
    default_due_days: 2,
    note_template: "Rezervasyon: {reference_code}",
  });

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const resp = await api.get("/agency/payment-settings");
        if (!alive) return;
        const offline = resp.data?.offline || {};
        setForm({
          enabled: Boolean(offline.enabled),
          account_name: offline.account_name || "",
          bank_name: offline.bank_name || "",
          iban: offline.iban || "",
          swift: offline.swift || "",
          currency: offline.currency || "TRY",
          default_due_days:
            typeof offline.default_due_days === "number" ? offline.default_due_days : 2,
          note_template: offline.note_template || "Rezervasyon: {reference_code}",
        });
        setInfo("");
      } catch (err) {
        const detail = err?.response?.data?.detail;
        const code = typeof detail === "object" ? detail.code : null;
        if (code === "AGENCY_SETTINGS_NOT_FOUND" || code === "PAYMENT_SETTINGS_MISSING") {
          if (!alive) return;
          setInfo("Henüz ödeme ayarları tanımlanmamış. Kaydettiğinizde oluşturulacaktır.");
        } else {
          toast.error(apiErrorMessage(err));
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  function handleChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!isAdmin) {
      toast.error("Bu ayarları sadece acenta yöneticisi güncelleyebilir.");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        offline: {
          enabled: form.enabled,
          account_name: form.account_name.trim(),
          bank_name: form.bank_name.trim() || null,
          iban: form.iban.trim(),
          swift: form.swift.trim() || null,
          currency: form.currency || "TRY",
          default_due_days: Number(form.default_due_days) || 2,
          note_template: form.note_template || "Rezervasyon: {reference_code}",
        },
      };

      const resp = await api.put("/agency/payment-settings", payload);
      const offline = resp.data?.offline || {};
      setForm((prev) => ({
        ...prev,
        enabled: Boolean(offline.enabled),
        account_name: offline.account_name || prev.account_name,
        bank_name: offline.bank_name || "",
        iban: offline.iban || prev.iban,
        swift: offline.swift || "",
        currency: offline.currency || prev.currency,
        default_due_days:
          typeof offline.default_due_days === "number" ? offline.default_due_days : prev.default_due_days,
        note_template: offline.note_template || prev.note_template,
      }));
      setInfo("");
      toast.success("Ödeme ayarları kaydedildi.");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const code = typeof detail === "object" ? detail.code : null;
      if (code === "VALIDATION_ERROR") {
        toast.error(detail.message || "Geçersiz veri girdiniz.");
      } else if (err?.response?.status === 403) {
        toast.error("Bu işlem için yetkiniz yok.");
      } else {
        toast.error(apiErrorMessage(err));
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto p-4">
        <Card className="border rounded-2xl">
          <CardContent className="py-8 text-sm text-muted-foreground text-center">
            Ödeme ayarları yükleniyor...
          </CardContent>
        </Card>
      </div>
    );
  }

  const disabled = !isAdmin;

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Ödeme Ayarları</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Offline IBAN ile ödeme almak için hesap bilgilerinizi tanımlayın.
        </p>
        {info && (
          <p className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            {info}
          </p>
        )}
        {!isAdmin && (
          <p className="mt-2 text-xs text-muted-foreground">
            Bu sayfadaki ayarları sadece <strong>agency_admin</strong> rolüne sahip kullanıcılar düzenleyebilir.
          </p>
        )}
      </div>

      <Card className="border rounded-2xl">
        <CardHeader>
          <CardTitle>Offline Ödeme (IBAN)</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="flex items-center justify-between gap-3 border rounded-lg px-3 py-2 bg-muted/40">
              <div>
                <div className="text-sm font-medium">Offline ödeme durumu</div>
                <div className="text-xs text-muted-foreground">
                  Etkinleştirildiğinde, rezervasyon detayında offline ödeme talimatları gösterilir.
                </div>
              </div>
              <button
                type="button"
                onClick={() => !disabled && handleChange("enabled", !form.enabled)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full border transition ${
                  form.enabled ? "bg-emerald-500 border-emerald-500" : "bg-muted border-border"
                } ${disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition ${
                    form.enabled ? "translate-x-5" : "translate-x-1"
                  }`}
                />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-xs font-medium">Hesap Sahibi *</Label>
                <Input
                  value={form.account_name}
                  onChange={(e) => handleChange("account_name", e.target.value)}
                  disabled={disabled}
                  placeholder="Örn: Syroce Turizm A.Ş."
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs font-medium">Banka Adı</Label>
                <Input
                  value={form.bank_name}
                  onChange={(e) => handleChange("bank_name", e.target.value)}
                  disabled={disabled}
                  placeholder="Örn: Demo Bankası"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-xs font-medium">IBAN *</Label>
                <Input
                  value={form.iban}
                  onChange={(e) => handleChange("iban", e.target.value)}
                  disabled={disabled}
                  placeholder="TR.."
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs font-medium">SWIFT (opsiyonel)</Label>
                <Input
                  value={form.swift}
                  onChange={(e) => handleChange("swift", e.target.value)}
                  disabled={disabled}
                  placeholder="Örn: DEMOTRXX"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-xs font-medium">Para Birimi</Label>
                <Input
                  value={form.currency}
                  onChange={(e) => handleChange("currency", e.target.value.toUpperCase())}
                  disabled={disabled}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs font-medium">Vade (gün)</Label>
                <Input
                  type="number"
                  min={0}
                  max={365}
                  value={form.default_due_days}
                  onChange={(e) => handleChange("default_due_days", e.target.value)}
                  disabled={disabled}
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-medium">Not Şablonu</Label>
              <Textarea
                rows={3}
                value={form.note_template}
                onChange={(e) => handleChange("note_template", e.target.value)}
                disabled={disabled}
                className="text-xs"
                placeholder="Örn: Rezervasyon: {reference_code} / Misafir: {guest_name}"
              />
              <p className="text-[11px] text-muted-foreground mt-1">
                Şablonda <code className="font-mono">{`{reference_code}`}</code> gibi placeholder&apos;lar kullanabilirsiniz.
              </p>
            </div>

            {isAdmin && (
              <div className="flex justify-end pt-2">
                <Button type="submit" disabled={saving}>
                  {saving ? "Kaydediliyor..." : "Kaydet"}
                </Button>
              </div>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
