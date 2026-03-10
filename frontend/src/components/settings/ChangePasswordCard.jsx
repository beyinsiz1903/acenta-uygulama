import React, { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";

import { api, apiErrorMessage } from "../../lib/api";
import { changePasswordSchema } from "../../lib/validations";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { toast } from "../ui/sonner";

export const ChangePasswordCard = () => {
  const [lastSuccessMessage, setLastSuccessMessage] = useState("");
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  async function onSubmit(values) {
    setLastSuccessMessage("");
    try {
      const { data } = await api.post("/settings/change-password", {
        current_password: values.current_password,
        new_password: values.new_password,
      });

      const successMessage = data?.revoked_other_sessions > 0
        ? `Şifreniz güncellendi. ${data.revoked_other_sessions} diğer oturum kapatıldı.`
        : (data?.message || "Şifreniz güncellendi.");

      setLastSuccessMessage(successMessage);
      reset();
      toast.success(successMessage);
    } catch (error) {
      toast.error(apiErrorMessage(error));
    }
  }

  return (
    <Card className="rounded-[28px] border-border/60 shadow-sm" data-testid="settings-change-password-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl" data-testid="settings-change-password-title">
          <KeyRound className="h-5 w-5 text-primary" /> Şifre Değiştir
        </CardTitle>
        <CardDescription data-testid="settings-change-password-description">
          Mevcut şifrenizi doğrulayın ve hesabınız için yeni bir şifre belirleyin.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4 md:grid-cols-3" onSubmit={handleSubmit(onSubmit)} noValidate data-testid="settings-change-password-form">
          <div className="space-y-2">
            <Label htmlFor="settings-current-password">Mevcut şifre</Label>
            <Input id="settings-current-password" type="password" autoComplete="current-password" data-testid="settings-current-password-input" {...register("current_password")} />
            {errors.current_password ? <p className="text-xs text-destructive" data-testid="settings-current-password-error">{errors.current_password.message}</p> : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="settings-new-password">Yeni şifre</Label>
            <Input id="settings-new-password" type="password" autoComplete="new-password" data-testid="settings-new-password-input" {...register("new_password")} />
            {errors.new_password ? <p className="text-xs text-destructive" data-testid="settings-new-password-error">{errors.new_password.message}</p> : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="settings-confirm-password">Yeni şifre tekrar</Label>
            <Input id="settings-confirm-password" type="password" autoComplete="new-password" data-testid="settings-confirm-password-input" {...register("confirm_password")} />
            {errors.confirm_password ? <p className="text-xs text-destructive" data-testid="settings-confirm-password-error">{errors.confirm_password.message}</p> : null}
          </div>

          <div className="md:col-span-3 flex flex-col gap-3 rounded-3xl border border-border/60 bg-muted/20 p-4" data-testid="settings-change-password-helper">
            <p className="text-sm text-muted-foreground" data-testid="settings-change-password-helper-text">
              Güvenliğiniz için en az 10 karakter, 1 büyük harf, 1 rakam ve 1 özel karakter içeren bir şifre kullanın. Şifre değiştiğinde diğer aktif oturumlar otomatik kapatılır.
            </p>
            {lastSuccessMessage ? (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800" data-testid="settings-change-password-success-message">
                {lastSuccessMessage}
              </div>
            ) : null}
            <div className="flex justify-end">
              <Button type="submit" disabled={isSubmitting} className="gap-2" data-testid="settings-change-password-submit-button">
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                {isSubmitting ? "Güncelleniyor..." : "Şifreyi Güncelle"}
              </Button>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};