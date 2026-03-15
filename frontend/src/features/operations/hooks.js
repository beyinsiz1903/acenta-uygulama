/**
 * Operations feature — TanStack Query hooks.
 */
import { useQuery } from "@tanstack/react-query";
import { operationsApi } from "./api";

export const opsKeys = {
  all: ["ops"],
  guestCases: (filters) => [...opsKeys.all, "guest-cases", filters],
  guestCaseDetail: (id) => [...opsKeys.all, "guest-cases", id],
  tasks: (filters) => [...opsKeys.all, "tasks", filters],
  incidents: (filters) => [...opsKeys.all, "incidents", filters],
  bookingDetail: (id) => [...opsKeys.all, "bookings", id],
};

export function useGuestCases(filters = {}, options = {}) {
  return useQuery({
    queryKey: opsKeys.guestCases(filters),
    queryFn: () => operationsApi.getGuestCases(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useOpsTasks(filters = {}, options = {}) {
  return useQuery({
    queryKey: opsKeys.tasks(filters),
    queryFn: () => operationsApi.getOpsTasks(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useOpsIncidents(filters = {}, options = {}) {
  return useQuery({
    queryKey: opsKeys.incidents(filters),
    queryFn: () => operationsApi.getIncidents(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useOpsBookingDetail(bookingId, options = {}) {
  return useQuery({
    queryKey: opsKeys.bookingDetail(bookingId),
    queryFn: () => operationsApi.getBookingDetail(bookingId),
    enabled: !!bookingId,
    staleTime: 30_000,
    ...options,
  });
}
