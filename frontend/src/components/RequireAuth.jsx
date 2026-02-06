import React from "react";
import { Navigate, useLocation } from "react-router-dom";

function getUser() {
  try {
    return JSON.parse(localStorage.getItem("acenta_user"));
  } catch {
    return null;
  }
}

function getToken() {
  return localStorage.getItem("acenta_token");
}

/**
 * @param {ReactNode} children
 * @param {string[]} roles - allowed roles
 */
export default function RequireAuth({ children, roles }) {
  const location = useLocation();
  const token = getToken();
  const user = getUser();

  // 1️⃣ Not logged in
  if (!token || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // 2️⃣ Role validation
  const userRoles = user.roles || [];

  if (roles && roles.length > 0) {
    const hasRole = roles.some((r) => userRoles.includes(r));
    if (!hasRole) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  // 3️⃣ Context validation (agency/hotel rolleri için, admin/super_admin hariç)
  const isAdminLike = userRoles.includes("super_admin") || userRoles.includes("admin");

  if (!isAdminLike && (userRoles.includes("agency_admin") || userRoles.includes("agency_agent"))) {
    if (!user.agency_id) {
      return <Navigate to="/error-context?reason=agency_id_missing" replace />;
    }
  }

  if (!isAdminLike && (userRoles.includes("hotel_admin") || userRoles.includes("hotel_staff"))) {
    if (!user.hotel_id) {
      return <Navigate to="/error-context?reason=hotel_id_missing" replace />;
    }
  }

  return children;
}
