import React, { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// React Query client with default options
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});

// ─── Eager imports (critical path) ───
import LoginPage from "./pages/LoginPage";
import B2BLoginPage from "./b2b/B2BLoginPage";
import B2BAuthGuard from "./b2b/B2BAuthGuard";
import B2BLayout from "./b2b/B2BLayout";
import UnauthorizedPage from "./pages/UnauthorizedPage";
import RequireAuth from "./components/RequireAuth";
import AppShell from "./components/AppShell";
import AdminLayout from "./layouts/AdminLayout";
import AgencyLayout from "./layouts/AgencyLayout";
import HotelLayout from "./layouts/HotelLayout";
import { Navigate } from "react-router-dom";
import NotFoundPage from "./pages/NotFoundPage";
import { Toaster } from "./components/ui/sonner";
import { useTheme } from "./theme/useTheme";
import { getBrandNameFromThemeCache } from "./hooks/useSeo";

// ─── Loading fallback ───
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
        <span className="text-sm text-muted-foreground font-medium">Yükleniyor...</span>
      </div>
    </div>
  );
}

// ─── Lazy imports (code-split pages) ───
const B2BBookingsPage = lazy(() => import("./b2b/pages/B2BBookingsPage"));
const B2BBookingDetailPage = lazy(() => import("./b2b/pages/B2BBookingDetailPage"));
const B2BAccountPage = lazy(() => import("./b2b/pages/B2BAccountPage"));
const PublicMyBookingRequestPage = lazy(() => import("./pages/PublicMyBookingRequestPage"));
const PublicMyBookingDetailPage = lazy(() => import("./pages/PublicMyBookingDetailPage"));
const PublicClickToPayPage = lazy(() => import("./pages/public/PublicClickToPayPage"));
const BookSearchPage = lazy(() => import("./pages/public/BookSearchPage"));
const BookProductPage = lazy(() => import("./pages/public/BookProductPage"));
const BookCheckoutPage = lazy(() => import("./pages/public/BookCheckoutPage"));
const BookCompletePage = lazy(() => import("./pages/public/BookCompletePage"));
const BookTourProductPage = lazy(() => import("./pages/public/BookTourProductPage"));
const BookTourCheckoutPage = lazy(() => import("./pages/public/BookTourCheckoutPage"));
const PublicCMSPage = lazy(() => import("./pages/public/PublicCMSPage"));
const PublicCampaignPage = lazy(() => import("./pages/public/PublicCampaignPage"));
const PublicPartnerApplyPage = lazy(() => import("./pages/public/PublicPartnerApplyPage"));
const SignupPage = lazy(() => import("./pages/public/SignupPage"));
const PricingPage = lazy(() => import("./pages/public/PricingPage"));
const WebPOSPage = lazy(() => import("./pages/WebPOSPage"));
const AdvancedReportsPage = lazy(() => import("./pages/AdvancedReportsPage"));
const OnboardingWizardPage = lazy(() => import("./pages/OnboardingWizardPage"));
const PublicHomePage = lazy(() => import("./pages/PublicHomePage"));
const StorefrontSearchPage = lazy(() => import("./pages/storefront/StorefrontSearchPage"));
const StorefrontOfferPage = lazy(() => import("./pages/storefront/StorefrontOfferPage"));
const StorefrontCheckoutPage = lazy(() => import("./pages/storefront/StorefrontCheckoutPage"));

const AdminAgenciesPage = lazy(() => import("./pages/AdminAgenciesPage"));
const AdminAgencyUsersPage = lazy(() => import("./pages/AdminAgencyUsersPage"));
const AdminAgencyModulesPage = lazy(() => import("./pages/AdminAgencyModulesPage"));
const AdminAllUsersPage = lazy(() => import("./pages/AdminAllUsersPage"));
const ResetPasswordPage = lazy(() => import("./pages/ResetPasswordPage"));
const AdminHotelsPage = lazy(() => import("./pages/AdminHotelsPage"));
const AdminToursPage = lazy(() => import("./pages/AdminToursPage"));
const AdminLinksPage = lazy(() => import("./pages/AdminLinksPage"));
const AdminAgencyContractsPage = lazy(() => import("./pages/AdminAgencyContractsPage"));
const AdminCMSPagesPage = lazy(() => import("./pages/AdminCMSPagesPage"));
const AdminAuditLogsPage = lazy(() => import("./pages/AdminAuditLogsPage"));
const AdminEmailLogsPage = lazy(() => import("./pages/AdminEmailLogsPage"));
const AdminPilotDashboardPage = lazy(() => import("./pages/AdminPilotDashboardPage"));
const AdminMetricsPage = lazy(() => import("./pages/AdminMetricsPage"));
const AdminMatchAlertsPolicyPage = lazy(() => import("./pages/AdminMatchAlertsPolicyPage"));

