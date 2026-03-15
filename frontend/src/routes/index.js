/**
 * Route module index.
 *
 * All domain-specific route definitions are split into separate files
 * for maintainability and code ownership.
 */
export { publicRoutes } from "./publicRoutes";
export { adminRoutes } from "./adminRoutes";
export { coreRoutes, b2bPortalRoute } from "./coreRoutes";
export { agencyRoutes } from "./agencyRoutes";
export { hotelRoutes } from "./hotelRoutes";
export { b2bRoutes } from "./b2bRoutes";
