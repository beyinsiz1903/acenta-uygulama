/**
 * Centralized query key registry.
 *
 * All TanStack Query keys are namespaced by feature domain.
 * Re-exports keys from each feature module for cross-feature cache invalidation.
 *
 * Usage:
 *   import { queryKeys } from "@/shared/queryKeys";
 *   queryClient.invalidateQueries({ queryKey: queryKeys.bookings.all });
 */
export { authKeys } from "../features/auth/hooks";
export { dashboardKeys } from "../features/dashboard/hooks";
export { reservationKeys } from "../features/bookings/hooks";
export { inventoryKeys } from "../features/inventory/hooks";
export { financeKeys } from "../features/finance/hooks";
export { crmKeys } from "../features/crm/hooks";
export { opsKeys } from "../features/operations/hooks";
export { analyticsKeys } from "../features/analytics/hooks";
export { governanceKeys } from "../features/governance/hooks";
