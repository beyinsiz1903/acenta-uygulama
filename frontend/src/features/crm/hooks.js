/**
 * CRM feature — TanStack Query hooks.
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { crmApi } from "./api";

export const crmKeys = {
  all: ["crm"],
  customers: (filters) => [...crmKeys.all, "customers", filters],
  customerDetail: (id) => [...crmKeys.all, "customers", id],
  tasks: (filters) => [...crmKeys.all, "tasks", filters],
  events: (filters) => [...crmKeys.all, "events", filters],
  pipeline: () => [...crmKeys.all, "pipeline"],
  duplicates: () => [...crmKeys.all, "duplicates"],
};

export function useCustomers(filters = {}, options = {}) {
  return useQuery({
    queryKey: crmKeys.customers(filters),
    queryFn: () => crmApi.getCustomers(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useCustomerDetail(id, options = {}) {
  return useQuery({
    queryKey: crmKeys.customerDetail(id),
    queryFn: () => crmApi.getCustomerDetail(id),
    enabled: !!id,
    staleTime: 30_000,
    ...options,
  });
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: crmApi.createCustomer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: crmKeys.all });
    },
  });
}

export function useUpdateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }) => crmApi.updateCustomer(id, payload),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: crmKeys.customerDetail(id) });
      queryClient.invalidateQueries({ queryKey: crmKeys.all });
    },
  });
}

export function useCrmTasks(filters = {}, options = {}) {
  return useQuery({
    queryKey: crmKeys.tasks(filters),
    queryFn: () => crmApi.getTasks(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useCrmEvents(filters = {}, options = {}) {
  return useQuery({
    queryKey: crmKeys.events(filters),
    queryFn: () => crmApi.getEvents(filters),
    staleTime: 30_000,
    ...options,
  });
}

export function useCrmPipeline(options = {}) {
  return useQuery({
    queryKey: crmKeys.pipeline(),
    queryFn: crmApi.getPipeline,
    staleTime: 60_000,
    ...options,
  });
}
