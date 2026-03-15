import { lazy } from "react";
import { Route } from "react-router-dom";

// ─── Lazy imports: B2B pages ───
const B2BBookingsPage = lazy(() => import("../b2b/pages/B2BBookingsPage"));
const B2BBookingDetailPage = lazy(() => import("../b2b/pages/B2BBookingDetailPage"));
const B2BAccountPage = lazy(() => import("../b2b/pages/B2BAccountPage"));

/**
 * B2B portal route children — rendered inside B2BLayout.
 * Parent: /b2b/*
 */
export const b2bRoutes = (
  <>
    <Route path="bookings" element={<B2BBookingsPage />} />
    <Route path="bookings/:bookingId" element={<B2BBookingDetailPage />} />
    <Route path="account" element={<B2BAccountPage />} />
  </>
);
