/**
 * Syroce Design System (SDS) — Timeline
 *
 * Activity/audit timeline component.
 */
import React from "react";
import { cn } from "../../lib/utils";
import { Skeleton } from "../../components/ui/skeleton";
import { Avatar, AvatarFallback } from "../../components/ui/avatar";
import {
  Plus,
  Pencil,
  ArrowRight,
  MessageSquare,
  Settings,
} from "lucide-react";

const TYPE_ICONS = {
  created: Plus,
  updated: Pencil,
  status_change: ArrowRight,
  comment: MessageSquare,
  system: Settings,
};

const TYPE_COLORS = {
  created: "bg-emerald-500 text-white",
  updated: "bg-blue-500 text-white",
  status_change: "bg-amber-500 text-white",
  comment: "bg-violet-500 text-white",
  system: "bg-gray-400 text-white",
};

function formatRelativeTime(date) {
  const now = new Date();
  const d = new Date(date);
  const diffMs = now - d;
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffMin < 1) return "az önce";
  if (diffMin < 60) return `${diffMin} dk önce`;
  if (diffHour < 24) return `${diffHour} saat önce`;
  if (diffDay < 7) return `${diffDay} gün önce`;
  return d.toLocaleDateString("tr-TR", { day: "numeric", month: "short", year: "numeric" });
}

export function Timeline({ events = [], loading = false, emptyText = "Henüz aktivite yok." }) {
  if (loading) {
    return (
      <div className="space-y-4" data-testid="timeline-loading">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="h-8 w-8 rounded-full shrink-0" />
            <div className="space-y-1.5 flex-1">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8" data-testid="timeline-empty">
        {emptyText}
      </p>
    );
  }

  return (
    <div className="relative space-y-0" data-testid="timeline">
      {events.map((event, i) => {
        const Icon = TYPE_ICONS[event.type] || Settings;
        const colorClass = TYPE_COLORS[event.type] || TYPE_COLORS.system;
        const isLast = i === events.length - 1;

        return (
          <div
            key={event.id}
            className="relative flex gap-3 pb-6"
            data-testid={`timeline-event-${event.id}`}
          >
            {/* Line */}
            {!isLast && (
              <div className="absolute left-4 top-8 bottom-0 w-px bg-border" />
            )}

            {/* Icon */}
            <div
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full z-10",
                colorClass
              )}
            >
              <Icon className="h-3.5 w-3.5" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 pt-0.5">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-foreground">
                  {event.title}
                </p>
                <time className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatRelativeTime(event.timestamp)}
                </time>
              </div>
              {event.description && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {event.description}
                </p>
              )}
              {event.user && (
                <div className="flex items-center gap-1.5 mt-1.5">
                  <Avatar className="h-5 w-5">
                    <AvatarFallback className="text-[9px]">
                      {event.user.name?.slice(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-xs text-muted-foreground">{event.user.name}</span>
                </div>
              )}
              {event.metadata && Object.keys(event.metadata).length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {Object.entries(event.metadata).map(([key, value]) => (
                    <span
                      key={key}
                      className="inline-flex items-center rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground"
                    >
                      {key}: {value}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default Timeline;
