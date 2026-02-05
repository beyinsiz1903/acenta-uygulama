import React from "react";
import { NavLink } from "react-router-dom";
import { cn } from "../../../lib/utils";

const groups = [
  {
    key: "general",
    label: "Genel",
    items: [{ label: "Genel Bakış", to: "/app/partners" }],
  },
  {
    key: "ops",
    label: "Operasyon",
    items: [
      { label: "Gelen Kutusu", to: "/app/partners/inbox" },
      { label: "Davetler", to: "/app/partners/invites" },
      { label: "İlişkiler", to: "/app/partners/relationships" },
    ],
  },
  {
    key: "growth",
    label: "Büyütme",
    items: [{ label: "Keşfet", to: "/app/partners/discovery" }],
  },
  {
    key: "finance",
    label: "Finans",
    items: [{ label: "Mutabakat", to: "/app/partners/statements" }],
  },
];

export default function PartnerSubNav() {
  return (
    <nav className="border-b border-border">
      <div className="flex items-center gap-4 overflow-x-auto">
        {groups.map((group, idx) => (
          <div key={group.key} className="flex items-center gap-3 shrink-0">
            {idx > 0 && (
              <div
                className="h-6 w-px bg-border"
                aria-hidden="true"
              />
            )}

            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[11px] text-muted-foreground uppercase tracking-wide">
                {group.label}
              </span>

              <div className="flex items-center gap-2">
                {group.items.map((tab) => (
                  <NavLink
                    key={tab.to}
                    to={tab.to}
                    end={tab.to === "/app/partners"}
                    className={({ isActive }) =>
                      cn(
                        "inline-flex items-center rounded-full px-3 py-1 text-xs font-medium transition",
                        "border border-transparent hover:bg-accent hover:text-foreground",
                        isActive && "bg-primary text-primary-foreground border-primary shadow-sm"
                      )
                    }
                  >
                    {tab.label}
                  </NavLink>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </nav>
  );
}
