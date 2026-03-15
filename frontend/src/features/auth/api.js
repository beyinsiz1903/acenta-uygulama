/**
 * Auth feature — API layer.
 * All authentication-related API calls.
 */
import { api, apiPostWithNetworkFallback } from "../../lib/api";

export const authApi = {
  login: async ({ email, password, otp_code, tenant_id, tenant_slug }) => {
    const { data } = await apiPostWithNetworkFallback("/auth/login", {
      email,
      password,
      otp_code,
      tenant_id,
      tenant_slug,
    });
    return data;
  },

  logout: async () => {
    await api.post("/auth/logout");
  },

  revokeAllSessions: async () => {
    const { data } = await api.post("/auth/revoke-all-sessions");
    return data;
  },

  resetPassword: async ({ email }) => {
    const { data } = await api.post("/auth/reset-password", { email });
    return data;
  },
};
