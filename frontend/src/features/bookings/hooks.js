/**
 * Bookings feature — TanStack Query hooks.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { bookingsApi } from "./api";

export const reservationKeys = {
  all: ["reservations"],
  list: (filters) => [...reservationKeys.all, "list", filters],
  detail: (id) => [...reservationKeys.all, "detail", id],
};

export function useReservations(filters = {}, options = {}) {
  return useQuery({
    queryKey: reservationKeys.list(filters),
    queryFn: () => bookingsApi.list(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useReservationDetail(id, options = {}) {
  return useQuery({
    queryKey: reservationKeys.detail(id),
    queryFn: () => bookingsApi.detail(id),
    enabled: !!id,
    staleTime: 30_000,
    ...options,
  });
}

export function useCreateReservation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: bookingsApi.reserve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reservationKeys.all });
    },
  });
}

export function useConfirmBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => bookingsApi.confirm(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: reservationKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: reservationKeys.all });
    },
  });
}

export function useRejectBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }) => bookingsApi.reject(id, reason),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: reservationKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: reservationKeys.all });
    },
  });
}

export function useCancelBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => bookingsApi.cancel(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: reservationKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: reservationKeys.all });
    },
  });
}

// ─── Agency Bookings ───
export const agencyBookingKeys = {
  all: ["agency-bookings"],
  list: () => [...agencyBookingKeys.all, "list"],
};

export function useAgencyBookings(options = {}) {
  return useQuery({
    queryKey: agencyBookingKeys.list(),
    queryFn: bookingsApi.agencyList,
    staleTime: 30_000,
    ...options,
  });
}

// ─── Products ───
export const productKeys = {
  all: ["products"],
  list: (filters) => [...productKeys.all, "list", filters],
};

export function useProducts(filters = {}, options = {}) {
  return useQuery({
    queryKey: productKeys.list(filters),
    queryFn: () => bookingsApi.listProducts(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useDeleteProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: bookingsApi.deleteProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: productKeys.all });
    },
  });
}
