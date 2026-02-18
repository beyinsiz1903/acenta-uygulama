import React, { Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

const LoginPage = React.lazy(() => import("./pages/LoginPage"));
const B2BLoginPage = React.lazy(() => import("./b2b/B2BLoginPage"));
const B2BAuthGuard = React.lazy(() => import("./b2b/B2BAuthGuard"));
const B2BLayout = React.lazy(() => import("./b2b/B2BLayout"));
const B2BBookingsPage = React.lazy(() => import("./b2b/pages/B2BBookingsPage"));
const B2BBookingDetailPage = React.lazy(() => import("./b2b/pages/B2BBookingDetailPage"));
const B2BAccountPage = React.lazy(() => import("./b2b/pages/B2BAccountPage"));
const UnauthorizedPage = React.lazy(() => import("./pages/UnauthorizedPage"));
const RequireAuth = React.lazy(() => import("./components/RequireAuth"));
const AppShell = React.lazy(() => import("./components/AppShell"));
const AdminLayout = React.lazy(() => import("./layouts/AdminLayout"));
const AgencyLayout = React.lazy(() => import("./layouts/AgencyLayout"));
const PublicMyBookingRequestPage = React.lazy(() => import("./pages/PublicMyBookingRequestPage"));
const PublicMyBookingDetailPage = React.lazy(() => import("./pages/PublicMyBookingDetailPage"));
const PublicClickToPayPage = React.lazy(() => import("./pages/public/PublicClickToPayPage"));
const BookSearchPage = React.lazy(() => import("./pages/public/BookSearchPage"));
const BookProductPage = React.lazy(() => import("./pages/public/BookProductPage"));
const BookCheckoutPage = React.lazy(() => import("./pages/public/BookCheckoutPage"));
const BookCompletePage = React.lazy(() => import("./pages/public/BookCompletePage"));
const BookTourProductPage = React.lazy(() => import("./pages/public/BookTourProductPage"));
const BookTourCheckoutPage = React.lazy(() => import("./pages/public/BookTourCheckoutPage"));
const PublicCMSPage = React.lazy(() => import("./pages/public/PublicCMSPage"));
const PublicCampaignPage = React.lazy(() => import("./pages/public/PublicCampaignPage"));
const PublicPartnerApplyPage = React.lazy(() => import("./pages/public/PublicPartnerApplyPage"));
const SignupPage = React.lazy(() => import("./pages/public/SignupPage"));
const PricingPage = React.lazy(() => import("./pages/public/PricingPage"));
const WebPOSPage = React.lazy(() => import("./pages/WebPOSPage"));
const AdvancedReportsPage = React.lazy(() => import("./pages/AdvancedReportsPage"));
const OnboardingWizardPage = React.lazy(() => import("./pages/OnboardingWizardPage"));
const PublicHomePage = React.lazy(() => import("./pages/PublicHomePage"));
const StorefrontSearchPage = React.lazy(() => import("./pages/storefront/StorefrontSearchPage"));
const StorefrontOfferPage = React.lazy(() => import("./pages/storefront/StorefrontOfferPage"));
const StorefrontCheckoutPage = React.lazy(() => import("./pages/storefront/StorefrontCheckoutPage"));

const HotelLayout = React.lazy(() => import("./layouts/HotelLayout"));
const AdminAgenciesPage = React.lazy(() => import("./pages/AdminAgenciesPage"));
const AdminAgencyUsersPage = React.lazy(() => import("./pages/AdminAgencyUsersPage"));
const ResetPasswordPage = React.lazy(() => import("./pages/ResetPasswordPage"));
const AdminHotelsPage = React.lazy(() => import("./pages/AdminHotelsPage"));
const AdminToursPage = React.lazy(() => import("./pages/AdminToursPage"));
const AdminLinksPage = React.lazy(() => import("./pages/AdminLinksPage"));
const AdminCMSPagesPage = React.lazy(() => import("./pages/AdminCMSPagesPage"));
const AdminAuditLogsPage = React.lazy(() => import("./pages/AdminAuditLogsPage"));
const AdminEmailLogsPage = React.lazy(() => import("./pages/AdminEmailLogsPage"));
const AdminPilotDashboardPage = React.lazy(() => import("./pages/AdminPilotDashboardPage"));
const AdminMetricsPage = React.lazy(() => import("./pages/AdminMetricsPage"));
const AdminMatchAlertsPolicyPage = React.lazy(() => import("./pages/AdminMatchAlertsPolicyPage"));

// Enterprise Hardening (E1-E4) pages
const AdminBrandingPage = React.lazy(() => import("./pages/AdminBrandingPage"));
const AdminApprovalInboxPage = React.lazy(() => import("./pages/AdminApprovalInboxPage"));
const AdminTenantExportPage = React.lazy(() => import("./pages/AdminTenantExportPage"));
const AdminScheduledReportsPage = React.lazy(() => import("./pages/AdminScheduledReportsPage"));

// Feature modules (E-Fatura, SMS, Tickets)
const AdminEFaturaPage = React.lazy(() => import("./pages/AdminEFaturaPage"));
const AdminSMSPage = React.lazy(() => import("./pages/AdminSMSPage"));
const AdminTicketsPage = React.lazy(() => import("./pages/AdminTicketsPage"));

// Operational Excellence (O1-O5)
const AdminSystemBackupsPage = React.lazy(() => import("./pages/admin/AdminSystemBackupsPage"));
const AdminSystemIntegrityPage = React.lazy(() => import("./pages/admin/AdminSystemIntegrityPage"));
const AdminSystemMetricsPage = React.lazy(() => import("./pages/admin/AdminSystemMetricsPage"));
const AdminSystemErrorsPage = React.lazy(() => import("./pages/admin/AdminSystemErrorsPage"));
const AdminSystemUptimePage = React.lazy(() => import("./pages/admin/AdminSystemUptimePage"));
const AdminSystemIncidentsPage = React.lazy(() => import("./pages/admin/AdminSystemIncidentsPage"));

// Production Go-Live Pack (A)
const AdminPreflightPage = React.lazy(() => import("./pages/admin/AdminPreflightPage"));
const AdminRunbookPage = React.lazy(() => import("./pages/admin/AdminRunbookPage"));

// Cost/Performance Pack (B)
const AdminPerfDashboardPage = React.lazy(() => import("./pages/admin/AdminPerfDashboardPage"));

// Enterprise Demo Pack (C)
const AdminDemoGuidePage = React.lazy(() => import("./pages/admin/AdminDemoGuidePage"));

// Product Mode Settings
const AdminProductModePage = React.lazy(() => import("./pages/admin/AdminProductModePage"));

// Data & Migration
const AdminImportPage = React.lazy(() => import("./pages/admin/AdminImportPage"));
const AdminPortfolioSyncPage = React.lazy(() => import("./pages/admin/AdminPortfolioSyncPage"));

const AdminMatchesPage = React.lazy(() => import("./pages/AdminMatchesPage"));
const AdminExportsPage = React.lazy(() => import("./pages/AdminExportsPage"));
const AdminMatchDetailPage = React.lazy(() => import("./pages/AdminMatchDetailPage"));
const AdminMatchRiskTrendsPage = React.lazy(() => import("./pages/AdminMatchRiskTrendsPage"));
const AdminActionPoliciesPage = React.lazy(() => import("./pages/AdminActionPoliciesPage"));
const AdminApprovalsPage = React.lazy(() => import("./pages/AdminApprovalsPage"));
const AdminCatalogPage = React.lazy(() => import("./pages/AdminCatalogPage"));
const AdminCatalogHotelsPage = React.lazy(() => import("./pages/AdminCatalogHotelsPage"));
const AdminPricingPage = React.lazy(() => import("./pages/AdminPricingPage"));
const AdminPricingRulesPage = React.lazy(() => import("./pages/AdminPricingRulesPage"));
const AdminFunnelPage = React.lazy(() => import("./pages/AdminFunnelPage"));
const AdminB2BFunnelPage = React.lazy(() => import("./pages/AdminB2BFunnelPage"));
const AdminB2BAnnouncementsPage = React.lazy(() => import("./pages/AdminB2BAnnouncementsPage"));
const AdminB2BDashboardPage = React.lazy(() => import("./pages/AdminB2BDashboardPage"));
const AdminExecutiveDashboardPage = React.lazy(() => import("./pages/AdminExecutiveDashboardPage"));
const AdminB2BMarketplacePage = React.lazy(() => import("./pages/AdminB2BMarketplacePage"));
const AdminMarketplaceListingsPage = React.lazy(() => import("./pages/marketplace/AdminMarketplaceListingsPage"));
const B2BMarketplaceCatalogPage = React.lazy(() => import("./pages/marketplace/B2BMarketplaceCatalogPage"));
const AdminThemePage = React.lazy(() => import("./pages/AdminThemePage"));
const AdminReportingPage = React.lazy(() => import("./pages/AdminReportingPage"));
const AdminVillaCalendarPage = React.lazy(() => import("./pages/AdminVillaCalendarPage"));
const AdminPricingIncidentsPage = React.lazy(() => import("./pages/AdminPricingIncidentsPage"));
const AdminB2BDiscountsPage = React.lazy(() => import("./pages/AdminB2BDiscountsPage"));
const AdminCouponsPage = React.lazy(() => import("./pages/AdminCouponsPage"));
const AdminCampaignsPage = React.lazy(() => import("./pages/AdminCampaignsPage"));
const AdminIntegrationsPage = React.lazy(() => import("./pages/AdminIntegrationsPage"));
const AdminPartnersPage = React.lazy(() => import("./pages/AdminPartnersPage"));
const AdminJobsPage = React.lazy(() => import("./pages/AdminJobsPage"));
const AdminApiKeysPage = React.lazy(() => import("./pages/AdminApiKeysPage"));
const OpsB2BQueuesPage = React.lazy(() => import("./pages/OpsB2BQueuesPage"));
const InboxPage = React.lazy(() => import("./pages/InboxPage"));
const PartnerInboxPage = React.lazy(() => import("./pages/partners/PartnerInboxPage"));
const PartnerDiscoveryPage = React.lazy(() => import("./pages/partners/PartnerDiscoveryPage"));
const AdminFinanceRefundsPage = React.lazy(() => import("./pages/AdminFinanceRefundsPage"));
const PartnerInvitesPage = React.lazy(() => import("./pages/partners/PartnerInvitesPage"));
const PartnerRelationshipsPage = React.lazy(() => import("./pages/partners/PartnerRelationshipsPage"));
const PartnerStatementsPage = React.lazy(() => import("./pages/partners/PartnerStatementsPage"));
const PartnerLayout = React.lazy(() => import("./pages/partners/PartnerLayout"));
const PartnerOverviewPage = React.lazy(() => import("./pages/partners/PartnerOverviewPage"));
const PartnerB2BNetworkPage = React.lazy(() => import("./pages/partners/PartnerB2BNetworkPage"));

const AdminOpsIncidentsPage = React.lazy(() => import("./pages/ops/AdminOpsIncidentsPage"));
const AdminFinanceExposurePage = React.lazy(() => import("./pages/AdminFinanceExposurePage"));
const AdminB2BAgenciesSummaryPage = React.lazy(() => import("./pages/AdminB2BAgenciesSummaryPage"));
const AdminB2BAgencyProductsPage = React.lazy(() => import("./pages/AdminB2BAgencyProductsPage"));
const AdminSettlementsPage = React.lazy(() => import("./pages/AdminSettlementsPage"));
const AdminSettlementRunsPage = React.lazy(() => import("./pages/AdminSettlementRunsPage"));
const AdminSettlementRunDetailPage = React.lazy(() => import("./pages/AdminSettlementRunDetailPage"));
const OpsSupplierAccrualsPage = React.lazy(() => import("./pages/OpsSupplierAccrualsPage"));
const AdminSupplierSettlementBridgePage = React.lazy(() => import("./pages/AdminSupplierSettlementBridgePage"));
const AdminTenantFeaturesPage = React.lazy(() => import("./pages/admin/AdminTenantFeaturesPage"));
const AdminAuditLogPage = React.lazy(() => import("./pages/admin/AdminAuditLogPage"));
const AdminAnalyticsPage = React.lazy(() => import("./pages/admin/AdminAnalyticsPage"));
const AdminTenantHealthPage = React.lazy(() => import("./pages/admin/AdminTenantHealthPage"));
const DashboardPage = React.lazy(() => import("./pages/DashboardPage"));
const ProductsPage = React.lazy(() => import("./pages/ProductsPage"));
const InventoryPage = React.lazy(() => import("./pages/InventoryPage"));
const ReservationsPage = React.lazy(() => import("./pages/ReservationsPage"));
const CustomersPage = React.lazy(() => import("./pages/CustomersPage"));
const B2BPage = React.lazy(() => import("./pages/B2BPage"));
const B2BBookingPage = React.lazy(() => import("./pages/B2BBookingPage"));
const ReportsPage = React.lazy(() => import("./pages/ReportsPage"));
const SettingsPage = React.lazy(() => import("./pages/SettingsPage"));
const AgencyHotelsPage = React.lazy(() => import("./pages/AgencyHotelsPage"));
const AgencyAvailabilityPage = React.lazy(() => import("./pages/AgencyAvailabilityPage"));
const AgencyHotelDetailPage = React.lazy(() => import("./pages/AgencyHotelDetailPage"));
const AgencyHotelSearchPage = React.lazy(() => import("./pages/AgencyHotelSearchPage"));
const AgencySearchResultsPage = React.lazy(() => import("./pages/AgencySearchResultsPage"));
const AgencyBookingNewPage = React.lazy(() => import("./pages/AgencyBookingNewPage"));
const AgencyBookingTestPage = React.lazy(() => import("./pages/AgencyBookingTestPage"));
const SimpleBookingTest = React.lazy(() => import("./pages/SimpleBookingTest"));
const WebBookingPage = React.lazy(() => import("./pages/WebBookingPage"));
const AgencyBookingDraftPage = React.lazy(() => import("./pages/AgencyBookingDraftPage"));
const AgencyBookingConfirmedPage = React.lazy(() => import("./pages/AgencyBookingConfirmedPage"));
const AgencyBookingPendingPage = React.lazy(() => import("./pages/AgencyBookingPendingPage"));
const AgencyBookingsListPage = React.lazy(() => import("./pages/AgencyBookingsListPage"));
const AgencySettlementsPage = React.lazy(() => import("./pages/AgencySettlementsPage"));
const AgencyHelpPage = React.lazy(() => import("./pages/AgencyHelpPage"));
const B2BPortalPage = React.lazy(() => import("./pages/B2BPortalPage"));
const OpsGuestCasesPage = React.lazy(() => import("./pages/OpsGuestCasesPage"));
const OpsBookingDetailPage = React.lazy(() => import("./pages/ops/OpsBookingDetailPage"));
const CrmCustomersPage = React.lazy(() => import("./pages/crm/CrmCustomersPage"));
const CrmCustomerDetailPage = React.lazy(() => import("./pages/crm/CrmCustomerDetailPage"));
const CrmTasksPage = React.lazy(() => import("./pages/crm/CrmTasksPage"));
const CrmEventsPage = React.lazy(() => import("./pages/crm/CrmEventsPage"));
const CrmPipelinePage = React.lazy(() => import("./pages/crm/CrmPipelinePage"));
const CrmDuplicateCustomersPage = React.lazy(() => import("./pages/crm/CrmDuplicateCustomersPage"));
const OpsTasksPage = React.lazy(() => import("./pages/OpsTasksPage"));
const ToursListPage = React.lazy(() => import("./pages/ToursListPage"));
const TourDetailPage = React.lazy(() => import("./pages/TourDetailPage"));

const HotelBookingsPage = React.lazy(() => import("./pages/HotelBookingsPage"));
const HotelStopSellPage = React.lazy(() => import("./pages/HotelStopSellPage"));
const HotelAllocationsPage = React.lazy(() => import("./pages/HotelAllocationsPage"));
const HotelSettlementsPage = React.lazy(() => import("./pages/HotelSettlementsPage"));
const HotelIntegrationsPage = React.lazy(() => import("./pages/HotelIntegrationsPage"));
const HotelHelpPage = React.lazy(() => import("./pages/HotelHelpPage"));
const NotFoundPage = React.lazy(() => import("./pages/NotFoundPage"));
const ErrorContextPage = React.lazy(() => import("./pages/ErrorContextPage"));

import { Toaster } from "./components/ui/sonner";
import { useTheme } from "./theme/useTheme";
import { getBrandNameFromThemeCache } from "./hooks/useSeo";

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
    <BrowserRouter>
      <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-sm text-muted-foreground">Yükleniyor...</div>}>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<PublicHomePage />} />
        <Route path="/s/:tenantKey" element={<StorefrontSearchPage />} />
        <Route path="/s/:tenantKey/search" element={<StorefrontSearchPage />} />
        <Route path="/s/:tenantKey/offers/:offerId" element={<StorefrontOfferPage />} />
        <Route path="/s/:tenantKey/checkout" element={<StorefrontCheckoutPage />} />
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
            <Route path="agencies/:agencyId/users" element={<AdminAgencyUsersPage />} />
            <Route path="b2b/dashboard" element={<AdminB2BDashboardPage />} />
            <Route path="b2b/marketplace" element={<AdminB2BMarketplacePage />} />
            <Route path="hotels" element={<AdminHotelsPage />} />
            <Route path="tours" element={<AdminToursPage />} />
            <Route path="b2b/dashboard" element={<AdminB2BDashboardPage />} />
            <Route path="links" element={<AdminLinksPage />} />
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
            <Route path="b2b/dashboard" element={<AdminB2BDashboardPage />} />
            <Route path="tours" element={<AdminToursPage />} />
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

      <Toaster position="top-right" richColors closeButton />
    </BrowserRouter>
  );
}

export default App;
