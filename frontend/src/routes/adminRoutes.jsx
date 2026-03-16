import { lazy } from "react";
import { Route, Navigate } from "react-router-dom";

// ─── Lazy imports: Admin pages ───
const AdminAgenciesPage = lazy(() => import("../pages/AdminAgenciesPage"));
const AdminAgencyUsersPage = lazy(() => import("../pages/AdminAgencyUsersPage"));
const AdminAgencyModulesPage = lazy(() => import("../pages/AdminAgencyModulesPage"));
const AdminAllUsersPage = lazy(() => import("../pages/AdminAllUsersPage"));
const AdminHotelsPage = lazy(() => import("../pages/AdminHotelsPage"));
const AdminToursPage = lazy(() => import("../pages/AdminToursPage"));
const AdminLinksPage = lazy(() => import("../pages/AdminLinksPage"));
const AdminAgencyContractsPage = lazy(() => import("../pages/AdminAgencyContractsPage"));
const AdminCMSPagesPage = lazy(() => import("../pages/AdminCMSPagesPage"));
const AdminAuditLogsPage = lazy(() => import("../pages/AdminAuditLogsPage"));
const AdminEmailLogsPage = lazy(() => import("../pages/AdminEmailLogsPage"));
const AdminPilotDashboardPage = lazy(() => import("../pages/AdminPilotDashboardPage"));
const PilotSetupWizardPage = lazy(() => import("../pages/PilotSetupWizardPage"));
const PilotOnboardingDashboardPage = lazy(() => import("../pages/PilotOnboardingDashboardPage"));
const InventorySyncDashboardPage = lazy(() => import("../pages/InventorySyncDashboardPage"));
const AdminMetricsPage = lazy(() => import("../pages/AdminMetricsPage"));
const AdminMatchAlertsPolicyPage = lazy(() => import("../pages/AdminMatchAlertsPolicyPage"));
const AdminBrandingPage = lazy(() => import("../pages/AdminBrandingPage"));
const AdminApprovalInboxPage = lazy(() => import("../pages/AdminApprovalInboxPage"));
const AdminTenantExportPage = lazy(() => import("../pages/AdminTenantExportPage"));
const AdminScheduledReportsPage = lazy(() => import("../pages/AdminScheduledReportsPage"));
const AdminEFaturaPage = lazy(() => import("../pages/AdminEFaturaPage"));
const AdminAccountingPage = lazy(() => import("../pages/AdminAccountingPage"));
const AdminAccountingProvidersPage = lazy(() => import("../pages/AdminAccountingProvidersPage"));
const AdminFinanceOpsPage = lazy(() => import("../pages/AdminFinanceOpsPage"));
const AdminSMSPage = lazy(() => import("../pages/AdminSMSPage"));
const AdminTicketsPage = lazy(() => import("../pages/AdminTicketsPage"));
const AdminSystemBackupsPage = lazy(() => import("../pages/admin/AdminSystemBackupsPage"));
const AdminSystemIntegrityPage = lazy(() => import("../pages/admin/AdminSystemIntegrityPage"));
const AdminSystemMetricsPage = lazy(() => import("../pages/admin/AdminSystemMetricsPage"));
const AdminSystemErrorsPage = lazy(() => import("../pages/admin/AdminSystemErrorsPage"));
const AdminSystemUptimePage = lazy(() => import("../pages/admin/AdminSystemUptimePage"));
const AdminSystemIncidentsPage = lazy(() => import("../pages/admin/AdminSystemIncidentsPage"));
const AdminPreflightPage = lazy(() => import("../pages/admin/AdminPreflightPage"));
const AdminRunbookPage = lazy(() => import("../pages/admin/AdminRunbookPage"));
const AdminPerfDashboardPage = lazy(() => import("../pages/admin/AdminPerfDashboardPage"));
const AdminDemoGuidePage = lazy(() => import("../pages/admin/AdminDemoGuidePage"));
const AdminProductModePage = lazy(() => import("../pages/admin/AdminProductModePage"));
const AdminImportPage = lazy(() => import("../pages/admin/AdminImportPage"));
const AdminPortfolioSyncPage = lazy(() => import("../pages/admin/AdminPortfolioSyncPage"));
const AdminAllModulesPage = lazy(() => import("../pages/admin/AdminAllModulesPage"));
const ProductionActivationPage = lazy(() => import("../pages/admin/ProductionActivationPage"));
const PlatformHardeningPage = lazy(() => import("../pages/admin/PlatformHardeningPage"));
const AdminMatchesPage = lazy(() => import("../pages/AdminMatchesPage"));
const AdminExportsPage = lazy(() => import("../pages/AdminExportsPage"));
const AdminMatchDetailPage = lazy(() => import("../pages/AdminMatchDetailPage"));
const AdminMatchRiskTrendsPage = lazy(() => import("../pages/AdminMatchRiskTrendsPage"));
const AdminActionPoliciesPage = lazy(() => import("../pages/AdminActionPoliciesPage"));
const AdminApprovalsPage = lazy(() => import("../pages/AdminApprovalsPage"));
const AdminCatalogPage = lazy(() => import("../pages/AdminCatalogPage"));
const AdminCatalogHotelsPage = lazy(() => import("../pages/AdminCatalogHotelsPage"));
const AdminPricingPage = lazy(() => import("../pages/AdminPricingPage"));
const AdminPricingRulesPage = lazy(() => import("../pages/AdminPricingRulesPage"));
const AdminFunnelPage = lazy(() => import("../pages/AdminFunnelPage"));
const AdminB2BFunnelPage = lazy(() => import("../pages/AdminB2BFunnelPage"));
const AdminB2BAnnouncementsPage = lazy(() => import("../pages/AdminB2BAnnouncementsPage"));
const AdminB2BDashboardPage = lazy(() => import("../pages/AdminB2BDashboardPage"));
const AdminExecutiveDashboardPage = lazy(() => import("../pages/AdminExecutiveDashboardPage"));
const AdminB2BMarketplacePage = lazy(() => import("../pages/AdminB2BMarketplacePage"));
const AdminMarketplaceListingsPage = lazy(() => import("../pages/marketplace/AdminMarketplaceListingsPage"));
const AdminThemePage = lazy(() => import("../pages/AdminThemePage"));
const AdminReportingPage = lazy(() => import("../pages/AdminReportingPage"));
const AdminVillaCalendarPage = lazy(() => import("../pages/AdminVillaCalendarPage"));
const AdminPricingIncidentsPage = lazy(() => import("../pages/AdminPricingIncidentsPage"));
const AdminB2BDiscountsPage = lazy(() => import("../pages/AdminB2BDiscountsPage"));
const AdminCouponsPage = lazy(() => import("../pages/AdminCouponsPage"));
const AdminCampaignsPage = lazy(() => import("../pages/AdminCampaignsPage"));
const AdminIntegrationsPage = lazy(() => import("../pages/AdminIntegrationsPage"));
const AdminPartnersPage = lazy(() => import("../pages/AdminPartnersPage"));
const AdminJobsPage = lazy(() => import("../pages/AdminJobsPage"));
const AdminApiKeysPage = lazy(() => import("../pages/AdminApiKeysPage"));
const OpsB2BQueuesPage = lazy(() => import("../pages/OpsB2BQueuesPage"));
const AdminFinanceRefundsPage = lazy(() => import("../pages/AdminFinanceRefundsPage"));
const AdminFinanceExposurePage = lazy(() => import("../pages/AdminFinanceExposurePage"));
const AdminB2BAgenciesSummaryPage = lazy(() => import("../pages/AdminB2BAgenciesSummaryPage"));
const AdminB2BAgencyProductsPage = lazy(() => import("../pages/AdminB2BAgencyProductsPage"));
const AdminSettlementsPage = lazy(() => import("../pages/AdminSettlementsPage"));
const AdminSettlementRunsPage = lazy(() => import("../pages/AdminSettlementRunsPage"));
const AdminSettlementRunDetailPage = lazy(() => import("../pages/AdminSettlementRunDetailPage"));
const OpsSupplierAccrualsPage = lazy(() => import("../pages/OpsSupplierAccrualsPage"));
const AdminSupplierSettlementBridgePage = lazy(() => import("../pages/AdminSupplierSettlementBridgePage"));
const AdminTenantFeaturesPage = lazy(() => import("../pages/admin/AdminTenantFeaturesPage"));
const AdminAuditLogPage = lazy(() => import("../pages/admin/AdminAuditLogPage"));
const AdminAnalyticsPage = lazy(() => import("../pages/admin/AdminAnalyticsPage"));
const AdminTenantHealthPage = lazy(() => import("../pages/admin/AdminTenantHealthPage"));
const ReconciliationDashboardPage = lazy(() => import("../pages/admin/ReconciliationDashboardPage"));
const KPIAnalyticsDashboardPage = lazy(() => import("../pages/admin/KPIAnalyticsDashboardPage"));
const SupplierEconomicsPage = lazy(() => import("../pages/admin/SupplierEconomicsPage"));
const RevenueOptimizationPage = lazy(() => import("../pages/admin/RevenueOptimizationPage"));
const PlatformMonitoringPage = lazy(() => import("../pages/admin/PlatformMonitoringPage"));
const OperationsReadinessPage = lazy(() => import("../pages/admin/OperationsReadinessPage"));
const MarketLaunchPage = lazy(() => import("../pages/admin/MarketLaunchPage"));
const AdminSupplierCredentialsPage = lazy(() => import("../pages/admin/AdminSupplierCredentialsPage"));
const SupplierOnboardingPage = lazy(() => import("../pages/admin/SupplierOnboardingPage"));
const SupplierCertificationConsolePage = lazy(() => import("../pages/admin/SupplierCertificationConsolePage"));
const CacheHealthDashboardPage = lazy(() => import("../pages/admin/CacheHealthDashboardPage"));
const GrowthEnginePage = lazy(() => import("../pages/admin/GrowthEnginePage"));

