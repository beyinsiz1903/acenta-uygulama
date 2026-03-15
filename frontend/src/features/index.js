/**
 * Features directory index.
 *
 * Domain-driven frontend architecture:
 * Each feature module owns its API layer, hooks, components, and pages.
 *
 * Dependency rules:
 *   features/X → design-system/  OK
 *   features/X → shared/         OK
 *   features/X → features/Y      FORBIDDEN
 */
export const FEATURE_DOMAINS = [
  "auth",
  "dashboard",
  "bookings",
  "inventory",
  "finance",
  "crm",
  "operations",
  "b2b",
  "admin",
  "analytics",
  "governance",
];
