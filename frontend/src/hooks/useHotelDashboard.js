/**
 * React Query hook for Hotel Dashboard - Sprint 4
 *
 * Provides daily hotel operations data.
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export const hotelDashboardKeys = {
  all: ["hotel-dashboard"],
  today: () => [...hotelDashboardKeys.all, "today"],
};

export function useHotelToday(options = {}) {
  return useQuery({
    queryKey: hotelDashboardKeys.today(),
    queryFn: async () => {
      const { data } = await api.get("/dashboard/hotel-today");
      return data;
    },
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
    ...options,
  });
}
