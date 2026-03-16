/**
 * Refunds feature — TanStack Query hooks.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { refundsApi } from "./api";

export const refundKeys = {
  all: ["refunds"],
  list: (filters) => [...refundKeys.all, "list", filters],
  detail: (caseId) => [...refundKeys.all, "detail", caseId],
  financials: (bookingId) => [...refundKeys.all, "financials", bookingId],
  history: (bookingId) => [...refundKeys.all, "history", bookingId],
  documents: (caseId) => [...refundKeys.all, "documents", caseId],
  tasks: (caseId) => [...refundKeys.all, "tasks", caseId],
};

/* ─── Queries ─── */

export function useRefundList(filters = {}, options = {}) {
  return useQuery({
    queryKey: refundKeys.list(filters),
    queryFn: () => refundsApi.list(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useRefundDetail(caseId, options = {}) {
  return useQuery({
    queryKey: refundKeys.detail(caseId),
    queryFn: () => refundsApi.detail(caseId),
    enabled: !!caseId,
    staleTime: 15_000,
    ...options,
  });
}

export function useBookingFinancials(bookingId, options = {}) {
  return useQuery({
    queryKey: refundKeys.financials(bookingId),
    queryFn: () => refundsApi.bookingFinancials(bookingId),
    enabled: !!bookingId,
    staleTime: 30_000,
    ...options,
  });
}

export function useRefundHistory(bookingId, options = {}) {
  return useQuery({
    queryKey: refundKeys.history(bookingId),
    queryFn: () => refundsApi.bookingRefundHistory(bookingId),
    enabled: !!bookingId,
    staleTime: 30_000,
    ...options,
  });
}

export function useRefundDocuments(caseId, options = {}) {
  return useQuery({
    queryKey: refundKeys.documents(caseId),
    queryFn: () => refundsApi.listDocuments(caseId),
    enabled: !!caseId,
    staleTime: 15_000,
    ...options,
  });
}

export function useRefundTasks(caseId, options = {}) {
  return useQuery({
    queryKey: refundKeys.tasks(caseId),
    queryFn: () => refundsApi.listTasks(caseId),
    enabled: !!caseId,
    staleTime: 15_000,
    ...options,
  });
}

/* ─── Mutations ─── */

export function useApproveStep1() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, amount }) => refundsApi.approveStep1(caseId, amount),
    onSuccess: () => qc.invalidateQueries({ queryKey: refundKeys.all }),
  });
}

export function useApproveStep2() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, note }) => refundsApi.approveStep2(caseId, note),
    onSuccess: () => qc.invalidateQueries({ queryKey: refundKeys.all }),
  });
}

export function useRejectRefund() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, reason }) => refundsApi.reject(caseId, reason),
    onSuccess: () => qc.invalidateQueries({ queryKey: refundKeys.all }),
  });
}

export function useMarkPaid() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, paymentReference }) =>
      refundsApi.markPaid(caseId, paymentReference),
    onSuccess: () => qc.invalidateQueries({ queryKey: refundKeys.all }),
  });
}

export function useCloseRefund() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, note }) => refundsApi.close(caseId, note),
    onSuccess: () => qc.invalidateQueries({ queryKey: refundKeys.all }),
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, file, tag, note }) =>
      refundsApi.uploadDocument(caseId, { file, tag, note }),
    onSuccess: (_, { caseId }) =>
      qc.invalidateQueries({ queryKey: refundKeys.documents(caseId) }),
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId }) => refundsApi.deleteDocument(documentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: refundKeys.all }),
  });
}

export function useCreateRefundTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => refundsApi.createTask(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: refundKeys.all }),
  });
}

export function useUpdateRefundTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, patch }) => refundsApi.updateTask(taskId, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: refundKeys.all }),
  });
}
