import {
  clearToken,
  getRefreshToken,
  hasStoredSessionCandidate,
  persistBootstrappedUser,
  persistRefreshSession,
} from "./authSession";

export function buildCompatRefreshPayload() {
  const refreshToken = getRefreshToken();
  return refreshToken ? { refresh_token: refreshToken } : {};
}

export async function bootstrapAuthSession(client) {
  try {
    const { data } = await client.get("/auth/me", {
      skipAuthRefresh: true,
      skipAuthRedirect: true,
    });
    return persistBootstrappedUser(data);
  } catch (err) {
    if (err?.response?.status !== 401) {
      throw err;
    }
  }

  if (!hasStoredSessionCandidate()) {
    clearToken();
    return null;
  }

  try {
    const refreshResponse = await client.post("/auth/refresh", buildCompatRefreshPayload(), {
      skipAuthRefresh: true,
      skipAuthRedirect: true,
    });
    persistRefreshSession(refreshResponse.data);

    const { data } = await client.get("/auth/me", {
      skipAuthRefresh: true,
      skipAuthRedirect: true,
    });
    return persistBootstrappedUser(data);
  } catch {
    clearToken();
    return null;
  }
}