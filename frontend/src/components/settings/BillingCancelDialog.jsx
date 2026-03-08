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

export const BillingCancelDialog = ({ open, loading, onOpenChange, onConfirm }) => {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="rounded-3xl" data-testid="billing-cancel-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle data-testid="billing-cancel-dialog-title">
            Aboneliği dönem sonunda iptal et
          </AlertDialogTitle>
          <AlertDialogDescription data-testid="billing-cancel-dialog-description">
            Aboneliğiniz mevcut dönem sonuna kadar aktif kalır. Sonrasında otomatik olarak sona erer.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading} data-testid="billing-cancel-dialog-cancel">
            Vazgeç
          </AlertDialogCancel>
          <AlertDialogAction
            disabled={loading}
            onClick={(event) => {
              event.preventDefault();
              onConfirm();
            }}
            data-testid="billing-cancel-dialog-confirm"
          >
            {loading ? "İşleniyor..." : "Aboneliği İptal Et"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};