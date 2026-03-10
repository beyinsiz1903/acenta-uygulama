import React from "react";
import { Building2, Fingerprint, Mail, ShieldCheck, User2 } from "lucide-react";

import { Badge } from "../ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";

const ROLE_LABELS = {
  super_admin: "Süper Admin",
  admin: "Admin",
  agency_admin: "Acente Yöneticisi",
  agency_agent: "Acente Kullanıcısı",
  hotel_admin: "Otel Yöneticisi",
  hotel_staff: "Otel Personeli",
  sales: "Satış",
  ops: "Operasyon",
  accounting: "Muhasebe",
  b2b_agent: "B2B Kullanıcısı",
};

function getRoleLabel(role) {
  return ROLE_LABELS[role] || role;
}

export const UserProfileSummaryCard = ({ user, agencyName = "", canManageUsers = false, showBillingSection = true }) => {
  const roles = user?.roles || [];
  const agencyValue = agencyName || user?.agency_id || "Tanımlı değil";
  const tenantValue = user?.tenant_id || user?.organization_id || "Tanımlı değil";

  return (
    <Card className="overflow-hidden rounded-[28px] border-border/60 bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.10),transparent_32%),linear-gradient(180deg,rgba(255,255,255,0.95),rgba(248,250,252,0.98))] shadow-sm" data-testid="settings-profile-card">
      <CardHeader className="gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <CardTitle className="flex items-center gap-2 text-xl" data-testid="settings-profile-title">
            <User2 className="h-5 w-5 text-primary" /> Kullanıcı Bilgileri
          </CardTitle>
          <CardDescription className="mt-2 max-w-2xl text-sm" data-testid="settings-profile-description">
            Hesabınıza ait temel bilgiler burada görünür. {canManageUsers ? "Aşağıda ekip kullanıcılarını da yönetebilirsiniz." : showBillingSection ? "Güvenlik ve faturalama bağlantılarını bu sayfadan kullanabilirsiniz." : "Güvenlik ve şifre işlemlerini bu sayfadan yönetebilirsiniz."}
          </CardDescription>
        </div>

        <div className="flex flex-wrap gap-2" data-testid="settings-profile-role-list">
          {roles.length > 0 ? roles.map((role) => (
            <Badge key={role} variant="secondary" className="rounded-full border border-border/70 bg-background/80 px-3 py-1 text-xs font-medium" data-testid={`settings-profile-role-${role}`}>
              <ShieldCheck className="mr-1.5 h-3.5 w-3.5 text-primary" />
              {getRoleLabel(role)}
            </Badge>
          )) : (
            <Badge variant="secondary" className="rounded-full px-3 py-1 text-xs" data-testid="settings-profile-role-empty">
              Rol tanımlı değil
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-3xl border border-border/60 bg-background/80 p-4" data-testid="settings-profile-name-card">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <User2 className="h-3.5 w-3.5" /> Ad Soyad
          </div>
          <div className="mt-2 text-base font-semibold text-foreground" data-testid="settings-profile-name">
            {user?.name || "Tanımlanmadı"}
          </div>
        </div>

        <div className="rounded-3xl border border-border/60 bg-background/80 p-4" data-testid="settings-profile-email-card">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <Mail className="h-3.5 w-3.5" /> E-posta
          </div>
          <div className="mt-2 break-all text-base font-semibold text-foreground" data-testid="settings-profile-email">
            {user?.email || "Tanımlanmadı"}
          </div>
        </div>

        <div className="rounded-3xl border border-border/60 bg-background/80 p-4" data-testid="settings-profile-agency-card">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <Building2 className="h-3.5 w-3.5" /> Bağlı Acenta
          </div>
          <div className="mt-2 text-base font-semibold text-foreground" data-testid="settings-profile-agency">
            {agencyValue}
          </div>
        </div>

        <div className="rounded-3xl border border-border/60 bg-background/80 p-4" data-testid="settings-profile-tenant-card">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <Fingerprint className="h-3.5 w-3.5" /> Çalışma Alanı
          </div>
          <div className="mt-2 break-all text-sm font-semibold text-foreground" data-testid="settings-profile-tenant">
            {tenantValue}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};