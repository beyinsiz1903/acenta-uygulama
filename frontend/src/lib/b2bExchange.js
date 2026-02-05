import { api } from "./api";

export async function fetchMyListings() {
  const res = await api.get("/b2b/listings/my");
  return res.data;
}

export async function createListing(payload) {
  const res = await api.post("/b2b/listings", payload);
  return res.data;
}

export async function updateListing(listingId, payload) {
  const res = await api.patch(`/b2b/listings/${listingId}`, payload);
  return res.data;
}

export async function fetchAvailableListings() {
  const res = await api.get("/b2b/listings/available");
  return res.data;
}

export async function createMatchRequest(payload) {
  const res = await api.post("/b2b/match-request", payload);
  return res.data;
}

export async function fetchMyMatchRequests() {
  const res = await api.get("/b2b/match-request/my");
  return res.data;
}

export async function fetchIncomingMatchRequests() {
  const res = await api.get("/b2b/match-request/incoming");
  return res.data;
}

export async function approveMatchRequest(id) {
  const res = await api.patch(`/b2b/match-request/${id}/approve`);
  return res.data;
}

export async function rejectMatchRequest(id) {
  const res = await api.patch(`/b2b/match-request/${id}/reject`);
  return res.data;
}

export async function completeMatchRequest(id) {
  const res = await api.patch(`/b2b/match-request/${id}/complete`);
  return res.data;
}
