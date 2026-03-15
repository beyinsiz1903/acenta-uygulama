/**
 * Governance feature — TanStack Query hooks.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { governanceApi } from "./api";

export const governanceKeys = {
  all: ["governance"],
  auditLogs: (filters) => [...governanceKeys.all, "audit-logs", filters],
  approvals: (filters) => [...governanceKeys.all, "approvals", filters],
  actionPolicies: () => [...governanceKeys.all, "action-policies"],
};

export function useAuditLogs(filters = {}, options = {}) {
  return useQuery({
    queryKey: governanceKeys.auditLogs(filters),
    queryFn: () => governanceApi.getAuditLogs(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useApprovals(filters = {}, options = {}) {
  return useQuery({
    queryKey: governanceKeys.approvals(filters),
    queryFn: () => governanceApi.getApprovals(filters),
    staleTime: 15_000,
    ...options,
  });
}

export function useApproveRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: governanceApi.approveRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: governanceKeys.all });
    },
  });
}

export function useRejectRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }) => governanceApi.rejectRequest(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: governanceKeys.all });
    },
  });
}
