// frontend/src/lib/crm.js
import { api, apiErrorMessage } from "./api";

export async function listCustomers(params) {
  try {
    const res = await api.get("/crm/customers", { params });
    return res.data; // { items, total, page, page_size }
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function createCustomer(body) {
  try {
    const res = await api.post("/crm/customers", body);
    return res.data; // CustomerOut
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function getCustomer(id) {
  try {
    const res = await api.get(`/crm/customers/${id}`);
    return res.data; // CustomerDetailOut
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function patchCustomer(id, body) {
  try {
    const res = await api.patch(`/crm/customers/${id}`, body);
    return res.data; // CustomerOut
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function listTasks(params) {
  try {
    const res = await api.get("/crm/tasks", { params });
    return res.data; // { items, total, page, page_size }
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function createTask(body) {
  try {
    const res = await api.post("/crm/tasks", body);
    return res.data; // TaskOut
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function patchTask(id, body) {
  try {
    const res = await api.patch(`/crm/tasks/${id}`, body);
    return res.data; // TaskOut
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function listDeals(params) {
  try {
    const res = await api.get("/crm/deals", { params });
    return res.data; // { items, total, page, page_size }
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function createDeal(body) {
  try {
    const res = await api.post("/crm/deals", body);
    return res.data; // DealOut
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function patchDeal(id, body) {
  try {
    const res = await api.patch(`/crm/deals/${id}`, body);
    return res.data; // DealOut
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function listActivities(params) {
  try {
    const res = await api.get("/crm/activities", { params });
    return res.data; // { items, total, page, page_size }
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function createActivity(body) {
  try {
    const res = await api.post("/crm/activities", body);
    return res.data; // ActivityOut
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}


export async function listCustomerDuplicates() {
  try {
    const res = await api.get("/crm/customers/duplicates");
    return res.data; // DuplicateCustomerClusterOut[]
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}

export async function mergeCustomers({ primaryId, duplicateIds, dryRun = false }) {
  try {
    const payload = {
      primary_id: primaryId,
      duplicate_ids: duplicateIds,
      dry_run: dryRun,
    };
    const res = await api.post("/crm/customers/merge", payload);
    return res.data; // CustomerMergeResultOut
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}


export async function listCrmEvents(params) {
  try {
    const res = await api.get("/crm/events", { params });
    return res.data; // { items, total, page, page_size }
  } catch (err) {
    throw { message: apiErrorMessage(err), raw: err };
  }
}
