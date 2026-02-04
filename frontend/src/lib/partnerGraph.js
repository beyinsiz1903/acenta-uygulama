import { api, apiErrorMessage } from "./api";

export async function fetchPartnerInbox() {
  try {
    const res = await api.get("/partner-graph/inbox");
    return res.data || {};
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function fetchPartnerNotificationsSummary() {
  try {
    const res = await api.get("/partner-graph/notifications/summary");
    return res.data || {};
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function acceptPartnerRelationship(id) {
  try {
    const res = await api.post(`/partner-graph/relationships/${id}/accept`);
    return res.data || {};
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function activatePartnerRelationship(id) {
  try {
    const res = await api.post(`/partner-graph/relationships/${id}/activate`);
    return res.data || {};
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function searchTenants(q) {
  try {
    const res = await api.get("/partner-graph/discovery/search", { params: { q } });
    return res.data || [];
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function invitePartnerBySlug(buyerTenantSlug, note) {
  try {
    const payload = { buyer_tenant_slug: buyerTenantSlug };
    if (note && note.trim()) {
      payload.note = note.trim();
    }
    const res = await api.post("/partner-graph/invite", payload);
    return res.data || {};
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function fetchRelationships(params) {
  const { statuses, role = "any", limit = 50, cursor } = params || {};

  const query = new URLSearchParams();
  if (Array.isArray(statuses) && statuses.length > 0) {
    query.set("status", statuses.join(","));
  }
  if (role) query.set("role", role);
  if (limit) query.set("limit", String(limit));
  if (cursor) query.set("cursor", cursor);

  try {
    const res = await api.get(`/partner-graph/relationships?${query.toString()}`);
    return res.data || { items: [], next_cursor: null };
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}
