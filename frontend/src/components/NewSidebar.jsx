import React from "react";
import { NavLink } from "react-router-dom";
import { LogOut, PanelLeft, PanelLeftClose } from "lucide-react";

import { formatMoneyCompact } from "../lib/format";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";

function makeNavTestId(prefix, to) {
  const safePath = String(to || "item")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .toLowerCase();

  return `${prefix}-${safePath}`;
}

function SidebarNavItem({ to, label, icon: Icon, collapsed = false, end = false, onClick, testIdPrefix }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      data-testid={makeNavTestId(testIdPrefix, to)}
      className={({ isActive }) =>
        cn(
          "group flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-primary text-primary-foreground shadow-sm"
            : "text-muted-foreground hover:bg-accent hover:text-foreground",
          collapsed && "justify-center px-2.5"
        )
      }
      title={collapsed ? label : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </NavLink>
  );
}

function SidebarSection({ section, collapsed, filterItems, onItemClick, testIdPrefix, sectionTestIdPrefix }) {
  const visibleItems = filterItems(section.items);
  if (!visibleItems.length) {
    return null;
  }

  return (
    <div data-testid={`${sectionTestIdPrefix}-${section.group.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
      {!collapsed && (
        <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground/70">
          {section.group}
        </div>
      )}
      {collapsed && <div className="mx-2 my-2 h-px bg-border/50" />}

      <div className="space-y-1">
        {visibleItems.map((item) => (
          <SidebarNavItem
            key={item.to}
            to={item.to}
            label={item.label}
            icon={item.icon}
            collapsed={collapsed}
            end={item.end}
            onClick={onItemClick}
            testIdPrefix={testIdPrefix}
          />
        ))}
      </div>
    </div>
  );
}

function AccountLinks({ items, collapsed, onItemClick, dataTestId, testIdPrefix }) {
  if (!items.length) {
    return null;
  }

  return (
    <div className="border-t border-border/50 px-2 py-2" data-testid={dataTestId}>
      {!collapsed && (
        <div className="px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground/70">
          Hesap
        </div>
      )}
      <div className="space-y-1">
        {items.map((item) => (
          <SidebarNavItem
            key={item.to}
            to={item.to}
            label={item.label}
            icon={item.icon}
            collapsed={collapsed}
            end={item.end}
            onClick={onItemClick}
            testIdPrefix={testIdPrefix}
          />
        ))}
      </div>
    </div>
  );
}

export const NewSidebar = ({
  variant = "desktop",
  sections,
  accountLinks,
  filterItems,
  collapsed = false,
  onToggleCollapse,
  sidebarStats,
  showStats = true,
  onItemClick,
  onLogout,
  user,
  lang,
}) => {
  if (variant === "mobile") {
    return (
      <div className="flex h-full flex-col bg-background">
        <div className="flex-1 overflow-y-auto px-3 py-3">
          <div className="space-y-4">
            {sections.map((section) => (
              <SidebarSection
                key={section.group}
                section={section}
                collapsed={false}
                filterItems={filterItems}
                onItemClick={onItemClick}
                testIdPrefix="mobile-sidebar-link"
                sectionTestIdPrefix="mobile-sidebar-section"
              />
            ))}
          </div>

          <div className="mt-4">
            <AccountLinks
              items={accountLinks}
              collapsed={false}
              onItemClick={onItemClick}
              dataTestId="mobile-sidebar-account-links"
              testIdPrefix="mobile-sidebar-account-link"
            />
          </div>
        </div>

        <div className="border-t px-3 py-3">
          <Button
            variant="outline"
            size="sm"
            className="w-full gap-2 text-xs"
            onClick={onLogout}
            data-testid="mobile-logout"
          >
            <LogOut className="h-3.5 w-3.5" /> Çıkış yap
          </Button>
        </div>
      </div>
    );
  }

  return (
    <aside
      className={cn(
        "hidden shrink-0 flex-col border-r bg-card/70 md:flex",
        "sticky top-[53px] h-[calc(100vh-53px)] transition-all duration-200",
        collapsed ? "w-[64px]" : "w-[232px]"
      )}
      data-testid="sidebar"
    >
      <div className="flex items-center justify-end border-b border-border/50 px-2 py-2">
        <button
          onClick={onToggleCollapse}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted/60"
          data-testid="sidebar-toggle"
          title={collapsed ? "Kenar çubuğunu genişlet" : "Kenar çubuğunu daralt"}
          type="button"
        >
          {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      {!collapsed && showStats && (
        <div className="grid grid-cols-3 gap-1 border-b border-border/50 px-2 py-2">
          <div className="rounded-lg bg-muted/35 p-2 text-center" data-testid="new-sidebar-stat-total-card">
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Toplam</div>
            <div className="text-xs font-semibold text-foreground" data-testid="sb-total">
              {sidebarStats.total}
            </div>
          </div>
          <div className="rounded-lg bg-muted/35 p-2 text-center" data-testid="new-sidebar-stat-pending-card">
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Bekleyen</div>
            <div className="text-xs font-semibold text-foreground" data-testid="sb-pending">
              {sidebarStats.pending}
            </div>
          </div>
          <div className="rounded-lg bg-muted/35 p-2 text-center" data-testid="new-sidebar-stat-revenue-card">
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Ciro 7G</div>
            <div className="text-xs font-semibold text-foreground" data-testid="sb-rev7">
              {formatMoneyCompact(sidebarStats.revenue7d, "TRY")}
            </div>
          </div>
        </div>
      )}

      <nav className="flex-1 space-y-4 overflow-y-auto px-2 py-3" data-testid="new-sidebar-nav">
        {sections.map((section) => (
          <SidebarSection
            key={section.group}
            section={section}
            collapsed={collapsed}
            filterItems={filterItems}
            testIdPrefix="sidebar-link"
            sectionTestIdPrefix="sidebar-section"
          />
        ))}
      </nav>

      <AccountLinks
        items={accountLinks}
        collapsed={collapsed}
        dataTestId="sidebar-account-links"
        testIdPrefix="sidebar-account-link"
      />

      {!collapsed && (
        <div className="border-t border-border/50 px-3 py-3 text-[11px] text-muted-foreground" data-testid="new-sidebar-footer-meta">
          <div className="font-medium text-foreground">{user?.name || user?.email || "Kullanıcı"}</div>
          <div className="mt-0.5">{(user?.roles || ["-"])[0]} · {new Date().toLocaleDateString(lang === "en" ? "en-US" : "tr-TR")}</div>
        </div>
      )}
    </aside>
  );
};