/**
 * Platform Hardening — shared helpers.
 */
import React from "react";
import { Badge } from "../../components/ui/badge";

export const severityColor = (s) =>
  ({ critical: "destructive", high: "default", medium: "secondary", low: "outline" }[s] || "outline");

export const statusBadge = (s) => {
  if (s === "done" || s === "completed")
    return <Badge data-testid="status-done" className="bg-emerald-600 text-white">Done</Badge>;
  if (s === "in_progress")
    return <Badge data-testid="status-progress" className="bg-amber-500 text-white">In Progress</Badge>;
  return <Badge data-testid="status-planned" variant="outline">Planned</Badge>;
};
