/**
 * Bookings feature — TanStack Query hooks.
 * Re-exports existing hooks + adds new mutations.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { bookingsApi } from "./api";

// Re-export existing hooks for backward compatibility
export {
  reservationKeys,
  useReservations,
  useReservationDetail,
} from "../../hooks/useReservations";

// Import keys for cache invalidation
import { reservationKeys } from "../../hooks/useReservations";

export function useCreateBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: bookingsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: reservationKeys.all });
    },
  });
}

export function useCancelBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }) => bookingsApi.cancel(id, reason),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: reservationKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: reservationKeys.all });
    },
  });
}

export function useUpdateBookingStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }) => bookingsApi.updateStatus(id, status),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: reservationKeys.detail(id) });
      const previous = queryClient.getQueryData(reservationKeys.detail(id));
      queryClient.setQueryData(reservationKeys.detail(id), (old) =>
        old ? { ...old, status } : old
      );
      return { previous };
    },
    onError: (_, { id }, context) => {
      if (context?.previous) {
        queryClient.setQueryData(reservationKeys.detail(id), context.previous);
      }
    },
    onSettled: (_, __, { id }) => {
      queryClient.invalidateQueries({ queryKey: reservationKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: reservationKeys.all });
    },
  });
}
