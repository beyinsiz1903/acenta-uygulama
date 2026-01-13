import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import LoginPage from "./pages/LoginPage";
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

import HotelLayout from "./layouts/HotelLayout";
import AdminAgenciesPage from "./pages/AdminAgenciesPage";
import AdminHotelsPage from "./pages/AdminHotelsPage";
import AdminLinksPage from "./pages/AdminLinksPage";
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
import OpsB2BQueuesPage from "./pages/OpsB2BQueuesPage";
import InboxPage from "./pages/InboxPage";
import AdminFinanceRefundsPage from "./pages/AdminFinanceRefundsPage";
import DashboardPage from "./pages/DashboardPage";
import ProductsPage from "./pages/ProductsPage";
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
import CrmPipelinePage from "./pages/crm/CrmPipelinePage";

import HotelBookingsPage from "./pages/HotelBookingsPage";
import HotelStopSellPage from "./pages/HotelStopSellPage";
import HotelAllocationsPage from "./pages/HotelAllocationsPage";
import HotelSettlementsPage from "./pages/HotelSettlementsPage";
import HotelIntegrationsPage from "./pages/HotelIntegrationsPage";
import HotelHelpPage from "./pages/HotelHelpPage";
import NotFoundPage from "./pages/NotFoundPage";
import { Toaster } from "./components/ui/sonner";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LoginPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/test/booking" element={<AgencyBookingTestPage />} />
        <Route path="/test/simple" element={<SimpleBookingTest />} />
        <Route path="/booking" element={<WebBookingPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="/pay/:token" element={<PublicClickToPayPage />} />
        <Route path="/book" element={<BookSearchPage />} />
        <Route path="/book/:productId" element={<BookProductPage />} />
        <Route path="/book/:productId/checkout" element={<BookCheckoutPage />} />
        <Route path="/book/complete" element={<BookCompletePage />} />

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
            <Route path="hotels" element={<AdminHotelsPage />} />
            <Route path="links" element={<AdminLinksPage />} />
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
            <Route path="approvals" element={<AdminApprovalsPage />} />
            <Route path="exports" element={<AdminExportsPage />} />
            <Route path="finance/refunds" element={<AdminFinanceRefundsPage />} />
            <Route path="ops/b2b" element={<OpsB2BQueuesPage />} />
          </Route>
        </Route>

        {/* Inbox Route */}
        <Route
          path="/app/inbox"
          element={
            <RequireAuth roles={["super_admin", "admin", "ops", "agency_admin", "agency_agent", "hotel_admin", "hotel_staff"]}>
              <InboxPage />
            </RequireAuth>
          }
        />

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
          <Route path="crm/customers" element={<CrmCustomersPage />} />
          <Route path="crm/tasks" element={<CrmTasksPage />} />

          <Route path="crm/customers/:customerId" element={<CrmCustomerDetailPage />} />
          <Route path="ops/guest-cases" element={<OpsGuestCasesPage />} />
          <Route path="ops/bookings/:bookingId" element={<OpsBookingDetailPage />} />
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
