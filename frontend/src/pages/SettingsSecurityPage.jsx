import React, { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, RefreshCw, ShieldCheck, SmartphoneNfc } from "lucide-react";

import { toast } from "../components/ui/sonner";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { api, apiErrorMessage, clearToken, getUser } from "../lib/api";
import { authKeys, useCurrentUser } from "../hooks/useAuth";
import { sortSessionsByActivity } from "../lib/sessionSecurity";
import { SessionCard } from "../components/settings/SessionCard";
import { SessionRevokeDialog } from "../components/settings/SessionRevokeDialog";
import { SettingsSectionNav } from "../components/settings/SettingsSectionNav";

const sessionQueryKey = ["auth", "sessions", "list"];

function SessionListSkeleton() {
  return (
    <div className="space-y-3" data-testid="active-sessions-loading">
      {[0, 1, 2].map((item) => (
        <div key={item} className="rounded-3xl border border-border/60 bg-card/80 p-5">
          <div className="flex flex-col gap-4">
            <div className="flex items-start gap-3">
              <Skeleton className="h-12 w-12 rounded-2xl" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-4 w-full max-w-[32rem]" />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <Skeleton className="h-20 rounded-2xl" />
              <Skeleton className="h-20 rounded-2xl" />
              <Skeleton className="h-20 rounded-2xl" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function SettingsSecurityPage() {
  const queryClient = useQueryClient();
  const [dialogState, setDialogState] = useState({ open: false, mode: null, session: null });

  const cachedUser = getUser();
  const canManageUsers = (cachedUser?.roles || []).some((role) => ["super_admin", "admin"].includes(role));

  const currentUserQuery = useCurrentUser();
  const sessionsQuery = useQuery({
    queryKey: sessionQueryKey,
    queryFn: async () => {
      const response = await api.get("/auth/sessions");
      return Array.isArray(response.data) ? response.data : [];
    },
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  });

  const currentSessionId = currentUserQuery.data?.current_session_id || cachedUser?.current_session_id || "";
  const sessions = useMemo(
    () => sortSessionsByActivity(sessionsQuery.data || [], currentSessionId),
    [currentSessionId, sessionsQuery.data]
  );
  const otherSessions = sessions.filter((session) => session.id !== currentSessionId);

  const revokeSingleMutation = useMutation({
    mutationFn: async (sessionId) => {
      await api.post(`/auth/sessions/${sessionId}/revoke`);
      return sessionId;
    },
  });

  const revokeOthersMutation = useMutation({
    mutationFn: async (sessionIds) => {
      const results = [];

      for (const sessionId of sessionIds) {
        try {
          await api.post(`/auth/sessions/${sessionId}/revoke`);
          results.push({ status: "fulfilled", sessionId });
        } catch (error) {
          results.push({ status: "rejected", sessionId, error });
        }
      }

      return {
        total: sessionIds.length,
        revoked: results.filter((result) => result.status === "fulfilled").length,
        failed: results.filter((result) => result.status === "rejected").length,
      };
    },
  });

  const dialogLoading = dialogState.mode === "others"
    ? revokeOthersMutation.isPending
    : revokeSingleMutation.isPending;

  async function refreshSessions() {
    await Promise.all([
      sessionsQuery.refetch(),
      queryClient.invalidateQueries({ queryKey: authKeys.user() }),
    ]);
  }

  function openSingleRevokeDialog(session) {
    setDialogState({ open: true, mode: "single", session });
  }

  function openOtherSessionsDialog() {
    setDialogState({ open: true, mode: "others", session: null });
  }

  async function handleDialogConfirm() {
    try {
      if (dialogState.mode === "others") {
        const result = await revokeOthersMutation.mutateAsync(otherSessions.map((session) => session.id));
        setDialogState({ open: false, mode: null, session: null });
        await refreshSessions();

        if (result.failed > 0) {
          toast(`${result.revoked} oturum kapatıldı, ${result.failed} oturum kapatılamadı.`);
        } else {
          toast.success(`${result.revoked} diğer oturum kapatıldı.`);
        }
        return;
      }

      const revokedSessionId = await revokeSingleMutation.mutateAsync(dialogState.session.id);
      const revokedCurrentSession = revokedSessionId === currentSessionId;

      if (revokedCurrentSession) {
        toast.success("Bu cihazdaki oturum kapatıldı. Yeniden giriş yapmanız gerekiyor.");
        clearToken();
        queryClient.clear();
        window.location.assign("/login?reason=session_revoked");
        return;
      }

      setDialogState({ open: false, mode: null, session: null });
      await refreshSessions();
      toast.success("Oturum kapatıldı.");
    } catch (error) {
      toast.error(apiErrorMessage(error));
    }
  }

  return (
    <div className="space-y-6" data-testid="settings-security-page">
      <div className="space-y-3">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-foreground">Güvenlik</h1>
          <p className="mt-2 text-base text-muted-foreground" data-testid="settings-security-subtitle">
            Aktif cihazları görüntüleyin, mevcut oturumu ayırt edin ve ihtiyaç halinde oturumları sonlandırın.
          </p>
        </div>
        <SettingsSectionNav showUsersSection={canManageUsers} />
      </div>

      <Card
        className="overflow-hidden rounded-[28px] border border-border/60 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.12),transparent_44%),linear-gradient(180deg,rgba(255,255,255,0.94),rgba(248,250,252,0.98))] shadow-sm"
        data-testid="active-sessions-summary-card"
      >
        <CardHeader className="gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-xl">
              <ShieldCheck className="h-5 w-5 text-primary" /> Aktif Oturumlar
            </CardTitle>
            <CardDescription className="mt-2 max-w-2xl text-sm">
              “Bu oturumu kapat” yalnızca seçilen cihazı sonlandırır. “Diğer tüm oturumları kapat” ise mevcut cihazı açık bırakır.
            </CardDescription>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              variant="outline"
              onClick={() => sessionsQuery.refetch()}
              disabled={sessionsQuery.isFetching || revokeSingleMutation.isPending || revokeOthersMutation.isPending}
              data-testid="refresh-sessions-button"
            >
              {sessionsQuery.isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Listeyi yenile
            </Button>
            <Button
              variant="destructive"
              onClick={openOtherSessionsDialog}
              disabled={otherSessions.length === 0 || revokeOthersMutation.isPending || revokeSingleMutation.isPending}
              data-testid="revoke-other-sessions-button"
            >
              <SmartphoneNfc className="h-4 w-4" /> Diğer tüm oturumları kapat
            </Button>
          </div>
        </CardHeader>

        <CardContent className="grid gap-3 md:grid-cols-3">
          <div className="rounded-3xl border border-border/60 bg-background/80 p-4" data-testid="active-sessions-total-count">
            <div className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Toplam aktif</div>
            <div className="mt-2 text-3xl font-semibold text-foreground">{sessions.length}</div>
          </div>
          <div className="rounded-3xl border border-border/60 bg-background/80 p-4" data-testid="active-sessions-current-count">
            <div className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Bu cihaz</div>
            <div className="mt-2 text-3xl font-semibold text-foreground">{currentSessionId ? 1 : 0}</div>
          </div>
          <div className="rounded-3xl border border-border/60 bg-background/80 p-4" data-testid="active-sessions-other-count">
            <div className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">Diğer cihazlar</div>
            <div className="mt-2 text-3xl font-semibold text-foreground">{otherSessions.length}</div>
          </div>
        </CardContent>
      </Card>

      {sessionsQuery.isLoading ? <SessionListSkeleton /> : null}

      {!sessionsQuery.isLoading && sessionsQuery.isError ? (
        <div
          className="rounded-3xl border border-destructive/25 bg-destructive/5 px-4 py-3 text-sm text-destructive"
          data-testid="active-sessions-error"
        >
          {apiErrorMessage(sessionsQuery.error)}
        </div>
      ) : null}

      {!sessionsQuery.isLoading && !sessionsQuery.isError && sessions.length === 0 ? (
        <Card className="rounded-3xl border-dashed border-border/60" data-testid="active-sessions-empty-state">
          <CardContent className="flex flex-col items-start gap-3 p-6">
            <div className="rounded-2xl border border-border/60 bg-muted/30 p-3 text-primary">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">Aktif oturum bulunamadı</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Yeni giriş yaptığınızda bu ekranda cihaz geçmişiniz görünecek.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {!sessionsQuery.isLoading && !sessionsQuery.isError && sessions.length > 0 ? (
        <div className="space-y-3" data-testid="active-sessions-list">
          {sessions.map((session) => (
            <SessionCard
              key={session.id}
              session={session}
              isCurrent={session.id === currentSessionId}
              isBusy={revokeSingleMutation.isPending || revokeOthersMutation.isPending}
              onRevoke={openSingleRevokeDialog}
            />
          ))}
        </div>
      ) : null}

      <SessionRevokeDialog
        open={dialogState.open}
        mode={dialogState.mode}
        session={dialogState.session}
        currentSessionId={currentSessionId}
        otherSessionCount={otherSessions.length}
        loading={dialogLoading}
        onOpenChange={(open) => setDialogState((current) => ({ ...current, open }))}
        onConfirm={handleDialogConfirm}
      />
    </div>
  );
}