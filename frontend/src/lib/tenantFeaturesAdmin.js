import { api, apiErrorMessage } from "./api";

export async function fetchTenantList(search) {
  const params = {};
  if (search) params.search = search;
  const res = await api.get("/admin/tenants", { params });
  return res.data;
}

export async function fetchTenantFeaturesAdmin(tenantId) {
  const res = await api.get(`/admin/tenants/${tenantId}/features`);
  return res.data;
}

export async function updateTenantFeaturesAdmin(tenantId, features) {
  const res = await api.patch(`/admin/tenants/${tenantId}/features`, { features });
  return res.data;
}
