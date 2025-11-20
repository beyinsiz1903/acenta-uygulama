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
import MobileGM from "@/pages/MobileGM";
import CostManagement from "@/pages/CostManagement";
import { Toaster } from "@/components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

console.log('🔍 Backend Configuration:', {
  BACKEND_URL,
  API,
  fullUrl: `${API}/auth/login`
});

axios.defaults.baseURL = API;

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const storedUser = localStorage.getItem('user');
    const storedTenant = localStorage.getItem('tenant');
    
    if (token && storedUser) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      setUser(JSON.parse(storedUser));
      if (storedTenant && storedTenant !== 'null') {
        setTenant(JSON.parse(storedTenant));
      }
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const handleLogin = (token, userData, tenantData) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('tenant', tenantData ? JSON.stringify(tenantData) : 'null');
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setUser(userData);
    setTenant(tenantData);
    setIsAuthenticated(true);
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
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
