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

/**
 * Filter menu items by enabled features.
 * Items with requiredFeature are hidden if that feature is not enabled.
 * Items without requiredFeature are always shown.
 */
export function filterMenuByFeatures(menu, hasFeature) {
  if (!hasFeature) return menu;

  return menu
    .map((section) => {
      if (section.children) {
        const filtered = section.children.filter(
          (item) => !item.requiredFeature || hasFeature(item.requiredFeature),
        );
        if (filtered.length === 0) {
          // If the section itself has a requiredFeature check
          if (section.requiredFeature && !hasFeature(section.requiredFeature)) {
            return null;
          }
          return null;
        }
        return { ...section, children: filtered };
      }
      // Top-level items
      if (section.requiredFeature && !hasFeature(section.requiredFeature)) {
        return null;
      }
      return section;
    })
    .filter(Boolean);
}
