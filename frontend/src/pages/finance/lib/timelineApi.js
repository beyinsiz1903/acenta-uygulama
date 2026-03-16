const API = process.env.REACT_APP_BACKEND_URL;

function authHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchTimeline({ skip = 0, limit = 50, entity_type, entity_id, actor, action } = {}) {
  const params = new URLSearchParams({ skip, limit });
  if (entity_type) params.set("entity_type", entity_type);
  if (entity_id) params.set("entity_id", entity_id);
  if (actor) params.set("actor", actor);
  if (action) params.set("action", action);
  const res = await fetch(`${API}/api/activity-timeline?${params}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Timeline fetch failed");
  return res.json();
}

export async function fetchTimelineStats() {
  const res = await fetch(`${API}/api/activity-timeline/stats`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Timeline stats fetch failed");
  return res.json();
}

export async function fetchEntityTimeline(entityType, entityId, limit = 50) {
  const res = await fetch(`${API}/api/activity-timeline/entity/${entityType}/${entityId}?limit=${limit}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Entity timeline fetch failed");
  return res.json();
}

export async function fetchConfigVersions(entityType, entityId, limit = 20) {
  const res = await fetch(`${API}/api/config-versions/${entityType}/${entityId}?limit=${limit}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Config versions fetch failed");
  return res.json();
}
