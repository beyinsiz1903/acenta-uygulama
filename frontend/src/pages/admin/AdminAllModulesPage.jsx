import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, LayoutGrid, Search, ShieldCheck, Sparkles } from "lucide-react";

import PageHeader from "../../components/PageHeader";
import { Badge } from "../../components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import {
  ADMIN_MODULE_SECTIONS,
  ADMIN_NAV_SECTIONS,
  APP_NAV_SECTIONS,
  buildScopedNavSections,
} from "../../lib/appNavigation";
import { cn } from "../../lib/utils";

const SECTION_DESCRIPTIONS = {
  "ANA MENÜ": "Çekirdek ürün akışları ve günlük operasyon ekranları.",
  "ADMIN MERKEZ": "Tenant, kullanıcı, audit ve platform yönetimi ekranları.",
  "KATALOG & İÇERİK": "Ürün, içerik, tema ve katalog yönetimi modülleri.",
  "B2B & BÜYÜME": "B2B kanal, partner ağı ve büyüme operasyonları.",
  "FİNANS & RAPORLAMA": "Fiyatlandırma, mutabakat, export ve analitik yüzeyleri.",
  "OPERASYON & SİSTEM": "Sistem dayanıklılığı, entegrasyon ve operasyon modülleri.",
  "DOĞRUDAN ERİŞİM": "Sidebar dışında kalan ama admin erişimine açık operasyon ekranları.",
};

