import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useCurrentUser } from "../hooks/useAuth";
import { rememberPostLoginRedirect } from "../lib/authRedirect";
import { hasAnyRole, normalizeRoles } from "../lib/roles";

/**
 * @param {ReactNode} children
 * @param {string[]} roles - allowed roles
 */
export default function RequireAuth({ children, roles }) {
  const location = useLocation();
  const { data: user, isLoading, isFetching } = useCurrentUser();

  if (isLoading || (isFetching && !user)) {
    return (
      <div
        className="flex min-h-[40vh] items-center justify-center text-sm text-muted-foreground"
        data-testid="auth-guard-loading"
      >
        Oturum doğrulanıyor...
      </div>
    );
  }

  // 1️⃣ Not logged in
  if (!user) {
    rememberPostLoginRedirect(location);
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  // 2️⃣ Role validation
  const userRoles = normalizeRoles(user);

  if (roles && roles.length > 0) {
    if (!hasAnyRole(userRoles, roles)) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  // 3️⃣ Context validation (agency/hotel rolleri için, admin/super_admin hariç)
  const isAdminLike = hasAnyRole(userRoles, ["super_admin", "admin"]);

  if (!isAdminLike && hasAnyRole(userRoles, ["agency_admin", "agency_agent"])) {
    if (!user.agency_id) {
      return <Navigate to="/error-context?reason=agency_id_missing" replace />;
    }
  }

  if (!isAdminLike && hasAnyRole(userRoles, ["hotel_admin", "hotel_staff"])) {
    if (!user.hotel_id) {
      return <Navigate to="/error-context?reason=hotel_id_missing" replace />;
    }
  }

  return children;
}
