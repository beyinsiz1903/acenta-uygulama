/**
 * Navigation Utilities — Persona resolver, filter helpers, path utils.
 *
 * Faz 3: Persona-Based Navigation Platform
 */
import { normalizeRoles } from "../../lib/roles";

/* ------------------------------------------------------------------ */
/*  Persona Resolver                                                    */
/* ------------------------------------------------------------------ */

/**
 * Resolves the active persona for a given user object.
 * Returns: "admin" | "agency" | "hotel"
 *
 * B2B users are handled by a separate layout (B2BLayout) and
 * never reach AppShell, so "b2b" is not returned here.
 */
export function resolvePersona(user) {
  const roles = normalizeRoles(user);

  if (
    roles.includes("super_admin") ||
    roles.includes("admin") ||
    roles.includes("sales") ||
    roles.includes("ops") ||
    roles.includes("accounting") ||
    roles.includes("b2b_agent")
  ) {
    return "admin";
  }

  if (roles.includes("agency_admin") || roles.includes("agency_agent")) {
    return "agency";
  }

  if (roles.includes("hotel_admin") || roles.includes("hotel_staff")) {
    return "hotel";
  }

  return "admin"; // fallback
}

/* ------------------------------------------------------------------ */
/*  Flat Item Collector (for Command Palette / Search)                  */
/* ------------------------------------------------------------------ */

/**
 * Collects all navigation items from sections into a flat array.
 * Includes all items regardless of visibleInSidebar flag.
 * Useful for command palette search.
 */
export function flattenNavItems(sections) {
  const items = [];
  for (const section of sections) {
    if (!section.items) continue;
    for (const item of section.items) {
      if (item.to) {
        items.push({ ...item, sectionGroup: section.group });
      }
    }
  }
  return items;
}

/* ------------------------------------------------------------------ */
/*  Sidebar Filter (respects visibleInSidebar)                          */
/* ------------------------------------------------------------------ */

/**
 * Filters items for sidebar display.
 * Items with visibleInSidebar === false are excluded.
 * This is a pre-filter; AppShell applies additional mode/feature filters.
 */
export function filterSidebarItems(items) {
  return items.filter((it) => it.visibleInSidebar !== false);
}
