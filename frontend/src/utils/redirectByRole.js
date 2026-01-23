export function redirectByRole(user) {
  if (!user || !user.roles) return "/login";

  // 1) Global süper adminler
  if (user.roles.includes("super_admin")) {
    return "/app/admin/agencies";
  }

  // 2) Acenta rolleri (B2B Portal)
  if (user.roles.includes("agency_admin") || user.roles.includes("agency_agent")) {
    return "/app/agency/hotels";
  }

  // 3) Otel rolleri
  if (user.roles.includes("hotel_admin") || user.roles.includes("hotel_staff")) {
    return "/app/hotel/bookings";
  }

  // 4) İç ofis rolleri (admin, satış, operasyon, muhasebe, b2b_agent)
  if (user.roles.some((r) => ["admin", "sales", "ops", "accounting", "b2b_agent"].includes(r))) {
    return "/app/settings";
  }

  // 5) Diğer tüm roller gerçekten yetkisiz
  return "/unauthorized";
}
