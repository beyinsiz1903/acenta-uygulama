import React from "react";
import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../ui/tooltip";

export function MatchLegalNoticeShort() {
  return (
    <div className="mt-1 flex items-start gap-2 text-xs text-muted-foreground" data-testid="match-legal-notice-short">
      <span>
        Bu kayıt, iki tesis arasında yapılan <span className="font-medium">resmî yönlendirmeyi</span> gösterir; konaklama
        gerçekleştiğine dair kanıt değildir.
      </span>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="mt-[1px] inline-flex h-4 w-4 items-center justify-center rounded-full border border-border/60 bg-background/80"
              aria-label="Eşleşme kaydı hakkında bilgi"
              data-testid="match-legal-notice-info-trigger"
            >
              <Info className="h-3 w-3" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-xs">
            <p className="text-[11px] leading-snug">
              Eşleşme kaydı, misafirin talebi doğrultusunda yapılan yönlendirme sürecini belgelemek içindir. Konaklama
              gerçekleşti/gerçekleşmedi bilgisi bu kaydın kapsamı değildir. Hizmet bedeli, yönlendirme oluşturulduğunda
              oluşur.
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}

export function MatchLegalInfoBox() {
  return (
    <div
      className="mt-3 rounded-md border border-border/60 bg-muted/40 px-3 py-2 text-[11px] leading-snug text-muted-foreground"
      data-testid="match-legal-info-box"
    >
      <div className="mb-1 font-medium text-foreground">Bilgilendirme</div>
      <ul className="space-y-0.5 list-disc pl-4">
        <li>
          Eşleşme, bir tesisin misafiri başka bir tesise <span className="font-medium">resmî olarak yönlendirmesi</span>
          anlamına gelir.
        </li>
        <li>
          Bu ekran, <span className="font-medium">konaklamayı doğrulamak</span> amacıyla tasarlanmamıştır.
        </li>
        <li>
          Misafirin gidip gitmemesi (no-show vb.) işletmelerin kendi operasyonel sürecidir.
        </li>
        <li>
          Platformumuzda hizmet bedeli, yönlendirme/eşleşme oluşturulduğu anda doğar.
        </li>
      </ul>
    </div>
  );
}
