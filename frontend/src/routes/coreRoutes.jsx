import { lazy } from "react";
import { Route, Navigate } from "react-router-dom";
import { getUser } from "../lib/api";
import { resolvePersona } from "../navigation";

// ─── Lazy imports: Core app pages ───
const DashboardPage = lazy(() => import("../pages/DashboardPage"));
const AgencyDashboardPage = lazy(() => import("../pages/AgencyDashboardPage"));
const ReservationsPage = lazy(() => import("../pages/ReservationsPage"));
const AdvancedReportsPage = lazy(() => import("../pages/AdvancedReportsPage"));
const UsagePage = lazy(() => import("../pages/UsagePage"));
const OnboardingWizardPage = lazy(() => import("../pages/OnboardingWizardPage"));
const SettingsPage = lazy(() => import("../pages/SettingsPage"));
const SettingsBillingPage = lazy(() => import("../pages/SettingsBillingPage"));
const SettingsSecurityPage = lazy(() => import("../pages/SettingsSecurityPage"));
const ProductsPage = lazy(() => import("../pages/ProductsPage"));
const InventoryPage = lazy(() => import("../pages/InventoryPage"));
const B2BPage = lazy(() => import("../pages/B2BPage"));
const B2BBookingPage = lazy(() => import("../pages/B2BBookingPage"));
const WebPOSPage = lazy(() => import("../pages/WebPOSPage"));
const InboxPage = lazy(() => import("../pages/InboxPage"));
const B2BPortalPage = lazy(() => import("../pages/B2BPortalPage"));
const AdminEFaturaPage = lazy(() => import("../pages/AdminEFaturaPage"));
const ToursListPage = lazy(() => import("../pages/ToursListPage"));
const TourDetailPage = lazy(() => import("../pages/TourDetailPage"));
const B2BMarketplaceCatalogPage = lazy(() => import("../pages/marketplace/B2BMarketplaceCatalogPage"));

// CRM
const CrmCustomersPage = lazy(() => import("../pages/crm/CrmCustomersPage"));
const CrmCustomerDetailPage = lazy(() => import("../pages/crm/CrmCustomerDetailPage"));
const CrmTasksPage = lazy(() => import("../pages/crm/CrmTasksPage"));
const CrmEventsPage = lazy(() => import("../pages/crm/CrmEventsPage"));
const CrmPipelinePage = lazy(() => import("../pages/crm/CrmPipelinePage"));
const CrmDuplicateCustomersPage = lazy(() => import("../pages/crm/CrmDuplicateCustomersPage"));

// Ops
const OpsGuestCasesPage = lazy(() => import("../pages/OpsGuestCasesPage"));
const OpsBookingDetailPage = lazy(() => import("../pages/ops/OpsBookingDetailPage"));
const OpsTasksPage = lazy(() => import("../pages/OpsTasksPage"));
const AdminOpsIncidentsPage = lazy(() => import("../pages/ops/AdminOpsIncidentsPage"));

// Partners
const PartnerLayout = lazy(() => import("../pages/partners/PartnerLayout"));
const PartnerOverviewPage = lazy(() => import("../pages/partners/PartnerOverviewPage"));
const PartnerInboxPage = lazy(() => import("../pages/partners/PartnerInboxPage"));
const PartnerDiscoveryPage = lazy(() => import("../pages/partners/PartnerDiscoveryPage"));
const PartnerB2BNetworkPage = lazy(() => import("../pages/partners/PartnerB2BNetworkPage"));
const PartnerInvitesPage = lazy(() => import("../pages/partners/PartnerInvitesPage"));
const PartnerRelationshipsPage = lazy(() => import("../pages/partners/PartnerRelationshipsPage"));
const PartnerStatementsPage = lazy(() => import("../pages/partners/PartnerStatementsPage"));

/** Persona-aware dashboard selector */
function DashboardRouter() {
  const user = getUser();
  const persona = resolvePersona(user);
  if (persona === "agency") return <AgencyDashboardPage />;
  return <DashboardPage />;
}

/**
 * Core app route children — rendered inside AppShell.
 * Parent: /app/*
 */
export const coreRoutes = (
  <>
    <Route index element={<DashboardRouter />} />
    <Route path="customers" element={<Navigate to="/app/crm/customers" replace />} />
    <Route path="reservations" element={<ReservationsPage />} />
    <Route path="reports" element={<AdvancedReportsPage />} />
    <Route path="usage" element={<UsagePage />} />
    <Route path="onboarding" element={<OnboardingWizardPage />} />
    {/* Settings */}
    <Route path="settings/billing" element={<SettingsBillingPage />} />
    <Route path="settings/security" element={<SettingsSecurityPage />} />
    <Route path="settings" element={<SettingsPage />} />
    {/* Products & Inventory */}
    <Route path="b2b/marketplace" element={<B2BMarketplaceCatalogPage />} />
    <Route path="products" element={<ProductsPage />} />
    <Route path="inventory" element={<InventoryPage />} />
    <Route path="b2b" element={<B2BPage />} />
    <Route path="b2b-book" element={<B2BBookingPage />} />
    <Route path="finance/webpos" element={<WebPOSPage />} />
    <Route path="inbox" element={<InboxPage />} />
    <Route path="invoices" element={<AdminEFaturaPage />} />
    {/* Tours */}
    <Route path="tours" element={<ToursListPage />} />
    <Route path="tours/:tourId" element={<TourDetailPage />} />
    {/* Partners */}
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
    {/* CRM */}
    <Route path="crm/customers" element={<CrmCustomersPage />} />
    <Route path="crm/duplicates" element={<CrmDuplicateCustomersPage />} />
    <Route path="crm/pipeline" element={<CrmPipelinePage />} />
    <Route path="crm/tasks" element={<CrmTasksPage />} />
    <Route path="crm/events" element={<CrmEventsPage />} />
    <Route path="crm/customers/:customerId" element={<CrmCustomerDetailPage />} />
    {/* Operations */}
    <Route path="ops/guest-cases" element={<OpsGuestCasesPage />} />
    <Route path="ops/bookings/:bookingId" element={<OpsBookingDetailPage />} />
    <Route path="ops/tasks" element={<OpsTasksPage />} />
    <Route path="ops/incidents" element={<AdminOpsIncidentsPage />} />
  </>
);

/**
 * B2B Portal route — standalone, outside main app shell.
 */
export const b2bPortalRoute = (
  <Route path="/app/b2b/portal" element={<B2BPortalPage />} />
);
