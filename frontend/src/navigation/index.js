/**
 * Navigation Module — Faz 3: Persona-Based Navigation Platform
 *
 * Central export for persona-based navigation.
 * AppShell imports from here instead of lib/appNavigation.js.
 *
 * Usage:
 *   import { resolvePersona, getPersonaNavSections, getPersonaAccountLinks } from "../navigation";
 */
import { ADMIN_SIDEBAR_SECTIONS, ADMIN_ACCOUNT_LINKS } from "./personas/admin.navigation";
import { AGENCY_SIDEBAR_SECTIONS, AGENCY_ACCOUNT_LINKS } from "./personas/agency.navigation";
import { HOTEL_SIDEBAR_SECTIONS, HOTEL_ACCOUNT_LINKS } from "./personas/hotel.navigation";
import { B2B_SIDEBAR_SECTIONS, B2B_ACCOUNT_LINKS } from "./personas/b2b.navigation";

export { resolvePersona, flattenNavItems, filterSidebarItems } from "./shared/navigation.utils";

const PERSONA_NAV_MAP = {
  admin: ADMIN_SIDEBAR_SECTIONS,
  agency: AGENCY_SIDEBAR_SECTIONS,
  hotel: HOTEL_SIDEBAR_SECTIONS,
  b2b: B2B_SIDEBAR_SECTIONS,
};

const PERSONA_ACCOUNT_MAP = {
  admin: ADMIN_ACCOUNT_LINKS,
  agency: AGENCY_ACCOUNT_LINKS,
  hotel: HOTEL_ACCOUNT_LINKS,
  b2b: B2B_ACCOUNT_LINKS,
};

/**
 * Returns navigation sections for a given persona.
 * Items already have resolved `to` paths (no pathByScope resolution needed).
 */
export function getPersonaNavSections(persona) {
  return PERSONA_NAV_MAP[persona] || ADMIN_SIDEBAR_SECTIONS;
}

/**
 * Returns account links for a given persona.
 */
export function getPersonaAccountLinks(persona) {
  return PERSONA_ACCOUNT_MAP[persona] || [];
}

// Re-export persona-specific sections for direct access (e.g., AdminAllModulesPage)
export { ADMIN_SIDEBAR_SECTIONS, ADMIN_ACCOUNT_LINKS };
export { AGENCY_SIDEBAR_SECTIONS, AGENCY_ACCOUNT_LINKS };
export { HOTEL_SIDEBAR_SECTIONS, HOTEL_ACCOUNT_LINKS };
export { B2B_SIDEBAR_SECTIONS, B2B_ACCOUNT_LINKS };
