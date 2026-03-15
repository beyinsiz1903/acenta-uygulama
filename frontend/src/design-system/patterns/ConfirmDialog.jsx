/**
 * Syroce Design System (SDS) — ConfirmDialog
 *
 * Standard confirmation dialog for destructive or important actions.
 */
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
} from "../../components/ui/alert-dialog";
import { cn } from "../../lib/utils";

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  variant = "default",
  confirmLabel = "Onayla",
  cancelLabel = "Vazgeç",
  onConfirm,
  loading = false,
}) {
  const handleConfirm = async () => {
    await onConfirm?.();
    onOpenChange?.(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent data-testid="confirm-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle data-testid="confirm-dialog-title">
            {title}
          </AlertDialogTitle>
          <AlertDialogDescription data-testid="confirm-dialog-description">
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel
            disabled={loading}
            data-testid="confirm-dialog-cancel"
          >
            {cancelLabel}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={loading}
            className={cn(
              variant === "destructive" &&
                "bg-destructive text-destructive-foreground hover:bg-destructive/90"
            )}
            data-testid="confirm-dialog-confirm"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                {confirmLabel}
              </span>
            ) : (
              confirmLabel
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export default ConfirmDialog;