/**
 * Admin route children — rendered inside AdminLayout.
 * Parent: /app/admin/*
 */
export const adminRoutes = (
  <>
    <Route index element={<Navigate to="dashboard" replace />} />
    {/* Core Admin */}
    <Route path="dashboard" element={<AdminExecutiveDashboardPage />} />
    <Route path="agencies" element={<AdminAgenciesPage />} />
    <Route path="agencies/:agencyId/users" element={<AdminAgencyUsersPage />} />
    <Route path="agency-modules" element={<AdminAgencyModulesPage />} />
    <Route path="all-users" element={<AdminAllUsersPage />} />
    <Route path="hotels" element={<AdminHotelsPage />} />
    <Route path="tours" element={<AdminToursPage />} />
    <Route path="links" element={<AdminLinksPage />} />
    <Route path="agency-contracts" element={<AdminAgencyContractsPage />} />
    <Route path="partners" element={<AdminPartnersPage />} />
    <Route path="integrations" element={<AdminIntegrationsPage />} />
    <Route path="jobs" element={<AdminJobsPage />} />
    <Route path="api-keys" element={<AdminApiKeysPage />} />
    {/* B2B */}
    <Route path="b2b/dashboard" element={<AdminB2BDashboardPage />} />
    <Route path="b2b/marketplace" element={<AdminB2BMarketplacePage />} />
    <Route path="b2b/funnel" element={<AdminB2BFunnelPage />} />
    <Route path="b2b/announcements" element={<AdminB2BAnnouncementsPage />} />
    <Route path="b2b/discounts" element={<AdminB2BDiscountsPage />} />
    <Route path="b2b/agency-products" element={<AdminB2BAgencyProductsPage />} />
    <Route path="admin/b2b/agency-products" element={<AdminB2BAgencyProductsPage />} />
    {/* Content & Marketing */}
    <Route path="cms/pages" element={<AdminCMSPagesPage />} />
    <Route path="theme" element={<AdminThemePage />} />
    <Route path="coupons" element={<AdminCouponsPage />} />
    <Route path="campaigns" element={<AdminCampaignsPage />} />
    <Route path="branding" element={<AdminBrandingPage />} />
    {/* Catalog & Pricing */}
    <Route path="catalog" element={<AdminCatalogPage />} />
    <Route path="catalog/hotels" element={<AdminCatalogHotelsPage />} />
    <Route path="pricing" element={<AdminPricingPage />} />
    <Route path="pricing/rules" element={<AdminPricingRulesPage />} />
    <Route path="pricing/funnel" element={<AdminFunnelPage />} />
    <Route path="pricing/incidents" element={<AdminPricingIncidentsPage />} />
    <Route path="marketplace/listings" element={<AdminMarketplaceListingsPage />} />
    {/* Finance */}
    <Route path="finance/refunds" element={<AdminFinanceRefundsPage />} />
    <Route path="finance/exposure" element={<AdminFinanceExposurePage />} />
    <Route path="finance/b2b-agencies" element={<AdminB2BAgenciesSummaryPage />} />
    <Route path="finance/settlements" element={<AdminSettlementsPage />} />
    <Route path="finance/settlement-runs" element={<AdminSettlementRunsPage />} />
    <Route path="finance/settlement-runs/:settlementId" element={<AdminSettlementRunDetailPage />} />
    <Route path="finance/supplier-settlement-bridge" element={<AdminSupplierSettlementBridgePage />} />
    <Route path="finance-ops" element={<AdminFinanceOpsPage />} />
    <Route path="efatura" element={<AdminEFaturaPage />} />
    <Route path="accounting" element={<AdminAccountingPage />} />
    <Route path="accounting-providers" element={<AdminAccountingProvidersPage />} />
    {/* Operations */}
    <Route path="ops/finance/supplier-accruals" element={<OpsSupplierAccrualsPage />} />
    <Route path="ops/b2b" element={<OpsB2BQueuesPage />} />
    {/* Monitoring & Analytics */}
    <Route path="metrics" element={<AdminMetricsPage />} />
    <Route path="reporting" element={<AdminReportingPage />} />
    <Route path="analytics" element={<AdminAnalyticsPage />} />
    <Route path="analytics-kpi" element={<KPIAnalyticsDashboardPage />} />
    <Route path="reconciliation" element={<ReconciliationDashboardPage />} />
    <Route path="supplier-economics" element={<SupplierEconomicsPage />} />
    <Route path="revenue-optimization" element={<RevenueOptimizationPage />} />
    <Route path="platform-monitoring" element={<PlatformMonitoringPage />} />
    <Route path="perf-dashboard" element={<AdminPerfDashboardPage />} />
    {/* Matches & Risk */}
    <Route path="matches" element={<AdminMatchesPage />} />
    <Route path="matches/:id" element={<AdminMatchDetailPage />} />
    <Route path="reports/match-risk" element={<AdminMatchesPage />} />
    <Route path="reports/match-risk-trends" element={<AdminMatchRiskTrendsPage />} />
    <Route path="settings/match-alerts" element={<AdminMatchAlertsPolicyPage />} />
    <Route path="settings/action-policies" element={<AdminActionPoliciesPage />} />
    {/* Governance & Audit */}
    <Route path="audit" element={<AdminAuditLogsPage />} />
    <Route path="audit-logs" element={<AdminAuditLogPage />} />
    <Route path="email-logs" element={<AdminEmailLogsPage />} />
    <Route path="approvals" element={<AdminApprovalsPage />} />
    <Route path="approval-inbox" element={<AdminApprovalInboxPage />} />
    <Route path="exports" element={<AdminExportsPage />} />
    <Route path="scheduled-reports" element={<AdminScheduledReportsPage />} />
    <Route path="tenant-export" element={<AdminTenantExportPage />} />
    <Route path="tenant-features" element={<AdminTenantFeaturesPage />} />
    <Route path="tenant-health" element={<AdminTenantHealthPage />} />
    <Route path="modules" element={<AdminAllModulesPage />} />
    {/* Inventory & Supplier */}
    <Route path="inventory-sync" element={<InventorySyncDashboardPage />} />
    <Route path="supplier-credentials" element={<AdminSupplierCredentialsPage />} />
    <Route path="supplier-onboarding" element={<SupplierOnboardingPage />} />
    <Route path="certification-console" element={<SupplierCertificationConsolePage />} />
    <Route path="cache-health" element={<CacheHealthDashboardPage />} />
    <Route path="villas/:productId/calendar" element={<AdminVillaCalendarPage />} />
    {/* Pilot & Onboarding */}
    <Route path="pilot-dashboard" element={<AdminPilotDashboardPage />} />
    <Route path="pilot-wizard" element={<PilotSetupWizardPage />} />
    <Route path="pilot-onboarding" element={<PilotOnboardingDashboardPage />} />
    {/* System & Platform */}
    <Route path="system-backups" element={<AdminSystemBackupsPage />} />
    <Route path="system-integrity" element={<AdminSystemIntegrityPage />} />
    <Route path="system-metrics" element={<AdminSystemMetricsPage />} />
    <Route path="system-errors" element={<AdminSystemErrorsPage />} />
    <Route path="system-uptime" element={<AdminSystemUptimePage />} />
    <Route path="system-incidents" element={<AdminSystemIncidentsPage />} />
    <Route path="preflight" element={<AdminPreflightPage />} />
    <Route path="runbook" element={<AdminRunbookPage />} />
    <Route path="platform-hardening" element={<PlatformHardeningPage />} />
    <Route path="production-activation" element={<ProductionActivationPage />} />
    <Route path="operations-readiness" element={<OperationsReadinessPage />} />
    <Route path="market-launch" element={<MarketLaunchPage />} />
    <Route path="growth-engine" element={<GrowthEnginePage />} />
    {/* Data & Migration */}
    <Route path="import" element={<AdminImportPage />} />
    <Route path="google-sheets" element={<Navigate to="/app/admin/portfolio-sync" replace />} />
    <Route path="portfolio-sync" element={<AdminPortfolioSyncPage />} />
    {/* Communication */}
    <Route path="sms" element={<AdminSMSPage />} />
    <Route path="tickets" element={<AdminTicketsPage />} />
    {/* Settings & Demo */}
    <Route path="product-mode" element={<AdminProductModePage />} />
    <Route path="demo-guide" element={<AdminDemoGuidePage />} />
  </>
);
