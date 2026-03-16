import React from "react";
import { Badge } from "../../../components/ui/badge";

export function RefundStatusBadge({ status }) {
  if (!status) return <Badge variant="outline">-</Badge>;
  switch (status) {
    case "open":
      return <Badge variant="outline">Acik</Badge>;
    case "pending_approval_1":
    case "pending_approval":
      return <Badge variant="outline">1. onay bekliyor</Badge>;
    case "pending_approval_2":
      return <Badge variant="outline">2. onay bekliyor</Badge>;
    case "approved":
      return <Badge variant="secondary">Onaylandi</Badge>;
    case "paid":
      return <Badge variant="secondary">Odendi</Badge>;
    case "rejected":
      return <Badge variant="destructive" className="gap-1">Reddedildi</Badge>;
    case "closed":
      return <Badge variant="secondary">Kapali</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export function TaskStatusBadge({ status }) {
  if (!status) return <Badge variant="outline" className="text-2xs px-1 py-0">-</Badge>;
  switch (status) {
    case "open":
      return <Badge variant="outline" className="text-2xs px-1 py-0">Acik</Badge>;
    case "in_progress":
      return <Badge variant="default" className="text-2xs px-1 py-0">Devam ediyor</Badge>;
    case "done":
      return <Badge variant="secondary" className="text-2xs px-1 py-0">Tamamlandi</Badge>;
    case "cancelled":
      return <Badge variant="destructive" className="text-2xs px-1 py-0">Iptal</Badge>;
    default:
      return <Badge variant="outline" className="text-2xs px-1 py-0">{status}</Badge>;
  }
}

export function PriorityBadge({ priority }) {
  if (!priority) return null;
  switch (priority) {
    case "high":
      return <Badge variant="destructive" className="text-2xs px-1 py-0">Yuksek</Badge>;
    case "medium":
      return <Badge variant="default" className="text-2xs px-1 py-0">Orta</Badge>;
    case "low":
      return <Badge variant="outline" className="text-2xs px-1 py-0">Dusuk</Badge>;
    default:
      return <Badge variant="outline" className="text-2xs px-1 py-0">{priority}</Badge>;
  }
}
