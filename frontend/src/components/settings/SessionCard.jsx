import React from "react";
import { Clock3, LaptopMinimal, MapPin, ShieldCheck, Smartphone, Trash2 } from "lucide-react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { formatSessionRelative, formatSessionTimestamp, getSessionDeviceInfo } from "../../lib/sessionSecurity";
import { cn } from "../../lib/utils";

export const SessionCard = ({ session, isCurrent, isBusy, onRevoke }) => {
  const sessionInfo = getSessionDeviceInfo(session?.user_agent);
  const DeviceIcon = sessionInfo.deviceType === "mobile" ? Smartphone : LaptopMinimal;

  return (
    <Card
      className={cn(
        "overflow-hidden rounded-3xl border-border/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.7),rgba(248,250,252,0.95))] shadow-sm",
        isCurrent && "border-primary/35 shadow-md"
      )}
      data-testid={`active-session-card-${session.id}`}
    >
      <CardContent className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1 space-y-4">
            <div className="flex flex-wrap items-start gap-3">
              <div className="rounded-2xl border border-border/60 bg-background/90 p-3 text-primary">
                <DeviceIcon className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3
                    className="text-base font-semibold text-foreground"
                    data-testid={`active-session-device-${session.id}`}
                  >
                    {sessionInfo.deviceLabel}
                  </h3>
                  {isCurrent ? (
                    <Badge data-testid={`active-session-current-badge-${session.id}`}>Bu cihaz</Badge>
                  ) : (
                    <Badge variant="secondary" data-testid={`active-session-remote-badge-${session.id}`}>
                      Aktif
                    </Badge>
                  )}
                </div>
                <p
                  className="mt-2 break-words text-sm text-muted-foreground"
                  data-testid={`active-session-user-agent-${session.id}`}
                >
                  {sessionInfo.userAgentLabel}
                </p>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-border/60 bg-background/80 px-4 py-3">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                  <MapPin className="h-3.5 w-3.5" /> IP
                </div>
                <div className="mt-2 text-sm font-medium text-foreground" data-testid={`active-session-ip-${session.id}`}>
                  {session.ip_address || "Bilinmiyor"}
                </div>
              </div>

              <div className="rounded-2xl border border-border/60 bg-background/80 px-4 py-3">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                  <ShieldCheck className="h-3.5 w-3.5" /> Son aktif
                </div>
                <div className="mt-2 text-sm font-medium text-foreground" data-testid={`active-session-last-used-${session.id}`}>
                  {formatSessionRelative(session.last_used_at)}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">{formatSessionTimestamp(session.last_used_at)}</div>
              </div>

              <div className="rounded-2xl border border-border/60 bg-background/80 px-4 py-3">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                  <Clock3 className="h-3.5 w-3.5" /> Oluşturuldu
                </div>
                <div className="mt-2 text-sm font-medium text-foreground" data-testid={`active-session-created-${session.id}`}>
                  {formatSessionTimestamp(session.created_at)}
                </div>
              </div>
            </div>
          </div>

          <div className="flex shrink-0 items-start lg:pl-4">
            <Button
              variant="destructive"
              size="sm"
              disabled={isBusy}
              onClick={() => onRevoke(session)}
              data-testid={`revoke-session-button-${session.id}`}
            >
              <Trash2 className="h-4 w-4" />
              Bu oturumu kapat
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};