import { useState, useEffect, Suspense, lazy } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from '@/lib/queryClient';

// Critical imports - loaded immediately
import AuthPage from "@/pages/AuthPage";
import Dashboard from "@/pages/Dashboard";

// Lazy load all other pages for faster initial load
const GMDashboard = lazy(() => import("@/pages/GMDashboard"));
const EnhancedGMDashboard = lazy(() => import("@/pages/EnhancedGMDashboard"));
const PMSModule = lazy(() => import("@/pages/PMSModule"));
const InvoiceModule = lazy(() => import("@/pages/InvoiceModule"));
const RMSModule = lazy(() => import("@/pages/RMSModule"));
const ChannelManagerModule = lazy(() => import("@/pages/ChannelManagerModule"));
const ReservationCalendar = lazy(() => import("@/pages/ReservationCalendar"));
const Settings = lazy(() => import("@/pages/Settings"));
const PendingAR = lazy(() => import("@/pages/PendingAR"));
const CityLedgerAccounts = lazy(() => import("@/pages/CityLedgerAccounts"));
const LoyaltyModule = lazy(() => import("@/pages/LoyaltyModule"));
const MarketplaceModule = lazy(() => import("@/pages/MarketplaceModule"));
const HotelInventory = lazy(() => import("@/pages/HotelInventory"));
const GuestPortal = lazy(() => import("@/pages/GuestPortal"));
const TemplateManager = lazy(() => import("@/pages/TemplateManager"));
const SelfCheckin = lazy(() => import("@/pages/SelfCheckin"));
const DigitalKey = lazy(() => import("@/pages/DigitalKey"));
const UpsellStore = lazy(() => import("@/pages/UpsellStore"));
const StaffMobileApp = lazy(() => import("@/pages/StaffMobileApp"));
const OTAMessagingHub = lazy(() => import("@/pages/OTAMessagingHub"));
const EFaturaModule = lazy(() => import("@/pages/EFaturaModule"));
const MessagingCenter = lazy(() => import("@/pages/MessagingCenter"));
const SalesModule = lazy(() => import("@/pages/SalesModule"));
const GroupReservations = lazy(() => import("@/pages/GroupReservations"));
const MultiPropertyDashboard = lazy(() => import("@/pages/MultiPropertyDashboard"));
const HousekeepingMobileApp = lazy(() => import("@/pages/HousekeepingMobileApp"));
const AIEnhancedPMS = lazy(() => import("@/pages/AIEnhancedPMS"));
const Reports = lazy(() => import("@/pages/Reports"));
const MobileDashboard = lazy(() => import("@/pages/MobileDashboard"));
const MobileHousekeeping = lazy(() => import("@/pages/MobileHousekeeping"));
const MobileFrontDesk = lazy(() => import("@/pages/MobileFrontDesk"));
const MobileFnB = lazy(() => import("@/pages/MobileFnB"));
const MobileMaintenance = lazy(() => import("@/pages/MobileMaintenance"));
const MobileFinance = lazy(() => import("@/pages/MobileFinance"));
const MobileSecurity = lazy(() => import("@/pages/MobileSecurity"));
const MobileGM = lazy(() => import("@/pages/MobileGM"));
const MobileOrderTracking = lazy(() => import("@/pages/MobileOrderTracking"));
const MobileInventory = lazy(() => import("@/pages/MobileInventory"));
const MobileApprovals = lazy(() => import("@/pages/MobileApprovals"));
const ExecutiveDashboard = lazy(() => import("@/pages/ExecutiveDashboard"));
const RevenueManagementMobile = lazy(() => import("@/pages/RevenueManagementMobile"));
const GMEnhancedDashboard = lazy(() => import("@/pages/GMEnhancedDashboard"));
const SalesCRMMobile = lazy(() => import("@/pages/SalesCRMMobile"));
import LandingPage from "@/pages/LandingPage";
import SimpleAdminPanel from "@/pages/SimpleAdminPanel";
import RateManagementMobile from "@/pages/RateManagementMobile";
import RevenueMobile from "@/pages/RevenueMobile";
import ChannelManagerMobile from "@/pages/ChannelManagerMobile";
import CorporateContractsMobile from "@/pages/CorporateContractsMobile";
import SystemPerformanceMonitor from "@/pages/SystemPerformanceMonitor";
import LogViewer from "@/pages/LogViewer";
import MobileLogViewer from "@/pages/MobileLogViewer";
import NetworkTestTools from "@/pages/NetworkTestTools";
import MaintenancePriorityVisual from "@/pages/MaintenancePriorityVisual";
import CostManagement from "@/pages/CostManagement";
import FeaturesShowcase from "@/pages/FeaturesShowcase";
import HousekeepingDashboard from "@/pages/HousekeepingDashboard";
import POSDashboard from "@/pages/POSDashboard";

