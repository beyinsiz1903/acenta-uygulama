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
