import { lazy } from "react";
import { Route, Navigate } from "react-router-dom";

// ─── Lazy imports: Hotel pages ───
const HotelBookingsPage = lazy(() => import("../pages/HotelBookingsPage"));
const HotelStopSellPage = lazy(() => import("../pages/HotelStopSellPage"));
const HotelAllocationsPage = lazy(() => import("../pages/HotelAllocationsPage"));
const HotelSettlementsPage = lazy(() => import("../pages/HotelSettlementsPage"));
const HotelIntegrationsPage = lazy(() => import("../pages/HotelIntegrationsPage"));
const HotelHelpPage = lazy(() => import("../pages/HotelHelpPage"));

/**
 * Hotel route children — rendered inside HotelLayout.
 * Parent: /app/hotel/*
 */
export const hotelRoutes = (
  <>
    <Route index element={<Navigate to="bookings" replace />} />
    <Route path="bookings" element={<HotelBookingsPage />} />
    <Route path="stop-sell" element={<HotelStopSellPage />} />
    <Route path="allocations" element={<HotelAllocationsPage />} />
    <Route path="settlements" element={<HotelSettlementsPage />} />
    <Route path="integrations" element={<HotelIntegrationsPage />} />
    <Route path="help" element={<HotelHelpPage />} />
  </>
);
