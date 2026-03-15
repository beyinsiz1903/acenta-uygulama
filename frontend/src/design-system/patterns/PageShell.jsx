/**
 * Syroce Design System (SDS) — PageShell
 *
 * Standard page wrapper providing consistent layout across all pages.
 * Includes: title, description, breadcrumbs, action buttons, optional tabs.
 */
import React from "react";
import { cn } from "../../lib/utils";
import { Skeleton } from "../../components/ui/skeleton";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "../../components/ui/breadcrumb";
import { Tabs, TabsList, TabsTrigger } from "../../components/ui/tabs";

export function PageShell({
  title,
  description,
  breadcrumbs,
  actions,
  tabs,
  activeTab,
  onTabChange,
  loading = false,
  children,
  className,
}) {
  if (loading) {
    return (
      <div className={cn("space-y-6", className)} data-testid="page-shell-loading">
        <div className="space-y-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-8 w-72" />
          <Skeleton className="h-4 w-96" />
        </div>
        <Skeleton className="h-[400px] w-full rounded-lg" />
      </div>
    );
  }

  return (
    <div className={cn("space-y-6", className)} data-testid="page-shell">
      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumb data-testid="page-shell-breadcrumbs">
          <BreadcrumbList>
            {breadcrumbs.map((crumb, i) => (
              <React.Fragment key={i}>
                {i > 0 && <BreadcrumbSeparator />}
                <BreadcrumbItem>
                  {i === breadcrumbs.length - 1 ? (
                    <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink href={crumb.href}>{crumb.label}</BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              </React.Fragment>
            ))}
          </BreadcrumbList>
        </Breadcrumb>
      )}

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <h1
            className="text-xl font-semibold tracking-tight text-foreground truncate"
            data-testid="page-shell-title"
          >
            {title}
          </h1>
          {description && (
            <p
              className="text-sm text-muted-foreground max-w-2xl"
              data-testid="page-shell-description"
            >
              {description}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex items-center gap-2 shrink-0" data-testid="page-shell-actions">
            {actions}
          </div>
        )}
      </div>

      {/* Tabs */}
      {tabs && tabs.length > 0 && (
        <Tabs
          value={activeTab}
          onValueChange={onTabChange}
          data-testid="page-shell-tabs"
        >
          <TabsList>
            {tabs.map((tab) => (
              <TabsTrigger
                key={tab.value}
                value={tab.value}
                data-testid={`page-shell-tab-${tab.value}`}
              >
                {tab.icon && <span className="mr-1.5">{tab.icon}</span>}
                {tab.label}
                {tab.count !== undefined && (
                  <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-xs font-medium">
                    {tab.count}
                  </span>
                )}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      )}

      {/* Content */}
      <div data-testid="page-shell-content">{children}</div>
    </div>
  );
}

export default PageShell;
