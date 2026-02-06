import { api, apiErrorMessage } from "./api";

export async function seedDemoData(body) {
  try {
    const res = await api.post("/admin/demo/seed", body);
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function getChecklist() {
  try {
    const res = await api.get("/activation/checklist");
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function completeChecklistItem(itemKey) {
  try {
    const res = await api.put(`/activation/checklist/${itemKey}/complete`);
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function createUpgradeRequest(body) {
  try {
    const res = await api.post("/upgrade-requests", body);
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function getTenantsHealth(filterType) {
  try {
    const params = filterType ? { filter_type: filterType } : {};
    const res = await api.get("/admin/tenants/health", { params });
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function getTrialStatus() {
  try {
    const res = await api.get("/onboarding/trial");
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function getPlans() {
  try {
    const res = await api.get("/onboarding/plans");
    return res.data;
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}
