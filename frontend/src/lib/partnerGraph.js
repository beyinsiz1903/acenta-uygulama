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
