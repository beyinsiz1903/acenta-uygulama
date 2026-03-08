import React from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { Button } from "../ui/button";

export const UsageTrialRecommendation = ({ trialConversion, testId = "usage-trial-recommendation" }) => {
  if (!trialConversion?.show) return null;

  return (
    <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4" data-testid={testId}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-full bg-primary/10 p-2 text-primary">
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground" data-testid={`${testId}-eyebrow`}>Trial conversion</p>
          <p className="mt-2 text-sm font-medium text-foreground" data-testid={`${testId}-message`}>{trialConversion.message}</p>
          <p className="mt-1 text-sm text-muted-foreground" data-testid={`${testId}-plan`}>Önerilen plan: {trialConversion.recommended_plan}</p>
          <Button asChild size="sm" className="mt-3" data-testid={`${testId}-cta-button`}>
            <Link to={trialConversion.cta_href || "/pricing"}>{trialConversion.cta_label || "Planları Gör"}</Link>
          </Button>
        </div>
      </div>
    </div>
  );
};