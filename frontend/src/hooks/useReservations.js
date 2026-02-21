/**
 * React Query hooks for reservations data.
 *
 * Provides:
 * - useReservations: List reservations with pagination/filters
 * - useReservationDetail: Single reservation by ID
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

// Query keys namespace
export const reservationKeys = {
  all: ["reservations"],
  list: (filters) => [...reservationKeys.all, "list", filters],
  detail: (id) => [...reservationKeys.all, "detail", id],
};

export function useReservations(filters = {}, options = {}) {
  return useQuery({
    queryKey: reservationKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.status) params.set("status", filters.status);
      if (filters.search) params.set("search", filters.search);
      if (filters.page) params.set("page", String(filters.page));
      if (filters.page_size) params.set("page_size", String(filters.page_size));
      const { data } = await api.get(`/reservations?${params.toString()}`);
      return data;
    },
    staleTime: 30 * 1000, // 30 sec
    ...options,
  });
}

export function useReservationDetail(id, options = {}) {
  return useQuery({
    queryKey: reservationKeys.detail(id),
    queryFn: async () => {
      const { data } = await api.get(`/reservations/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: 30 * 1000,
    ...options,
  });
}
