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
import AgencyHotelsPage from "./pages/AgencyHotelsPage";
import AgencyHotelDetailPage from "./pages/AgencyHotelDetailPage";
import AgencyHotelSearchPage from "./pages/AgencyHotelSearchPage";
import AgencySearchResultsPage from "./pages/AgencySearchResultsPage";
import AgencyBookingNewPage from "./pages/AgencyBookingNewPage";
import AgencyBookingDraftPage from "./pages/AgencyBookingDraftPage";
import AgencyBookingConfirmedPage from "./pages/AgencyBookingConfirmedPage";
import AgencyBookingsListPage from "./pages/AgencyBookingsListPage";
import AgencySettlementsPage from "./pages/AgencySettlementsPage";
import HotelBookingsPage from "./pages/HotelBookingsPage";
import HotelStopSellPage from "./pages/HotelStopSellPage";
import HotelAllocationsPage from "./pages/HotelAllocationsPage";
import HotelSettlementsPage from "./pages/HotelSettlementsPage";
import HotelIntegrationsPage from "./pages/HotelIntegrationsPage";
import NotFoundPage from "./pages/NotFoundPage";
import { Toaster } from "./components/ui/sonner";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<LoginPage />} />
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
            <Route path="bookings" element={<AgencyBookingsListPage />} />
            <Route path="settlements" element={<AgencySettlementsPage />} />
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
            <Route path="stop-sell" element={<HotelStopSellPage />} />
            <Route path="allocations" element={<HotelAllocationsPage />} />
            <Route path="settlements" element={<HotelSettlementsPage />} />
            <Route path="integrations" element={<HotelIntegrationsPage />} />
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
