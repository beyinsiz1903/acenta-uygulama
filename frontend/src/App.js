import React, { Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// React Query client with default options
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});

// ─── Eager imports (critical path) ───
import LoginPage from "./pages/LoginPage";
import B2BLoginPage from "./b2b/B2BLoginPage";
import B2BAuthGuard from "./b2b/B2BAuthGuard";
import B2BLayout from "./b2b/B2BLayout";
import UnauthorizedPage from "./pages/UnauthorizedPage";
import RequireAuth from "./components/RequireAuth";
import AppShell from "./components/AppShell";
import AdminLayout from "./layouts/AdminLayout";
import AgencyLayout from "./layouts/AgencyLayout";
import HotelLayout from "./layouts/HotelLayout";
import NotFoundPage from "./pages/NotFoundPage";
import { Toaster } from "./components/ui/sonner";
import { useTheme } from "./theme/useTheme";
import { getBrandNameFromThemeCache } from "./hooks/useSeo";

// ─── Domain route modules ───
import { publicRoutes } from "./routes/publicRoutes";
import { adminRoutes } from "./routes/adminRoutes";
import { coreRoutes, b2bPortalRoute } from "./routes/coreRoutes";
import { agencyRoutes } from "./routes/agencyRoutes";
import { hotelRoutes } from "./routes/hotelRoutes";
import { b2bRoutes } from "./routes/b2bRoutes";

// ─── Loading fallback ───
function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
        <span className="text-sm text-muted-foreground font-medium">Yükleniyor...</span>
      </div>
    </div>
  );
}

function App() {
  useTheme();

  // Global Organization + WebSite JSON-LD
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
    <QueryClientProvider client={queryClient}>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* ─── Public ─── */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/b2b/login" element={<B2BLoginPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        {publicRoutes}

        {/* ─── Admin ─── */}
        <Route
          path="/app/admin/*"
          element={
            <RequireAuth roles={["super_admin", "admin"]}>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route element={<AdminLayout />}>
            {adminRoutes}
          </Route>
        </Route>

        {/* ─── Core App ─── */}
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
          {coreRoutes}
        </Route>

        {/* ─── B2B Portal ─── */}
        <Route
          path="/b2b/*"
          element={
            <B2BAuthGuard>
              <B2BLayout />
            </B2BAuthGuard>
          }
        >
          {b2bRoutes}
        </Route>

        {/* ─── B2B Portal (standalone) ─── */}
        {b2bPortalRoute}

        {/* ─── Agency ─── */}
        <Route
          path="/app/agency/*"
          element={
            <RequireAuth roles={["agency_admin", "agency_agent", "admin", "super_admin"]}>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route element={<AgencyLayout />}>
            {agencyRoutes}
          </Route>
        </Route>

        {/* ─── Hotel ─── */}
        <Route
          path="/app/hotel/*"
          element={
            <RequireAuth roles={["hotel_admin", "hotel_staff", "admin", "super_admin"]}>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route element={<HotelLayout />}>
            {hotelRoutes}
          </Route>
        </Route>

        {/* ─── Fallback ─── */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      </Suspense>
      <Toaster position="top-right" richColors closeButton />
    </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
