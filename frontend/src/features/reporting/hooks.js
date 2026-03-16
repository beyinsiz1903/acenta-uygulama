/**
 * Reporting feature — TanStack Query hooks.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reportingApi } from "./api";

export const reportingKeys = {
  all: ["reporting"],
  schedules: () => [...reportingKeys.all, "schedules"],
};

export function useScheduledReports(options = {}) {
  return useQuery({
    queryKey: reportingKeys.schedules(),
    queryFn: reportingApi.getSchedules,
    staleTime: 30_000,
    select: (data) => data?.items || [],
    ...options,
  });
}

export function useCreateSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: reportingApi.createSchedule,
    onSuccess: () => qc.invalidateQueries({ queryKey: reportingKeys.schedules() }),
  });
}

export function useDeleteSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: reportingApi.deleteSchedule,
    onSuccess: () => qc.invalidateQueries({ queryKey: reportingKeys.schedules() }),
  });
}

export function useExecuteDueReports() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: reportingApi.executeDue,
    onSuccess: () => qc.invalidateQueries({ queryKey: reportingKeys.schedules() }),
  });
}
