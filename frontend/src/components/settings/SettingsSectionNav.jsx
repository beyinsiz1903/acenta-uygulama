import React from "react";
import { NavLink } from "react-router-dom";
import { CreditCard, ShieldCheck, Users } from "lucide-react";

import { cn } from "../../lib/utils";

const SETTINGS_LINKS = [
  {
    to: "/app/settings/billing",
    label: "Faturalama",
    description: "Plan, yenileme, ödeme yöntemi ve abonelik yönetimi.",
    icon: CreditCard,
    testId: "settings-section-link-billing",
  },
  {
    to: "/app/settings/security",
    label: "Aktif Oturumlar",
    description: "Cihazları gör, tek tek kapat veya diğer oturumları sonlandır.",
    icon: ShieldCheck,
    testId: "settings-section-link-security",
  },
  {
    to: "/app/settings",
    label: "Kullanıcılar",
    description: "Kullanıcı ve rol yönetimi ayarları.",
    icon: Users,
    testId: "settings-section-link-users",
  },
];

export const SettingsSectionNav = ({ showUsersSection = true }) => {
  const items = showUsersSection ? SETTINGS_LINKS : SETTINGS_LINKS.filter((item) => item.to !== "/app/settings");

  return (
    <div className="grid gap-3 md:grid-cols-3" data-testid="settings-section-nav">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            end
            to={item.to}
            data-testid={item.testId}
            className={({ isActive }) => cn(
              "group rounded-3xl border px-5 py-4 transition-all duration-200",
              isActive
                ? "border-primary/35 bg-primary/5 shadow-sm"
                : "border-border/60 bg-card/70 hover:border-primary/20 hover:bg-accent/40"
            )}
          >
            <div className="flex items-start gap-3">
              <div className="rounded-2xl border border-border/60 bg-background/80 p-2 text-primary">
                <Icon className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <div className="text-sm font-semibold text-foreground">{item.label}</div>
                <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
              </div>
            </div>
          </NavLink>
        );
      })}
    </div>
  );
};