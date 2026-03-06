import {
  clearToken,
  persistBootstrappedUser,
  persistRefreshSession,
} from "./authSession";

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

  try {
    const refreshResponse = await client.post("/auth/refresh", {}, {
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