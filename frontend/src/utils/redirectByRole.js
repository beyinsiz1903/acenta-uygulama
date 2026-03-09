export function redirectByRole(user) {
  if (!user || !user.roles) return "/login";

  // 1) Super admin her zaman tam yönetici yüzeyine iner
  if (user.roles.includes("super_admin")) {
    return "/app/admin/dashboard";
  }

  // 2) Platform admin doğrudan yönetici yüzeyine iner
  if (user.roles.includes("admin")) {
    return "/app/admin/dashboard";
  }

  // 3) Acenta rolleri
  if (user.roles.includes("agency_admin") || user.roles.includes("agency_agent")) {
    return "/app";
  }

  // 4) Otel rolleri
  if (user.roles.includes("hotel_admin") || user.roles.includes("hotel_staff")) {
    return "/app/hotel/bookings";
  }

  // 5) İç ofis rolleri (satış, operasyon, muhasebe, b2b_agent)
  if (user.roles.some((r) => ["sales", "ops", "accounting", "b2b_agent"].includes(r))) {
    return "/app";
  }

  // 6) Diğer tüm roller gerçekten yetkisiz
  return "/unauthorized";
}
