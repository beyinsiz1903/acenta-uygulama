/**
 * Syroce Design System (SDS) — EmptyState (Enhanced)
 *
 * Enhanced empty state with variants for different contexts.
 */
import React from "react";
import { cn } from "../../lib/utils";
import { Button } from "../../components/ui/button";
import {
  SearchX,
  AlertCircle,
  ShieldOff,
  Rocket,
  Inbox,
} from "lucide-react";

const VARIANT_CONFIG = {
  default: {
    icon: Inbox,
    iconColor: "text-muted-foreground",
  },
  search: {
    icon: SearchX,
    iconColor: "text-muted-foreground",
    defaultTitle: "Sonuç bulunamadı",
    defaultDescription: "Arama kriterlerinize uygun kayıt bulunamadı.",
  },
  error: {
    icon: AlertCircle,
    iconColor: "text-destructive",
    defaultTitle: "Bir hata oluştu",
    defaultDescription: "Veriler yüklenirken bir hata oluştu. Lütfen tekrar deneyin.",
  },
  "no-permission": {
    icon: ShieldOff,
    iconColor: "text-amber-500",
    defaultTitle: "Erişim yetkiniz yok",
    defaultDescription: "Bu sayfayı görüntüleme yetkiniz bulunmuyor.",
  },
  onboarding: {
    icon: Rocket,
    iconColor: "text-primary",
    defaultTitle: "Başlayalım!",
    defaultDescription: "Henüz kayıt eklenmedi. İlk kaydınızı oluşturun.",
  },
};

export function SdsEmptyState({
  variant = "default",
  icon: CustomIcon,
  title,
  description,
  action,
  secondaryAction,
  className,
}) {
  const config = VARIANT_CONFIG[variant] || VARIANT_CONFIG.default;
  const Icon = CustomIcon || config.icon;
  const displayTitle = title || config.defaultTitle || "Kayıt bulunamadı";
  const displayDescription = description || config.defaultDescription;

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center gap-4 py-12 px-4",
        className
      )}
      data-testid={`empty-state-${variant}`}
    >
      {Icon && (
        <div className="h-14 w-14 rounded-full bg-muted/60 flex items-center justify-center">
          <Icon className={cn("h-7 w-7", config.iconColor)} />
        </div>
      )}
      <div className="max-w-md space-y-1.5">
        <p className="font-semibold text-foreground">{displayTitle}</p>
        {displayDescription && (
          <p className="text-sm text-muted-foreground">{displayDescription}</p>
        )}
      </div>
      {(action || secondaryAction) && (
        <div className="flex items-center gap-3 mt-1">
          {action && (
            <Button
              onClick={action.onClick}
              variant={action.variant || "default"}
              data-testid="empty-state-action"
            >
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              onClick={secondaryAction.onClick}
              variant="outline"
              data-testid="empty-state-secondary-action"
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export default SdsEmptyState;
