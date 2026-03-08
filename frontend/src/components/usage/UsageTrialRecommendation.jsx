import React from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { Button } from "../ui/button";

export const UsageTrialRecommendation = ({ trialConversion, testId = "usage-trial-recommendation" }) => {
  if (!trialConversion?.show) return null;

  const recommendedPlanLabel = trialConversion.recommended_plan_label || `${trialConversion.recommended_plan} Plan`;

  return (
    <div className="rounded-3xl border border-sky-500/25 bg-[linear-gradient(135deg,rgba(14,116,144,0.08),rgba(56,189,248,0.14))] p-5 shadow-sm" data-testid={testId}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-full bg-sky-500/10 p-2 text-sky-700">
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground" data-testid={`${testId}-eyebrow`}>Trial önerisi</p>
          <p className="mt-2 text-sm font-medium text-foreground" data-testid={`${testId}-message`}>{trialConversion.message}</p>
          <div className="mt-3 rounded-2xl border border-white/70 bg-white/70 px-4 py-3 backdrop-blur" data-testid={`${testId}-plan-block`}>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground" data-testid={`${testId}-plan-label`}>Bu kullanım için önerilen plan:</p>
            <p className="mt-1 text-lg font-semibold text-foreground" data-testid={`${testId}-plan`}>{recommendedPlanLabel}</p>
          </div>
          <Button asChild size="sm" className="mt-3" data-testid={`${testId}-cta-button`}>
            <Link to={trialConversion.cta_href || "/pricing"}>{trialConversion.cta_label || "Planları Görüntüle"}</Link>
          </Button>
        </div>
      </div>
    </div>
  );
};