import React from "react";
import { CalendarClock, CreditCard, Layers3 } from "lucide-react";

import { Card, CardContent } from "../ui/card";

export const BillingSummaryCards = ({ planLabel, renewalDate, intervalLabel, statusLabel }) => {
  const items = [
    {
      key: "plan",
      label: "Mevcut Plan",
      value: planLabel,
      icon: Layers3,
      testId: "billing-current-plan-card",
    },
    {
      key: "renewal",
      label: "Sonraki Yenileme",
      value: renewalDate,
      icon: CalendarClock,
      testId: "billing-renewal-date-card",
    },
    {
      key: "status",
      label: "Faturalama Durumu",
      value: `${intervalLabel} · ${statusLabel}`,
      icon: CreditCard,
      testId: "billing-status-card",
    },
  ];

  return (
    <div className="grid gap-3 lg:grid-cols-3" data-testid="billing-summary-cards">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <Card key={item.key} className="rounded-3xl border-border/60 bg-card/85" data-testid={item.testId}>
            <CardContent className="flex items-start gap-3 p-5">
              <div className="rounded-2xl border border-border/60 bg-background/80 p-2 text-primary">
                <Icon className="h-4 w-4" />
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground" data-testid={`${item.testId}-label`}>
                  {item.label}
                </p>
                <p className="mt-2 text-lg font-semibold text-foreground" data-testid={`${item.testId}-value`}>
                  {item.value}
                </p>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};