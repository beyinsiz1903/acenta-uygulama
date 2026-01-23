import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import LoginPage from "./pages/LoginPage";
import B2BLoginPage from "./b2b/B2BLoginPage";
import B2BAuthGuard from "./b2b/B2BAuthGuard";
import B2BLayout from "./b2b/B2BLayout";
import B2BBookingsPage from "./b2b/pages/B2BBookingsPage";
import B2BBookingDetailPage from "./b2b/pages/B2BBookingDetailPage";
import B2BAccountPage from "./b2b/pages/B2BAccountPage";
import UnauthorizedPage from "./pages/UnauthorizedPage";
import RequireAuth from "./components/RequireAuth";
import AppShell from "./components/AppShell";
import AdminLayout from "./layouts/AdminLayout";
import AgencyLayout from "./layouts/AgencyLayout";
import PublicMyBookingRequestPage from "./pages/PublicMyBookingRequestPage";
import PublicMyBookingDetailPage from "./pages/PublicMyBookingDetailPage";
import PublicClickToPayPage from "./pages/public/PublicClickToPayPage";
import BookSearchPage from "./pages/public/BookSearchPage";
import BookProductPage from "./pages/public/BookProductPage";
import BookCheckoutPage from "./pages/public/BookCheckoutPage";
import BookCompletePage from "./pages/public/BookCompletePage";
import BookTourProductPage from "./pages/public/BookTourProductPage";
import BookTourCheckoutPage from "./pages/public/BookTourCheckoutPage";
import PublicCMSPage from "./pages/public/PublicCMSPage";
import PublicCampaignPage from "./pages/public/PublicCampaignPage";
import PublicPartnerApplyPage from "./pages/public/PublicPartnerApplyPage";
import PublicHomePage from "./pages/PublicHomePage";

import HotelLayout from "./layouts/HotelLayout";
import AdminAgenciesPage from "./pages/AdminAgenciesPage";
import AdminHotelsPage from "./pages/AdminHotelsPage";
import AdminToursPage from "./pages/AdminToursPage";
import AdminLinksPage from "./pages/AdminLinksPage";
import AdminCMSPagesPage from "./pages/AdminCMSPagesPage";
import AdminAuditLogsPage from "./pages/AdminAuditLogsPage";
import AdminEmailLogsPage from "./pages/AdminEmailLogsPage";
import AdminPilotDashboardPage from "./pages/AdminPilotDashboardPage";
import AdminMetricsPage from "./pages/AdminMetricsPage";
import AdminMatchAlertsPolicyPage from "./pages/AdminMatchAlertsPolicyPage";
import AdminMatchesPage from "./pages/AdminMatchesPage";
import AdminExportsPage from "./pages/AdminExportsPage";
import AdminMatchDetailPage from "./pages/AdminMatchDetailPage";
import AdminMatchRiskTrendsPage from "./pages/AdminMatchRiskTrendsPage";
import AdminActionPoliciesPage from "./pages/AdminActionPoliciesPage";
import AdminApprovalsPage from "./pages/AdminApprovalsPage";
import AdminCatalogPage from "./pages/AdminCatalogPage";
import AdminCatalogHotelsPage from "./pages/AdminCatalogHotelsPage";
import AdminPricingPage from "./pages/AdminPricingPage";
import AdminFunnelPage from "./pages/AdminFunnelPage";
import AdminB2BFunnelPage from "./pages/AdminB2BFunnelPage";
import AdminB2BAnnouncementsPage from "./pages/AdminB2BAnnouncementsPage";
import AdminB2BDashboardPage from "./pages/AdminB2BDashboardPage";
import AdminExecutiveDashboardPage from "./pages/AdminExecutiveDashboardPage";
import AdminB2BMarketplacePage from "./pages/AdminB2BMarketplacePage";
import AdminThemePage from "./pages/AdminThemePage";
import AdminReportingPage from "./pages/AdminReportingPage";
import AdminVillaCalendarPage from "./pages/AdminVillaCalendarPage";
import AdminPricingIncidentsPage from "./pages/AdminPricingIncidentsPage";
import AdminB2BDiscountsPage from "./pages/AdminB2BDiscountsPage";
import AdminCouponsPage from "./pages/AdminCouponsPage";
import AdminCampaignsPage from "./pages/AdminCampaignsPage";
import AdminIntegrationsPage from "./pages/AdminIntegrationsPage";
import AdminPartnersPage from "./pages/AdminPartnersPage";
import AdminJobsPage from "./pages/AdminJobsPage";
import AdminApiKeysPage from "./pages/AdminApiKeysPage";
import OpsB2BQueuesPage from "./pages/OpsB2BQueuesPage";
import InboxPage from "./pages/InboxPage";
import AdminFinanceRefundsPage from "./pages/AdminFinanceRefundsPage";
import AdminFinanceExposurePage from "./pages/AdminFinanceExposurePage";
import AdminB2BAgenciesSummaryPage from "./pages/AdminB2BAgenciesSummaryPage";
import AdminB2BAgencyProductsPage from "./pages/AdminB2BAgencyProductsPage";
import AdminSettlementsPage from "./pages/AdminSettlementsPage";
import AdminSettlementRunsPage from "./pages/AdminSettlementRunsPage";
import AdminSettlementRunDetailPage from "./pages/AdminSettlementRunDetailPage";
import OpsSupplierAccrualsPage from "./pages/OpsSupplierAccrualsPage";
import AdminSupplierSettlementBridgePage from "./pages/AdminSupplierSettlementBridgePage";
import DashboardPage from "./pages/DashboardPage";
import ProductsPage from "./pages/ProductsPage";
import InventoryPage from "./pages/InventoryPage";
import ReservationsPage from "./pages/ReservationsPage";
import CustomersPage from "./pages/CustomersPage";
import B2BPage from "./pages/B2BPage";
import B2BBookingPage from "./pages/B2BBookingPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";
import AgencyHotelsPage from "./pages/AgencyHotelsPage";
import AgencyHotelDetailPage from "./pages/AgencyHotelDetailPage";
import AgencyHotelSearchPage from "./pages/AgencyHotelSearchPage";
import AgencySearchResultsPage from "./pages/AgencySearchResultsPage";
import AgencyBookingNewPage from "./pages/AgencyBookingNewPage";
import AgencyBookingTestPage from "./pages/AgencyBookingTestPage";
import SimpleBookingTest from "./pages/SimpleBookingTest";
import WebBookingPage from "./pages/WebBookingPage";
import AgencyBookingDraftPage from "./pages/AgencyBookingDraftPage";
import AgencyBookingConfirmedPage from "./pages/AgencyBookingConfirmedPage";
import AgencyBookingPendingPage from "./pages/AgencyBookingPendingPage";
import AgencyBookingsListPage from "./pages/AgencyBookingsListPage";
import AgencySettlementsPage from "./pages/AgencySettlementsPage";
import AgencyHelpPage from "./pages/AgencyHelpPage";
import B2BPortalPage from "./pages/B2BPortalPage";
import OpsGuestCasesPage from "./pages/OpsGuestCasesPage";
import OpsBookingDetailPage from "./pages/ops/OpsBookingDetailPage";
import CrmCustomersPage from "./pages/crm/CrmCustomersPage";
import CrmCustomerDetailPage from "./pages/crm/CrmCustomerDetailPage";
import CrmTasksPage from "./pages/crm/CrmTasksPage";
import CrmEventsPage from "./pages/crm/CrmEventsPage";
import CrmPipelinePage from "./pages/crm/CrmPipelinePage";
import CrmDuplicateCustomersPage from "./pages/crm/CrmDuplicateCustomersPage";

