/**
 * React Query hooks for authentication.
 *
 * Provides:
 * - useCurrentUser: Get current user data
 * - useLogin: Mutation for login
 * - useLogout: Mutation for logout (with JWT revocation)
 * - useRevokeAllSessions: Mutation for revoking all sessions
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, clearToken } from "../lib/api";
import { bootstrapAuthSession } from "../lib/cookieAuthCompat";
import { persistLoginSession } from "../lib/authSession";

// Query keys namespace
export const authKeys = {
  all: ["auth"],
  user: () => [...authKeys.all, "user"],
};

export function useCurrentUser(options = {}) {
  return useQuery({
    queryKey: authKeys.user(),
    queryFn: async () => bootstrapAuthSession(api),
    enabled: options.enabled ?? true,
    staleTime: 5 * 60 * 1000, // 5 min
    retry: false,
    ...options,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ email, password, otp_code, tenant_id, tenant_slug }) => {
      const { data } = await api.post("/auth/login", { email, password, otp_code, tenant_id, tenant_slug });
      return data;
    },
    onSuccess: (data) => {
      if (data?.user) {
        persistLoginSession(data);
        queryClient.setQueryData(authKeys.user(), data.user);
      }
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      try {
        await api.post("/auth/logout");
      } catch {
        // Even if the server call fails, clear local state
      }
    },
    onSettled: () => {
      clearToken();
      queryClient.clear(); // Clear all cached data
    },
  });
}

export function useRevokeAllSessions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/auth/revoke-all-sessions");
      return data;
    },
    onSuccess: () => {
      clearToken();
      queryClient.clear();
    },
  });
}