// Enterprise Hardening (E1-E4) pages
const AdminBrandingPage = lazy(() => import("./pages/AdminBrandingPage"));
const AdminApprovalInboxPage = lazy(() => import("./pages/AdminApprovalInboxPage"));
const AdminTenantExportPage = lazy(() => import("./pages/AdminTenantExportPage"));
const AdminScheduledReportsPage = lazy(() => import("./pages/AdminScheduledReportsPage"));

// Feature modules
const AdminEFaturaPage = lazy(() => import("./pages/AdminEFaturaPage"));
const AdminSMSPage = lazy(() => import("./pages/AdminSMSPage"));
const AdminTicketsPage = lazy(() => import("./pages/AdminTicketsPage"));

// Operational Excellence
const AdminSystemBackupsPage = lazy(() => import("./pages/admin/AdminSystemBackupsPage"));
const AdminSystemIntegrityPage = lazy(() => import("./pages/admin/AdminSystemIntegrityPage"));
const AdminSystemMetricsPage = lazy(() => import("./pages/admin/AdminSystemMetricsPage"));
const AdminSystemErrorsPage = lazy(() => import("./pages/admin/AdminSystemErrorsPage"));
const AdminSystemUptimePage = lazy(() => import("./pages/admin/AdminSystemUptimePage"));
const AdminSystemIncidentsPage = lazy(() => import("./pages/admin/AdminSystemIncidentsPage"));
const AdminPreflightPage = lazy(() => import("./pages/admin/AdminPreflightPage"));
const AdminRunbookPage = lazy(() => import("./pages/admin/AdminRunbookPage"));
const AdminPerfDashboardPage = lazy(() => import("./pages/admin/AdminPerfDashboardPage"));
const AdminDemoGuidePage = lazy(() => import("./pages/admin/AdminDemoGuidePage"));
const AdminProductModePage = lazy(() => import("./pages/admin/AdminProductModePage"));
const AdminImportPage = lazy(() => import("./pages/admin/AdminImportPage"));
const AdminPortfolioSyncPage = lazy(() => import("./pages/admin/AdminPortfolioSyncPage"));

