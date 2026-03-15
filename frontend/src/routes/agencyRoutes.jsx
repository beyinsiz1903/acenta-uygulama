import { lazy } from "react";
import { Route, Navigate } from "react-router-dom";

// ─── Lazy imports: Agency pages ───
const PMSDashboardPage = lazy(() => import("../pages/PMSDashboardPage"));
const PMSRoomsPage = lazy(() => import("../pages/PMSRoomsPage"));
const PMSAccountingPage = lazy(() => import("../pages/PMSAccountingPage"));
const PMSInvoicesPage = lazy(() => import("../pages/PMSInvoicesPage"));
const AgencyHotelsPage = lazy(() => import("../pages/AgencyHotelsPage"));
const AgencyHotelDetailPage = lazy(() => import("../pages/AgencyHotelDetailPage"));
const AgencyHotelSearchPage = lazy(() => import("../pages/AgencyHotelSearchPage"));
const AgencyAvailabilityPage = lazy(() => import("../pages/AgencyAvailabilityPage"));
const AgencySheetConnectionsPage = lazy(() => import("../pages/AgencySheetConnectionsPage"));
const AgencySearchResultsPage = lazy(() => import("../pages/AgencySearchResultsPage"));
const AgencyBookingNewPage = lazy(() => import("../pages/AgencyBookingNewPage"));
const AgencyBookingDraftPage = lazy(() => import("../pages/AgencyBookingDraftPage"));
const AgencyBookingConfirmedPage = lazy(() => import("../pages/AgencyBookingConfirmedPage"));
const AgencyBookingPendingPage = lazy(() => import("../pages/AgencyBookingPendingPage"));
const AgencyBookingsListPage = lazy(() => import("../pages/AgencyBookingsListPage"));
const AgencySettlementsPage = lazy(() => import("../pages/AgencySettlementsPage"));
const AgencyHelpPage = lazy(() => import("../pages/AgencyHelpPage"));
const UnifiedSearchPage = lazy(() => import("../pages/agency/UnifiedSearchPage"));

/**
 * Agency route children — rendered inside AgencyLayout.
 * Parent: /app/agency/*
 */
export const agencyRoutes = (
  <>
    <Route index element={<Navigate to="pms" replace />} />
    <Route path="pms" element={<PMSDashboardPage />} />
    <Route path="pms/rooms" element={<PMSRoomsPage />} />
    <Route path="pms/accounting" element={<PMSAccountingPage />} />
    <Route path="pms/invoices" element={<PMSInvoicesPage />} />
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
    <Route path="unified-search" element={<UnifiedSearchPage />} />
  </>
);