// New 5-star hotel features
const OnlineCheckin = lazy(() => import("@/pages/OnlineCheckin"));
const FlashReport = lazy(() => import("@/pages/FlashReport"));
const GroupSales = lazy(() => import("@/pages/GroupSales"));
const VIPManagement = lazy(() => import("@/pages/VIPManagement"));
const SalesCRM = lazy(() => import("@/pages/SalesCRM"));
const ServiceRecovery = lazy(() => import("@/pages/ServiceRecovery"));
const SpaWellness = lazy(() => import("@/pages/SpaWellness"));
const MeetingEvents = lazy(() => import("@/pages/MeetingEvents"));
const AIChatbot = lazy(() => import("@/pages/AIChatbot"));
const DynamicPricing = lazy(() => import("@/pages/DynamicPricing"));
const ReputationCenter = lazy(() => import("@/pages/ReputationCenter"));
const MultiProperty = lazy(() => import("@/pages/MultiProperty"));
const PaymentGateway = lazy(() => import("@/pages/PaymentGateway"));
const AdvancedLoyalty = lazy(() => import("@/pages/AdvancedLoyalty"));
const GDSIntegration = lazy(() => import("@/pages/GDSIntegration"));
const StaffManagement = lazy(() => import("@/pages/StaffManagement"));
const GuestJourney = lazy(() => import("@/pages/GuestJourney"));
const ArrivalList = lazy(() => import("@/pages/ArrivalList"));
const AIWhatsAppConcierge = lazy(() => import("@/pages/AIWhatsAppConcierge"));
const PredictiveAnalytics = lazy(() => import("@/pages/PredictiveAnalytics"));
const SocialMediaRadar = lazy(() => import("@/pages/SocialMediaRadar"));
const RevenueAutopilot = lazy(() => import("@/pages/RevenueAutopilot"));
const HRComplete = lazy(() => import("@/pages/HRComplete"));
const FnBComplete = lazy(() => import("@/pages/FnBComplete"));
const KitchenDisplay = lazy(() => import("@/pages/KitchenDisplay"));
const NightAuditLogs = lazy(() => import("@/pages/NightAuditLogs"));
const FrontdeskAuditChecklist = lazy(() => import("@/pages/FrontdeskAuditChecklist"));
const CorporateContractsDashboard = lazy(() => import("@/pages/CorporateContractsDashboard"));
const MaintenanceWorkOrders = lazy(() => import("@/pages/MaintenanceWorkOrders"));
const MaintenanceAssets = lazy(() => import("@/pages/MaintenanceAssets"));
const MaintenancePlans = lazy(() => import("@/pages/MaintenancePlans"));

import { Toaster } from "@/components/ui/sonner";

// Loading component
const LoadingFallback = () => (
  <div className="flex items-center justify-center h-screen">
    <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
  </div>
);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

console.log('🔍 Backend Configuration:', {
  BACKEND_URL,
  usingRelativeURL: true,
  baseURL: '/api'
});

// Use relative URL for same-origin requests (better for container routing)
axios.defaults.baseURL = '/api';
axios.defaults.timeout = 30000;