const AdminMatchesPage = lazy(() => import("./pages/AdminMatchesPage"));
const AdminExportsPage = lazy(() => import("./pages/AdminExportsPage"));
const AdminMatchDetailPage = lazy(() => import("./pages/AdminMatchDetailPage"));
const AdminMatchRiskTrendsPage = lazy(() => import("./pages/AdminMatchRiskTrendsPage"));
const AdminActionPoliciesPage = lazy(() => import("./pages/AdminActionPoliciesPage"));
const AdminApprovalsPage = lazy(() => import("./pages/AdminApprovalsPage"));
const AdminCatalogPage = lazy(() => import("./pages/AdminCatalogPage"));
const AdminCatalogHotelsPage = lazy(() => import("./pages/AdminCatalogHotelsPage"));
const AdminPricingPage = lazy(() => import("./pages/AdminPricingPage"));
const AdminPricingRulesPage = lazy(() => import("./pages/AdminPricingRulesPage"));
const AdminFunnelPage = lazy(() => import("./pages/AdminFunnelPage"));
const AdminB2BFunnelPage = lazy(() => import("./pages/AdminB2BFunnelPage"));
const AdminB2BAnnouncementsPage = lazy(() => import("./pages/AdminB2BAnnouncementsPage"));
const AdminB2BDashboardPage = lazy(() => import("./pages/AdminB2BDashboardPage"));
const AdminExecutiveDashboardPage = lazy(() => import("./pages/AdminExecutiveDashboardPage"));
const AdminB2BMarketplacePage = lazy(() => import("./pages/AdminB2BMarketplacePage"));
const AdminMarketplaceListingsPage = lazy(() => import("./pages/marketplace/AdminMarketplaceListingsPage"));
const B2BMarketplaceCatalogPage = lazy(() => import("./pages/marketplace/B2BMarketplaceCatalogPage"));
const AdminThemePage = lazy(() => import("./pages/AdminThemePage"));
const AdminReportingPage = lazy(() => import("./pages/AdminReportingPage"));
const AdminVillaCalendarPage = lazy(() => import("./pages/AdminVillaCalendarPage"));
const AdminPricingIncidentsPage = lazy(() => import("./pages/AdminPricingIncidentsPage"));
const AdminB2BDiscountsPage = lazy(() => import("./pages/AdminB2BDiscountsPage"));
const AdminCouponsPage = lazy(() => import("./pages/AdminCouponsPage"));
const AdminCampaignsPage = lazy(() => import("./pages/AdminCampaignsPage"));
const AdminIntegrationsPage = lazy(() => import("./pages/AdminIntegrationsPage"));
const AdminPartnersPage = lazy(() => import("./pages/AdminPartnersPage"));
const AdminJobsPage = lazy(() => import("./pages/AdminJobsPage"));
const AdminApiKeysPage = lazy(() => import("./pages/AdminApiKeysPage"));
const OpsB2BQueuesPage = lazy(() => import("./pages/OpsB2BQueuesPage"));
const InboxPage = lazy(() => import("./pages/InboxPage"));
const PartnerInboxPage = lazy(() => import("./pages/partners/PartnerInboxPage"));
const PartnerDiscoveryPage = lazy(() => import("./pages/partners/PartnerDiscoveryPage"));
const AdminFinanceRefundsPage = lazy(() => import("./pages/AdminFinanceRefundsPage"));
const PartnerInvitesPage = lazy(() => import("./pages/partners/PartnerInvitesPage"));
const PartnerRelationshipsPage = lazy(() => import("./pages/partners/PartnerRelationshipsPage"));
const PartnerStatementsPage = lazy(() => import("./pages/partners/PartnerStatementsPage"));
const PartnerLayout = lazy(() => import("./pages/partners/PartnerLayout"));
const PartnerOverviewPage = lazy(() => import("./pages/partners/PartnerOverviewPage"));
const PartnerB2BNetworkPage = lazy(() => import("./pages/partners/PartnerB2BNetworkPage"));

