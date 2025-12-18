export function redirectByRole(user) {
  if (!user || !user.roles) return "/login";

  if (user.roles.includes("super_admin")) {
    return "/app/admin/agencies";
  }

  if (user.roles.includes("agency_admin") || user.roles.includes("agency_agent")) {
    return "/app/agency/hotels";
  }

  if (user.roles.includes("hotel_admin") || user.roles.includes("hotel_staff")) {
    return "/app/hotel"; // şimdilik placeholder
  }

  return "/unauthorized";
}