import HotelBookingsPage from "./pages/HotelBookingsPage";
import HotelStopSellPage from "./pages/HotelStopSellPage";
import HotelAllocationsPage from "./pages/HotelAllocationsPage";
import HotelSettlementsPage from "./pages/HotelSettlementsPage";
import HotelIntegrationsPage from "./pages/HotelIntegrationsPage";
import HotelHelpPage from "./pages/HotelHelpPage";
import NotFoundPage from "./pages/NotFoundPage";
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
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<PublicHomePage />} />
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

        {/* Admin Routes */}
        <Route
          path="/app/admin/*"
          element={
            <RequireAuth roles={["super_admin"]}>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route element={<AdminLayout />}>
            <Route path="agencies" element={<AdminAgenciesPage />} />
            <Route path="b2b/dashboard" element={<AdminB2BDashboardPage />} />
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
            <Route path="pricing/funnel" element={<AdminFunnelPage />} />
            <Route path="b2b/funnel" element={<AdminB2BFunnelPage />} />
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
          </Route>
        </Route>

        {/* Inbox Route moved under /app/* so that it renders inside AppShell */}
        {/* Core App Routes (Dashboard, Products, CRM, etc.) */}
        <Route
          path="/app/*"
          element={
            <RequireAuth roles={["admin", "sales", "ops", "accounting", "b2b_agent", "super_admin"]}>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="reservations" element={<ReservationsPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="b2b" element={<B2BPage />} />
          <Route path="b2b-book" element={<B2BBookingPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="inbox" element={<InboxPage />} />
          <Route path="crm/customers" element={<CrmCustomersPage />} />
          <Route path="crm/duplicates" element={<CrmDuplicateCustomersPage />} />
          <Route path="crm/pipeline" element={<CrmPipelinePage />} />
          <Route path="crm/tasks" element={<CrmTasksPage />} />
          <Route path="crm/events" element={<CrmEventsPage />} />
          <Route path="crm/customers/:customerId" element={<CrmCustomerDetailPage />} />
          <Route path="ops/guest-cases" element={<OpsGuestCasesPage />} />
          <Route path="ops/bookings/:bookingId" element={<OpsBookingDetailPage />} />
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
            <RequireAuth roles={["agency_admin", "agency_agent"]}>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route element={<AgencyLayout />}>
            <Route path="hotels" element={<AgencyHotelsPage />} />
            <Route path="hotels/:hotelId" element={<AgencyHotelDetailPage />} />
            <Route path="hotels/:hotelId/search" element={<AgencyHotelSearchPage />} />
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