const AdminOpsIncidentsPage = lazy(() => import("./pages/ops/AdminOpsIncidentsPage"));
const AdminFinanceExposurePage = lazy(() => import("./pages/AdminFinanceExposurePage"));
const AdminB2BAgenciesSummaryPage = lazy(() => import("./pages/AdminB2BAgenciesSummaryPage"));
const AdminB2BAgencyProductsPage = lazy(() => import("./pages/AdminB2BAgencyProductsPage"));
const AdminSettlementsPage = lazy(() => import("./pages/AdminSettlementsPage"));
const AdminSettlementRunsPage = lazy(() => import("./pages/AdminSettlementRunsPage"));
const AdminSettlementRunDetailPage = lazy(() => import("./pages/AdminSettlementRunDetailPage"));
const OpsSupplierAccrualsPage = lazy(() => import("./pages/OpsSupplierAccrualsPage"));
const AdminSupplierSettlementBridgePage = lazy(() => import("./pages/AdminSupplierSettlementBridgePage"));
const AdminTenantFeaturesPage = lazy(() => import("./pages/admin/AdminTenantFeaturesPage"));
const AdminAuditLogPage = lazy(() => import("./pages/admin/AdminAuditLogPage"));
const AdminAnalyticsPage = lazy(() => import("./pages/admin/AdminAnalyticsPage"));
const AdminTenantHealthPage = lazy(() => import("./pages/admin/AdminTenantHealthPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ProductsPage = lazy(() => import("./pages/ProductsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const ReservationsPage = lazy(() => import("./pages/ReservationsPage"));
const CustomersPage = lazy(() => import("./pages/CustomersPage"));
const B2BPage = lazy(() => import("./pages/B2BPage"));
const B2BBookingPage = lazy(() => import("./pages/B2BBookingPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const SettingsSecurityPage = lazy(() => import("./pages/SettingsSecurityPage"));
const AgencyHotelsPage = lazy(() => import("./pages/AgencyHotelsPage"));
const AgencyAvailabilityPage = lazy(() => import("./pages/AgencyAvailabilityPage"));
const AgencyHotelDetailPage = lazy(() => import("./pages/AgencyHotelDetailPage"));
const AgencyHotelSearchPage = lazy(() => import("./pages/AgencyHotelSearchPage"));
const AgencySearchResultsPage = lazy(() => import("./pages/AgencySearchResultsPage"));
const AgencyBookingNewPage = lazy(() => import("./pages/AgencyBookingNewPage"));
const AgencyBookingTestPage = lazy(() => import("./pages/AgencyBookingTestPage"));
const SimpleBookingTest = lazy(() => import("./pages/SimpleBookingTest"));
const WebBookingPage = lazy(() => import("./pages/WebBookingPage"));
const AgencyBookingDraftPage = lazy(() => import("./pages/AgencyBookingDraftPage"));
const AgencyBookingConfirmedPage = lazy(() => import("./pages/AgencyBookingConfirmedPage"));
const AgencyBookingPendingPage = lazy(() => import("./pages/AgencyBookingPendingPage"));
const AgencyBookingsListPage = lazy(() => import("./pages/AgencyBookingsListPage"));
const AgencySettlementsPage = lazy(() => import("./pages/AgencySettlementsPage"));
const AgencyHelpPage = lazy(() => import("./pages/AgencyHelpPage"));
const AgencySheetConnectionsPage = lazy(() => import("./pages/AgencySheetConnectionsPage"));
const B2BPortalPage = lazy(() => import("./pages/B2BPortalPage"));
const OpsGuestCasesPage = lazy(() => import("./pages/OpsGuestCasesPage"));
const OpsBookingDetailPage = lazy(() => import("./pages/ops/OpsBookingDetailPage"));
const CrmCustomersPage = lazy(() => import("./pages/crm/CrmCustomersPage"));
const CrmCustomerDetailPage = lazy(() => import("./pages/crm/CrmCustomerDetailPage"));
const CrmTasksPage = lazy(() => import("./pages/crm/CrmTasksPage"));
const CrmEventsPage = lazy(() => import("./pages/crm/CrmEventsPage"));
const CrmPipelinePage = lazy(() => import("./pages/crm/CrmPipelinePage"));
const CrmDuplicateCustomersPage = lazy(() => import("./pages/crm/CrmDuplicateCustomersPage"));
const OpsTasksPage = lazy(() => import("./pages/OpsTasksPage"));
const ToursListPage = lazy(() => import("./pages/ToursListPage"));
const TourDetailPage = lazy(() => import("./pages/TourDetailPage"));

const HotelBookingsPage = lazy(() => import("./pages/HotelBookingsPage"));
const HotelStopSellPage = lazy(() => import("./pages/HotelStopSellPage"));
const HotelAllocationsPage = lazy(() => import("./pages/HotelAllocationsPage"));
const HotelSettlementsPage = lazy(() => import("./pages/HotelSettlementsPage"));
const HotelIntegrationsPage = lazy(() => import("./pages/HotelIntegrationsPage"));
const HotelHelpPage = lazy(() => import("./pages/HotelHelpPage"));
const ErrorContextPage = lazy(() => import("./pages/ErrorContextPage"));
const PrivacyPolicyPage = lazy(() => import("./pages/PrivacyPolicyPage"));
const TermsOfServicePage = lazy(() => import("./pages/TermsOfServicePage"));

function App() {
  // Load theme on app mount
  useTheme();

  // Global Organization + WebSite JSON-LD (tekil)
  if (typeof document !== "undefined") {
    const origin = window.location.origin;
    const brandName = getBrandNameFromThemeCache();

    const existingOrg = document.getElementById("org-schema-jsonld");
    if (!existingOrg) {
      const script = document.createElement("script");
      script.id = "org-schema-jsonld";
      script.type = "application/ld+json";
      script.text = JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Organization",
        name: brandName,
        url: origin,
      });
      document.head.appendChild(script);
    }

    const existingSite = document.getElementById("website-schema-jsonld");
    if (!existingSite) {
      const script = document.createElement("script");
      script.id = "website-schema-jsonld";
      script.type = "application/ld+json";
      script.text = JSON.stringify({
        "@context": "https://schema.org",
        "@type": "WebSite",
        name: brandName,
        url: origin,
        potentialAction: {
          "@type": "SearchAction",
          target: `${origin}/book?q={search_term_string}`,
          "query-input": "required name=search_term_string",
        },
      });
      document.head.appendChild(script);
    }
  }

  return (
    <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<PublicHomePage />} />
        <Route path="/s/:tenantKey" element={<StorefrontSearchPage />} />
        <Route path="/s/:tenantKey/search" element={<StorefrontSearchPage />} />
        <Route path="/s/:tenantKey/offers/:offerId" element={<StorefrontOfferPage />} />
        <Route path="/s/:tenantKey/checkout" element={<StorefrontCheckoutPage />} />
        <Route path="/privacy" element={<PrivacyPolicyPage />} />
        <Route path="/terms" element={<TermsOfServicePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/b2b/login" element={<B2BLoginPage />} />
        <Route path="/test/booking" element={<AgencyBookingTestPage />} />
        <Route path="/test/simple" element={<SimpleBookingTest />} />
        <Route path="/booking" element={<WebBookingPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="/pay/:token" element={<PublicClickToPayPage />} />
        <Route path="/book" element={<BookSearchPage />} />
        <Route path="/book/:productId" element={<BookProductPage />} />
        <Route path="/book/:productId/checkout" element={<BookCheckoutPage />} />
        <Route path="/book/complete" element={<BookCompletePage />} />
        <Route path="/book/tour/:tourId" element={<BookTourProductPage />} />
        <Route path="/book/tour/:tourId/checkout" element={<BookTourCheckoutPage />} />
        <Route path="/p/:slug" element={<PublicCMSPage />} />
        <Route path="/campaigns/:slug" element={<PublicCampaignPage />} />
        <Route path="/partners/apply" element={<PublicPartnerApplyPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/pricing" element={<PricingPage />} />

        {/* Admin Routes */}
        <Route
          path="/app/admin/*"
          element={
            <RequireAuth roles={["super_admin", "admin"]}>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route element={<AdminLayout />}>
            <Route path="agencies" element={<AdminAgenciesPage />} />
            <Route path="agencies/:agencyId/users" element={<AdminAgencyUsersPage />} />
            <Route path="agency-modules" element={<AdminAgencyModulesPage />} />
            <Route path="all-users" element={<AdminAllUsersPage />} />
            <Route path="b2b/dashboard" element={<AdminB2BDashboardPage />} />
            <Route path="b2b/marketplace" element={<AdminB2BMarketplacePage />} />
            <Route path="hotels" element={<AdminHotelsPage />} />
            <Route path="tours" element={<AdminToursPage />} />
            <Route path="links" element={<AdminLinksPage />} />
            <Route path="agency-contracts" element={<AdminAgencyContractsPage />} />
            <Route path="cms/pages" element={<AdminCMSPagesPage />} />
            <Route path="audit" element={<AdminAuditLogsPage />} />
            <Route path="email-logs" element={<AdminEmailLogsPage />} />
            <Route path="pilot-dashboard" element={<AdminPilotDashboardPage />} />
            <Route path="metrics" element={<AdminMetricsPage />} />
            <Route path="matches" element={<AdminMatchesPage />} />
            <Route path="matches/:id" element={<AdminMatchDetailPage />} />
            <Route path="reports/match-risk" element={<AdminMatchesPage />} />
            <Route path="reports/match-risk-trends" element={<AdminMatchRiskTrendsPage />} />
            <Route path="settings/match-alerts" element={<AdminMatchAlertsPolicyPage />} />
            <Route path="settings/action-policies" element={<AdminActionPoliciesPage />} />
            <Route path="catalog" element={<AdminCatalogPage />} />
            <Route path="catalog/hotels" element={<AdminCatalogHotelsPage />} />
            <Route path="pricing" element={<AdminPricingPage />} />
            <Route path="pricing/rules" element={<AdminPricingRulesPage />} />
            <Route path="pricing/funnel" element={<AdminFunnelPage />} />
            <Route path="b2b/funnel" element={<AdminB2BFunnelPage />} />
            <Route path="marketplace/listings" element={<AdminMarketplaceListingsPage />} />
            <Route path="b2b/announcements" element={<AdminB2BAnnouncementsPage />} />
            <Route path="pricing/incidents" element={<AdminPricingIncidentsPage />} />
            <Route path="b2b/discounts" element={<AdminB2BDiscountsPage />} />
            <Route path="dashboard" element={<AdminExecutiveDashboardPage />} />
            <Route path="partners" element={<AdminPartnersPage />} />
            <Route path="integrations" element={<AdminIntegrationsPage />} />
            <Route path="jobs" element={<AdminJobsPage />} />
            <Route path="api-keys" element={<AdminApiKeysPage />} />
            <Route path="reporting" element={<AdminReportingPage />} />
            <Route path="villas/:productId/calendar" element={<AdminVillaCalendarPage />} />
            <Route path="theme" element={<AdminThemePage />} />
            <Route path="coupons" element={<AdminCouponsPage />} />
            <Route path="campaigns" element={<AdminCampaignsPage />} />
            <Route path="approvals" element={<AdminApprovalsPage />} />
            <Route path="exports" element={<AdminExportsPage />} />
            <Route path="finance/refunds" element={<AdminFinanceRefundsPage />} />
            <Route path="finance/exposure" element={<AdminFinanceExposurePage />} />
            <Route path="finance/b2b-agencies" element={<AdminB2BAgenciesSummaryPage />} />
            <Route path="admin/b2b/agency-products" element={<AdminB2BAgencyProductsPage />} />
            <Route path="finance/settlements" element={<AdminSettlementsPage />} />
            <Route path="finance/settlement-runs" element={<AdminSettlementRunsPage />} />
            <Route path="finance/settlement-runs/:settlementId" element={<AdminSettlementRunDetailPage />} />
            <Route path="ops/finance/supplier-accruals" element={<OpsSupplierAccrualsPage />} />
            <Route path="finance/supplier-settlement-bridge" element={<AdminSupplierSettlementBridgePage />} />
            <Route path="ops/b2b" element={<OpsB2BQueuesPage />} />
            <Route path="tenant-features" element={<AdminTenantFeaturesPage />} />
            <Route path="audit-logs" element={<AdminAuditLogPage />} />
            <Route path="analytics" element={<AdminAnalyticsPage />} />
            <Route path="tenant-health" element={<AdminTenantHealthPage />} />
            {/* Enterprise Hardening (E1-E4) */}
            <Route path="branding" element={<AdminBrandingPage />} />
            <Route path="approval-inbox" element={<AdminApprovalInboxPage />} />
            <Route path="tenant-export" element={<AdminTenantExportPage />} />
            <Route path="scheduled-reports" element={<AdminScheduledReportsPage />} />
            {/* Feature modules */}
            <Route path="efatura" element={<AdminEFaturaPage />} />
            <Route path="sms" element={<AdminSMSPage />} />
            <Route path="tickets" element={<AdminTicketsPage />} />
            {/* Operational Excellence (O1-O5) */}
            <Route path="system-backups" element={<AdminSystemBackupsPage />} />
            <Route path="system-integrity" element={<AdminSystemIntegrityPage />} />
            <Route path="system-metrics" element={<AdminSystemMetricsPage />} />
            <Route path="system-errors" element={<AdminSystemErrorsPage />} />
            <Route path="system-uptime" element={<AdminSystemUptimePage />} />
            <Route path="system-incidents" element={<AdminSystemIncidentsPage />} />
            {/* Production Go-Live Pack */}
            <Route path="preflight" element={<AdminPreflightPage />} />
            <Route path="runbook" element={<AdminRunbookPage />} />
            {/* Cost/Performance Pack */}
            <Route path="perf-dashboard" element={<AdminPerfDashboardPage />} />
            {/* Enterprise Demo Pack */}
            <Route path="demo-guide" element={<AdminDemoGuidePage />} />
            {/* Product Mode Settings */}
            <Route path="product-mode" element={<AdminProductModePage />} />
            {/* Data & Migration */}
            <Route path="import" element={<AdminImportPage />} />
            <Route path="portfolio-sync" element={<AdminPortfolioSyncPage />} />
          </Route>
        </Route>

        {/* Inbox Route moved under /app/* so that it renders inside AppShell */}
        {/* Core App Routes (Dashboard, Products, CRM, etc.) */}
        <Route
          path="/app/*"
          element={
            <RequireAuth
              roles={["admin", "sales", "ops", "accounting", "b2b_agent", "super_admin", "agency_admin", "agency_agent"]}
            >
              <AppShell />
            </RequireAuth>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="onboarding" element={<OnboardingWizardPage />} />
          <Route path="b2b/marketplace" element={<B2BMarketplaceCatalogPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="reservations" element={<ReservationsPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="b2b" element={<B2BPage />} />
          <Route path="b2b-book" element={<B2BBookingPage />} />
          <Route path="reports" element={<AdvancedReportsPage />} />
          <Route path="finance/webpos" element={<WebPOSPage />} />
          <Route path="settings/security" element={<SettingsSecurityPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="inbox" element={<InboxPage />} />
          <Route path="partners" element={<PartnerLayout />}>
            <Route index element={<PartnerOverviewPage />} />
            <Route path="inbox" element={<PartnerInboxPage />} />
            <Route path="discovery" element={<PartnerDiscoveryPage />} />
            <Route path="b2b" element={<PartnerB2BNetworkPage />} />
            <Route path="invites" element={<PartnerInvitesPage />} />
            <Route path="relationships" element={<PartnerRelationshipsPage />} />
            <Route path="statements" element={<PartnerStatementsPage />} />
            <Route path="relationships-old" element={<Navigate to="/app/partners/invites" replace />} />
            <Route path="invites-old" element={<Navigate to="/app/partners/invites" replace />} />
          </Route>
          <Route path="crm/customers" element={<CrmCustomersPage />} />
          <Route path="crm/duplicates" element={<CrmDuplicateCustomersPage />} />
          <Route path="crm/pipeline" element={<CrmPipelinePage />} />
          <Route path="crm/tasks" element={<CrmTasksPage />} />
          <Route path="crm/events" element={<CrmEventsPage />} />
          <Route path="crm/customers/:customerId" element={<CrmCustomerDetailPage />} />
          <Route path="ops/guest-cases" element={<OpsGuestCasesPage />} />
          <Route path="ops/bookings/:bookingId" element={<OpsBookingDetailPage />} />
          <Route path="ops/tasks" element={<OpsTasksPage />} />
          <Route path="ops/incidents" element={<AdminOpsIncidentsPage />} />
          <Route path="tours" element={<ToursListPage />} />
          <Route path="tours/:tourId" element={<TourDetailPage />} />
        </Route>

        {/* B2B Portal Routes (New, outside /app shell, dedicated layout) */}
        <Route
          path="/b2b/*"
          element={
            <B2BAuthGuard>
              <B2BLayout />
            </B2BAuthGuard>
          }
        >
          <Route path="bookings" element={<B2BBookingsPage />} />
          <Route path="bookings/:bookingId" element={<B2BBookingDetailPage />} />
          <Route path="account" element={<B2BAccountPage />} />
        </Route>

        {/* Agency Routes (Core Flow) */}
        <Route path="/app/b2b/portal" element={<B2BPortalPage />} />

        <Route
          path="/app/agency/*"
          element={
            <RequireAuth roles={["agency_admin", "agency_agent", "admin", "super_admin"]}>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route element={<AgencyLayout />}>
            <Route path="hotels" element={<AgencyHotelsPage />} />
            <Route path="hotels/:hotelId" element={<AgencyHotelDetailPage />} />
            <Route path="hotels/:hotelId/search" element={<AgencyHotelSearchPage />} />
            <Route path="availability" element={<AgencyAvailabilityPage />} />
            <Route path="sheets" element={<AgencySheetConnectionsPage />} />
            <Route path="search" element={<AgencySearchResultsPage />} />
            <Route path="booking/new" element={<AgencyBookingNewPage />} />
            <Route path="booking/draft/:draftId" element={<AgencyBookingDraftPage />} />
            <Route path="booking/confirmed/:bookingId" element={<AgencyBookingConfirmedPage />} />
            <Route path="booking/pending/:bookingId" element={<AgencyBookingPendingPage />} />
            <Route path="bookings" element={<AgencyBookingsListPage />} />
            <Route path="settlements" element={<AgencySettlementsPage />} />
            <Route path="help" element={<AgencyHelpPage />} />
          </Route>
        </Route>

        {/* Public self-service my-booking routes */}
        <Route path="/my-booking" element={<PublicMyBookingRequestPage />} />
        <Route path="/my-booking/:token" element={<PublicMyBookingDetailPage />} />
        <Route path="/app/reset-password" element={<ResetPasswordPage />} />
        <Route path="/error-context" element={<ErrorContextPage />} />

        {/* Hotel Routes */}
        <Route
          path="/app/hotel/*"
          element={
            <RequireAuth roles={["hotel_admin", "hotel_staff"]}>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route element={<HotelLayout />}>
            <Route path="bookings" element={<HotelBookingsPage />} />
            <Route path="stop-sell" element={<HotelStopSellPage />} />
            <Route path="allocations" element={<HotelAllocationsPage />} />
            <Route path="settlements" element={<HotelSettlementsPage />} />
            <Route path="integrations" element={<HotelIntegrationsPage />} />
            <Route path="help" element={<HotelHelpPage />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      </Suspense>
      <Toaster position="top-right" richColors closeButton />
    </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
