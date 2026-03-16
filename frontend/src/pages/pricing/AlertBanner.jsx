import React from "react";
import { Bell, BellOff, AlertTriangle } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "../../components/ui/tooltip";

export function AlertBanner({ alerts, onClear }) {
  const activeAlerts = alerts?.active_alerts;
  if (!activeAlerts?.length) return null;

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 flex items-center gap-3" data-testid="hit-rate-alert-banner">
      <div className="bg-amber-100 p-2 rounded-lg">
        <Bell className="w-4 h-4 text-amber-600" />
      </div>
      <div className="flex-1">
        {activeAlerts.map((a, i) => (
          <div key={i} className="flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span className="text-sm text-amber-800 font-medium">{a.message}</span>
            <Badge variant="outline" className="text-[10px] border-amber-300 text-amber-700 ml-1">
              {a.type}
            </Badge>
          </div>
        ))}
      </div>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="ghost" size="sm" onClick={onClear} className="h-7 px-2 text-amber-600 hover:text-amber-700" data-testid="clear-alerts-btn">
            <BellOff className="w-3.5 h-3.5" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>Alert gecmisini temizle</TooltipContent>
      </Tooltip>
    </div>
  );
}
