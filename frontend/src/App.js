import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import RequireAuth from "./components/RequireAuth";
import AppShell from "./components/AppShell";
import LoginPage from "./pages/LoginPage";
import UnauthorizedPage from "./pages/UnauthorizedPage";
import ErrorContextPage from "./pages/ErrorContextPage";
import DashboardPage from "./pages/DashboardPage";
import ProductsPage from "./pages/ProductsPage";
import InventoryPage from "./pages/InventoryPage";
import ReservationsPage from "./pages/ReservationsPage";
import CustomersPage from "./pages/CustomersPage";
import CrmPage from "./pages/CrmPage";
import B2BPage from "./pages/B2BPage";
import B2BBookingPage from "./pages/B2BBookingPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";
import AgencyHotelsPage from "./pages/AgencyHotelsPage";
import AgencyHotelDetailPage from "./pages/AgencyHotelDetailPage";
import AgencySearchResultsPage from "./pages/AgencySearchResultsPage";
import AgencyBookingNewPage from "./pages/AgencyBookingNewPage";
import AdminLinksPage from "./pages/AdminLinksPage";
import AdminAgenciesPage from "./pages/AdminAgenciesPage";
import AdminHotelsPage from "./pages/AdminHotelsPage";

import AdminLayout from "./layouts/AdminLayout";
import AgencyLayout from "./layouts/AgencyLayout";

import { Toaster } from "./components/ui/sonner";

export default function App() {
  return (
    <BrowserRouter>
      <Toaster richColors />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="/error-context" element={<ErrorContextPage />} />

        {/* Super Admin Routes */}
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
          </Route>
        </Route>

        {/* Agency Routes */}
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
            <Route path="search" element={<AgencySearchResultsPage />} />
            <Route path="booking/new" element={<AgencyBookingNewPage />} />
          </Route>
        </Route>

        {/* Legacy/Common Routes (temporary - will be role-gated later) */}
        <Route
          path="/app"
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="reservations" element={<ReservationsPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="crm" element={<CrmPage />} />
          <Route path="b2b" element={<B2BPage />} />
          <Route path="b2b-book" element={<B2BBookingPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        <Route path="/" element={<Navigate to="/app" replace />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