function slugify(value) {
  return String(value || "section")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function ModuleStatCard({ title, value, subtitle, testId }) {
  return (
    <Card className="border-border/70 shadow-sm" data-testid={testId}>
      <CardHeader className="pb-3">
        <CardDescription className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          {title}
        </CardDescription>
        <CardTitle className="text-3xl font-semibold tracking-tight text-foreground">{value}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground" data-testid={`${testId}-subtitle`}>{subtitle}</p>
      </CardContent>
    </Card>
  );
}

function ModuleLinkCard({ item, sectionLabel, isSidebarItem }) {
  const Icon = item.icon || LayoutGrid;

  return (
    <Link
      to={item.to}
      className="group flex h-full items-start justify-between gap-4 rounded-2xl border border-border/70 bg-background/80 p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
      data-testid={`admin-module-link-${item.key}`}
    >
      <div className="min-w-0 space-y-3">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl border border-primary/10 bg-primary/5 p-2 text-primary" data-testid={`admin-module-icon-${item.key}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground" data-testid={`admin-module-title-${item.key}`}>{item.label}</p>
            <p className="truncate text-xs text-muted-foreground" data-testid={`admin-module-section-${item.key}`}>{sectionLabel}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="outline"
            className={cn(
              "rounded-full border px-2 py-0.5 text-[11px]",
              isSidebarItem ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-600"
            )}
            data-testid={`admin-module-badge-${item.key}`}
          >
            {isSidebarItem ? "Sidebar" : "Ek modül"}
          </Badge>
          <Badge variant="outline" className="rounded-full px-2 py-0.5 text-[11px]" data-testid={`admin-module-route-badge-${item.key}`}>
            {item.to}
          </Badge>
        </div>
      </div>

      <ArrowUpRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-colors duration-200 group-hover:text-primary" />
    </Link>
  );
}

export default function AdminAllModulesPage() {
  const [search, setSearch] = useState("");

  const coreSections = useMemo(
    () => buildScopedNavSections(APP_NAV_SECTIONS.filter((section) => section.showInSidebar !== false), "admin"),
    [],
  );
  const moduleSections = useMemo(() => buildScopedNavSections(ADMIN_MODULE_SECTIONS, "admin"), []);
  const sidebarAdminSections = useMemo(() => buildScopedNavSections(ADMIN_NAV_SECTIONS, "admin"), []);

  const sidebarKeys = useMemo(() => {
    return new Set(
      [...coreSections, ...sidebarAdminSections]
        .flatMap((section) => section.items)
        .filter((item) => item.to)
        .map((item) => item.key),
    );
  }, [coreSections, sidebarAdminSections]);

  const registrySections = useMemo(() => {
    return [...coreSections, ...moduleSections]
      .map((section) => ({
        ...section,
        items: (section.items || []).filter((item) => item.to),
      }))
      .filter((section) => section.items.length > 0);
  }, [coreSections, moduleSections]);

  const filteredSections = useMemo(() => {
    const term = search.trim().toLowerCase();
    return registrySections
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => {
          if (!term) return true;
          return [item.label, item.to, section.group].join(" ").toLowerCase().includes(term);
        }),
      }))
      .filter((section) => section.items.length > 0);
  }, [registrySections, search]);

  const totalRoutes = registrySections.reduce((sum, section) => sum + section.items.length, 0);
  const sidebarCount = sidebarKeys.size;
  const extraCount = Math.max(totalRoutes - sidebarCount, 0);
  const filteredCount = filteredSections.reduce((sum, section) => sum + section.items.length, 0);

  return (
    <div className="space-y-6" data-testid="admin-all-modules-page">
      <PageHeader
        title="Tüm Modüller"
        subtitle="Sidebar bilinçli olarak sadeleştirildi. Super admin erişimine açık tüm ekranları buradan arayıp açabilirsiniz."
        icon={<LayoutGrid className="h-5 w-5" />}
      />

      <Card className="overflow-hidden border-primary/15 bg-[linear-gradient(135deg,rgba(37,99,235,0.06),rgba(14,165,233,0.02))] shadow-sm" data-testid="admin-modules-hero-card">
        <CardContent className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/15 bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-primary" data-testid="admin-modules-hero-badge">
              <Sparkles className="h-3.5 w-3.5" />
              Super admin görünürlüğü
            </div>
            <p className="max-w-2xl text-sm leading-6 text-slate-700" data-testid="admin-modules-hero-text">
              Günlük kullanılan çekirdek ekranlar sidebar&apos;da kaldı. Daha seyrek kullanılan yönetici yüzeyleri, operasyon araçları ve ileri modüller bu katalog ekranında toplandı.
            </p>
          </div>

          <div className="w-full max-w-md">
            <label className="relative block" data-testid="admin-modules-search-wrapper">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Sayfa, route veya grup ara"
                className="h-11 rounded-full border-white/80 bg-white/90 pl-10 shadow-sm"
                data-testid="admin-modules-search-input"
              />
            </label>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3" data-testid="admin-modules-stats-grid">
        <ModuleStatCard title="Toplam erişim" value={totalRoutes} subtitle="Super admin için kataloglanan toplam sayfa" testId="admin-modules-stat-total" />
        <ModuleStatCard title="Sidebar çekirdeği" value={sidebarCount} subtitle="Hızlı erişim için solda tutulan sayfalar" testId="admin-modules-stat-sidebar" />
        <ModuleStatCard
          title="Arama sonucu"
          value={filteredCount}
          subtitle={search ? `“${search}” için eşleşen sayfa sayısı` : `${extraCount} ek modül katalog ekranında listeleniyor`}
          testId="admin-modules-stat-results"
        />
      </div>

      <div className="space-y-5" data-testid="admin-modules-sections">
        {filteredSections.map((section) => (
          <Card key={section.group} className="border-border/70 shadow-sm" data-testid={`admin-module-group-${slugify(section.group)}`}>
            <CardHeader className="border-b border-border/60 pb-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <CardTitle className="text-lg font-semibold text-foreground" data-testid={`admin-module-group-title-${slugify(section.group)}`}>
                    {section.group}
                  </CardTitle>
                  <CardDescription className="mt-1 text-sm leading-6 text-muted-foreground" data-testid={`admin-module-group-description-${slugify(section.group)}`}>
                    {SECTION_DESCRIPTIONS[section.group] || "Bu gruptaki tüm ekranlar super admin erişimine açıktır."}
                  </CardDescription>
                </div>
                <Badge variant="outline" className="w-fit rounded-full px-3 py-1 text-xs" data-testid={`admin-module-group-count-${slugify(section.group)}`}>
                  {section.items.length} sayfa
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-5">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid={`admin-module-group-grid-${slugify(section.group)}`}>
                {section.items.map((item) => (
                  <ModuleLinkCard key={item.key} item={item} sectionLabel={section.group} isSidebarItem={sidebarKeys.has(item.key)} />
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredCount === 0 ? (
        <Card className="border-dashed" data-testid="admin-modules-empty-state">
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <div className="rounded-full bg-muted p-3 text-muted-foreground">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground" data-testid="admin-modules-empty-title">Sonuç bulunamadı</p>
              <p className="mt-1 text-sm text-muted-foreground" data-testid="admin-modules-empty-description">
                Arama ifadesini değiştirin veya route parçalarıyla tekrar deneyin.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}