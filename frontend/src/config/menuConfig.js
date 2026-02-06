import { adminNav } from "../nav/adminNav";
import { agencyNav } from "../nav/agencyNav";
import { hotelNav } from "../nav/hotelNav";

export const MENU_CONFIG = {
  super_admin: adminNav,
  agency: agencyNav,
  hotel: hotelNav,
};

export function getMenuForUser(user) {
  if (!user) return [];

  if (user.roles?.includes("super_admin") || user.roles?.includes("admin")) {
    return MENU_CONFIG.super_admin;
  }

  if (
    user.roles?.includes("agency_admin") ||
    user.roles?.includes("agency_agent")
  ) {
    return MENU_CONFIG.agency;
  }

  if (user.roles?.includes("hotel_admin") || user.roles?.includes("hotel_staff")) {
    return MENU_CONFIG.hotel;
  }

  return [];
}
