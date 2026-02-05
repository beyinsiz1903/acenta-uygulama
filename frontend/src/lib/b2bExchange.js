import { api, apiErrorMessage } from "./api";

function wrapError(err) {
  return { message: apiErrorMessage(err), raw: err };
}

export async function fetchMyListings() {
  try {
    const res = await api.get("/b2b/listings/my");
    return res.data || [];
  } catch (err) {
    throw wrapError(err);
  }
}

export async function createListing(payload) {
  try {
    const res = await api.post("/b2b/listings", payload);
    return res.data;
  } catch (err) {
    throw wrapError(err);
  }
}

export async function updateListing(listingId, payload) {
  try {
    const res = await api.patch(`/b2b/listings/${listingId}`, payload);
    return res.data;
  } catch (err) {
    throw wrapError(err);
  }
}

export async function fetchAvailableListings() {
  try {
    const res = await api.get("/b2b/listings/available");
    return res.data || [];
  } catch (err) {
    throw wrapError(err);
  }
}

export async function createMatchRequest(payload) {
  try {
    const res = await api.post("/b2b/match-request", payload);
    return res.data;
  } catch (err) {
    throw wrapError(err);
  }
}

export async function fetchMyMatchRequests() {
  try {
    const res = await api.get("/b2b/match-request/my");
    return res.data || [];
  } catch (err) {
    throw wrapError(err);
  }
}

export async function fetchIncomingMatchRequests() {
  try {
    const res = await api.get("/b2b/match-request/incoming");
    return res.data || [];
  } catch (err) {
    throw wrapError(err);
  }
}

export async function approveMatchRequest(id) {
  try {
    const res = await api.patch(`/b2b/match-request/${id}/approve`);
    return res.data;
  } catch (err) {
    throw wrapError(err);
  }
}

export async function rejectMatchRequest(id) {
  try {
    const res = await api.patch(`/b2b/match-request/${id}/reject`);
    return res.data;
  } catch (err) {
    throw wrapError(err);
  }
}

export async function completeMatchRequest(id) {
  try {
    const res = await api.patch(`/b2b/match-request/${id}/complete`);
    return res.data;
  } catch (err) {
    throw wrapError(err);
  }
}
