export function redirectByRole(user) {
  if (!user || !user.roles) return "/login";

  // 1) Ürün yüzeyi sadeleştirme: admin ve agency kullanıcıları aynı çekirdek girişe iner
  if (user.roles.includes("super_admin")) {
    return "/app";
  }

  // 2) Acenta rolleri
  if (user.roles.includes("agency_admin") || user.roles.includes("agency_agent")) {
    return "/app";
  }

  // 3) Otel rolleri
  if (user.roles.includes("hotel_admin") || user.roles.includes("hotel_staff")) {
    return "/app/hotel/bookings";
  }

  // 4) İç ofis rolleri (admin, satış, operasyon, muhasebe, b2b_agent)
  if (user.roles.some((r) => ["admin", "sales", "ops", "accounting", "b2b_agent"].includes(r))) {
    return "/app";
  }

  // 5) Diğer tüm roller gerçekten yetkisiz
  return "/unauthorized";
}
