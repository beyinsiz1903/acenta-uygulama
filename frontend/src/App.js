import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import LoginPage from "./pages/LoginPage";
import UnauthorizedPage from "./pages/UnauthorizedPage";
import RequireAuth from "./components/RequireAuth";
import AppShell from "./components/AppShell";
import AdminLayout from "./layouts/AdminLayout";
import AgencyLayout from "./layouts/AgencyLayout";
import HotelLayout from "./layouts/HotelLayout";
import AdminAgenciesPage from "./pages/AdminAgenciesPage";
import AdminHotelsPage from "./pages/AdminHotelsPage";
import AdminLinksPage from "./pages/AdminLinksPage";
import AdminAuditLogsPage from "./pages/AdminAuditLogsPage";
import AdminEmailLogsPage from "./pages/AdminEmailLogsPage";
import AdminPilotDashboardPage from "./pages/AdminPilotDashboardPage";
import AdminMetricsPage from "./pages/AdminMetricsPage";
import AgencyHotelsPage from "./pages/AgencyHotelsPage";
import AgencyCatalogHotelsPage from "./pages/AgencyCatalogHotelsPage";
import AgencyCatalogProductsPage from "./pages/AgencyCatalogProductsPage";
import AgencyCatalogBookingsPage from "./pages/AgencyCatalogBookingsPage";
import AgencyCatalogBookingDetailPage from "./pages/AgencyCatalogBookingDetailPage";
import AgencyCatalogCapacityPage from "./pages/AgencyCatalogCapacityPage";
import AgencyCatalogOverbooksPage from "./pages/AgencyCatalogOverbooksPage";

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
import AgencyBookingPrintPage from "./pages/AgencyBookingPrintPage";
import AgencySettlementsPage from "./pages/AgencySettlementsPage";
import AgencyReportsPage from "./pages/AgencyReportsPage";
import AgencyCrmFollowupsPage from "./pages/AgencyCrmFollowupsPage";
import AgencyHelpPage from "./pages/AgencyHelpPage";
import AgencyToursPage from "./pages/AgencyToursPage";
import AgencyTourEditPage from "./pages/AgencyTourEditPage";
import AgencyTourBookingsPage from "./pages/AgencyTourBookingsPage";
import AgencyTourBookingDetailPage from "./pages/AgencyTourBookingDetailPage";
import AgencyPaymentSettingsPage from "./pages/AgencyPaymentSettingsPage";
import HotelBookingsPage from "./pages/HotelBookingsPage";
import HotelBookingPrintPage from "./pages/HotelBookingPrintPage";
import HotelStopSellPage from "./pages/HotelStopSellPage";
import HotelAllocationsPage from "./pages/HotelAllocationsPage";
import HotelSettlementsPage from "./pages/HotelSettlementsPage";
import HotelDashboardPage from "./pages/HotelDashboardPage";
import HotelIntegrationsPage from "./pages/HotelIntegrationsPage";
import HotelHelpPage from "./pages/HotelHelpPage";
import HotelPublicBookingPage from "./pages/HotelPublicBookingPage";
import PublicAgencyBookingPage from "./pages/PublicAgencyBookingPage";
import PublicToursPage from "./pages/PublicToursPage";
import PublicTourDetailPage from "./pages/PublicTourDetailPage";
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
        <Route path="/public/hotel/:hotelSlug" element={<HotelPublicBookingPage />} />
        <Route path="/booking/:agencySlug" element={<PublicAgencyBookingPage />} />
        <Route path="/tours" element={<PublicToursPage />} />
        <Route path="/tours/:id" element={<PublicTourDetailPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />

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
          </Route>
        </Route>

        {/* Agency Routes (Core Flow) */}
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
            <Route path="bookings/:id/print" element={<AgencyBookingPrintPage />} />
            <Route path="settlements" element={<AgencySettlementsPage />} />
            <Route path="reports" element={<AgencyReportsPage />} />
            <Route path="help" element={<AgencyHelpPage />} />

            <Route path="products/hotels" element={<AgencyCatalogHotelsPage />} />
            <Route path="tours" element={<AgencyToursPage />} />
            <Route path="tours/new" element={<AgencyTourEditPage />} />
            <Route path="tours/:id" element={<AgencyTourEditPage />} />
            <Route path="tour-bookings" element={<AgencyTourBookingsPage />} />
            <Route path="tour-bookings/:id" element={<AgencyTourBookingDetailPage />} />
            <Route path="catalog/products" element={<AgencyCatalogProductsPage />} />
            <Route path="catalog/bookings" element={<AgencyCatalogBookingsPage />} />
            <Route path="catalog/bookings/:id" element={<AgencyCatalogBookingDetailPage />} />
            <Route path="catalog/capacity" element={<AgencyCatalogCapacityPage />} />
            <Route path="settings/payment" element={<AgencyPaymentSettingsPage />} />
          </Route>
        </Route>

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
            <Route path="bookings/:id/print" element={<HotelBookingPrintPage />} />
            <Route path="stop-sell" element={<HotelStopSellPage />} />
            <Route path="allocations" element={<HotelAllocationsPage />} />
            <Route path="settlements" element={<HotelSettlementsPage />} />
            <Route path="dashboard" element={<HotelDashboardPage />} />
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
