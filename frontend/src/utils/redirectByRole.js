import { hasAnyRole } from "../lib/roles";

export function redirectByRole(user) {
  if (!user) return "/login";

  // 1) Super admin her zaman tam yönetici yüzeyine iner
  if (hasAnyRole(user, ["super_admin"])) {
    return "/app/admin/dashboard";
  }

  // 2) Platform admin doğrudan yönetici yüzeyine iner
  if (hasAnyRole(user, ["admin"])) {
    return "/app/admin/dashboard";
  }

  // 3) Acenta rolleri
  if (hasAnyRole(user, ["agency_admin", "agency_agent"])) {
    return "/app";
  }

  // 4) Otel rolleri
  if (hasAnyRole(user, ["hotel_admin", "hotel_staff"])) {
    return "/app/hotel/bookings";
  }

  // 5) İç ofis rolleri (satış, operasyon, muhasebe, b2b_agent)
  if (hasAnyRole(user, ["sales", "ops", "accounting", "b2b_agent"])) {
    return "/app";
  }

  // 6) Diğer tüm roller gerçekten yetkisiz
  return "/unauthorized";
}
