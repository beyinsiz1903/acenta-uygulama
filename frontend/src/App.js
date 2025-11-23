import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import AuthPage from "@/pages/AuthPage";
import Dashboard from "@/pages/Dashboard";
import GMDashboard from "@/pages/GMDashboard";
import EnhancedGMDashboard from "@/pages/EnhancedGMDashboard";
import PMSModule from "@/pages/PMSModule";
import InvoiceModule from "@/pages/InvoiceModule";
import RMSModule from "@/pages/RMSModule";
import ChannelManagerModule from "@/pages/ChannelManagerModule";
import ReservationCalendar from "@/pages/ReservationCalendar";
import Settings from "@/pages/Settings";
import PendingAR from "@/pages/PendingAR";
import LoyaltyModule from "@/pages/LoyaltyModule";
import MarketplaceModule from "@/pages/MarketplaceModule";
import GuestPortal from "@/pages/GuestPortal";
import TemplateManager from "@/pages/TemplateManager";
import SelfCheckin from "@/pages/SelfCheckin";
import DigitalKey from "@/pages/DigitalKey";
import UpsellStore from "@/pages/UpsellStore";
import StaffMobileApp from "@/pages/StaffMobileApp";
import OTAMessagingHub from "@/pages/OTAMessagingHub";
import EFaturaModule from "@/pages/EFaturaModule";
import MessagingCenter from "@/pages/MessagingCenter";
import SalesModule from "@/pages/SalesModule";
import GroupReservations from "@/pages/GroupReservations";
import MultiPropertyDashboard from "@/pages/MultiPropertyDashboard";
import HousekeepingMobileApp from "@/pages/HousekeepingMobileApp";
import AIEnhancedPMS from "@/pages/AIEnhancedPMS";
import Reports from "@/pages/Reports";
import MobileDashboard from "@/pages/MobileDashboard";
import MobileHousekeeping from "@/pages/MobileHousekeeping";
import MobileFrontDesk from "@/pages/MobileFrontDesk";
import MobileFnB from "@/pages/MobileFnB";
import MobileMaintenance from "@/pages/MobileMaintenance";
import MobileFinance from "@/pages/MobileFinance";
import MobileSecurity from "@/pages/MobileSecurity";
import MobileGM from "@/pages/MobileGM";
import MobileOrderTracking from "@/pages/MobileOrderTracking";
import MobileInventory from "@/pages/MobileInventory";
import MobileApprovals from "@/pages/MobileApprovals";
import ExecutiveDashboard from "@/pages/ExecutiveDashboard";
import RevenueManagementMobile from "@/pages/RevenueManagementMobile";
import GMEnhancedDashboard from "@/pages/GMEnhancedDashboard";
import SalesCRMMobile from "@/pages/SalesCRMMobile";
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
import { Toaster } from "@/components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

console.log('🔍 Backend Configuration:', {
  BACKEND_URL,
  API,
  fullUrl: `${API}/auth/login`
});

axios.defaults.baseURL = API;
axios.defaults.timeout = 30000;

// Setup axios interceptor for token
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
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

  // Setup axios interceptor for handling auth errors
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        // If we get 401 Unauthorized, logout the user
        if (error.response && error.response.status === 401) {
          console.warn('Authentication error detected, logging out...');
          handleLogout();
        }
        return Promise.reject(error);
      }
    );

    // Cleanup interceptor on unmount
    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    const storedTenant = localStorage.getItem('tenant');
    
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
      } catch (e) {
        console.error('Failed to restore auth state:', e);
        // Clear invalid data
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('tenant');
      }
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
    return <div className="loading-screen">Loading...</div>;
  }

  // Guest user routes
  if (isAuthenticated && user?.role === 'guest') {
    return (
      <div className="App">
        <Toaster position="top-right" />
        <BrowserRouter>
          <Routes>
            <Route path="/*" element={<GuestPortal user={user} onLogout={handleLogout} />} />
          </Routes>
        </BrowserRouter>
      </div>
    );
  }

  // Hotel admin routes
  return (
    <div className="App">
      <Toaster position="top-right" />
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={
              isAuthenticated ? (
                <GMDashboard user={user} tenant={tenant} onLogout={handleLogout} />
              ) : (
                <Navigate to="/auth" replace />
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
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
