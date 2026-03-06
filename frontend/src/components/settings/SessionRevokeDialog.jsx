import React from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";

export const SessionRevokeDialog = ({
  open,
  mode,
  session,
  currentSessionId,
  otherSessionCount,
  loading,
  onOpenChange,
  onConfirm,
}) => {
  const isCurrentSession = mode === "single" && session?.id === currentSessionId;
  const title = mode === "others"
    ? "Diğer tüm oturumları kapat"
    : isCurrentSession
      ? "Bu cihazdaki oturumu kapat"
      : "Bu oturumu kapat";

  const description = mode === "others"
    ? `Bu işlem ${otherSessionCount} diğer aktif oturumu sonlandırır. Mevcut cihazdaki oturumunuz açık kalır.`
    : isCurrentSession
      ? "Bu oturumu kapatırsanız mevcut cihazdan hemen çıkış yapılır ve yeniden giriş yapmanız gerekir."
      : "Seçilen oturum hemen geçersiz olur. O cihaz uygulamayı kullanmaya devam edemez.";

  const confirmLabel = mode === "others"
    ? "Diğer oturumları kapat"
    : isCurrentSession
      ? "Bu cihazdan çıkış yap"
      : "Oturumu kapat";

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="rounded-3xl" data-testid="session-revoke-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle data-testid="session-revoke-dialog-title">{title}</AlertDialogTitle>
          <AlertDialogDescription data-testid="session-revoke-dialog-description">
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading} data-testid="session-revoke-dialog-cancel">
            Vazgeç
          </AlertDialogCancel>
          <AlertDialogAction
            disabled={loading}
            onClick={(event) => {
              event.preventDefault();
              onConfirm();
            }}
            data-testid="session-revoke-dialog-confirm"
          >
            {loading ? "İşleniyor..." : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};