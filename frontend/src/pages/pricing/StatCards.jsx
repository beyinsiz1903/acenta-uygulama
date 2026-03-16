import React from "react";
import { Layers, Zap, Globe, Tag, Shield } from "lucide-react";
import { Card, CardContent } from "../../components/ui/card";

export function StatCards({ stats }) {
  const cards = [
    { label: "Toplam Kural", value: stats.total_rules || 0, icon: Layers, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Aktif Kural", value: stats.active_rules || 0, icon: Zap, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Kanal", value: stats.channel_count || 0, icon: Globe, color: "text-violet-600", bg: "bg-violet-50" },
    { label: "Aktif Promosyon", value: stats.active_promotions || 0, icon: Tag, color: "text-amber-600", bg: "bg-amber-50" },
    { label: "Guardrail", value: stats.active_guardrails || 0, icon: Shield, color: "text-rose-600", bg: "bg-rose-50" },
  ];
  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4" data-testid="pricing-stat-cards">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <Card key={i} className="border">
            <CardContent className="p-4 flex items-center gap-3">
              <div className={`${c.bg} p-2.5 rounded-lg`}><Icon className={`w-5 h-5 ${c.color}`} /></div>
              <div>
                <p className="text-xs text-muted-foreground">{c.label}</p>
                <p className="text-xl font-bold">{c.value}</p>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
