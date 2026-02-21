/**
 * React Query hooks for tours data.
 *
 * Provides:
 * - useTours: List tours with search/filter/pagination
 * - useTourDetail: Single tour detail by ID
 * - useTourReservation: Mutation for creating a tour reservation
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

// Query keys namespace
export const tourKeys = {
  all: ["tours"],
  list: (filters) => [...tourKeys.all, "list", filters],
  detail: (id) => [...tourKeys.all, "detail", id],
};

export function useTours(filters = {}, options = {}) {
  return useQuery({
    queryKey: tourKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.q) params.set("q", filters.q);
      if (filters.destination) params.set("destination", filters.destination);
      if (filters.category) params.set("category", filters.category);
      if (filters.min_price) params.set("min_price", String(filters.min_price));
      if (filters.max_price) params.set("max_price", String(filters.max_price));
      if (filters.page) params.set("page", String(filters.page));
      if (filters.page_size) params.set("page_size", String(filters.page_size));
      const { data } = await api.get(`/tours?${params.toString()}`);
      return data;
    },
    staleTime: 2 * 60 * 1000, // 2 min
    ...options,
  });
}

export function useTourDetail(tourId, options = {}) {
  return useQuery({
    queryKey: tourKeys.detail(tourId),
    queryFn: async () => {
      const { data } = await api.get(`/tours/${tourId}`);
      return data;
    },
    enabled: !!tourId,
    staleTime: 5 * 60 * 1000, // 5 min
    ...options,
  });
}

export function useTourReservation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ tourId, payload }) => {
      const { data } = await api.post(`/tours/${tourId}/reserve`, payload);
      return data;
    },
    onSuccess: () => {
      // Invalidate tours list to refresh availability
      queryClient.invalidateQueries({ queryKey: tourKeys.all });
    },
  });
}
