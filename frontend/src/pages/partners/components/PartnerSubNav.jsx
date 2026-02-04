import React from "react";
import { NavLink } from "react-router-dom";
import { cn } from "../../../lib/utils";

const tabs = [
  { label: "Genel Bakış", to: "/app/partners" },
  { label: "Gelen Kutusu", to: "/app/partners/inbox" },
  { label: "Davetler", to: "/app/partners/invites" },
  { label: "İlişkiler", to: "/app/partners/relationships" },
  { label: "Keşfet", to: "/app/partners/discovery" },
  { label: "Mutabakat", to: "/app/partners/statements" },
];

export default function PartnerSubNav() {
  return (
    <nav className="border-b border-border">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
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
    </nav>
  );
}