// Setup axios interceptor for token and caching
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Add cache headers for GET requests
    if (config.method === 'get') {
      config.headers['Cache-Control'] = 'max-age=60'; // Cache for 60 seconds
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Setup response interceptor for 401 errors
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.warn('⚠️ 401 Unauthorized - Token may be invalid');
      // Don't auto-logout on first 401, let app handle it
    }
    return Promise.reject(error);
  }
);

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);

  // Setup axios interceptor for handling auth errors - DISABLED for now
  // The aggressive logout was causing issues with optional endpoints
  // useEffect(() => {
  //   const interceptor = axios.interceptors.response.use(
  //     (response) => response,
  //     (error) => {
  //       // If we get 401 Unauthorized, logout the user
  //       if (error.response && error.response.status === 401) {
  //         console.warn('Authentication error detected, logging out...');
  //         handleLogout();
  //       }
  //       return Promise.reject(error);
  //     }
  //   );

  //   // Cleanup interceptor on unmount
  //   return () => {
  //     axios.interceptors.response.eject(interceptor);
  //   };
  // }, []);

  useEffect(() => {
    console.log('🔄 App mounting - checking auth state...');
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    const storedTenant = localStorage.getItem('tenant');
    
    console.log('📦 LocalStorage check:', {
      hasToken: !!token,
      hasUser: !!storedUser,
      hasTenant: !!storedTenant
    });
    
    if (token && storedUser) {
      try {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);
        
        if (storedTenant && storedTenant !== 'null') {
          try {
            setTenant(JSON.parse(storedTenant));
          } catch (e) {
            console.warn('Failed to parse tenant data:', e);
          }
        }
        setIsAuthenticated(true);
        console.log('✅ Auth state restored successfully');
      } catch (e) {
        console.error('❌ Failed to restore auth state:', e);
        // Clear invalid data
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('tenant');
      }
    } else {
      console.log('ℹ️ No auth data found in localStorage');
    }
    setLoading(false);
  }, []);

  const handleLogin = (token, userData, tenantData) => {
    console.log('🔐 handleLogin called with:', { token: token?.substring(0, 20) + '...', userData, tenantData });
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('tenant', tenantData ? JSON.stringify(tenantData) : 'null');
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setUser(userData);
    setTenant(tenantData);
    setIsAuthenticated(true);
    console.log('✅ Auth state updated:', { isAuthenticated: true, user: userData?.email });
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('tenant');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
    setTenant(null);
    setIsAuthenticated(false);
  };

  if (loading) {
    return (
      <div className="loading-screen" style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
      }}>
        <div style={{ textAlign: 'center', color: 'white' }}>
          <div className="spinner" style={{
            border: '4px solid rgba(255,255,255,0.3)',
            borderTop: '4px solid white',
            borderRadius: '50%',
            width: '40px',
            height: '40px',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 1rem'
          }}></div>
          <p>Yükleniyor...</p>
        </div>
      </div>
    );
  }

  // Guest user routes
  if (isAuthenticated && user?.role === 'guest') {
    return (
      <QueryClientProvider client={queryClient}>
        <div className="App">
          <Toaster position="top-right" />
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/guest-portal/*" element={<GuestPortal user={user} onLogout={handleLogout} />} />
            </Routes>
          </BrowserRouter>
        </div>
        {/* ReactQueryDevtools removed for production */}
      </QueryClientProvider>
    );
  }

  // Hotel admin routes
  return (
    <QueryClientProvider client={queryClient}>
      <div className="App">
        <Toaster position="top-right" />
        <BrowserRouter>
        <Routes>
          {/* Public Landing Page */}
          <Route path="/landing" element={<LandingPage />} />
          <Route path="/login" element={<Navigate to="/auth" replace />} />
          
          {/* Simple Admin Panel - No auth required for easy access */}
          <Route path="/system-status" element={<SimpleAdminPanel />} />
          
          <Route
            path="/"
            element={
              isAuthenticated ? (
                <Dashboard user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <LandingPage />
              )
            }
          />
          <Route
            path="/gm-classic"
            element={
              isAuthenticated ? (
                <GMDashboard user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/dashboard-simple"
            element={
              isAuthenticated ? (
                <Dashboard user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/auth"
            element={
              !isAuthenticated ? (
                <AuthPage onLogin={handleLogin} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route
            path="/ai-pms"
            element={
              isAuthenticated ? (
                <AIEnhancedPMS user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/pms"
            element={
              isAuthenticated ? (
                <PMSModule user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/invoices"
            element={
              isAuthenticated ? (
                <InvoiceModule user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/rms"
            element={
              isAuthenticated ? (
                <RMSModule user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/channel-manager"
            element={
              isAuthenticated ? (
                <ChannelManagerModule user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/reservation-calendar"
            element={
              isAuthenticated ? (
                <ReservationCalendar user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/settings"
            element={
              isAuthenticated ? (
                <Settings user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />

          <Route
            path="/pending-ar"
            element={
              isAuthenticated ? (
                <PendingAR user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/city-ledger"
            element={
              isAuthenticated ? (
                <CityLedgerAccounts user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/loyalty"
            element={
              isAuthenticated ? (
                <LoyaltyModule user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/marketplace"
            element={
              isAuthenticated ? (
                <MarketplaceModule user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/hotel-inventory"
            element={
              isAuthenticated ? (
                <HotelInventory user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/templates"
            element={
              isAuthenticated ? (
                <TemplateManager user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/guest/checkin/:bookingId"
            element={
              isAuthenticated ? (
                <SelfCheckin bookingId={window.location.pathname.split('/').pop()} onComplete={() => window.location.href = '/guest/portal'} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/guest/digital-key/:bookingId"
            element={
              isAuthenticated ? (
                <DigitalKey bookingId={window.location.pathname.split('/').pop()} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/guest/upsell/:bookingId"
            element={
              isAuthenticated ? (
                <UpsellStore bookingId={window.location.pathname.split('/').pop()} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/staff/mobile"
            element={
              isAuthenticated ? (
                <StaffMobileApp user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/ota-messaging-hub"
            element={
              isAuthenticated ? (
                <OTAMessagingHub user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/messaging-center"
            element={
              isAuthenticated ? (
                <MessagingCenter user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/sales"
            element={
              isAuthenticated ? (
                <SalesModule user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/frontdesk/audit-checklist"
            element={
              isAuthenticated ? (
                <FrontdeskAuditChecklist user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/reports/corporate-contracts"
            element={
              isAuthenticated ? (
                <CorporateContractsDashboard user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/maintenance/work-orders"
            element={
              isAuthenticated ? (
                <MaintenanceWorkOrders user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/maintenance/assets"
            element={
              isAuthenticated ? (
                <MaintenanceAssets user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/maintenance/plans"
            element={
              isAuthenticated ? (
                <MaintenancePlans user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />

          <Route
            path="/efatura"
            element={
              isAuthenticated ? (
                <EFaturaModule user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/e-fatura"
            element={
              isAuthenticated ? (
                <EFaturaModule user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/group-reservations"
            element={
              isAuthenticated ? (
                <GroupReservations user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/multi-property-dashboard"
            element={
              isAuthenticated ? (
                <MultiPropertyDashboard user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/housekeeping-mobile-app"
            element={
              isAuthenticated ? (
                <HousekeepingMobileApp user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/reports"
            element={
              isAuthenticated ? (
                <Reports user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          {/* Mobile Department Routes */}
          <Route
            path="/mobile"
            element={
              isAuthenticated ? (
                <MobileDashboard user={user} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/housekeeping"
            element={
              isAuthenticated ? (
                <MobileHousekeeping user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/frontdesk"
            element={
              isAuthenticated ? (
                <MobileFrontDesk user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/fnb"
            element={
              isAuthenticated ? (
                <MobileFnB user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/maintenance"
            element={
              isAuthenticated ? (
                <MobileMaintenance user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/finance"
            element={
              isAuthenticated ? (
                <MobileFinance user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/night-audit/logs"
            element={
              isAuthenticated ? (
                <NightAuditLogs user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/gm"
            element={
              isAuthenticated ? (
                <MobileGM user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/maintenance/priority-visual"
            element={
              isAuthenticated ? (
                <MaintenancePriorityVisual user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/security"
            element={
              isAuthenticated ? (
                <MobileSecurity user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/order-tracking"
            element={
              isAuthenticated ? (
                <MobileOrderTracking user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/inventory"
            element={
              isAuthenticated ? (
                <MobileInventory user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/approvals"
            element={
              isAuthenticated ? (
                <MobileApprovals user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/executive"
            element={
              isAuthenticated ? (
                <ExecutiveDashboard user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/revenue"
            element={
              isAuthenticated ? (
                <RevenueMobile user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/gm/enhanced"
            element={
              isAuthenticated ? (
                <GMEnhancedDashboard user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/sales"
            element={
              isAuthenticated ? (
                <SalesCRMMobile user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/rates"
            element={
              isAuthenticated ? (
                <RateManagementMobile user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/revenue"
            element={
              isAuthenticated ? (
                <RevenueMobile user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/channels"
            element={
              isAuthenticated ? (
                <ChannelManagerMobile user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/corporate"
            element={
              isAuthenticated ? (
                <CorporateContractsMobile user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/system/performance"
            element={
              isAuthenticated ? (
                <SystemPerformanceMonitor user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/system/logs"
            element={
              isAuthenticated ? (
                <LogViewer user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/mobile/logs"
            element={
              isAuthenticated ? (
                <MobileLogViewer user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/network/test"
            element={
              isAuthenticated ? (
                <NetworkTestTools user={user} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/cost-management"
            element={
              isAuthenticated ? (
                <CostManagement user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/features"
            element={
              isAuthenticated ? (
                <FeaturesShowcase user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/housekeeping"
            element={
              isAuthenticated ? (
                <HousekeepingDashboard user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/pos"
            element={
              isAuthenticated ? (
                <POSDashboard user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          
          {/* New 5-Star Hotel Features */}
          <Route
            path="/online-checkin/:bookingId"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <OnlineCheckin />
              </Suspense>
            }
          />
          <Route
            path="/flash-report"
            element={
              isAuthenticated ? (
                <Suspense fallback={<LoadingFallback />}>
                  <FlashReport user={user} tenant={tenant} onLogout={handleLogout} />
                </Suspense>
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/group-sales"
            element={
              isAuthenticated ? (
                <Suspense fallback={<LoadingFallback />}>
                  <GroupSales user={user} tenant={tenant} onLogout={handleLogout} />
                </Suspense>
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/vip-management"
            element={
              isAuthenticated ? (
                <Suspense fallback={<LoadingFallback />}>
                  <VIPManagement user={user} tenant={tenant} onLogout={handleLogout} />
                </Suspense>
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/sales-crm"
            element={
              isAuthenticated ? (
                <Suspense fallback={<LoadingFallback />}>
                  <SalesCRM user={user} tenant={tenant} onLogout={handleLogout} />
                </Suspense>
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route
            path="/service-recovery"
            element={
              isAuthenticated ? (
                <Suspense fallback={<LoadingFallback />}>
                  <ServiceRecovery user={user} tenant={tenant} onLogout={handleLogout} />
                </Suspense>
              ) : (
                <Navigate to="/auth" replace />
              )
            }
          />
          <Route path="/spa-wellness" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><SpaWellness user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/meeting-events" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><MeetingEvents user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/ai-chatbot" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><AIChatbot user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/dynamic-pricing" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><DynamicPricing user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/reputation-center" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><ReputationCenter user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/multi-property" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><MultiProperty user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/payment-gateway" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><PaymentGateway user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/advanced-loyalty" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><AdvancedLoyalty user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/gds-integration" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><GDSIntegration user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/staff-management" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><StaffManagement user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/guest-journey" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><GuestJourney user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/arrival-list" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><ArrivalList user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/ai-whatsapp-concierge" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><AIWhatsAppConcierge user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/predictive-analytics" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><PredictiveAnalytics user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/social-media-radar" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><SocialMediaRadar user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/revenue-autopilot" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><RevenueAutopilot user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/hr-complete" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><HRComplete user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/fnb-complete" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><FnBComplete user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
          <Route path="/kitchen-display" element={isAuthenticated ? <Suspense fallback={<LoadingFallback />}><KitchenDisplay user={user} tenant={tenant} onLogout={handleLogout} /></Suspense> : <Navigate to="/auth" replace />} />
        </Routes>
      </BrowserRouter>
      {/* ReactQueryDevtools removed for production */}
    </div>
  </QueryClientProvider>
  );
}

export default App;
