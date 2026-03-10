import {
  clearToken,
  persistBootstrappedUser,
  persistRefreshSession,
} from "./authSession";

import {
  apiGetWithNetworkFallback,
  apiPostWithNetworkFallback,
  clearToken as clearApiToken,
} from "./api";

// keep backward compatibility: auth session cleanup from both modules
const clearAllTokens = () => {
  clearToken();
  clearApiToken();
};

export async function bootstrapAuthSession(client) {
  void client;
  try {
    const { data } = await apiGetWithNetworkFallback("/auth/me", {
      skipAuthRefresh: true,
      skipAuthRedirect: true,
    });
    return persistBootstrappedUser(data);
  } catch (err) {
    if (err?.response?.status !== 401) {
      throw err;
    }
  }

  try {
    const refreshResponse = await apiPostWithNetworkFallback("/auth/refresh", {}, {
      skipAuthRefresh: true,
      skipAuthRedirect: true,
    });
    persistRefreshSession(refreshResponse.data);

    const { data } = await apiGetWithNetworkFallback("/auth/me", {
      skipAuthRefresh: true,
      skipAuthRedirect: true,
    });
    return persistBootstrappedUser(data);
  } catch {
    clearAllTokens();
    return null;
  }
}